import musicbrainzngs
import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, TPE2, TRCK, TYER # Added TYER

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

        release_details = musicbrainzngs.get_release_by_id(release_id, includes=["artist-credits", "media", "recordings", "release-groups"])

        audio_id3 = ID3(file_path)

        if release_details['release']['artist-credit']:
            album_artist_name = release_details['release']['artist-credit-string']
            audio_id3.delall('TPE2')
            audio_id3.add(TPE2(encoding=3, text=album_artist_name))
            log_entries_list.append(f"Set Album Artist to: {album_artist_name}")
            try:
                easy_audio = EasyID3(file_path) # Re-fetch to ensure it's EasyID3 object for this part
                easy_audio['albumartist'] = album_artist_name
                easy_audio.save()
            except Exception as e:
                log_entries_list.append(f"Note: Could not set 'albumartist' via EasyID3 for {file_path}: {e}")

        if release_details['release']['medium-list'] and release_details['release']['medium-list'][0]['track-list']:
            total_tracks = str(release_details['release']['medium-list'][0]['track-count'])
            current_track_title = audio.get('title', [None])[0]
            track_number_str = ""

            if current_track_title:
                for track_info in release_details['release']['medium-list'][0]['track-list']:
                    if track_info['recording']['title'].lower() == current_track_title.lower():
                        track_number_str = str(track_info['number'])
                        break

            track_tag_text = f"{track_number_str}/{total_tracks}" if track_number_str else f"1/{total_tracks}"
            audio_id3.delall('TRCK')
            audio_id3.add(TRCK(encoding=3, text=track_tag_text))
            log_entries_list.append(f"Set Track Number/Total to: {track_tag_text}")

        if release_details['release'].get('date'):
            year = release_details['release']['date'].split('-')[0]
            audio_id3.delall('TYER') # Remove existing year tag (TYER)
            audio_id3.delall('TDRC') # Remove existing year tag (TDRC)
            audio_id3.add(TYER(encoding=3, text=year)) # Add TYER via ID3 object
            log_entries_list.append(f"Set Year to: {year} using TYER")
            # Also attempt to set via EasyID3 for its 'date' key if read elsewhere,
            # though primary save will be via audio_id3.save()
            try:
                easy_audio_for_date = EasyID3(file_path)
                easy_audio_for_date['date'] = year
                easy_audio_for_date.save()
                log_entries_list.append(f"Also set 'date' via EasyID3 for {file_path}")
            except Exception as e:
                log_entries_list.append(f"Note: Could not also set 'date' via EasyID3 for {file_path}: {e}")

        try:
            art_info = musicbrainzngs.get_release_group_image_list(release['release-group']['id'])
            if art_info and art_info['images']:
                front_cover_url = None
                for img in art_info['images']:
                    if 'Front' in img['types'] and img.get('approved'):
                        front_cover_url = img['thumbnails']['large']
                        break
                if not front_cover_url and art_info['images'][0].get('approved'):
                     front_cover_url = art_info['images'][0]['thumbnails']['large']

                if front_cover_url:
                    log_entries_list.append(f"Fetching cover art from: {front_cover_url}")
                    response = requests.get(front_cover_url, timeout=10)
                    response.raise_for_status()

                    mime_type = 'image/jpeg'
                    if '.png' in front_cover_url:
                        mime_type = 'image/png'

                    audio_id3.delall('APIC')
                    audio_id3.add(APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3,
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

        audio_id3.save(v2_version=3)
        log_entries_list.append(f"Successfully updated tags for {file_path} from MusicBrainz.")

    except musicbrainzngs.WebServiceError as exc:
        log_entries_list.append(f"MusicBrainz API error for {file_path}: {exc}")
    except requests.exceptions.RequestException as exc:
        log_entries_list.append(f"Network error for {file_path} (e.g., fetching cover art): {exc}")
    except Exception as e:
        log_entries_list.append(f"An unexpected error occurred while processing {file_path}: {e}")
