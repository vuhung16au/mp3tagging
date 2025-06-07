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
import musicbrainzngs
import requests # For fetching cover art
from mutagen.id3 import APIC, TALB, TPE1, TPE2, TRCK, TYER, USLT # Added specific ID3 frames

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


def fetch_metadata_from_musicbrainz(file_path, log_entries_list):
    """
    Fetches metadata from MusicBrainz for a given MP3 file and updates its ID3 tags.

    Args:
        file_path (str): The path to the MP3 file.
        log_entries_list (list): A list to append log messages to.
    """
    try:
        audio = EasyID3(file_path)
    except ID3NoHeaderError:
        log_entries_list.append(f"Skipping {file_path}: No ID3 header found to read artist/album.")
        return
    except Exception as e:
        log_entries_list.append(f"Skipping {file_path}: Error reading initial tags: {e}")
        return

    artist = audio.get('artist', [None])[0]
    album = audio.get('album', [None])[0]

    if not artist or not album:
        log_entries_list.append(f"Skipping {file_path}: Artist or Album tag not found.")
        return

    log_entries_list.append(f"Processing {file_path}: Artist='{artist}', Album='{album}'")

    # Configure musicbrainzngs (replace with your app details)
    musicbrainzngs.set_useragent("tag-album-script", "0.1", "http://example.com/tag-album-script")

    try:
        # Search for the release
        # Note: 'release' is preferred over 'album' for MusicBrainz terminology for actual album releases
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=5)

        if not result['release-list']:
            log_entries_list.append(f"No results found on MusicBrainz for {artist} - {album} in {file_path}.")
            return

        # Assume the first result is the best match for now
        # More sophisticated matching could be added here (e.g., checking track count, year)
        release = result['release-list'][0]
        release_id = release['id']
        log_entries_list.append(f"Found release: {release['title']} ({release_id}) with score {release['ext:score']}%")

        # Get detailed release information, including recordings (tracks) and artist credits
        # Include 'artist-credits' for album artist, 'media' for track count, 'recordings' for track details
        release_details = musicbrainzngs.get_release_by_id(release_id, includes=["artist-credits", "media", "recordings", "release-groups"])

        # --- Update ID3 Tags ---
        audio_id3 = ID3(file_path) # Load with full ID3 object for more complex tags

        # Album Artist (TPE2)
        if release_details['release']['artist-credit']:
            album_artist_name = release_details['release']['artist-credit-string']
            audio_id3.delall('TPE2') # Remove existing album artist
            audio_id3.add(TPE2(encoding=3, text=album_artist_name))
            log_entries_list.append(f"Set Album Artist to: {album_artist_name}")
            # Also update EasyID3 view if possible, though 'albumartist' is standard
            try:
                easy_audio = EasyID3(file_path)
                easy_audio['albumartist'] = album_artist_name
                easy_audio.save()
            except Exception as e:
                log_entries_list.append(f"Note: Could not set 'albumartist' via EasyID3: {e}")


        # Track Number / Total Tracks (TRCK)
        # This requires matching the specific file to a track in the release
        # For simplicity, if it's a single file, we won't try to match it to a specific track number from album
        # If the release has media and tracks:
        if release_details['release']['medium-list'] and release_details['release']['medium-list'][0]['track-list']:
            total_tracks = str(release_details['release']['medium-list'][0]['track-count'])
            # Attempt to find the current track's title in the release to get its number
            # This is a simplified matching logic.
            current_track_title = audio.get('title', [None])[0]
            track_number_str = ""

            if current_track_title:
                for track_info in release_details['release']['medium-list'][0]['track-list']:
                    if track_info['recording']['title'].lower() == current_track_title.lower():
                        track_number_str = str(track_info['number'])
                        break

            if track_number_str:
                track_tag_text = f"{track_number_str}/{total_tracks}"
            else: # Fallback if specific track not matched or no title
                track_tag_text = f"1/{total_tracks}" # Default to 1 if not found or single file

            audio_id3.delall('TRCK')
            audio_id3.add(TRCK(encoding=3, text=track_tag_text))
            log_entries_list.append(f"Set Track Number/Total to: {track_tag_text}")

        # Year (TYER / TDRC in ID3 v2.4)
        # EasyID3 uses 'date' which maps to TDRC or TYER depending on version/format.
        # MusicBrainz provides 'date' like "YYYY-MM-DD" or "YYYY".
        if release_details['release'].get('date'):
            year = release_details['release']['date'].split('-')[0]
            audio['date'] = year # Using EasyID3 for simplicity here
            audio.save() # Save EasyID3 changes
            # For ID3 object directly:
            # audio_id3.delall('TYER')
            # audio_id3.add(TYER(encoding=3, text=year))
            log_entries_list.append(f"Set Year to: {year}")

        # Cover Art (APIC)
        try:
            # Get cover art from Cover Art Archive
            art_info = musicbrainzngs.get_release_group_image_list(release['release-group']['id'])
            if art_info and art_info['images']:
                # Prioritize front cover
                front_cover_url = None
                for img in art_info['images']:
                    if 'Front' in img['types'] and img.get('approved'):
                        front_cover_url = img['thumbnails']['large'] # or 'image' for full size
                        break
                if not front_cover_url and art_info['images'][0].get('approved'): # Fallback to first approved image
                     front_cover_url = art_info['images'][0]['thumbnails']['large']

                if front_cover_url:
                    log_entries_list.append(f"Fetching cover art from: {front_cover_url}")
                    response = requests.get(front_cover_url, timeout=10)
                    response.raise_for_status() # Raise an exception for bad status codes

                    # Determine mime type from URL or response headers if necessary
                    mime_type = 'image/jpeg' # Default, CAA usually provides JPEG
                    if '.png' in front_cover_url:
                        mime_type = 'image/png'

                    audio_id3.delall('APIC')
                    audio_id3.add(APIC(
                        encoding=3, # UTF-8
                        mime=mime_type,
                        type=3, # Cover (front)
                        desc='Cover',
                        data=response.content
                    ))
                    log_entries_list.append(f"Successfully embedded cover art from {front_cover_url}")
                else:
                    log_entries_list.append("No approved front cover art found on MusicBrainz.")
            else:
                log_entries_list.append("No cover art found on MusicBrainz for this release group.")
        except requests.exceptions.RequestException as e:
            log_entries_list.append(f"Error fetching cover art: {e}")
        except musicbrainzngs.WebServiceError as e:
            log_entries_list.append(f"MusicBrainz error fetching cover art: {e}")
        except Exception as e:
            log_entries_list.append(f"An unexpected error occurred during cover art processing: {e}")

        audio_id3.save(v2_version=3) # Save changes using ID3 object, ensure v2.3 for compatibility
        log_entries_list.append(f"Successfully updated tags for {file_path} from MusicBrainz.")

    except musicbrainzngs.WebServiceError as exc:
        log_entries_list.append(f"MusicBrainz API error for {file_path}: {exc}")
    except requests.exceptions.RequestException as exc:
        log_entries_list.append(f"Network error for {file_path} (e.g., fetching cover art): {exc}")
    except Exception as e:
        log_entries_list.append(f"An unexpected error occurred while processing {file_path}: {e}")


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
    parser.add_argument('--fetch-metadata', action='store_true', help='Fetch metadata from MusicBrainz for .mp3 files in the folder.')
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
        args.year is not None,
        args.fetch_metadata
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

    if args.fetch_metadata:
        log_entries = []
        files_processed_count = 0
        if args.recursive:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        file_path = os.path.join(root, file)
                        fetch_metadata_from_musicbrainz(file_path, log_entries)
                        files_processed_count +=1
        else:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                    fetch_metadata_from_musicbrainz(file_path, log_entries)
                    files_processed_count += 1

        if files_processed_count > 0:
            write_log(log_entries, "metadata_fetching")
        else:
            print("No MP3 files found to fetch metadata for.")


if __name__ == "__main__":
    main()


