import unittest
import os
import shutil
import sys
import subprocess
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tag_album_utils.set_tags import set_year_tag
from tag_album_utils.display import show_folder_tags, show_folder_tags_in_pretty_HTML
from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
from unittest.mock import patch, MagicMock, call

import musicbrainzngs
import requests

def mock_write_log(log_entries, operation):
    # print(f"Mocked write_log: Operation '{operation}' with {len(log_entries)} entries.")
    mock_write_log.last_entries = log_entries
    mock_write_log.last_operation = operation

class TestTagAlbum(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_test_mp3s"
        os.makedirs(self.test_dir, exist_ok=True)
        
        original_mp3_src_path = os.path.join(os.path.dirname(__file__), 'test-music.mp3')
        self.test_mp3_path = os.path.join(self.test_dir, "test.mp3")
        
        if os.path.exists(original_mp3_src_path):
            shutil.copy(original_mp3_src_path, self.test_mp3_path)
        else:
            with open(self.test_mp3_path, 'wb') as f:
                f.write(b'\xFF\xFB\x10\xC0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00TAG')
            try:
                audio = ID3()
                audio.save(self.test_mp3_path)
            except Exception:
                pass
        
        try: # Clear APIC frames before each metadata test might need it
            audio_id3_setup = ID3(self.test_mp3_path)
            if 'APIC:Cover' in audio_id3_setup or 'APIC:' in audio_id3_setup :
                audio_id3_setup.delall('APIC')
                audio_id3_setup.save()
        except ID3NoHeaderError:
            pass
        except Exception as e:
            print(f"Warning: Could not clear APIC frame in setUp for {self.test_mp3_path}: {e}")

        os.makedirs("logs", exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists("mp3_tags.html"):
            os.remove("mp3_tags.html")

    @patch('tag_album_utils.set_tags.write_log', new=mock_write_log)
    def test_set_year_tag(self): # Removed mock_write_log_patched argument
        set_year_tag(self.test_dir, "2023", recursive=False)
        try:
            audio = EasyID3(self.test_mp3_path)
            self.assertEqual(audio['date'], ['2023'])
        except ID3NoHeaderError:
            self.fail("ID3NoHeaderError raised after setting year tag.")
        except Exception as e:
            self.fail(f"Unexpected error when reading year tag: {e}")

    def test_show_year_in_plaintext(self):
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError:
            audio = ID3(); audio.save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        audio['date'] = '2024'; audio.save()
        import io; captured_output = io.StringIO(); old_stdout = sys.stdout; sys.stdout = captured_output
        try: show_folder_tags(self.test_dir, recursive=False)
        finally: sys.stdout = old_stdout
        output = captured_output.getvalue()
        self.assertIn("Year", output); self.assertIn("2024", output)

    def test_show_year_in_html(self):
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError:
            audio = ID3(); audio.save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        audio['date'] = '2025'; audio.save()
        show_folder_tags_in_pretty_HTML(self.test_dir, recursive=False)
        self.assertTrue(os.path.exists("mp3_tags.html"))
        with open("mp3_tags.html", 'r', encoding='utf-8') as f: html_content = f.read()
        self.assertIn("<th>Year</th>", html_content); self.assertIn("<td>2025</td>", html_content)
        if os.path.exists("mp3_tags.html"): os.remove("mp3_tags.html")

    def test_show_no_year_tag(self):
        try:
            audio = EasyID3(self.test_mp3_path)
            if 'date' in audio: del audio['date']; audio.save()
        except ID3NoHeaderError: pass
        import io; captured_output = io.StringIO(); old_stdout = sys.stdout; sys.stdout = captured_output
        try: show_folder_tags(self.test_dir, recursive=False)
        finally: sys.stdout = old_stdout
        output = captured_output.getvalue()
        lines = output.splitlines(); header_line_index = -1; year_column_index = -1
        for i, line_text in enumerate(lines):
            if "File Path" in line_text and "Year" in line_text:
                header_line_index = i; headers = [h.strip() for h in line_text.split('|')]
                try: year_column_index = headers.index("Year")
                except ValueError: self.fail("Year column not found.")
                break
        self.assertNotEqual(header_line_index, -1); found_unknown = False
        for i in range(header_line_index + 1, len(lines)):
            if self.test_mp3_path in lines[i]:
                values = [v.strip() for v in lines[i].split('|')]
                if len(values) > year_column_index and values[year_column_index] == "Unknown":
                    found_unknown = True; break
        self.assertTrue(found_unknown)

    def test_set_year_tag_via_main_argument(self):
        test_year = "2024"; script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.test_dir, "-y", test_year]
        try: subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e: self.fail(f"Script failed: {e.stderr}")
        audio = EasyID3(self.test_mp3_path); self.assertEqual(audio['date'], [test_year])

    def test_set_artist_tag_via_main_argument(self):
        test_artist = "Test Artist"; script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.test_dir, "-r", test_artist]
        try: subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e: self.fail(f"Script failed: {e.stderr}")
        audio = EasyID3(self.test_mp3_path); self.assertEqual(audio['artist'], [test_artist])

    def test_show_tags_plaintext_via_main_argument(self):
        test_artist,test_album,test_year = "Show Artist","Show Album","2026"
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        audio['artist'],audio['album'],audio['date'] = test_artist,test_album,test_year; audio.save()
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.test_dir, "--show"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True); output = result.stdout
        self.assertIn(test_artist, output); self.assertIn(test_album, output); self.assertIn(test_year, output)

    def test_show_tags_html_via_main_argument(self):
        test_artist,test_album,test_year = "HTML Artist","HTML Album","2027"
        html_report_path="mp3_tags.html"
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        audio['artist'],audio['album'],audio['date'] = test_artist,test_album,test_year; audio.save()
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.test_dir, "--show", "--html"]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue(os.path.exists(html_report_path))
        with open(html_report_path, 'r', encoding='utf-8') as f: html_content = f.read()
        self.assertIn(f"<td>{test_artist}</td>", html_content); self.assertIn(f"<td>{test_album}</td>", html_content); self.assertIn(f"<td>{test_year}</td>", html_content)

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_success(self, mock_set_useragent, mock_search_releases, mock_get_release_by_id, mock_get_release_group_image_list, mock_requests_get):
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        initial_artist, initial_album, initial_title = "Initial Artist", "Initial Album", "Initial Title"
        audio['artist'], audio['album'], audio['title'] = initial_artist, initial_album, initial_title; audio.save()
        mock_search_releases.return_value = {'release-list': [{'id': 'release-id-123', 'title': 'Fetched Album Title', 'ext:score': '100', 'artist-credit-string': 'Fetched Artist', 'release-group': {'id': 'rg-id-123'}}]}
        mock_get_release_by_id.return_value = {'release': {'id': 'release-id-123', 'title': 'Fetched Album Title', 'artist-credit-string': 'Fetched Album Artist', 'artist-credit': [{'artist':{'name':'Fetched Album Artist'}}], 'date': '2023-10-26', 'medium-list': [{'track-count': 2, 'track-list': [{'number': '1', 'recording': {'title': 'Another Title'}}, {'number': '2', 'recording': {'title': initial_title}}]}], 'release-group': {'id': 'rg-id-123'}}}
        mock_get_release_group_image_list.return_value = {'images': [{'types': ['Front'], 'approved': True, 'thumbnails': {'large': 'http://example.com/cover.jpg'}}]}
        mock_cover_response = MagicMock(); mock_cover_response.content = b'dummy jpeg data'; mock_cover_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_cover_response
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        audio_tags = ID3(self.test_mp3_path)
        self.assertEqual(audio_tags['TPE2'].text[0], 'Fetched Album Artist')
        self.assertEqual(audio_tags['TRCK'].text[0], '2/2')
        self.assertIn('APIC:Cover', audio_tags); self.assertEqual(audio_tags['APIC:Cover'].data, b'dummy jpeg data')
        easy_audio_tags = EasyID3(self.test_mp3_path)
        self.assertEqual(easy_audio_tags['date'][0], '2023')
        self.assertIn("Successfully updated tags for", "\n".join(log_entries))

    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_no_release_found(self, mock_set_useragent, mock_search_releases):
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        initial_artist, initial_album, initial_title = "ArtistNoRelease", "AlbumNoRelease", "Some Title"
        audio['artist'], audio['album'], audio['title'] = initial_artist, initial_album, initial_title; audio.save()
        initial_tags = dict(audio)
        mock_search_releases.return_value = {'release-list': []}
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        current_tags = EasyID3(self.test_mp3_path)
        self.assertEqual(dict(current_tags), initial_tags)
        self.assertIn(f"No results found on MusicBrainz for {initial_artist} - {initial_album}", "\n".join(log_entries))

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_release_found_no_cover_art(self, mock_set_useragent, mock_search_releases, mock_get_release_by_id, mock_get_release_group_image_list, mock_requests_get):
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        initial_artist, initial_album, initial_title = "ArtistNoCover", "AlbumNoCover", "TitleNoCover"
        audio['artist'], audio['album'], audio['title'] = initial_artist, initial_album, initial_title; audio.save()
        mock_search_releases.return_value = {'release-list': [{'id': 'release-id-nocover', 'title': 'Album Title No Cover', 'ext:score': '95', 'release-group': {'id': 'rg-id-nocover'}}]}
        mock_get_release_by_id.return_value = {'release': {'id': 'release-id-nocover', 'title': 'Album Title No Cover', 'artist-credit-string': 'Artist Name NoCover', 'artist-credit': [{'artist':{'name':'Artist Name NoCover'}}], 'date': '2022', 'medium-list': [{'track-count': 1, 'track-list': [{'number': '1', 'recording': {'title': initial_title}}]}], 'release-group': {'id': 'rg-id-nocover'}}}
        mock_get_release_group_image_list.return_value = {'images': []}
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        mock_requests_get.assert_not_called()
        audio_tags = ID3(self.test_mp3_path)
        self.assertNotIn('APIC:Cover', audio_tags)
        self.assertIn("No cover art found on MusicBrainz", "\n".join(log_entries))

    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_api_error_search(self, mock_set_useragent, mock_search_releases):
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        initial_artist, initial_album = "ArtistApiError", "AlbumApiError"
        audio['artist'], audio['album'] = initial_artist, initial_album; audio.save()
        initial_tags_check = dict(audio)
        mock_search_releases.side_effect = musicbrainzngs.WebServiceError("API search failed")
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        current_tags = EasyID3(self.test_mp3_path)
        self.assertEqual(dict(current_tags), initial_tags_check)
        self.assertIn(f"MusicBrainz API error for {self.test_mp3_path}: API search failed", "\n".join(log_entries))

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_network_error_cover(self, mock_set_useragent, mock_search_releases, mock_get_release_by_id, mock_get_release_group_image_list, mock_requests_get):
        try: audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
        initial_artist, initial_album, initial_title = "ArtistNetError", "AlbumNetError", "TitleNetError"
        audio['artist'], audio['album'], audio['title'] = initial_artist, initial_album, initial_title; audio.save()
        mock_search_releases.return_value = {'release-list': [{'id': 'release-id-neterr', 'title': 'Album Title NetErr', 'ext:score': '90', 'release-group': {'id': 'rg-id-neterr'}}]}
        mock_get_release_by_id.return_value = {'release': {'id': 'release-id-neterr', 'title': 'Album Title NetErr', 'artist-credit-string': 'Artist Name NetErr', 'artist-credit': [{'artist':{'name':'Artist Name NetErr'}}], 'date': '2021', 'medium-list': [{'track-count': 1, 'track-list': [{'number': '1', 'recording': {'title': initial_title}}]}], 'release-group': {'id': 'rg-id-neterr'}}}
        mock_get_release_group_image_list.return_value = {'images': [{'types': ['Front'], 'approved': True, 'thumbnails': {'large': 'http://example.com/cover-neterr.jpg'}}]}
        mock_requests_get.side_effect = requests.exceptions.RequestException("Network failed for cover")
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        audio_tags = ID3(self.test_mp3_path)
        self.assertNotIn('APIC:Cover', audio_tags)
        self.assertIn("Error fetching cover art: Network failed for cover", "\n".join(log_entries))

    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_missing_initial_artist_album_tags(self, mock_set_useragent):
        try:
            audio = EasyID3(self.test_mp3_path)
            if 'artist' in audio: del audio['artist']
            if 'album' in audio: del audio['album']
            audio['title'] = "Title Only"; audio.save()
        except ID3NoHeaderError:
            ID3().save(self.test_mp3_path); audio = EasyID3(self.test_mp3_path)
            audio['title'] = "Title Only"; audio.save()
        initial_tags_check = dict(EasyID3(self.test_mp3_path))
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        mock_set_useragent.assert_not_called()
        current_tags = EasyID3(self.test_mp3_path)
        self.assertEqual(dict(current_tags), initial_tags_check)
        self.assertIn(f"Skipping {self.test_mp3_path}: Artist or Album tag not found.", log_entries)

    @patch('tag_album_utils.fetch_metadata.EasyID3')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.set_useragent')
    def test_fetch_metadata_id3_no_header_error_initial_read(self, mock_set_useragent, mock_easy_id3_constructor):
        mock_easy_id3_constructor.side_effect = ID3NoHeaderError("Simulated no header error")
        log_entries = []; fetch_metadata_from_musicbrainz(self.test_mp3_path, log_entries)
        mock_easy_id3_constructor.assert_called_once_with(self.test_mp3_path)
        mock_set_useragent.assert_not_called()
        self.assertIn(f"Skipping {self.test_mp3_path}: No ID3 header found to read artist/album.", log_entries)

class TestRecursiveBehavior(unittest.TestCase):
    def setUp(self):
        self.base_dir = "temp_test_recursive"
        self.subdir = os.path.join(self.base_dir, "subdir")
        self.root_mp3_path = os.path.join(self.base_dir, "root_test.mp3")
        self.sub_mp3_path = os.path.join(self.subdir, "sub_test.mp3")
        os.makedirs(self.subdir, exist_ok=True)
        original_mp3_src_path = os.path.join(os.path.dirname(__file__), 'test-music.mp3')
        if not os.path.exists(original_mp3_src_path):
            with open(self.root_mp3_path, 'wb') as f: f.write(b'\xFF\xFB\x10\xC0\x00\x00TAG')
            ID3().save(self.root_mp3_path)
            with open(self.sub_mp3_path, 'wb') as f: f.write(b'\xFF\xFB\x10\xC0\x00\x00TAG')
            ID3().save(self.sub_mp3_path)
        else:
            shutil.copy(original_mp3_src_path, self.root_mp3_path)
            shutil.copy(original_mp3_src_path, self.sub_mp3_path)
        os.makedirs("logs", exist_ok=True)
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try:
                audio = EasyID3(mp3_path)
                if 'album' in audio: del audio['album']; audio.save()
            except ID3NoHeaderError: ID3().save(mp3_path)
            except Exception as e: print(f"Error clearing tags for {mp3_path}: {e}")

    def tearDown(self):
        if os.path.exists(self.base_dir): shutil.rmtree(self.base_dir)
        if os.path.exists("mp3_tags.html"): os.remove("mp3_tags.html")

    def test_non_recursive_tagging(self):
        album_name = "NonRecursiveTestAlbum"
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.base_dir, "-a", album_name]
        try: subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e: self.fail(f"Script execution failed: {e.stderr}")
        root_audio = EasyID3(self.root_mp3_path)
        self.assertEqual(root_audio['album'], [album_name])
        try:
            sub_audio = EasyID3(self.sub_mp3_path)
            self.assertNotIn('album', sub_audio)
        except (ID3NoHeaderError, KeyError): pass

    def test_recursive_tagging(self):
        album_name = "RecursiveTestAlbum"
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.base_dir, "-a", album_name, "-R"]
        try: subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e: self.fail(f"Script execution failed: {e.stderr}")
        root_audio = EasyID3(self.root_mp3_path)
        self.assertEqual(root_audio['album'], [album_name])
        sub_audio = EasyID3(self.sub_mp3_path)
        self.assertEqual(sub_audio['album'], [album_name])

    def test_show_tags_plaintext_recursive_via_main_argument(self):
        test_artist, test_album, test_year = "Recursive Show Artist", "Recursive Show Album", "2028"
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try: audio = EasyID3(mp3_path)
            except ID3NoHeaderError: ID3().save(mp3_path); audio = EasyID3(mp3_path)
            audio['artist'], audio['album'], audio['date'] = test_artist, test_album, test_year
            audio.save()
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.base_dir, "--show", "-R"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True); output = result.stdout
        self.assertTrue(output.count(test_artist) >= 2)
        self.assertTrue(output.count(test_album) >= 2)
        self.assertTrue(output.count(test_year) >= 2)

    def test_show_tags_html_recursive_via_main_argument(self):
        test_artist, test_album, test_year = "Recursive HTML Artist", "Recursive HTML Album", "2029"
        html_report_path = "mp3_tags.html"
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try: audio = EasyID3(mp3_path)
            except ID3NoHeaderError: ID3().save(mp3_path); audio = EasyID3(mp3_path)
            audio['artist'], audio['album'], audio['date'] = test_artist, test_album, test_year
            audio.save()
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [sys.executable, script_path, "-f", self.base_dir, "--show", "--html", "-R"]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.assertTrue(os.path.exists(html_report_path))
        with open(html_report_path, 'r', encoding='utf-8') as f: html_content = f.read()
        self.assertTrue(html_content.count(f"<td>{test_artist}</td>") >= 2)
        self.assertTrue(html_content.count(f"<td>{test_album}</td>") >= 2)
        self.assertTrue(html_content.count(f"<td>{test_year}</td>") >= 2)
        self.assertIn(f"<td>{os.path.join('/app', self.root_mp3_path)}</td>", html_content)
        self.assertIn(f"<td>{os.path.join('/app', self.sub_mp3_path)}</td>", html_content)


# --- New Test Class for --fetch-and-set-from-mb ---
class TestFetchAndSetFromMB(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_test_mb_mp3s"
        os.makedirs(self.test_dir, exist_ok=True)
        self.mp3_path = os.path.join(self.test_dir, "test_mb.mp3")
        self.sub_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(self.sub_dir, exist_ok=True)
        self.sub_mp3_path = os.path.join(self.sub_dir, "test_mb_sub.mp3")

        # Create dummy MP3 files
        self.create_dummy_mp3(self.mp3_path, initial_tags={'artist': 'Old Artist', 'album': 'Old Album', 'date': '1990', 'genre': 'Old Genre', 'title': 'Old Title'})
        self.create_dummy_mp3(self.sub_mp3_path, initial_tags={'artist': 'Old Sub Artist', 'album': 'Old Sub Album', 'date': '1991', 'genre': 'Old Sub Genre', 'title': 'Old Sub Title'})

        # Store original sys.argv
        self.original_argv = sys.argv

        # Mock musicbrainzngs and requests set_useragent which is called early
        # We patch them here if they are always going to be patched in this class's tests
        # Or patch them per-method if more granular control is needed.
        # For now, assume most tests will mock MB calls.
        patcher_mb_set_useragent = patch('musicbrainzngs.set_useragent')
        self.mock_mb_set_useragent = patcher_mb_set_useragent.start()
        self.addCleanup(patcher_mb_set_useragent.stop)


    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        # Restore original sys.argv
        sys.argv = self.original_argv
        # Clean up log files potentially created by tests
        for log_file in ["metadata_fetching_selective.log", "metadata_fetching_full.log", "logs/metadata_fetching_selective.log", "logs/metadata_fetching_full.log"]:
            if os.path.exists(log_file):
                os.remove(log_file)
            elif os.path.exists(os.path.join(self.test_dir, log_file)): # if tests change cwd
                 os.remove(os.path.join(self.test_dir, log_file))


    def create_dummy_mp3(self, path, initial_tags=None):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Create a minimal MP3 file structure if it doesn't exist or is empty
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                 with open(path, 'wb') as f:
                    # Minimal MP3 frame, not necessarily valid for playback but good enough for mutagen
                    f.write(b'\xFF\xFB\x10\xC0' + b'\x00' * 100) # Minimal frame + some padding

            # Try to load, if no header, save one
            try:
                audio = EasyID3(path)
            except ID3NoHeaderError:
                id3 = ID3()
                id3.save(path)
                audio = EasyID3(path) # Reload

            # Clear existing tags before setting new ones
            for key in list(audio.keys()): # list() to avoid issues with dict size change during iteration
                del audio[key]

            if initial_tags:
                for k, v in initial_tags.items():
                    audio[k] = v
            audio.save()

            # Clear APIC frames specifically for pristine state for cover art tests
            audio_id3 = ID3(path)
            audio_id3.delall('APIC')
            audio_id3.save()

        except Exception as e:
            self.fail(f"Failed to create dummy MP3 {path}: {e}")

    # --- Mock Data ---
    def get_mock_search_results(self, artist="Test Artist", album="Test Album", release_id="release-id-mock", rg_id="rg-id-mock", score="100"):
        return {
            'release-list': [{
                'id': release_id,
                'title': album,
                'ext:score': score,
                'artist-credit-string': artist, # Often this is album artist
                'artist-credit': [{'artist': {'name': artist}}],
                'release-group': {'id': rg_id, 'type': 'Album'}
            }]
        }

    def get_mock_release_details(self, release_id="release-id-mock", artist="Test Artist", album="Test Album", album_artist="Test Album Artist",
                                 year="2023", date_str="2023-01-01", track_title="Test Track", track_num="1", total_tracks="10",
                                 genre_list=None, tag_list=None, rg_id="rg-id-mock"):
        if genre_list is None: genre_list = ["Rock"]
        if tag_list is None: tag_list = ["Progressive Rock"]

        # Construct genre and tag structures for MB
        mb_genre_list = [{'name': g, 'count': '1'} for g in genre_list]
        mb_tag_list = [{'name': t, 'count': '1'} for t in tag_list]

        return {
            'release': {
                'id': release_id,
                'title': album,
                'artist-credit-string': album_artist,
                'artist-credit': [{'artist': {'name': album_artist}}], # Typically album artist
                'date': date_str,
                'medium-list': [{
                    'track-count': total_tracks,
                    'track-list': [{
                        'number': track_num,
                        'recording': {'title': track_title, 'artist-credit': [{'artist': {'name': artist}}]} # Track artist
                    }]
                }],
                'release-group': {
                    'id': rg_id,
                    'type': 'Album',
                    'genre-list': mb_genre_list, # Requires 'genres' include
                    'tag-list': mb_tag_list      # Requires 'tags' include
                }
            }
        }

    def get_mock_cover_art_list(self, approved=True, front=True, url="http://example.com/cover.jpg"):
        types = ["Front"] if front else ["Other"]
        return {'images': [{'types': types, 'approved': approved, 'thumbnails': {'large': url}, 'image': url}]}

    # --- Test Cases ---

    @patch('tag_album.fetch_and_set_metadata_from_mb') # Patching the orchestrator in tag_album.py
    def test_cli_parsing_fields_correctly_passed(self, mock_orchestrator):
        # This tests if main() correctly parses the CLI arg and calls the orchestrator
        # The orchestrator (fetch_and_set_metadata_from_mb in tag_album.py) will then call the util
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--fetch-and-set-from-mb', 'artist,album, year']

        # Import main from tag_album directly to test its argument parsing and dispatch
        from tag_album import main as tag_album_main
        tag_album_main()

        mock_orchestrator.assert_called_once_with(
            os.path.abspath(self.test_dir), # main normalizes path
            ['artist', 'album', 'year'], # Expect stripped and split list
            False # Recursive not specified
        )

    @patch('tag_album.fetch_metadata_from_musicbrainz') # Patched where it's used by the orchestrator
    @patch('tag_album.write_log') # Mock logging where it's used in tag_album module
    def test_integration_call_to_util_selective(self, mock_write_log_in_tag_album, mock_fetch_metadata_in_tag_album_module): # Corrected mock name to match definition
        from tag_album import fetch_and_set_metadata_from_mb as orchestrator_func

        fields = ['artist', 'genre']
        abs_test_dir = os.path.abspath(self.test_dir)
        # Pass absolute path to orchestrator, similar to how main() would after parsing args.folder
        orchestrator_func(abs_test_dir, fields, False)

        expected_mp3_path = os.path.join(abs_test_dir, os.path.basename(self.mp3_path))
        mock_fetch_metadata_in_tag_album_module.assert_called_once_with( # Use the correct mock name
            expected_mp3_path,
            unittest.mock.ANY,
            fields_to_fetch=fields
        )
        mock_write_log_in_tag_album.assert_called_once_with(unittest.mock.ANY, "metadata_fetching_selective")


    @patch('tag_album.fetch_metadata_from_musicbrainz') # Patched where it's used by main()
    @patch('tag_album.write_log') # Mock logging where it's used in tag_album module
    def test_integration_call_to_util_fetch_all(self, mock_write_log_in_tag_album, mock_fetch_metadata_in_tag_album_module):
        # Test that the --fetch-metadata (old flag) calls the util with fields_to_fetch=None
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--fetch-metadata']
        from tag_album import main as tag_album_main
        tag_album_main()

        # It should be called once for the mp3_path
        expected_mp3_path = os.path.abspath(self.mp3_path)
        mock_fetch_metadata_in_tag_album_module.assert_called_once_with(
            expected_mp3_path,
            unittest.mock.ANY, # for log_entries list
            fields_to_fetch=None # Explicitly None for fetch all
        )
        mock_write_log_in_tag_album.assert_called_once_with(unittest.mock.ANY, "metadata_fetching_full")


    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_artist_album_only(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        # Setup mocks
        # For this test, let's make artist and album_artist the same to simplify 'artist' tag checking
        # or acknowledge that 'artist' tag gets the 'album_artist' string.
        # Current code: audio['artist'] gets release_details['release']['artist-credit-string'] (album_artist)
        mock_artist_to_set = "New AlbumArtist" # This will be set to audio['artist']
        mock_search.return_value = self.get_mock_search_results(artist="Original Search Artist", album="New Album")
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Track Artist", album="New Album", album_artist=mock_artist_to_set,
            year="2024", track_title="New Title", genre_list=["New Genre"]
        )
        # No cover art call expected

        log_entries = []
        # Call the utility function directly
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['artist', 'album'])

        audio = EasyID3(self.mp3_path)
        self.assertEqual(audio.get('artist'), [mock_artist_to_set]) # Artist tag gets the release's artist-credit-string
        self.assertEqual(audio.get('album'), ['New Album'])
        # Check that other pre-existing tags were NOT changed
        self.assertEqual(audio.get('date'), ['1990']) # From setUp
        self.assertEqual(audio.get('genre'), ['Old Genre']) # From setUp
        self.assertNotIn('albumartist', audio) # Should not be added
        self.assertNotIn('tracknumber', audio) # Should not be added

        audio_id3 = ID3(self.mp3_path)
        self.assertEqual(audio_id3.getall('APIC'), []) # No cover art
        self.assertEqual(audio_id3.getall('TPE2'), []) # No Album Artist
        self.assertEqual(audio_id3.getall('TRCK'), []) # No Track Number

        mock_get_img_list.assert_not_called() # Crucial for cover art efficiency

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_genre_only(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        mock_search.return_value = self.get_mock_search_results(artist="Old Artist", album="Old Album") # Match initial file
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Old Artist", album="Old Album", album_artist="Unchanged AlbumArtist",
            year="1990", track_title="Old Title", genre_list=["Funk", "Soul"], tag_list=[] # New Genre
        )

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['genre'])

        audio = EasyID3(self.mp3_path)
        # Genre check - order independent
        actual_genre_str_genre_only = audio.get('genre')[0]
        actual_genres_set_genre_only = set(g.strip() for g in actual_genre_str_genre_only.split(','))
        self.assertEqual(actual_genres_set_genre_only, {"Funk", "Soul"})

        # Check other tags remain unchanged
        self.assertEqual(audio.get('artist'), ['Old Artist'])
        self.assertEqual(audio.get('album'), ['Old Album'])
        self.assertEqual(audio.get('date'), ['1990'])
        mock_get_img_list.assert_not_called()

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_year_only(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        mock_search.return_value = self.get_mock_search_results(artist="Old Artist", album="Old Album")
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Old Artist", album="Old Album", date_str="2025-12-11", year="2025" # New Year
        )

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['year'])

        audio = EasyID3(self.mp3_path)
        self.assertEqual(audio.get('date'), ['2025'])
        # Check other tags remain unchanged
        self.assertEqual(audio.get('artist'), ['Old Artist'])
        self.assertEqual(audio.get('album'), ['Old Album'])
        self.assertEqual(audio.get('genre'), ['Old Genre'])
        mock_get_img_list.assert_not_called()

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_coverart_only(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        mock_search.return_value = self.get_mock_search_results(artist="Old Artist", album="Old Album", rg_id="rg-cover-test")
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Old Artist", album="Old Album", rg_id="rg-cover-test" # Ensure RGID matches
        )
        mock_get_img_list.return_value = self.get_mock_cover_art_list(url="http://example.com/new_cover.png")
        mock_cover_response = MagicMock()
        mock_cover_response.content = b'new png data'
        mock_cover_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_cover_response

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['coverart'])

        audio_id3 = ID3(self.mp3_path)
        self.assertIsNotNone(audio_id3.getall('APIC'))
        self.assertEqual(audio_id3.getall('APIC')[0].data, b'new png data')
        self.assertEqual(audio_id3.getall('APIC')[0].mime, 'image/png')

        # Check other tags remain unchanged using EasyID3
        audio_easy = EasyID3(self.mp3_path)
        self.assertEqual(audio_easy.get('artist'), ['Old Artist'])
        self.assertEqual(audio_easy.get('album'), ['Old Album'])
        self.assertEqual(audio_easy.get('date'), ['1990'])

        mock_get_img_list.assert_called_once_with("rg-cover-test")
        mock_requests_get.assert_called_once_with("http://example.com/new_cover.png", timeout=10)

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_tracknumber_albumartist(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        mock_search.return_value = self.get_mock_search_results(artist="Old Artist", album="Old Album")
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Old Artist", album="Old Album", album_artist="New AlbumArtist",
            track_title="Old Title", track_num="5", total_tracks="15" # New track/total, New AlbumArtist
        )

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['tracknumber', 'albumartist'])

        audio_id3 = ID3(self.mp3_path)
        self.assertEqual(audio_id3.getall('TPE2')[0].text[0], "New AlbumArtist")
        self.assertEqual(audio_id3.getall('TRCK')[0].text[0], "5/15")

        # Check other tags remain unchanged
        audio_easy = EasyID3(self.mp3_path)
        self.assertEqual(audio_easy.get('artist'), ['Old Artist']) # Original artist tag from EasyID3
        self.assertEqual(audio_easy.get('album'), ['Old Album'])
        self.assertEqual(audio_easy.get('date'), ['1990'])
        self.assertEqual(audio_easy.get('genre'), ['Old Genre'])
        # Also check albumartist via EasyID3
        self.assertEqual(audio_easy.get('albumartist'), ["New AlbumArtist"])


    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_selective_combination_year_genre_coverart(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        mock_search.return_value = self.get_mock_search_results(artist="Old Artist", album="Old Album", rg_id="rg-combo-test")
        mock_get_id.return_value = self.get_mock_release_details(
            artist="Old Artist", album="Old Album", date_str="2077-07-07", year="2077", # New Year
            genre_list=["Cyberpunk", "Electronic"], tag_list=[], rg_id="rg-combo-test" # New Genre, empty tag_list
        )
        mock_get_img_list.return_value = self.get_mock_cover_art_list(url="http://example.com/combo_cover.jpg", approved=True, front=True)
        mock_cover_response = MagicMock()
        mock_cover_response.content = b'combo jpeg data'
        mock_cover_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_cover_response

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['year', 'genre', 'coverart'])

        audio_easy = EasyID3(self.mp3_path)
        self.assertEqual(audio_easy.get('date'), ['2077'])

        # Genre check - order independent
        actual_genre_str_combo = audio_easy.get('genre')[0]
        actual_genres_set_combo = set(g.strip() for g in actual_genre_str_combo.split(','))
        self.assertEqual(actual_genres_set_combo, {"Cyberpunk", "Electronic"})

        audio_id3 = ID3(self.mp3_path)
        self.assertIsNotNone(audio_id3.getall('APIC'))
        self.assertEqual(audio_id3.getall('APIC')[0].data, b'combo jpeg data')

        # Check other tags remain unchanged
        self.assertEqual(audio_easy.get('artist'), ['Old Artist'])
        self.assertEqual(audio_easy.get('album'), ['Old Album'])

        mock_get_img_list.assert_called_once_with("rg-combo-test")


    @patch('tag_album.fetch_metadata_from_musicbrainz') # Patched where it's used by main()
    @patch('tag_album.write_log') # Mock logging where it's used in tag_album module
    def test_recursive_processing_selective(self, mock_write_log_in_tag_album, mock_fetch_metadata_in_tag_album_module):
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--fetch-and-set-from-mb', 'artist', '-R']
        from tag_album import main as tag_album_main
        tag_album_main()

        expected_mp3_path_abs = os.path.abspath(self.mp3_path)
        expected_sub_mp3_path_abs = os.path.abspath(self.sub_mp3_path)
        expected_calls = [
            call(expected_mp3_path_abs, unittest.mock.ANY, fields_to_fetch=['artist']),
            call(expected_sub_mp3_path_abs, unittest.mock.ANY, fields_to_fetch=['artist'])
        ]
        # Check calls on the mock for the function as looked up in tag_album module
        mock_fetch_metadata_in_tag_album_module.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_fetch_metadata_in_tag_album_module.call_count, 2)
        mock_write_log_in_tag_album.assert_called_once_with(unittest.mock.ANY, "metadata_fetching_selective")

    # test_logging_file_names is implicitly covered by test_integration_call_to_util_selective and _fetch_all (checking write_log args)

    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_error_handling_mb_no_results_selective(self, mock_search):
        mock_search.return_value = {'release-list': []} # Simulate no results

        # Initial state of a tag that should not change
        audio_before = EasyID3(self.mp3_path)
        initial_year = audio_before.get('date', ['InitialYear'])

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=['year'])

        audio_after = EasyID3(self.mp3_path)
        self.assertEqual(audio_after.get('date'), initial_year) # Year should not have changed
        self.assertTrue(any("No results found on MusicBrainz" in entry for entry in log_entries))

    # --- Tests for --auto flag ---

    @patch('tag_album.fetch_and_set_metadata_from_mb') # Patch orchestrator
    def test_auto_flag_uses_default_fields(self, mock_orchestrator_func):
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--auto']
        from tag_album import main as tag_album_main
        tag_album_main()

        expected_default_fields = ['artist', 'genre', 'album', 'title']
        mock_orchestrator_func.assert_called_once_with(
            os.path.abspath(self.test_dir),
            expected_default_fields,
            False # Recursive not specified
        )

    @patch('tag_album.fetch_and_set_metadata_from_mb') # Patch orchestrator
    def test_auto_flag_with_recursion(self, mock_orchestrator_func):
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--auto', '-R']
        from tag_album import main as tag_album_main
        tag_album_main()

        expected_default_fields = ['artist', 'genre', 'album', 'title']
        mock_orchestrator_func.assert_called_once_with(
            os.path.abspath(self.test_dir),
            expected_default_fields,
            True # Recursive specified
        )

    @patch('tag_album.fetch_and_set_metadata_from_mb') # Patch orchestrator
    def test_auto_precedence_by_fetch_and_set_from_mb(self, mock_orchestrator_func):
        user_specified_fields = ['year', 'coverart']
        # Construct the argument string for fetch-and-set-from-mb
        fetch_arg_str = ','.join(user_specified_fields)
        sys.argv = ['tag_album.py', '--folder', self.test_dir, '--auto', '--fetch-and-set-from-mb', fetch_arg_str]
        from tag_album import main as tag_album_main
        tag_album_main()

        mock_orchestrator_func.assert_called_once_with(
            os.path.abspath(self.test_dir),
            user_specified_fields, # User fields should take precedence
            False # Recursive not specified
        )

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_group_image_list')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.get_release_by_id')
    @patch('tag_album_utils.fetch_metadata.musicbrainzngs.search_releases')
    def test_auto_updates_title_field_via_util(self, mock_search, mock_get_id, mock_get_img_list, mock_requests_get):
        # This test verifies that 'title' is correctly processed by the utility function
        # when it's part of fields_to_fetch, as would be the case with --auto.

        initial_artist = "Old Artist" # Must match what's in self.mp3_path for search
        initial_album = "Old Album"
        # To test title setting, we'll ensure the local title matches the title in MB's tracklist,
        # and that title from MB is what we expect to be set.
        mb_track_title = "Matched Title from MB" # This will be used for both local and MB mock

        # Re-create the dummy MP3 with specific initial tags for this test
        self.create_dummy_mp3(self.mp3_path, initial_tags={'artist': initial_artist, 'album': initial_album, 'title': mb_track_title, 'genre': 'Old Genre', 'date': '1990'})

        mock_search.return_value = self.get_mock_search_results(artist=initial_artist, album=initial_album)

        mock_details = self.get_mock_release_details(
            artist=initial_artist,
            album=initial_album,
            album_artist="Some AlbumArtist",
            track_title=mb_track_title, # This title will be in the mock MB track list
            genre_list=["New Genre"],
            tag_list=[],
            year="2024"
        )
        mock_get_id.return_value = mock_details
        # Ensure the tag-list is truly empty in the final mock response.
        mock_get_id.return_value['release']['release-group']['tag-list'] = []


        auto_fields_to_fetch = ['artist', 'genre', 'album', 'title']

        log_entries = []
        from tag_album_utils.fetch_metadata import fetch_metadata_from_musicbrainz
        fetch_metadata_from_musicbrainz(self.mp3_path, log_entries, fields_to_fetch=auto_fields_to_fetch)

        audio = EasyID3(self.mp3_path)
        self.assertEqual(audio.get('title'), [mb_track_title]) # Title should be updated to mb_track_title

        # Genre check - order independent, expecting only "New Genre"
        actual_genre_str = audio.get('genre')[0]
        actual_genres_set = set(g.strip() for g in actual_genre_str.split(','))
        self.assertEqual(actual_genres_set, {"New Genre"}) # Reverted diagnostic: This is the correct expectation

        self.assertEqual(audio.get('album'), [initial_album])
        self.assertEqual(audio.get('artist'), ["Some AlbumArtist"])
        self.assertEqual(audio.get('date'), ['1990'])
        mock_get_img_list.assert_not_called()


if __name__ == '__main__':
    unittest.main()
