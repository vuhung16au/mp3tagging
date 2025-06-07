# tag-album.py
# This script allows users to view and set 'Artist', 'Album', 'Genre', 'Rating', 'Year', and cover art tags
# for .mp3 files. By default, it processes files only in the specified folder.
# Use the -R or --recursive flag to process files in subdirectories as well.
# It can display tags in the terminal or generate an HTML report, and logs all operations.

import os
import sys
import argparse
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError # APIC, TALB, TPE1, TPE2, TRCK, TYER, USLT are imported in submodules
from prettytable import PrettyTable # Imported in display module, but might be needed if main script uses it directly elsewhere (currently not)
from yattag import Doc # Imported in display module
import datetime # Imported in utils module
import musicbrainzngs # Imported in fetch_metadata module
import requests # Imported in fetch_metadata module

from tag_album_utils.display import show_folder_tags_in_pretty_HTML, show_folder_tags
from tag_album_utils.set_tags import set_artist_tag, set_album_tag, set_genre_tag, set_rating_tag, set_cover_art, set_year_tag
from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
from tag_album_utils.utils import write_log
from tag_album_utils.fetch_metadata import fetch_metadata_from_acoustid

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
    parser.add_argument('--fetch-and-set-acoustid-tags', action='store_true', help='Fetch tags from AcoustID and set them.')
    parser.add_argument('--fields', type=str, help='Comma-separated list of fields to fetch from AcoustID (e.g., "title,artist,album,genre"). Required if --fetch-and-set-acoustid-tags is used.')
    parser.add_argument('-R', '--recursive', action='store_true', help='Recursively process .mp3 files in subdirectories. If not set, only files in the specified folder are processed.')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    action_or_tag_specified = any([
        args.show,
        args.html,
        args.album is not None,
        args.artist is not None,
        args.genre is not None,
        args.rating is not None,
        args.cover_art is not None,
        args.year is not None,
        args.fetch_metadata,
        args.fetch_and_set_acoustid_tags
    ])

    if not action_or_tag_specified:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.fetch_and_set_acoustid_tags and not args.fields:
        print("Error: --fields is required when --fetch-and-set-acoustid-tags is used.")
        sys.exit(1)

    folder = os.path.abspath(os.path.normpath(args.folder))

    if args.show and args.html: # This implies --html is an enhancement to --show
        show_folder_tags_in_pretty_HTML(folder, args.recursive)
    elif args.show:
        show_folder_tags(folder, args.recursive)
    elif args.html: # Handle if --html is called without --show (generate HTML directly)
        show_folder_tags_in_pretty_HTML(folder, args.recursive)


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
                for file_name in files: # Renamed 'file' to 'file_name' to avoid conflict
                    if file_name.lower().endswith('.mp3'):
                        file_path = os.path.join(root, file_name)
                        fetch_metadata_from_musicbrainz(file_path, log_entries)
                        files_processed_count +=1
        else:
            for file_name in os.listdir(folder): # Renamed 'file' to 'file_name'
                file_path = os.path.join(folder, file_name)
                if os.path.isfile(file_path) and file_name.lower().endswith('.mp3'):
                    fetch_metadata_from_musicbrainz(file_path, log_entries)
                    files_processed_count += 1

        if files_processed_count > 0:
            write_log(log_entries, "metadata_fetching") # write_log is imported
        else:
            print("No MP3 files found to fetch metadata for.")

    if args.fetch_and_set_acoustid_tags:
        log_entries = []
        files_processed_count = 0
        acoustid_api_key = "MDCUvH3Ppp"
        requested_fields_list = [field.strip() for field in args.fields.split(',')]

        if args.recursive:
            for root, _, files in os.walk(folder):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path = os.path.join(root, file_name)
                        status = fetch_metadata_from_acoustid(file_path, acoustid_api_key, requested_fields_list, log_entries)
                        if status == "FPCLAC_NOT_FOUND":
                            print(f"Error: The 'fpcalc' utility is required for AcoustID tagging but was not found or is not executable. Please install libchromaprint-tools (or equivalent for your OS) and ensure 'fpcalc' is in your system's PATH.", file=sys.stderr)
                            print("Aborting AcoustID tagging.", file=sys.stderr)
                            sys.exit(1)
                        # elif status == "FPCLAC_ERROR":
                        #     print(f"Error: Failed to execute 'fpcalc' for file: {file_path}. See log for details.", file=sys.stderr)
                        files_processed_count += 1
        else:
            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)
                if os.path.isfile(file_path) and file_name.lower().endswith('.mp3'):
                    status = fetch_metadata_from_acoustid(file_path, acoustid_api_key, requested_fields_list, log_entries)
                    if status == "FPCLAC_NOT_FOUND":
                        print(f"Error: The 'fpcalc' utility is required for AcoustID tagging but was not found or is not executable. Please install libchromaprint-tools (or equivalent for your OS) and ensure 'fpcalc' is in your system's PATH.", file=sys.stderr)
                        print("Aborting AcoustID tagging.", file=sys.stderr)
                        sys.exit(1)
                    # elif status == "FPCLAC_ERROR":
                    #     print(f"Error: Failed to execute 'fpcalc' for file: {file_path}. See log for details.", file=sys.stderr)
                    files_processed_count += 1

        if files_processed_count > 0:
            write_log(log_entries, "acoustid_fetching")
        else:
            print("No MP3 files found for AcoustID processing.")


if __name__ == "__main__":
    main()
