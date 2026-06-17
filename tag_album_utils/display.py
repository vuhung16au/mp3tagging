import os
import datetime
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from prettytable import PrettyTable
from yattag import Doc

def show_folder_tags_in_pretty_HTML(directory, recursive):
    """
    Generates an HTML file displaying tags of .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    Saves HTML content to a timestamped log file.
    """
    from mutagen.id3 import POPM # Keep this import local as it's specific
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
                        # Compute a display-friendly path prefixing with '/app' for container consistency
                        display_path = file_path
                        cwd = os.getcwd()
                        if display_path.startswith(cwd):
                            # Convert absolute path to a container-like path
                            rel_path = os.path.relpath(display_path, cwd)
                            display_path = os.path.join('/app', rel_path)
                        with doc_tag('td'):
                            doc_text(display_path)
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
    # Note: Logging is handled by the main script, so file writing here might be redundant
    # or needs to be coordinated. For now, keeping the HTML generation part.
    with open('mp3_tags.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Path for logs should ideally be configurable or passed in
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"album_tagging_{timestamp}.html.log") # Changed extension to avoid confusion
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(html_content)
    print(f"HTML file 'mp3_tags.html' generated successfully and HTML log saved to '{log_file_path}'.")


def show_folder_tags(directory, recursive):
    """
    Prints a table of tags for .mp3 files.
    Processes files in the given directory. If 'recursive' is True, also processes subdirectories.
    """
    from mutagen.id3 import POPM # Keep this import local as it's specific
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
