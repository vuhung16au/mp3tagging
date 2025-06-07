import musicbrainzngs
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TPE2, TRCK, TYER, TCON # Added TYER, TCON for Genre
# Removed EasyID3NotLoadedError as it's not standard


def fetch_metadata_from_musicbrainz(file_path, log_entries_list, fields_to_fetch=None):
    """
    Fetches metadata from MusicBrainz for a given MP3 file and updates its ID3 tags.

    Args:
        file_path (str): The path to the MP3 file.
        log_entries_list (list): A list to append log messages to.
        fields_to_fetch (list, optional): A list of specific fields to fetch (e.g., ['artist', 'album', 'genre', 'year', 'coverart', 'tracknumber', 'albumartist']).
                                         If None or empty, fetches all relevant fields.
    """
    # Normalize fields_to_fetch for easier checking
    if fields_to_fetch:
        normalized_fields = [field.lower().strip() for field in fields_to_fetch]
    else:
        normalized_fields = [] # Indicates fetch all

    def should_process_field(field_name):
        if not normalized_fields: # If list is empty, means fetch all
            return True
        return field_name.lower() in normalized_fields

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
    # Consider making app name, version, and contact configurable or passed in
    musicbrainzngs.set_useragent("tag-album-script", "0.1", "http://example.com/tag-album-script")

    try:
        # Search for the release
        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=5)

        if not result['release-list']:
            log_entries_list.append(f"No results found on MusicBrainz for {artist} - {album} in {file_path}.")
            return

        release = result['release-list'][0]
        release_id = release['id']
        log_entries_list.append(f"Found release: {release['title']} ({release_id}) with score {release['ext:score']}%")

        # Determine necessary includes for get_release_by_id
        mb_includes = ["artist-credits", "release-groups"] # Basic includes
        if should_process_field('tracknumber') or should_process_field('year') or should_process_field('genre'): # year can be in release group or media
            mb_includes.extend(["media", "recordings"])
        if should_process_field('genre'):
            mb_includes.extend(["genres", "tags"]) # For genre information from release group

        release_details = musicbrainzngs.get_release_by_id(release_id, includes=list(set(mb_includes)))

        # Update Artist (TPE1) if requested - Note: MB search is by artist, so this is more like confirming/standardizing
        if should_process_field('artist'):
            if release_details['release']['artist-credit']:
                new_artist_name = release_details['release']['artist-credit-string'] # This is often Album Artist
                # For track artist, one might need to iterate through recordings if different
                # For simplicity, using release artist as the primary artist tag TPE1
                audio['artist'] = new_artist_name # Using EasyID3 object
                log_entries_list.append(f"Set Artist to: {new_artist_name}")


        # Update Album (TALB) if requested - Similar to artist, search is by album.
        if should_process_field('album'):
            new_album_name = release_details['release']['title']
            audio['album'] = new_album_name # Using EasyID3 object
            log_entries_list.append(f"Set Album to: {new_album_name}")

        # Save changes made by EasyID3 for artist/album before proceeding with ID3 object
        # This save is for any changes made to the 'audio' (EasyID3) object, like artist/album
        made_easyid3_changes = False
        if should_process_field('artist') and release_details['release']['artist-credit']:
            # This check was already there, added made_easyid3_changes flag
            made_easyid3_changes = True
        if should_process_field('album'):
            # This check was already there, added made_easyid3_changes flag
            made_easyid3_changes = True

        if made_easyid3_changes:
            try:
                audio.save()
                log_entries_list.append(f"Saved artist/album changes via EasyID3 for {file_path}.")
            # Removed EasyID3NotLoadedError specific catch block
            except Exception as e:
                log_entries_list.append(f"Error saving artist/album changes via EasyID3 for {file_path}: {e}")

        # Load full ID3 object for manipulation AFTER EasyID3 saves (if any)
        audio_id3 = ID3(file_path)

        if should_process_field('albumartist') and release_details['release']['artist-credit']:
            album_artist_name = release_details['release']['artist-credit-string']
            audio_id3.delall('TPE2')
            audio_id3.add(TPE2(encoding=3, text=album_artist_name))
            log_entries_list.append(f"Set Album Artist to: {album_artist_name}")
            # EasyID3 often handles 'albumartist' well
            try:
                easy_audio_aa = EasyID3(file_path)
                easy_audio_aa['albumartist'] = album_artist_name
                easy_audio_aa.save()
            except Exception as e:
                log_entries_list.append(f"Note: Could not set 'albumartist' also via EasyID3 for {file_path}: {e}")
        elif should_process_field('albumartist'):
            log_entries_list.append(f"Album artist requested but not found in MusicBrainz data for {file_path}.")


        if should_process_field('tracknumber') and release_details['release']['medium-list'] and release_details['release']['medium-list'][0]['track-list']:
            total_tracks = str(release_details['release']['medium-list'][0]['track-count'])
            # Re-fetch current title using EasyID3 for this specific task
            try:
                current_title_audio = EasyID3(file_path)
                current_track_title = current_title_audio.get('title', [None])[0]
            except Exception:
                current_track_title = None # Fallback if reading title fails

            track_number_str = ""
            if current_track_title:
                for track_info in release_details['release']['medium-list'][0]['track-list']:
                    if 'recording' in track_info and track_info['recording']['title'].lower() == current_track_title.lower():
                        track_number_str = str(track_info['number'])
                        break

            track_tag_text = f"{track_number_str}/{total_tracks}" if track_number_str else f"1/{total_tracks}" # Default to 1 if no match
            audio_id3.delall('TRCK')
            audio_id3.add(TRCK(encoding=3, text=track_tag_text))
            log_entries_list.append(f"Set Track Number/Total to: {track_tag_text}")
        elif should_process_field('tracknumber'):
            log_entries_list.append(f"Track number requested but not found in MusicBrainz data for {file_path}.")

        if should_process_field('year') and release_details['release'].get('date'):
            year = release_details['release']['date'].split('-')[0]
            audio_id3.delall('TYER')
            audio_id3.delall('TDRC') # TDRC is more common for full date, TYER for year only
            audio_id3.add(TYER(encoding=3, text=year))
            log_entries_list.append(f"Set Year to: {year} using TYER")
            try:
                easy_audio_date = EasyID3(file_path)
                easy_audio_date['date'] = year
                easy_audio_date.save()
            except Exception as e:
                log_entries_list.append(f"Note: Could not also set 'date' via EasyID3 for {file_path}: {e}")
        elif should_process_field('year'):
            log_entries_list.append(f"Year requested but not found in MusicBrainz data for {file_path}.")

        if should_process_field('genre'):
            genre_tags = []
            # Genre from release group tags
            if 'tag-list' in release_details['release']['release-group']:
                genre_tags.extend([tag['name'] for tag in release_details['release']['release-group']['tag-list']])
            # Genre from release group genres (requires 'genres' include)
            if 'genre-list' in release_details['release']['release-group']:
                 genre_tags.extend([genre['name'] for genre in release_details['release']['release-group']['genre-list']])

            if genre_tags:
                # Limit to a few genres and join them, as TCON is often a single string.
                # MusicBrainz can have many tags; pick the most relevant or common ones if possible.
                # For now, just take the first one found if multiple, or join a few.
                genre_str = ", ".join(list(set(genre_tags))[:3]) # Take up to 3 unique genres
                audio_id3.delall('TCON')
                audio_id3.add(TCON(encoding=3, text=genre_str))
                log_entries_list.append(f"Set Genre to: {genre_str}")
                try: # Also try to set via EasyID3
                    easy_audio_genre = EasyID3(file_path)
                    easy_audio_genre['genre'] = genre_str
                    easy_audio_genre.save()
                except Exception as e:
                    log_entries_list.append(f"Note: Could not set 'genre' via EasyID3 for {file_path}: {e}")
            else:
                log_entries_list.append(f"Genre requested but no genre tags found in MusicBrainz data for {file_path}.")


        if should_process_field('coverart'):
            try:
                # Ensure release_group id is available
                if 'release-group' not in release_details['release'] or 'id' not in release_details['release']['release-group']:
                    log_entries_list.append(f"Cannot fetch cover art: Missing release-group ID in MB data for {file_path}.")
                else:
                    rgid = release_details['release']['release-group']['id']
                    art_info = musicbrainzngs.get_release_group_image_list(rgid)
                    if art_info and art_info['images']:
                        front_cover_url = None
                        for img in art_info['images']:
                            if 'Front' in img['types'] and img.get('approved'):
                                front_cover_url = img['thumbnails'].get('large') or img['image'] # Prefer large thumbnail, fallback to original image URL
                                break
                        if not front_cover_url and art_info['images'][0].get('approved'): # Fallback to first approved image if no front
                            front_cover_url = art_info['images'][0]['thumbnails'].get('large') or art_info['images'][0]['image']

                        if front_cover_url:
                            log_entries_list.append(f"Fetching cover art from: {front_cover_url}")
                            response = requests.get(front_cover_url, timeout=10)
                            response.raise_for_status()

                            mime_type = 'image/jpeg'
                            if '.png' in front_cover_url.lower(): # Check lowercased URL
                                mime_type = 'image/png'

                            audio_id3.delall('APIC')
                            audio_id3.add(APIC(
                                encoding=3,
                                mime=mime_type,
                                type=3, # 3 is for front cover
                                desc='Cover',
                                data=response.content
                            ))
                            log_entries_list.append(f"Successfully embedded cover art from {front_cover_url}")
                        else:
                            log_entries_list.append(f"No approved front cover art found on MusicBrainz for release group {rgid}.")
                    else:
                        log_entries_list.append(f"No cover art found on MusicBrainz for release group {rgid}.")
            except requests.exceptions.RequestException as e:
                log_entries_list.append(f"Error fetching cover art: {e}")
            except musicbrainzngs.WebServiceError as e:
                log_entries_list.append(f"MusicBrainz error fetching cover art: {e}")
            except Exception as e:
                log_entries_list.append(f"An unexpected error occurred during cover art processing: {e}")
        else:
            log_entries_list.append("Skipping cover art fetch as 'coverart' not in fields_to_fetch or fields_to_fetch is empty but other fields were specified.")


        # Save all ID3 changes made through audio_id3 object
        audio_id3.save(v2_version=3)
        log_entries_list.append(f"Successfully updated tags for {file_path} from MusicBrainz based on requested fields.")

    except musicbrainzngs.WebServiceError as exc:
# This part of the diff seems to be a repetition or incorrect. The changes for cover art are already above.
# The audio_id3.save() and final exception handling are also correctly placed above.
# I will assume this is an artifact of the diff generation and the code above is the source of truth.
# The key is that the cover art block is now wrapped in `if should_process_field('coverart'):`
# and the logging for skipping is outside that block if coverart is not requested.
# Final save and error handling should remain at the end of the try-block for MB processing.
        log_entries_list.append(f"MusicBrainz API error for {file_path}: {exc}")
    except requests.exceptions.RequestException as exc:
        log_entries_list.append(f"Network error for {file_path} (e.g., fetching cover art): {exc}")
    except Exception as e:
        log_entries_list.append(f"An unexpected error occurred while processing {file_path}: {e}")
