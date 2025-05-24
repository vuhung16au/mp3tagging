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
    Generates an HTML file displaying the Artist, Album, Genre, and Rating tags of all .mp3 files in the given directory.
    Also saves the HTML content to a timestamped log file in the 'logs' directory.
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
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith('.mp3'):
                            file_path = os.path.join(root, file)
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
                            with tag('tr'):
                                with tag('td'):
                                    text(file_path)
                                with tag('td'):
                                    text(artist)
                                with tag('td'):
                                    text(album)
                                with tag('td'):
                                    text(genre)
                                with tag('td'):
                                    text(rating)
                                with tag('td'):
                                    text(year)
    html_content = doc.getvalue()
    with open('mp3_tags.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join("logs", f"album_tagging_{timestamp}.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(html_content)
    print(f"HTML file 'mp3_tags.html' generated successfully and log saved to '{log_file_path}'.")


def show_folder_tags(directory):
    """
    Prints a table of Artist, Album, Genre, and Rating tags for all .mp3 files in the given directory.
    """
    from mutagen.id3 import POPM
    table = PrettyTable()
    table.field_names = ["File Path", "Artist", "Album", "Genre", "Rating", "Year"]
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
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
                table.add_row([file_path, artist, album, genre, rating, year])
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
                        from mutagen.id3 import ID3
                        id3 = ID3()
                        id3.save(file_path)
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['artist'] = artist_name
                audio.save(file_path)
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
                        from mutagen.id3 import ID3
                        id3 = ID3()
                        id3.save(file_path)
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['album'] = album_name
                audio.save(file_path)
                log_entries.append(f"Set album tag for {file_path}")
    write_log(log_entries, "album_tagging")


def set_genre_tag(directory, genre_name):
    """
    Sets the 'Genre' tag for all .mp3 files in the given directory.
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
                        from mutagen.id3 import ID3
                        id3 = ID3()
                        id3.save(file_path)
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['genre'] = genre_name
                audio.save(file_path)
                log_entries.append(f"Set genre tag for {file_path}")
    write_log(log_entries, "genre_tagging")


def set_rating_tag(directory, rating):
    """
    Sets a user-defined rating (1-5) for all .mp3 files in the given directory.
    Uses the POPM (Popularimeter) frame for rating.
    Logs each file processed or skipped.
    """
    from mutagen.id3 import POPM
    log_entries = []
    # Map 1-5 stars to 0-255 scale (commonly used by players)
    rating_map = {1: 1, 2: 64, 3: 128, 4: 196, 5: 255}
    popm_rating = rating_map.get(rating, 0)
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = ID3(file_path)
                except ID3NoHeaderError:
                    try:
                        audio = ID3()
                        audio.add_tags()
                        audio.save(file_path)
                        audio = ID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                # Set POPM frame (email, rating, play count)
                audio.delall('POPM')
                audio.add(POPM(email='user@example.com', rating=popm_rating, count=0))
                audio.save(file_path)
                log_entries.append(f"Set rating {rating} for {file_path}")
    write_log(log_entries, "rating_tagging")


def set_cover_art(directory, image_path):
    """
    Embeds a cover art image (JPG/PNG) into all .mp3 files in the given directory.
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
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = ID3(file_path)
                except ID3NoHeaderError:
                    try:
                        audio = ID3()
                        audio.add_tags()
                        audio.save(file_path)
                        audio = ID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio.delall('APIC')
                audio.add(APIC(
                    encoding=3,  # UTF-8
                    mime=mime,
                    type=3,  # Cover (front)
                    desc='Cover',
                    data=img_data
                ))
                audio.save(file_path)
                log_entries.append(f"Embedded cover art for {file_path}")
    write_log(log_entries, "coverart_tagging")


def set_year_tag(directory, year_value):
    """
    Sets the 'Year' tag for all .mp3 files in the given directory.
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
                        from mutagen.id3 import ID3
                        id3 = ID3()
                        id3.save(file_path)
                        audio = EasyID3(file_path)
                    except Exception as e:
                        log_entries.append(f"Skipping file {file_path}: {e}")
                        continue
                audio['date'] = year_value
                audio.save(file_path)
                log_entries.append(f"Set year tag to {year_value} for {file_path}")
    write_log(log_entries, "year_tagging")


def main():
    """
    Parses command-line arguments and executes the requested operations.
    """
    parser = argparse.ArgumentParser(description='Set the "Album", "Artist", "Genre", "Rating", and Cover Art tags of all the .mp3 files in a folder.')
    parser.add_argument('-f', '--folder', type=str, default=os.getcwd(), help='Folder containing .mp3 files')
    parser.add_argument('-a', '--album', type=str, help='Album name to set')
    parser.add_argument('-r', '--artist', type=str, help='Artist name to set')
    parser.add_argument('-g', '--genre', type=str, help='Genre to set')
    parser.add_argument('--rating', type=int, choices=range(1,6), help='Rating to set (1-5)')
    parser.add_argument('--cover-art', type=str, help='Path to cover art image (JPG or PNG)')
    parser.add_argument('-y', '--year', type=str, help='Year to set (e.g., 2023)')
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
    if args.genre:
        set_genre_tag(folder, args.genre)
    if args.rating:
        set_rating_tag(folder, args.rating)
    if args.cover_art:
        set_cover_art(folder, args.cover_art)
    if args.year:
        set_year_tag(folder, args.year)


if __name__ == "__main__":
    main()


