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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join("logs", f"album_tagging_{timestamp}.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(html_content)
    print(f"HTML file 'mp3_tags.html' generated successfully and log saved to '{log_file_path}'.")


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


def write_log(log_entries, operation):
    """
    Writes log entries to a timestamped log file in the 'logs' directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join("logs", f"{operation}_{timestamp}.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(log_entries))
    print(f"{operation.capitalize()} operation completed. Log saved to '{log_file_path}'.")


def set_artist_tag(directory, artist_name, recursive):
    """
    Sets the 'Artist' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
                from mutagen.id3 import ID3
                id3 = ID3()
                id3.save(file_path)
                audio = EasyID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        audio['artist'] = artist_name
        audio.save(file_path)
        entries.append(f"Set artist tag for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "artist_tagging")


def set_album_tag(directory, album_name, recursive):
    """
    Sets the 'Album' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
                from mutagen.id3 import ID3
                id3 = ID3()
                id3.save(file_path)
                audio = EasyID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        audio['album'] = album_name
        audio.save(file_path)
        entries.append(f"Set album tag for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "album_tagging")


def set_genre_tag(directory, genre_name, recursive):
    """
    Sets the 'Genre' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
                from mutagen.id3 import ID3
                id3 = ID3()
                id3.save(file_path)
                audio = EasyID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        audio['genre'] = genre_name
        audio.save(file_path)
        entries.append(f"Set genre tag for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "genre_tagging")


def set_rating_tag(directory, rating, recursive):
    """
    Sets a user-defined rating (1-5) for .mp3 files using the POPM frame.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    from mutagen.id3 import POPM
    log_entries = []
    # Map 1-5 stars to 0-255 scale (commonly used by players)
    rating_map = {1: 1, 2: 64, 3: 128, 4: 196, 5: 255}
    popm_rating = rating_map.get(rating, 0)

    def process_file(file_path, entries):
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            try:
                audio = ID3()
                audio.add_tags()
                audio.save(file_path)
                audio = ID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        # Set POPM frame (email, rating, play count)
        audio.delall('POPM')
        audio.add(POPM(email='user@example.com', rating=popm_rating, count=0))
        audio.save(file_path)
        entries.append(f"Set rating {rating} for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "rating_tagging")


def set_cover_art(directory, image_path, recursive):
    """
    Embeds cover art (JPG/PNG) into .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    from mutagen.id3 import APIC, error
    log_entries = []
    # Determine image mime type
    ext = os.path.splitext(image_path)[1].lower()
    if ext == '.jpg' or ext == '.jpeg':
        mime = 'image/jpeg'
    elif ext == '.png':
        mime = 'image/png'
    else:
        print("Unsupported image format. Use JPG or PNG.")
        return
    try:
        with open(image_path, 'rb') as img_in:
            img_data = img_in.read()
    except Exception as e:
        print(f"Failed to read image file: {e}")
        return

    def process_file(file_path, entries):
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            try:
                audio = ID3()
                audio.add_tags()
                audio.save(file_path)
                audio = ID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        audio.delall('APIC')
        audio.add(APIC(
            encoding=3,  # UTF-8
            mime=mime,
            type=3,  # Cover (front)
            desc='Cover',
            data=img_data
        ))
        audio.save(file_path)
        entries.append(f"Embedded cover art for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "coverart_tagging")


def set_year_tag(directory, year_value, recursive):
    """
    Sets the 'Year' tag for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Logs each file processed or skipped.
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
                from mutagen.id3 import ID3
                id3 = ID3()
                id3.save(file_path)
                audio = EasyID3(file_path)
            except Exception as e:
                entries.append(f"Skipping file {file_path}: {e}")
                return
        audio['date'] = year_value
        audio.save(file_path)
        entries.append(f"Set year tag to {year_value} for {file_path}")

    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.mp3'):
                    file_path = os.path.join(root, file)
                    process_file(file_path, log_entries)
    else:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                process_file(file_path, log_entries)
    write_log(log_entries, "year_tagging")


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

    # If no arguments are provided (other than the script name itself), print help and exit.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

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
        set_album_tag(folder, args.album, args.recursive)
    if args.artist:
        set_artist_tag(folder, args.artist, args.recursive)
    if args.genre:
        set_genre_tag(folder, args.genre, args.recursive)
    if args.rating:
        set_rating_tag(folder, args.rating, args.recursive)
    if args.cover_art:
        set_cover_art(folder, args.cover_art, args.recursive)
    if args.year:
        set_year_tag(folder, args.year, args.recursive)


if __name__ == "__main__":
    main()


