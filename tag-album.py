# tag-album.py
# This script allows users to view and set 'Artist' and 'Album' tags for all .mp3 files in a specified folder.
# It can display tags in the terminal or generate an HTML report, and logs all operations.

import os
import sys
import argparse
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from prettytable import PrettyTable
from yattag import Doc
import datetime


def show_folder_tags_in_pretty_HTML(directory):
    """
    Generates an HTML file displaying the Artist and Album tags of all .mp3 files in the given directory.
    Also saves the HTML content to a timestamped log file in the 'logs' directory.
    """
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
                # Walk through the directory and process each .mp3 file
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith('.mp3'):
                            file_path = os.path.join(root, file)
                            try:
                                audio = EasyID3(file_path)
                                artist = audio.get('artist', ['Unknown'])[0]
                                album = audio.get('album', ['Unknown'])[0]
                            except ID3NoHeaderError:
                                artist = 'Unknown'
                                album = 'Unknown'
                            with tag('tr'):
                                with tag('td'):
                                    text(file_path)
                                with tag('td'):
                                    text(artist)
                                with tag('td'):
                                    text(album)
    html_content = doc.getvalue()
    # Write HTML output to file (overwrites if exists)
    with open('mp3_tags.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Save the HTML content to a timestamped log file for auditing
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join("logs", f"album_tagging_{timestamp}.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(html_content)

    print(f"HTML file 'mp3_tags.html' generated successfully and log saved to '{log_file_path}'.")


def show_folder_tags(directory):
    """
    Prints a table of Artist and Album tags for all .mp3 files in the given directory.
    """
    table = PrettyTable()
    table.field_names = ["File Path", "Artist", "Album"]

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = EasyID3(file_path)
                    artist = audio.get('artist', ['Unknown'])[0]
                    album = audio.get('album', ['Unknown'])[0]
                except ID3NoHeaderError:
                    artist = 'Unknown'
                    album = 'Unknown'
                table.add_row([file_path, artist, album])

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


def set_artist_tag(directory, artist_name):
    """
    Sets the 'Artist' tag for all .mp3 files in the given directory.
    Logs each file processed or skipped.
    """
    log_entries = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = EasyID3(file_path)
                except ID3NoHeaderError:
                    try:
                        audio = ID3(file_path)
                        audio.add_tags()
                        audio.save()
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['artist'] = artist_name
                audio.save()
                log_entries.append(f"Set artist tag for {file_path}")
    write_log(log_entries, "artist_tagging")


def set_album_tag(directory, album_name):
    """
    Sets the 'Album' tag for all .mp3 files in the given directory.
    Logs each file processed or skipped.
    """
    log_entries = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = EasyID3(file_path)
                except ID3NoHeaderError:
                    try:
                        audio = ID3(file_path)
                        audio.add_tags()
                        audio.save()
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['album'] = album_name
                audio.save()
                log_entries.append(f"Set album tag for {file_path}")
    write_log(log_entries, "album_tagging")


def main():
    """
    Parses command-line arguments and executes the requested operations.
    """
    parser = argparse.ArgumentParser(description='Set the "Album" and "Artist" tags of all the .mp3 files in a folder.')
    parser.add_argument('-f', '--folder', type=str, default=os.getcwd(), help='Folder containing .mp3 files')
    parser.add_argument('-a', '--album', type=str, help='Album name to set')
    parser.add_argument('-r', '--artist', type=str, help='Artist name to set')
    parser.add_argument('--show', action='store_true', help='Show tags of all .mp3 files in the folder')
    parser.add_argument('--html', action='store_true', help='Save tags of all .mp3 files in the folder as HTML')

    args = parser.parse_args()

    # Security: Ensure the folder path is absolute and normalized
    folder = os.path.abspath(os.path.normpath(args.folder))

    if args.show and args.html:
        show_folder_tags_in_pretty_HTML(folder)
    elif args.show:
        show_folder_tags(folder)
    if args.album:
        set_album_tag(folder, args.album)
    if args.artist:
        set_artist_tag(folder, args.artist)


if __name__ == "__main__":
    main()


