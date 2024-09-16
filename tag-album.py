import os
import sys
import argparse
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from prettytable import PrettyTable
from yattag import Doc

def show_folder_tags_in_pretty_HTML(directory):
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
    with open('mp3_tags.html', 'w') as f:
        f.write(html_content)
    print("HTML file 'mp3_tags.html' generated successfully.")
def show_folder_tags(directory):
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

def set_artist_tag(directory, artist_name):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = EasyID3(file_path)
                except ID3NoHeaderError:
                    audio = ID3(file_path)
                    audio.add_tags()
                    audio = EasyID3(file_path)
                audio['artist'] = artist_name
                audio.save()
                print(f"Set artist tag for {file_path}")
                
def set_album_tag(directory, album_name):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    audio = EasyID3(file_path)
                except ID3NoHeaderError:
                    audio = ID3(file_path)
                    audio.add_tags()
                    audio = EasyID3(file_path)
                audio['album'] = album_name
                audio.save()
                print(f"Set album tag for {file_path}")

def main():
    parser = argparse.ArgumentParser(description='Set the "Album" and "Artist" tags of all the .mp3 files in a folder.')
    parser.add_argument('-f', '--folder', type=str, default=os.getcwd(), help='Folder containing .mp3 files')
    parser.add_argument('-a', '--album', type=str, help='Album name to set')
    parser.add_argument('-r', '--artist', type=str, help='Artist name to set')
    parser.add_argument('--show', action='store_true', help='Show tags of all .mp3 files in the folder')
    parser.add_argument('--html', action='store_true', help='Save tags of all .mp3 files in the folder as HTML')

    args = parser.parse_args()
    
    if args.show and args.html:
        show_folder_tags_in_pretty_HTML(args.folder)
    elif args.show:
        show_folder_tags(args.folder)
    if args.album:
        set_album_tag(args.folder, args.album)
    if args.artist:
        set_artist_tag(args.folder, args.artist)

if __name__ == "__main__":
    main()


