# tag-album.py
# This script allows users to view and set 'Artist', 'Album', 'Genre', 'Rating', 'Year', and cover art tags
# for .mp3 files. By default, it processes files only in the specified folder.
# Use the -R or --recursive flag to process files in subdirectories as well.
# It can display tags in the terminal or generate an HTML report, and logs all operations.

import os
import sys
import argparse
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from prettytable import PrettyTable
from yattag import Doc
import datetime
import logging


def show_folder_tags_in_pretty_HTML(directory, recursive):
    """
    Generates an HTML file displaying tags of .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Saves HTML content to a timestamped log file.
    """
    from mutagen.id3 import POPM
    doc, tag, text = Doc().tagtext()
    with tag('html'):
        with tag('head'):
            with tag('title'):
                text('MP3 Tags')
            with tag('style'):
                text("""
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                table, th, td {
                    border: 1px solid black;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: #f2f2f2;
                }
                """)
        with tag('body'):
            with tag('h2'):
                text('MP3 Tags')
            with tag('table'):
                with tag('tr'):
                    with tag('th'):
                        text('File Path')
                    with tag('th'):
                        text('Artist')
                    with tag('th'):
                        text('Album')
                    with tag('th'):
                        text('Genre')
                    with tag('th'):
                        text('Rating')
                    with tag('th'):
                        text('Year')

                def process_file(file_path, doc_tag, doc_text):
                    try:
                        try:
                            audio = EasyID3(file_path)
                            artist = audio.get('artist', ['Unknown'])[0]
                            album = audio.get('album', ['Unknown'])[0]
                            genre = audio.get('genre', ['Unknown'])[0]
                            year = audio.get('date', ['Unknown'])[0]
                        except ID3NoHeaderError:
                            artist = 'Unknown'
                            album = 'Unknown'
                            genre = 'Unknown'
                            year = 'Unknown'
                        # Get rating from POPM frame
                        try:
                            id3 = ID3(file_path)
                            popms = id3.getall('POPM')
                            if popms:
                                rating_val = popms[0].rating
                                # Map 0-255 to 1-5 stars
                                if rating_val >= 196:
                                    rating = '5'
                                elif rating_val >= 128:
                                    rating = '4'
                                elif rating_val >= 64:
                                    rating = '3'
                                elif rating_val >= 1:
                                    rating = '2'
                                else:
                                    rating = '1'
                            else:
                                rating = 'Unknown'
                        except Exception:
                            rating = 'Unknown'
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
                        artist = 'Error'
                        album = 'Error'
                        genre = 'Error'
                        year = 'Error'
                        rating = 'Error'
                    with doc_tag('tr'):
                        with doc_tag('td'):
                            doc_text(file_path)
                        with doc_tag('td'):
                            doc_text(artist)
                        with doc_tag('td'):
                            doc_text(album)
                        with doc_tag('td'):
                            doc_text(genre)
                        with doc_tag('td'):
                            doc_text(rating)
                        with doc_tag('td'):
                            doc_text(year)

                if recursive:
                    for root, _, files in os.walk(directory):
                        for file in files:
                            if file.lower().endswith('.mp3'):
                                file_path = os.path.join(root, file)
                                process_file(file_path, tag, text)
                else:
                    for file in os.listdir(directory):
                        file_path = os.path.join(directory, file)
                        if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                            process_file(file_path, tag, text)

    html_content = doc.getvalue()
    with open('mp3_tags.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"HTML file 'mp3_tags.html' generated successfully.")


def show_folder_tags(directory, recursive):
    """
    Prints a table of tags for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    """
    from mutagen.id3 import POPM
    table = PrettyTable()
    table.field_names = ["File Path", "Artist", "Album", "Genre", "Rating", "Year"]

    def process_file(file_path, tbl):
        try:
            try:
                audio = EasyID3(file_path)
                artist = audio.get('artist', ['Unknown'])[0]
                album = audio.get('album', ['Unknown'])[0]
                genre = audio.get('genre', ['Unknown'])[0]
                year = audio.get('date', ['Unknown'])[0]
            except ID3NoHeaderError:
                artist = 'Unknown'
                album = 'Unknown'
                genre = 'Unknown'
                year = 'Unknown'
            # Get rating from POPM frame
            try:
                id3 = ID3(file_path)
                popms = id3.getall('POPM')
                if popms:
                    rating_val = popms[0].rating
                    if rating_val >= 196:
                        rating = '5'
                    elif rating_val >= 128:
                        rating = '4'
                    elif rating_val >= 64:
                        rating = '3'
                    elif rating_val >= 1:
                        rating = '2'
                    else:
                        rating = '1'
                else:
                    rating = 'Unknown'
            except Exception:
                rating = 'Unknown'
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            artist = 'Error'
            album = 'Error'
            genre = 'Error'
            year = 'Error'
            rating = 'Error'
        tbl.add_row([file_path, artist, album, genre, rating, year])

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, table)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, table)
    print(table)


def _iterate_files(directory, recursive, process_file_callback, operation_name, logger):
    """
    Iterates over .mp3 files in a directory (recursively or not) and applies a callback.
    Counts successes and failures and logs a summary.
    """
    processed_count = 0
    error_count = 0

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    if process_file_callback(file_path):
                        processed_count += 1
                    else:
                        error_count += 1
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                if process_file_callback(file_path):
                    processed_count += 1
                else:
                    error_count += 1
    logger.info(f"Finished {operation_name} operation. Processed {processed_count} files, {error_count} errors.")


def set_artist_tag(directory, artist_name, recursive, logger):
    """
    Sets the 'Artist' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    def _handle_set_artist(file_path_for_action):
        try:
            audio = EasyID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                # Attempt to create tags if they don't exist
                id3 = ID3()
                id3.save(file_path_for_action)
                audio = EasyID3(file_path_for_action) # Re-load after creating
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False
        
        audio['artist'] = artist_name
        try:
            audio.save()
            logger.info(f"Set artist tag for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving artist tag for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_artist, "artist tagging", logger)


def set_album_tag(directory, album_name, recursive, logger):
    """
    Sets the 'Album' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    def _handle_set_album(file_path_for_action):
        try:
            audio = EasyID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                id3 = ID3()
                id3.save(file_path_for_action)
                audio = EasyID3(file_path_for_action)
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False
        
        audio['album'] = album_name
        try:
            audio.save()
            logger.info(f"Set album tag for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving album tag for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_album, "album tagging", logger)


def set_genre_tag(directory, genre_name, recursive, logger):
    """
    Sets the 'Genre' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    def _handle_set_genre(file_path_for_action):
        try:
            audio = EasyID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                id3 = ID3()
                id3.save(file_path_for_action)
                audio = EasyID3(file_path_for_action)
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False

        audio['genre'] = genre_name
        try:
            audio.save()
            logger.info(f"Set genre tag for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving genre tag for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_genre, "genre tagging", logger)


def set_rating_tag(directory, rating, recursive, logger):
    """
    Sets a user-defined rating (1-5) for .mp3 files using the POPM frame.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    from mutagen.id3 import POPM
    # Map 1-5 stars to 0-255 scale (commonly used by players)
    rating_map = {1: 1, 2: 64, 3: 128, 4: 196, 5: 255}
    popm_rating_value = rating_map.get(rating, 0)

    def _handle_set_rating(file_path_for_action):
        try:
            audio = ID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                audio = ID3()
                audio.add_tags() # Ensure tags are created before saving
                audio.save(file_path_for_action)
                audio = ID3(file_path_for_action) # Re-load after creating
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False
        
        audio.delall('POPM')
        audio.add(POPM(email='user@example.com', rating=popm_rating_value, count=0))
        try:
            audio.save()
            logger.info(f"Set rating {rating} for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving rating for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_rating, "rating tagging", logger)


def set_cover_art(directory, image_path, recursive, logger):
    """
    Embeds cover art (JPG/PNG) into .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    from mutagen.id3 import APIC, error
    # Determine image mime type
    ext = os.path.splitext(image_path)[1].lower()
    if ext == '.jpg' or ext == '.jpeg':
        mime = 'image/jpeg'
    elif ext == '.png':
        mime = 'image/png'
    else:
        logger.error("Unsupported image format. Use JPG or PNG.")
        return
    try:
        with open(image_path, 'rb') as img_in:
            img_data = img_in.read()
    except Exception as e:
        logger.error(f"Failed to read image file: {e}")
        return

    def _handle_set_cover_art(file_path_for_action):
        try:
            audio = ID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                audio = ID3()
                audio.add_tags() # Ensure tags are created
                audio.save(file_path_for_action)
                audio = ID3(file_path_for_action) # Re-load
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False
        
        audio.delall('APIC')
        audio.add(APIC(
            encoding=3,  # UTF-8
            mime=mime,
            type=3,  # Cover (front)
            desc='Cover',
            data=img_data
        ))
        try:
            audio.save()
            logger.info(f"Embedded cover art for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving cover art for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_cover_art, "cover art tagging", logger)


def set_year_tag(directory, year_value, recursive, logger):
    """
    Sets the 'Year' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    def _handle_set_year(file_path_for_action):
        try:
            audio = EasyID3(file_path_for_action)
        except ID3NoHeaderError:
            try:
                id3 = ID3()
                id3.save(file_path_for_action)
                audio = EasyID3(file_path_for_action)
            except Exception as e:
                logger.error(f"Error initializing tags for {file_path_for_action}: {e}")
                return False
        except Exception as e:
            logger.error(f"Error loading audio for {file_path_for_action}: {e}")
            return False
        
        audio['date'] = year_value
        try:
            audio.save()
            logger.info(f"Set year tag to {year_value} for {file_path_for_action}")
            return True
        except Exception as e:
            logger.error(f"Error saving year tag for {file_path_for_action}: {e}")
            return False

    _iterate_files(directory, recursive, _handle_set_year, "year tagging", logger)


def main():
    """
    Parses command-line arguments and executes the requested operations.
    """
    epilog_text = """
Usage examples:
  Show tags:
    python3 tag_album.py --folder /path/to/music --show
  Set album and artist:
    python3 tag_album.py --folder /path/to/music --artist "Artist Name" --album "Album Name"
  Set cover art:
    python3 tag_album.py --folder /path/to/music --cover-art /path/to/image.jpg
  Use recursive option:
    python3 tag_album.py --folder /path/to/music --artist "New Artist" -R
"""
    parser = argparse.ArgumentParser(
        description='View or set ID3 tags (Album, Artist, Genre, Rating, Year, Cover Art) for .mp3 files in a specified folder.',
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-f', '--folder', type=str, default=os.getcwd(), help='Directory containing .mp3 files. Defaults to the current working directory.')
    parser.add_argument('-a', '--album', type=str, help='Album name to set for all .mp3 files.')
    parser.add_argument('-r', '--artist', type=str, help='Artist name to set for all .mp3 files.')
    parser.add_argument('-g', '--genre', type=str, help='Genre to set for all .mp3 files.')
    parser.add_argument('--rating', type=int, choices=range(1,6), help='Rating to set (1-5 stars) for all .mp3 files.')
    parser.add_argument('--cover-art', type=str, help='Path to an image file (JPG or PNG) to embed as cover art.')
    parser.add_argument('-y', '--year', type=str, help='Year to set (e.g., "2023") for all .mp3 files.')
    parser.add_argument('--show', action='store_true', help='Display current ID3 tags of .mp3 files in a table format in the terminal.')
    parser.add_argument('--html', action='store_true', help='Generate an HTML file ("mp3_tags.html") displaying current ID3 tags.')
    parser.add_argument('-R', '--recursive', action='store_true', help='Recursively process .mp3 files in subdirectories. If not set, only files in the specified folder are processed.')

    args = parser.parse_args()

    # Setup logging
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # File handler
    fh = logging.FileHandler('mp3tagging.log')
    fh.setLevel(logging.DEBUG)
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("Logging configured.") # Added for testability

    # If no arguments are provided (other than the script name itself), print help and exit.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Determine if any action (show, html) or tag-setting operation was specified by the user.
    # We don't consider --folder or --recursive as actions themselves for this check,
    # as they only modify how other actions behave.
    action_or_tag_specified = any([
        args.show,
        args.html,
        args.album is not None,
        args.artist is not None,
        args.genre is not None,
        args.rating is not None,
        args.cover_art is not None,
        args.year is not None
    ])

    # If no action or tag setting was specified (e.g., "python tag_album.py --folder /some/path"),
    # print help and exit.
    if not action_or_tag_specified:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Security: Ensure the folder path is absolute and normalized
    folder = os.path.abspath(os.path.normpath(args.folder))

    if args.show and args.html:
        show_folder_tags_in_pretty_HTML(folder, args.recursive)
    elif args.show:
        show_folder_tags(folder, args.recursive)

    # Proceed with tag setting if any are specified
    if args.album:
        set_album_tag(folder, args.album, args.recursive, logger)
    if args.artist:
        set_artist_tag(folder, args.artist, args.recursive, logger)
    if args.genre:
        set_genre_tag(folder, args.genre, args.recursive, logger)
    if args.rating:
        set_rating_tag(folder, args.rating, args.recursive, logger)
    if args.cover_art:
        set_cover_art(folder, args.cover_art, args.recursive, logger)
    if args.year:
        set_year_tag(folder, args.year, args.recursive, logger)


if __name__ == "__main__":
    # logger needs to be accessible globally for all functions
    logger = None
    main()


