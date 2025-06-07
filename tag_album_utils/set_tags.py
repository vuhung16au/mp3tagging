import os
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, POPM, APIC
from .utils import write_log # Import write_log from utils module

def set_artist_tag(directory, artist_name, recursive):
    """
    Sets the 'Artist' tag for .mp3 files.
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
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
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
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
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
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
    """
    log_entries = []
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
    """
    log_entries = []
    ext = os.path.splitext(image_path)[1].lower()
    if ext == '.jpg' or ext == '.jpeg':
        mime = 'image/jpeg'
    elif ext == '.png':
        mime = 'image/png'
    else:
        log_entries.append(f"Unsupported image format for {image_path}. Use JPG or PNG.")
        # Print to console as well, as this is a user-facing issue
        print(f"Unsupported image format for {image_path}. Use JPG or PNG.")
        if log_entries: write_log(log_entries, "coverart_tagging_error")
        return
    try:
        with open(image_path, 'rb') as img_in:
            img_data = img_in.read()
    except Exception as e:
        log_entries.append(f"Failed to read image file {image_path}: {e}")
        print(f"Failed to read image file {image_path}: {e}")
        if log_entries: write_log(log_entries, "coverart_tagging_error")
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
            encoding=3,
            mime=mime,
            type=3,
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
    """
    log_entries = []

    def process_file(file_path, entries):
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            try:
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
