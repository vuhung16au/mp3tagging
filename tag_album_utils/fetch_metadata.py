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


import subprocess
import json
import os
# requests is already imported
# from mutagen.easyid3 import EasyID3 # Already imported
# from mutagen.id3 import ID3NoHeaderError # Already imported
from .set_tags import set_artist_tag, set_album_tag, set_genre_tag, set_title_tag # To be implemented in next step

def fetch_metadata_from_acoustid(file_path, api_key, requested_fields, log_entries_list):
    """
    Fetches metadata from AcoustID for a given MP3 file and updates its ID3 tags.

    Args:
        file_path (str): The path to the MP3 file.
        api_key (str): The AcoustID API key.
        requested_fields (list): A list of strings indicating which tags to fetch and set.
        log_entries_list (list): A list to append log messages to.
    """
    fpcalc_path = "fpcalc"
    file_name = os.path.basename(file_path)

    # 1. Check for fpcalc
    try:
        fpcalc_check = subprocess.run([fpcalc_path, "-version"], capture_output=True, text=True, check=False, timeout=5)
        if fpcalc_check.returncode != 0:
            log_entries_list.append(f"CRITICAL: fpcalc not found or not executable at '{fpcalc_path}'. Please ensure it is installed and in your PATH. Exit code {fpcalc_check.returncode}. Stderr: {fpcalc_check.stderr.strip()}")
            return "FPCLAC_NOT_FOUND"
    except FileNotFoundError:
        log_entries_list.append(f"CRITICAL: fpcalc command not found at '{fpcalc_path}'. Please ensure it is installed and in your PATH.")
        return "FPCLAC_NOT_FOUND"
    except subprocess.TimeoutExpired:
        log_entries_list.append(f"CRITICAL: fpcalc -version command timed out for '{fpcalc_path}'.")
        return "FPCLAC_NOT_FOUND" # Or a different error like FPCLAC_TIMEOUT, but NOT_FOUND is actionable for user.
    except Exception as e:
        log_entries_list.append(f"CRITICAL: Failed to check fpcalc version for '{fpcalc_path}': {e}")
        return "FPCLAC_NOT_FOUND" # Or a different error.

    # 2. Execute fpcalc
    try:
        process = subprocess.run([fpcalc_path, "-json", file_path], capture_output=True, text=True, check=False, timeout=15) # check=False to handle error manually
        if process.returncode != 0:
            log_entries_list.append(f"Error for {file_name}: fpcalc execution failed with exit code {process.returncode}. Command: '{process.args}'. stderr: {process.stderr.strip()}")
            return "FPCLAC_ERROR"
        fpcalc_output = json.loads(process.stdout)
        fingerprint = fpcalc_output.get("fingerprint")
        duration = fpcalc_output.get("duration")

        if not fingerprint or not duration:
            log_entries_list.append(f"Error for {file_name}: Could not extract fingerprint or duration from fpcalc JSON output. Output: {process.stdout[:200]}")
            return "FPCLAC_ERROR"
        log_entries_list.append(f"Successfully obtained fingerprint and duration for {file_name}.")

    # subprocess.CalledProcessError is not needed if check=False
    except subprocess.TimeoutExpired:
        log_entries_list.append(f"Error for {file_name}: fpcalc execution timed out for {file_path}.")
        return "FPCLAC_ERROR"
    except json.JSONDecodeError:
        log_entries_list.append(f"Error for {file_name}: Could not decode JSON from fpcalc output. Output: {process.stdout[:200]}")
        return "FPCLAC_ERROR"
    except Exception as e:
        log_entries_list.append(f"Error for {file_name}: An unexpected error occurred during fpcalc processing: {e}")
        return "FPCLAC_ERROR"

    # 3. Prepare for AcoustID API Call
    acoustid_meta_sources = {
        "title": "recordings",
        "artist": "recordings", # "recordingids" also useful for artists if we want MBIDs
        "album": "releasegroups", # "recordingids" also useful for album MBIDs via recordings
        # "genre": "releasegroups" # Genre from releasegroups can be via tags, often user-submitted.
                                 # Recordings can also have genres from MusicBrainz.
    }
    meta_param_parts = set(["compress"]) # "compress" is generally good to have.
    for field in requested_fields:
        source = acoustid_meta_sources.get(field)
        if source:
            meta_param_parts.add(source)

    # Ensure essential sources if specific fields are requested
    if "artist" in requested_fields : meta_param_parts.add("recordingids") # Needed for artist MBID
    if "album" in requested_fields : meta_param_parts.add("recordingids") # Needed for album MBID via recordings->releasegroups
    if "genre" in requested_fields: # Explicitly add sources that might contain genre
        meta_param_parts.add("recordings") # For MB genres associated with recordings
        meta_param_parts.add("releasegroups") # For user tags on release groups


    if not meta_param_parts or meta_param_parts == {"compress"}: # If only "compress" is there, add defaults
        meta_param = "recordings,releasegroups,compress"
    else:
        meta_param = ",".join(list(meta_param_parts))

    log_entries_list.append(f"For {file_name}, using AcoustID meta: {meta_param}")


    # 4. Call AcoustID API
    api_url = "https://api.acoustid.org/v2/lookup"
    params = {
        "client": api_key,
        "meta": meta_param,
        "duration": str(int(duration)),
        "fingerprint": fingerprint
    }

    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except requests.exceptions.HTTPError as e:
        log_entries_list.append(f"Error for {file_name}: AcoustID API request failed with HTTP status {e.response.status_code}: {e.response.text[:200]}")
        return "SUCCESS" # Or specific API_ERROR, but problem was not fpcalc
    except requests.exceptions.Timeout:
        log_entries_list.append(f"Error for {file_name}: AcoustID API request timed out.")
        return "SUCCESS" # Or specific API_ERROR
    except requests.exceptions.RequestException as e:
        log_entries_list.append(f"Error for {file_name}: AcoustID API request failed: {e}")
        return "SUCCESS" # Or specific API_ERROR
    except json.JSONDecodeError:
        log_entries_list.append(f"Error for {file_name}: Could not decode JSON from AcoustID API response. Response: {response.text[:200]}")
        return "SUCCESS" # Or specific API_ERROR

    # 5. Process API Response
    if api_data.get("status") == "ok" and api_data.get("results"):
        results = api_data["results"]
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        best_result = results[0]
        score = best_result.get("score", 0) * 100
        log_entries_list.append(f"Found match for {file_name}: Score {score:.2f}%")

        title_to_set = None
        artist_to_set = None
        album_to_set = None
        genre_to_set = None

        # Extract Tags
        try:
            if "title" in requested_fields and best_result.get("recordings"):
                title_to_set = best_result["recordings"][0].get("title")
                if not title_to_set: log_entries_list.append(f"Title not found in AcoustID response for {file_name}.")

            if "artist" in requested_fields and best_result.get("recordings"):
                if best_result["recordings"][0].get("artists"):
                    artist_to_set = best_result["recordings"][0]["artists"][0].get("name")
                    if not artist_to_set: log_entries_list.append(f"Artist name not found in AcoustID response for {file_name}.")
                else:
                    log_entries_list.append(f"Artist section not found in AcoustID recordings for {file_name}.")

            if "album" in requested_fields:
                # Album can be from recordings -> releasegroups
                if best_result.get("recordings") and best_result["recordings"][0].get("releasegroups"):
                    album_to_set = best_result["recordings"][0]["releasegroups"][0].get("title")
                # Or directly from results -> releasegroups if that part of 'meta' was requested and fruitful
                elif best_result.get("releasegroups"):
                     album_to_set = best_result["releasegroups"][0].get("title")
                if not album_to_set: log_entries_list.append(f"Album not found in AcoustID response for {file_name}.")

            if "genre" in requested_fields:
                # Try MusicBrainz genre from recordings first
                if best_result.get("recordings") and best_result["recordings"][0].get("genres"):
                    genre_to_set = best_result["recordings"][0]["genres"][0].get("name")
                # Fallback to user tags on release groups (less reliable)
                elif best_result.get("releasegroups") and best_result["releasegroups"][0].get("tags") and best_result["releasegroups"][0]["tags"].get("genre"):
                     genre_to_set = best_result["releasegroups"][0]["tags"]["genre"][0] # take first genre tag
                if not genre_to_set: log_entries_list.append(f"Genre not found or could not be determined from AcoustID response for {file_name}.")

        except (KeyError, IndexError) as e:
            log_entries_list.append(f"Error for {file_name}: Issue extracting tag from AcoustID response structure: {e}. Response snippet: {str(best_result)[:200]}")
        except Exception as e: # Catch any other unexpected error during extraction
            log_entries_list.append(f"Unexpected error extracting tags for {file_name}: {e}")


        # 6. Set Tags using Mutagen (assuming adapted setters)
        # Note: The set_..._tag functions are assumed to be adapted to take (file_path, value, False, log_entries_list)
        # and that 'False' means 'not recursive' (as they operate on a single file here).
        # This adaptation is part of the next subtask.

        # Check if audio file can be loaded (basic check before trying to set tags)
        try:
            EasyID3(file_path) # Try to load, ID3NoHeaderError is fine for setting new tags
        except ID3NoHeaderError:
            log_entries_list.append(f"Info for {file_name}: No ID3 header, tags will be created.")
        except Exception as e:
            log_entries_list.append(f"Error for {file_name}: Cannot load audio file with EasyID3 to set tags: {e}. Skipping tag setting.")
            return "SUCCESS" # File specific error, but fpcalc worked.

        if title_to_set and "title" in requested_fields:
            set_title_tag(file_path, title_to_set, False, log_entries_list) # False for not recursive
        if artist_to_set and "artist" in requested_fields:
            set_artist_tag(file_path, artist_to_set, False, log_entries_list)
        if album_to_set and "album" in requested_fields:
            set_album_tag(file_path, album_to_set, False, log_entries_list)
        if genre_to_set and "genre" in requested_fields:
            set_genre_tag(file_path, genre_to_set, False, log_entries_list)

        log_entries_list.append(f"Tag setting process completed for {file_name}.")

    elif api_data.get("status") == "ok" and not api_data.get("results"):
        log_entries_list.append(f"No results found on AcoustID for {file_name}.")
    else:
        error_message = api_data.get("error", {}).get("message", "Unknown error")
        log_entries_list.append(f"AcoustID API returned status '{api_data.get('status')}' for {file_name}. Error: {error_message}")

    return "SUCCESS"
