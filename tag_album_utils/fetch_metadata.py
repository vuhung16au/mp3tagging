import musicbrainzngs
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TPE2, TRCK, TYER, TCON # Added TYER, TCON for Genre
# Removed EasyID3NotLoadedError as it's not standard
from mutagen.id3 import TIT2 # Import TIT2 for Title frame


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
        # Added 'title' to the condition for needing "media" and "recordings"
        if should_process_field('tracknumber') or should_process_field('year') or should_process_field('genre') or should_process_field('title'):
            mb_includes.extend(["media", "recordings"])
        if should_process_field('genre'):
            mb_includes.extend(["genres", "tags"]) # For genre information from release group

        release_details = musicbrainzngs.get_release_by_id(release_id, includes=list(set(mb_includes)))

        release_data = release_details.get('release', {}) # Safely get the main 'release' dictionary

        # Update Artist (TPE1) if requested
        if should_process_field('artist'):
            # The 'artist-credit-string' is often the Album Artist.
            # For track-specific artist, one would typically iterate through recordings.
            # Here, we're setting the main 'artist' tag from the release's artist-credit-string.
            new_artist_name = release_data.get('artist-credit-string')
            if new_artist_name:
                audio['artist'] = new_artist_name
                log_entries_list.append(f"Prepared Artist for update: {new_artist_name}")
            else:
                log_entries_list.append(f"Artist ('artist-credit-string') not found in MusicBrainz response for {file_path} when 'artist' field requested.")

        # Update Album (TALB) if requested
        if should_process_field('album'):
            new_album_name = release_data.get('title')
            if new_album_name:
                audio['album'] = new_album_name
                log_entries_list.append(f"Prepared Album for update: {new_album_name}")
            else:
                log_entries_list.append(f"Album title not found in MusicBrainz response for {file_path} when 'album' field requested.")

        made_easyid3_changes = False
        if should_process_field('artist') and release_data.get('artist-credit-string'):
            made_easyid3_changes = True
        if should_process_field('album') and release_data.get('title'):
            made_easyid3_changes = True

        mb_track_title_for_update = None
        track_number_str_for_id3 = ""
        total_tracks_str_for_id3 = ""

        medium_list = release_data.get('medium-list', [])
        if medium_list and isinstance(medium_list, list) and len(medium_list) > 0:
            # Consider the first medium for track processing
            medium_info = medium_list[0]
            total_tracks_count = medium_info.get('track-count')
            if total_tracks_count is not None:
                total_tracks_str_for_id3 = str(total_tracks_count)

            track_list = medium_info.get('track-list', [])
            if track_list:
                current_title_audio_local = EasyID3(file_path)
                current_track_title_local = current_title_audio_local.get('title', [None])[0]

                if current_track_title_local:
                    for track_info in track_list:
                        # Title for matching (as it appears on the release track list)
                        release_track_title = track_info.get('title')
                        recording_data = track_info.get('recording', {})
                        # Canonical title from the recording
                        canonical_recording_title = recording_data.get('title')

                        if release_track_title and release_track_title.lower() == current_track_title_local.lower():
                            track_number_str_for_id3 = track_info.get('number', "")
                            # Prefer the canonical recording title for updating, if available
                            mb_track_title_for_update = canonical_recording_title if canonical_recording_title else release_track_title
                            break

            if should_process_field('title'):
                if mb_track_title_for_update: # This means a track was matched
                    audio['title'] = mb_track_title_for_update
                    log_entries_list.append(f"Prepared Title for update: {mb_track_title_for_update}")
                    made_easyid3_changes = True
                else:
                    log_entries_list.append(f"Title requested, but track not matched or title not found in MB data for {file_path}.")
        else:
            if should_process_field('tracknumber') or should_process_field('title'):
                 log_entries_list.append(f"Medium/track list not found in MusicBrainz response for {file_path}.")


        if made_easyid3_changes:
            try:
                audio.save()
                log_entries_list.append(f"Saved EasyID3 changes (artist/album/title) for {file_path}.")
            except Exception as e:
                log_entries_list.append(f"Error saving EasyID3 changes for {file_path}: {e}")

        audio_id3 = ID3(file_path)

        if should_process_field('albumartist'):
            album_artist_name = release_data.get('artist-credit-string')
            if album_artist_name:
                audio_id3.delall('TPE2')
                audio_id3.add(TPE2(encoding=3, text=album_artist_name))
                log_entries_list.append(f"Set Album Artist to: {album_artist_name} using TPE2")
            else:
                log_entries_list.append(f"Album artist ('artist-credit-string') not found in MusicBrainz response for {file_path} when 'albumartist' field requested.")

        if should_process_field('tracknumber'):
            if track_number_str_for_id3 and total_tracks_str_for_id3:
                track_tag_text = f"{track_number_str_for_id3}/{total_tracks_str_for_id3}"
                audio_id3.delall('TRCK')
                audio_id3.add(TRCK(encoding=3, text=track_tag_text))
                log_entries_list.append(f"Set Track Number/Total to: {track_tag_text}")
            elif total_tracks_str_for_id3 :
                track_tag_text = f"1/{total_tracks_str_for_id3}"
                audio_id3.delall('TRCK')
                audio_id3.add(TRCK(encoding=3, text=track_tag_text))
                log_entries_list.append(f"Set Track Number/Total to: {track_tag_text} (track title not matched, defaulted to 1)")
            else:
                log_entries_list.append(f"Track number data not found in MusicBrainz for {file_path} when 'tracknumber' field requested.")

        if should_process_field('year'):
            release_date_str = release_data.get('date')
            year = None
            if release_date_str and isinstance(release_date_str, str) and '-' in release_date_str:
                year = release_date_str.split('-')[0]

            if year:
                audio_id3.delall('TYER')
                audio_id3.delall('TDRC')
                audio_id3.add(TYER(encoding=3, text=year))
                log_entries_list.append(f"Set Year to: {year} using TYER")
                try:
                    easy_audio_date = EasyID3(file_path)
                    easy_audio_date['date'] = year
                    easy_audio_date.save()
                except Exception as e:
                    log_entries_list.append(f"Note: Could not also set 'date' via EasyID3 for {file_path}: {e}")
            else:
                log_entries_list.append(f"Year (from release 'date') not found or in unexpected format in MusicBrainz response for {file_path} when 'year' field requested.")

        if should_process_field('genre'):
            genre_tags_list = []
            release_group_data = release_data.get('release-group', {})

            for tag in release_group_data.get('tag-list', []):
                if tag.get('name'): genre_tags_list.append(tag['name'])
            for genre_item in release_group_data.get('genre-list', []):
                 if genre_item.get('name'): genre_tags_list.append(genre_item['name'])

            if genre_tags_list:
                genre_str = ", ".join(list(set(genre_tags_list))[:3])
                audio_id3.delall('TCON')
                audio_id3.add(TCON(encoding=3, text=genre_str))
                log_entries_list.append(f"Set Genre to: {genre_str}")
                try:
                    easy_audio_genre = EasyID3(file_path)
                    easy_audio_genre['genre'] = genre_str
                    easy_audio_genre.save()
                except Exception as e:
                    log_entries_list.append(f"Note: Could not set 'genre' via EasyID3 for {file_path}: {e}")
            else:
                log_entries_list.append(f"Genre data not found in MusicBrainz response for {file_path} when 'genre' field requested.")

        if should_process_field('coverart'):
            release_group_data = release_data.get('release-group', {})
            rgid = release_group_data.get('id')
            if not rgid:
                log_entries_list.append(f"Cannot fetch cover art: Missing release-group ID in MB data for {file_path}.")
            else:
                try:
                    art_info = musicbrainzngs.get_release_group_image_list(rgid)
                    images = art_info.get('images', [])
                    if images:
                        front_cover_url = None
                        for img in images:
                            img_types = img.get('types', [])
                            if 'Front' in img_types and img.get('approved'):
                                front_cover_url = img.get('thumbnails', {}).get('large') or img.get('image')
                                break
                        if not front_cover_url and images[0].get('approved'):
                            front_cover_url = images[0].get('thumbnails', {}).get('large') or images[0].get('image')

                        if front_cover_url:
                            log_entries_list.append(f"Fetching cover art from: {front_cover_url}")
                            response = requests.get(front_cover_url, timeout=10)
                            response.raise_for_status()
                            mime_type = 'image/jpeg'
                            if '.png' in front_cover_url.lower():
                                mime_type = 'image/png'
                            audio_id3.delall('APIC')
                            audio_id3.add(APIC(encoding=3, mime=mime_type, type=3, desc='Cover', data=response.content))
                            log_entries_list.append(f"Successfully embedded cover art from {front_cover_url}")
                        else:
                            log_entries_list.append(f"No approved front cover art found on MusicBrainz for release group {rgid}.")
                    else:
                        log_entries_list.append(f"No cover art images found on MusicBrainz for release group {rgid}.")
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
