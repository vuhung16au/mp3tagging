import os
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, POPM, APIC, TIT2 # Added TIT2 for title
from .utils import write_log # Import write_log from utils module

# Helper function to handle ID3 header creation consistently
def _ensure_id3_header(file_path, entries):
    try:
        audio = EasyID3(file_path)
        return audio
    except ID3NoHeaderError:
        try:
            id3 = ID3()
            # id3.add_tags() # This might not be necessary if EasyID3 can handle it after save.
            id3.save(file_path)
            entries.append(f"Info: Created basic ID3 header for {os.path.basename(file_path)}")
            return EasyID3(file_path) # Now it should be readable
        except Exception as e:
            entries.append(f"Skipping file {os.path.basename(file_path)}: Could not create ID3 header: {e}")
            return None
    except Exception as e: # Other errors reading the file
        entries.append(f"Skipping file {os.path.basename(file_path)}: Error reading tags: {e}")
        return None

def _ensure_id3_header_for_id3_object(file_path, entries):
    try:
        audio = ID3(file_path)
        return audio
    except ID3NoHeaderError:
        try:
            id3 = ID3()
            id3.save(file_path) # Create file with basic ID3 structure
            entries.append(f"Info: Created basic ID3 header for {os.path.basename(file_path)}")
            return ID3(file_path) # Re-open
        except Exception as e:
            entries.append(f"Skipping file {os.path.basename(file_path)}: Could not create ID3 header for ID3 object: {e}")
            return None
    except Exception as e:
        entries.append(f"Skipping file {os.path.basename(file_path)}: Error reading tags with ID3: {e}")
        return None


def set_title_tag(path_or_target, title_name, recursive=False, log_entries_list=None):
    """
    Sets the 'Title' tag for .mp3 files.
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target


    def process_file(file_path, entries):
        audio = _ensure_id3_header(file_path, entries)
        if audio is None:
            return

        # audio['title'] = title_name # Using EasyID3 'title' key
        # For TIT2, it's better to use the ID3 object directly if there are issues with EasyID3 mapping
        try:
            # Re-open with ID3 to ensure TIT2 frame is handled correctly
            audio_id3 = ID3(file_path)
        except ID3NoHeaderError: # Should have been created by _ensure_id3_header, but as a fallback
            audio_id3 = ID3()
        except Exception as e:
            entries.append(f"Skipping file {os.path.basename(file_path)}: Error re-opening with ID3: {e}")
            return

        audio_id3.delall('TIT2') # Remove existing title frame
        audio_id3.add(TIT2(encoding=3, text=title_name)) # Add new title frame
        try:
            audio_id3.save(file_path)
            entries.append(f"Set title tag to '{title_name}' for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving title tag for {os.path.basename(file_path)}: {e}")


    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None: # Only write log if this function is the entry point
        write_log(current_log_entries, "title_tagging")


def set_artist_tag(path_or_target, value, recursive=False, log_entries_list=None):
    """
    Sets the 'Artist' tag for .mp3 files.
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    def process_file(file_path, entries):
        audio = _ensure_id3_header(file_path, entries)
        if audio is None:
            return
        audio['artist'] = value
        try:
            audio.save(file_path)
            entries.append(f"Set artist tag to '{value}' for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving artist tag for {os.path.basename(file_path)}: {e}")


    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None:
        write_log(current_log_entries, "artist_tagging")


def set_album_tag(path_or_target, value, recursive=False, log_entries_list=None):
    """
    Sets the 'Album' tag for .mp3 files.
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    def process_file(file_path, entries):
        audio = _ensure_id3_header(file_path, entries)
        if audio is None:
            return
        audio['album'] = value
        try:
            audio.save(file_path)
            entries.append(f"Set album tag to '{value}' for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving album tag for {os.path.basename(file_path)}: {e}")

    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None:
        write_log(current_log_entries, "album_tagging")


def set_genre_tag(path_or_target, value, recursive=False, log_entries_list=None):
    """
    Sets the 'Genre' tag for .mp3 files.
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    def process_file(file_path, entries):
        audio = _ensure_id3_header(file_path, entries)
        if audio is None:
            return
        audio['genre'] = value
        try:
            audio.save(file_path)
            entries.append(f"Set genre tag to '{value}' for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving genre tag for {os.path.basename(file_path)}: {e}")

    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None:
        write_log(current_log_entries, "genre_tagging")


def set_rating_tag(path_or_target, value, recursive=False, log_entries_list=None):
    """
    Sets a user-defined rating (1-5) for .mp3 files using the POPM frame.
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    rating_map = {1: 1, 2: 64, 3: 128, 4: 196, 5: 255}
    popm_rating = rating_map.get(value, 0) # value is the rating here

    def process_file(file_path, entries):
        audio = _ensure_id3_header_for_id3_object(file_path, entries)
        if audio is None:
            return
        audio.delall('POPM')
        audio.add(POPM(email='user@example.com', rating=popm_rating, count=0)) # Using popm_rating based on input 'value'
        try:
            audio.save(file_path)
            entries.append(f"Set rating to {value} for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving rating for {os.path.basename(file_path)}: {e}")

    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None:
        write_log(current_log_entries, "rating_tagging")


def set_cover_art(path_or_target, image_path_or_data, recursive=False, log_entries_list=None): # Renamed to match, but parameter is image_path
    """
    Embeds cover art (JPG/PNG) into .mp3 files.
    Can process a single file or a directory. image_path_or_data is path to image for now.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    # This part needs to be outside process_file if image_path_or_data is a path
    # If it were image_data, it could be passed directly to process_file.
    # For now, assume image_path_or_data is a file path.
    if not isinstance(image_path_or_data, str) or not os.path.exists(image_path_or_data):
        msg = f"Cover art path '{image_path_or_data}' is invalid or not a string."
        current_log_entries.append(msg)
        if log_entries_list is None: print(msg) # Print if standalone
        if log_entries_list is None: write_log(current_log_entries, "coverart_tagging_error")
        return

    ext = os.path.splitext(image_path_or_data)[1].lower()
    if ext == '.jpg' or ext == '.jpeg':
        mime = 'image/jpeg'
    elif ext == '.png':
        mime = 'image/png'
    else:
        msg = f"Unsupported image format for {image_path_or_data}. Use JPG or PNG."
        current_log_entries.append(msg)
        if log_entries_list is None: print(msg)
        if log_entries_list is None: write_log(current_log_entries, "coverart_tagging_error")
        return

    try:
        with open(image_path_or_data, 'rb') as img_in:
            img_data = img_in.read()
    except Exception as e:
        msg = f"Failed to read image file {image_path_or_data}: {e}"
        current_log_entries.append(msg)
        if log_entries_list is None: print(msg)
        if log_entries_list is None: write_log(current_log_entries, "coverart_tagging_error")
        return

    def process_file(file_path, entries):
        audio = _ensure_id3_header_for_id3_object(file_path, entries)
        if audio is None:
            return

        audio.delall('APIC')
        audio.add(APIC(
            encoding=3,
            mime=mime, # mime determined outside
            type=3,
            desc='Cover',
            data=img_data # img_data read outside
        ))
        try:
            audio.save(file_path)
            entries.append(f"Embedded cover art from {os.path.basename(image_path_or_data)} into {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving cover art for {os.path.basename(file_path)}: {e}")


    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file for cover art: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory for cover art.")

    if log_entries_list is None:
        write_log(current_log_entries, "coverart_tagging")


def set_year_tag(path_or_target, value, recursive=False, log_entries_list=None):
    """
    Sets the 'Year' tag for .mp3 files (using 'date' key in EasyID3).
    Can process a single file or a directory.
    """
    current_log_entries = log_entries_list if log_entries_list is not None else []
    file_name_for_log = os.path.basename(path_or_target) if os.path.isfile(path_or_target) else path_or_target

    def process_file(file_path, entries):
        audio = _ensure_id3_header(file_path, entries)
        if audio is None:
            return
        audio['date'] = str(value) # Ensure year is string for EasyID3 'date'
        try:
            audio.save(file_path)
            entries.append(f"Set year tag to '{value}' for {os.path.basename(file_path)}")
        except Exception as e:
            entries.append(f"Error saving year tag for {os.path.basename(file_path)}: {e}")

    if os.path.isfile(path_or_target):
        if path_or_target.lower().endswith('.mp3'):
            process_file(path_or_target, current_log_entries)
        else:
            current_log_entries.append(f"Skipping non-MP3 file: {file_name_for_log}")
    elif os.path.isdir(path_or_target):
        if recursive:
            for root, _, files in os.walk(path_or_target):
                for file_name in files:
                    if file_name.lower().endswith('.mp3'):
                        file_path_full = os.path.join(root, file_name)
                        process_file(file_path_full, current_log_entries)
        else:
            for file_name in os.listdir(path_or_target):
                file_path_full = os.path.join(path_or_target, file_name)
                if os.path.isfile(file_path_full) and file_name.lower().endswith('.mp3'):
                    process_file(file_path_full, current_log_entries)
    else:
        current_log_entries.append(f"Error: Path {path_or_target} is not a valid file or directory.")

    if log_entries_list is None:
        write_log(current_log_entries, "year_tagging")
