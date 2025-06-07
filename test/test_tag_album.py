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

if __name__ == '__main__':
    unittest.main()


import tempfile # For TestAcoustidFetching

# Need to import the function to be tested
from tag_album_utils.fetch_metadata import fetch_metadata_from_acoustid

class TestAcoustidFetching(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Use the existing test-music.mp3. Ensure it's copied from the correct relative path.
        original_mp3_src_path = os.path.join(os.path.dirname(__file__), 'test-music.mp3')
        self.test_mp3_path = os.path.join(self.temp_dir, "test_acoustid.mp3")

        if os.path.exists(original_mp3_src_path):
            shutil.copy(original_mp3_src_path, self.test_mp3_path)
            # Ensure the copied file has some basic ID3 structure for EasyID3 to work reliably
            # or for the setters to create one.
            try:
                # Try to clear tags that might interfere, especially if test-music.mp3 has prior tags
                audio = EasyID3(self.test_mp3_path)
                for key in list(audio.keys()): # list() to avoid RuntimeError for changing dict size
                    del audio[key]
                audio.save()
            except ID3NoHeaderError: # If no header, it's fine, setters will handle it
                # Attempt to create one so EasyID3 can open it later for assertions
                try:
                    id3 = ID3()
                    id3.save(self.test_mp3_path)
                except Exception as e_save:
                    print(f"Warning: Could not create initial ID3 header for {self.test_mp3_path} in setUp: {e_save}")
            except Exception as e:
                print(f"Warning: Could not clear tags for {self.test_mp3_path} in setUp: {e}")
        else:
            # Fallback if test-music.mp3 is missing (shouldn't happen in CI if repo is complete)
            with open(self.test_mp3_path, 'wb') as f:
                f.write(b'\xFF\xFB\x10\xC0' + b'\x00' * 10240) # Dummy MP3 data
            try:
                ID3().save(self.test_mp3_path) # Create a basic ID3 header
            except Exception as e:
                 print(f"Warning: Could not create fallback ID3 header for {self.test_mp3_path} in setUp: {e}")


        self.api_key = "MDCUvH3Ppp" # As used in main script
        self.sample_fpcalc_output_str = '{"duration": 180, "fingerprint": "some_fingerprint_string"}'
        self.sample_fpcalc_output_json = {"duration": 180, "fingerprint": "some_fingerprint_string"}

        self.sample_acoustid_response_json = {
            "status": "ok",
            "results": [{
                "score": 0.9,
                "id": "some_acoustid_id",
                "recordings": [{
                    "title": "Test Title from AcoustID",
                    "duration": 180,
                    "artists": [{"name": "Test Artist from AcoustID"}],
                    "genres": [{"name": "Electronic"}]
                }],
                "releasegroups": [{
                    "title": "Test Album from AcoustID",
                    "type": "Album"
                }]
            }]
        }
        # Ensure logs directory exists for any direct calls to setters that might log independently
        # although fetch_metadata_from_acoustid should manage its own log list.
        os.makedirs("logs", exist_ok=True)


    def tearDown(self):
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.subprocess.run')
    def test_fetch_and_set_acoustid_tags_success(self, mock_subprocess_run, mock_requests_get):

        def subprocess_run_side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd == ['fpcalc', '-version']:
                return MagicMock(returncode=0, stdout="fpcalc version 1.5.1", stderr="")
            elif cmd == ['fpcalc', '-json', self.test_mp3_path]:
                return MagicMock(returncode=0, stdout=self.sample_fpcalc_output_str, stderr="")
            return MagicMock(returncode=1, stdout="", stderr="Unknown command for mock_subprocess_run")

        mock_subprocess_run.side_effect = subprocess_run_side_effect

        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_acoustid_response_json
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise for 200
        mock_requests_get.return_value = mock_response

        log_entries = []
        status = fetch_metadata_from_acoustid(self.test_mp3_path, self.api_key,
                                              ["title", "artist", "album", "genre"], log_entries)

        self.assertEqual(status, "SUCCESS", f"Function returned {status} with logs: {log_entries}")

        # Assert subprocess.run calls
        call_fpcalc_version = call(['fpcalc', '-version'], capture_output=True, text=True, check=False, timeout=5)
        call_fpcalc_json = call(['fpcalc', '-json', self.test_mp3_path], capture_output=True, text=True, check=False, timeout=15) # check=False due to recent change
        mock_subprocess_run.assert_has_calls([call_fpcalc_version, call_fpcalc_json], any_order=True) # any_order might be true if other calls were made, but specific calls must exist

        # Assert requests.get call
        mock_requests_get.assert_called_once()
        actual_call_args = mock_requests_get.call_args
        self.assertEqual(actual_call_args[0][0], "https://api.acoustid.org/v2/lookup")

        expected_params = {
            "client": self.api_key,
            "meta": "recordings,releasegroups,compress,recordingids", # Adjusted based on requested fields
            "duration": str(self.sample_fpcalc_output_json["duration"]),
            "fingerprint": self.sample_fpcalc_output_json["fingerprint"]
        }
        # Normalize meta param for comparison by splitting, sorting, and rejoining
        actual_meta_set = set(actual_call_args[1]['params']['meta'].split(','))
        expected_meta_set = set(expected_params['meta'].split(','))
        self.assertEqual(actual_meta_set, expected_meta_set, "Meta parameters do not match")

        self.assertEqual(actual_call_args[1]['params']['client'], expected_params['client'])
        self.assertEqual(actual_call_args[1]['params']['duration'], expected_params['duration'])
        self.assertEqual(actual_call_args[1]['params']['fingerprint'], expected_params['fingerprint'])

        # Assert tags were written
        try:
            audio = EasyID3(self.test_mp3_path)
            self.assertEqual(audio.get('title'), ["Test Title from AcoustID"])
            self.assertEqual(audio.get('artist'), ["Test Artist from AcoustID"])
            self.assertEqual(audio.get('album'), ["Test Album from AcoustID"])
            self.assertEqual(audio.get('genre'), ["Electronic"])
        except Exception as e:
            self.fail(f"Failed to read tags from MP3 after AcoustID processing: {e}\nLogs: {log_entries}")


    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.subprocess.run')
    def test_fetch_metadata_fpcalc_not_found(self, mock_subprocess_run, mock_requests_get):
        # Simulate fpcalc -version failing (e.g., FileNotFoundError or non-zero return)
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="fpcalc not found")
        # Or, to simulate FileNotFoundError directly for the first call:
        # mock_subprocess_run.side_effect = FileNotFoundError("fpcalc not found at path")

        log_entries = []
        status = fetch_metadata_from_acoustid(self.test_mp3_path, self.api_key,
                                              ["title", "artist"], log_entries)

        self.assertEqual(status, "FPCLAC_NOT_FOUND")
        mock_requests_get.assert_not_called()
        # Check that a critical log message was added
        self.assertTrue(any("CRITICAL: fpcalc not found" in entry for entry in log_entries),
                        f"Critical fpcalc error not found in logs: {log_entries}")

    @patch('tag_album_utils.fetch_metadata.requests.get')
    @patch('tag_album_utils.fetch_metadata.subprocess.run')
    def test_fetch_metadata_fpcalc_json_error(self, mock_subprocess_run, mock_requests_get):
        # First call for version check is successful
        # Second call for JSON output fails
        def subprocess_run_side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd == ['fpcalc', '-version']:
                return MagicMock(returncode=0, stdout="fpcalc version 1.5.1", stderr="")
            elif cmd == ['fpcalc', '-json', self.test_mp3_path]:
                return MagicMock(returncode=1, stdout="", stderr="Error during fpcalc JSON generation") # Simulate fpcalc error
            return MagicMock(returncode=1, stdout="", stderr="Unknown command")

        mock_subprocess_run.side_effect = subprocess_run_side_effect

        log_entries = []
        status = fetch_metadata_from_acoustid(self.test_mp3_path, self.api_key,
                                              ["title", "artist"], log_entries)

        self.assertEqual(status, "FPCLAC_ERROR")
        mock_requests_get.assert_not_called()
        self.assertTrue(any("fpcalc execution failed" in entry for entry in log_entries),
                        f"FPCLAC_ERROR not logged correctly: {log_entries}")
