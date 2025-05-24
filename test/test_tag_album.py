import unittest
import os
import shutil
import sys # Ensure sys is imported before use
import subprocess
from mutagen.easyid3 import EasyID3 # Corrected: ID3NoHeaderError is from mutagen.id3
from mutagen.id3 import ID3, ID3NoHeaderError # Added ID3NoHeaderError here

# Add tag-album.py to sys.path to allow direct import
# This assumes tag-album.py is in the parent directory of test/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tag_album 

class TestTagAlbum(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_test_mp3s"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Path to the original test music file.
        # __file__ should be /app/test/test_tag_album.py
        # os.path.dirname(__file__) should be /app/test
        # So, original_mp3_src_path should correctly point to /app/test/test-music.mp3
        original_mp3_src_path = os.path.join(os.path.dirname(__file__), 'test-music.mp3')
        self.test_mp3_path = os.path.join(self.test_dir, "test.mp3")
        
        if os.path.exists(original_mp3_src_path):
            shutil.copy(original_mp3_src_path, self.test_mp3_path)
        else:
            # Fallback: create a minimal MP3 file if original is not found
            # This is a basic valid MP3 header. Not playable but Mutagen can read/write tags.
            # Using a slightly more common minimal MP3 structure.
            with open(self.test_mp3_path, 'wb') as f:
                # Frame sync (all 1s), MPEG Version 1, Layer 3, no CRC
                # Bitrate 32kbps, Sample rate 44100Hz, Frame padding No, Private bit No
                # Channel Mode Stereo
                # Minimal valid frame might be more complex, but this often works for tagging.
                f.write(b'\xFF\xFB\x10\xC0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00TAG')
            try:
                # Attempt to initialize ID3 tags to make it more robust for EasyID3
                audio = ID3() # Create new ID3 tag
                audio.save(self.test_mp3_path) # Save it to the file
            except Exception:
                # If ID3 initialization fails, we proceed with the minimal file.
                # set_year_tag itself has handling for ID3NoHeaderError
                pass
        
        # Ensure logs directory exists if any test run creates logs from tag_album.py
        os.makedirs("logs", exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists("mp3_tags.html"):
            os.remove("mp3_tags.html")
        # Do not remove "logs" directory as it might be used by the script generally.

    def test_set_year_tag(self):
        tag_album.set_year_tag(self.test_dir, "2023", recursive=False)
        try:
            audio = EasyID3(self.test_mp3_path)
            self.assertEqual(audio['date'], ['2023'])
        except ID3NoHeaderError:
            self.fail("ID3NoHeaderError raised after setting year tag. The set_year_tag function should have created ID3 headers if missing.")
        except Exception as e:
            self.fail(f"Unexpected error when reading year tag: {e}")

    def test_show_year_in_plaintext(self):
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: # If no ID3 header, create one for the test
            audio = ID3()
            audio.save(self.test_mp3_path)
            audio = EasyID3(self.test_mp3_path) # Reload
        audio['date'] = '2024'
        audio.save()

        import io
        captured_output = io.StringIO()
        old_stdout = sys.stdout # Save current stdout
        sys.stdout = captured_output # Redirect stdout
        try:
            tag_album.show_folder_tags(self.test_dir, recursive=False)
        finally:
            sys.stdout = old_stdout # Restore stdout
        
        output = captured_output.getvalue()
        self.assertIn("Year", output, "The 'Year' header is missing from plain text output.")
        self.assertIn("2024", output, "The year '2024' is missing from plain text output.")

    def test_show_year_in_html(self):
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError: # If no ID3 header, create one
            audio = ID3()
            audio.save(self.test_mp3_path)
            audio = EasyID3(self.test_mp3_path) # Reload
        audio['date'] = '2025'
        audio.save()

        tag_album.show_folder_tags_in_pretty_HTML(self.test_dir, recursive=False)
        
        self.assertTrue(os.path.exists("mp3_tags.html"), "HTML report file was not generated.")
        with open("mp3_tags.html", 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        self.assertIn("<th>Year</th>", html_content, "The 'Year' table header is missing from HTML output.")
        self.assertIn("<td>2025</td>", html_content, "The year '2025' is missing from HTML output.")
        if os.path.exists("mp3_tags.html"): # Clean up the generated HTML file
            os.remove("mp3_tags.html")

    def test_show_no_year_tag(self):
        # Ensure the test MP3 has no 'date' tag.
        try:
            audio = EasyID3(self.test_mp3_path)
            if 'date' in audio: # If 'date' tag exists
                del audio['date'] # Delete it
                audio.save()
        except ID3NoHeaderError:
            # This is the desired state - no ID3 header means no 'date' tag.
            pass 
        except Exception as e:
            self.fail(f"Failed to ensure no year tag for test: {e}")

        import io
        captured_output = io.StringIO()
        old_stdout = sys.stdout # Save current stdout
        sys.stdout = captured_output # Redirect stdout
        try:
            tag_album.show_folder_tags(self.test_dir, recursive=False)
        finally:
            sys.stdout = old_stdout # Restore stdout
        
        output = captured_output.getvalue()
        self.assertIn("Year", output, "The 'Year' header is missing from plain text output when tag is not set.")
        
        # More robust check for "Unknown" in the Year column
        lines = output.splitlines()
        header_line_index = -1
        year_column_index = -1

        for i, line_text in enumerate(lines):
            if "File Path" in line_text and "Artist" in line_text and "Year" in line_text: # Identify header row
                header_line_index = i
                headers = [h.strip() for h in line_text.split('|')] # Split by PrettyTable separator
                try:
                    year_column_index = headers.index("Year")
                except ValueError:
                    self.fail("Year column not found in table headers.")
                break
        
        self.assertNotEqual(header_line_index, -1, "Table header row not found in output.")

        found_unknown_for_year_in_file_row = False
        # Check rows after the header that contain the test MP3 path
        for i in range(header_line_index + 1, len(lines)):
            if self.test_mp3_path in lines[i]:
                values = [v.strip() for v in lines[i].split('|')]
                # Check if the row has enough columns and the value in Year column is "Unknown"
                if len(values) > year_column_index and values[year_column_index] == "Unknown":
                    found_unknown_for_year_in_file_row = True
                    break
        
        self.assertTrue(found_unknown_for_year_in_file_row, "Expected 'Unknown' for year tag in the file's row when not set.")

    def test_set_year_tag_via_main_argument(self):
        test_year = "2024"
        # Construct the path to tag_album.py relative to this test script
        # os.path.dirname(__file__) is /app/test
        # os.path.join(os.path.dirname(__file__), '..') is /app
        # script_path is /app/tag_album.py
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        cmd = [
            sys.executable, 
            script_path,
            "-f", self.test_dir,
            "-y", test_year
        ]
        
        try:
            # Run the script
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify the tag was set
        try:
            audio = EasyID3(self.test_mp3_path)
            self.assertEqual(audio['date'], [test_year])
        except ID3NoHeaderError:
            self.fail(f"ID3NoHeaderError raised after running script for year {test_year}. The script should have created ID3 headers if missing.")
        except KeyError:
            self.fail(f"'date' tag not found after running script for year {test_year}.")
        except Exception as e:
            self.fail(f"Unexpected error when reading year tag for {test_year}: {e}")

    def test_set_artist_tag_via_main_argument(self):
        test_artist_name = "Test Artist"
        # Construct the path to tag_album.py relative to this test script
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        cmd = [
            sys.executable,
            script_path,
            "-f", self.test_dir,
            "-r", test_artist_name  # -r for artist as per tag_album.py's argument parsing
        ]

        try:
            # Run the script
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify the tag was set
        try:
            audio = EasyID3(self.test_mp3_path)
            self.assertEqual(audio['artist'], [test_artist_name])
        except ID3NoHeaderError:
            self.fail(f"ID3NoHeaderError raised after running script for artist '{test_artist_name}'. The script should have created ID3 headers if missing.")
        except KeyError:
            self.fail(f"'artist' tag not found after running script for artist '{test_artist_name}'.")
        except Exception as e:
            self.fail(f"Unexpected error when reading artist tag for '{test_artist_name}': {e}")

    def test_show_tags_plaintext_via_main_argument(self):
        test_artist = "Show Artist"
        test_album = "Show Album"
        test_year = "2026"

        # Set tags on the test MP3 file
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError:
            audio = ID3()
            audio.save(self.test_mp3_path)
            audio = EasyID3(self.test_mp3_path) # Reload
        
        audio['artist'] = test_artist
        audio['album'] = test_album
        audio['date'] = test_year
        audio.save()

        # Construct the path to tag_album.py
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        # Prepare the command
        cmd = [
            sys.executable,
            script_path,
            "-f", self.test_dir,
            "--show"
        ]

        # Execute the command
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            output = result.stdout
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed for --show: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify the output
        self.assertIn("Artist", output, "The 'Artist' header is missing from --show output.")
        self.assertIn("Album", output, "The 'Album' header is missing from --show output.")
        self.assertIn("Year", output, "The 'Year' header is missing from --show output.")
        
        self.assertIn(test_artist, output, f"The artist '{test_artist}' is missing from --show output.")
        self.assertIn(test_album, output, f"The album '{test_album}' is missing from --show output.")
        self.assertIn(test_year, output, f"The year '{test_year}' is missing from --show output.")
        
        self.assertIn(os.path.basename(self.test_mp3_path), output, f"The filename '{os.path.basename(self.test_mp3_path)}' is missing from --show output.")

    def test_show_tags_html_via_main_argument(self):
        test_artist = "HTML Artist"
        test_album = "HTML Album"
        test_year = "2027"
        html_report_path = "mp3_tags.html"

        # Set tags on the test MP3 file
        try:
            audio = EasyID3(self.test_mp3_path)
        except ID3NoHeaderError:
            audio = ID3()
            audio.save(self.test_mp3_path)
            audio = EasyID3(self.test_mp3_path) # Reload
        
        audio['artist'] = test_artist
        audio['album'] = test_album
        audio['date'] = test_year
        audio.save()

        # Construct the path to tag_album.py
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        # Prepare the command
        cmd = [
            sys.executable,
            script_path,
            "-f", self.test_dir,
            "--show",
            "--html"
        ]

        # Execute the command
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed for --show --html: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify HTML file creation
        self.assertTrue(os.path.exists(html_report_path), f"HTML report file '{html_report_path}' was not generated.")

        # Read and verify HTML content
        with open(html_report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        self.assertIn("<th>Artist</th>", html_content, "The 'Artist' table header is missing from HTML output.")
        self.assertIn("<th>Album</th>", html_content, "The 'Album' table header is missing from HTML output.")
        self.assertIn("<th>Year</th>", html_content, "The 'Year' table header is missing from HTML output.")
        
        self.assertIn(f"<td>{test_artist}</td>", html_content, f"The artist '{test_artist}' is missing from HTML output.")
        self.assertIn(f"<td>{test_album}</td>", html_content, f"The album '{test_album}' is missing from HTML output.")
        self.assertIn(f"<td>{test_year}</td>", html_content, f"The year '{test_year}' is missing from HTML output.")
        
        # Check for the filename (potentially within a <td> tag)
        # Using basename as the full path might be formatted or truncated in HTML.
        self.assertIn(os.path.basename(self.test_mp3_path), html_content, f"The filename '{os.path.basename(self.test_mp3_path)}' is missing from HTML output.")
        # A more specific check if the structure is known:
        # self.assertIn(f"<td>{os.path.basename(self.test_mp3_path)}</td>", html_content, f"The filename '{os.path.basename(self.test_mp3_path)}' in a <td> tag is missing from HTML output.")

        # Cleanup of mp3_tags.html is handled by tearDown method

if __name__ == '__main__':
    unittest.main()


class TestRecursiveBehavior(unittest.TestCase):
    def setUp(self):
        self.base_dir = "temp_test_recursive"
        self.subdir = os.path.join(self.base_dir, "subdir")
        self.root_mp3_path = os.path.join(self.base_dir, "root_test.mp3")
        self.sub_mp3_path = os.path.join(self.subdir, "sub_test.mp3")
        
        os.makedirs(self.subdir, exist_ok=True)
        
        original_mp3_src_path = os.path.join(os.path.dirname(__file__), 'test-music.mp3')
        
        if not os.path.exists(original_mp3_src_path):
            # Create minimal MP3s if source is missing (fallback like in TestTagAlbumYear)
            with open(self.root_mp3_path, 'wb') as f:
                f.write(b'\xFF\xFB\x10\xC0\x00\x00TAG') # Minimal MP3
            ID3().save(self.root_mp3_path) # Ensure it has basic ID3 structure
            with open(self.sub_mp3_path, 'wb') as f:
                f.write(b'\xFF\xFB\x10\xC0\x00\x00TAG') # Minimal MP3
            ID3().save(self.sub_mp3_path) # Ensure it has basic ID3 structure
        else:
            shutil.copy(original_mp3_src_path, self.root_mp3_path)
            shutil.copy(original_mp3_src_path, self.sub_mp3_path)

        # Ensure logs directory exists for tag_album.py
        os.makedirs("logs", exist_ok=True)
        # Clear any pre-existing tags for a clean test slate
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try:
                audio = EasyID3(mp3_path)
                if 'album' in audio:
                    del audio['album']
                audio.save()
            except ID3NoHeaderError: # If no header, create one
                audio_id3 = ID3()
                audio_id3.save(mp3_path)
            except Exception as e:
                # If there's another error, print it to help diagnose
                print(f"Error clearing tags for {mp3_path}: {e}")


    def tearDown(self):
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        if os.path.exists("mp3_tags.html"): # Added cleanup for mp3_tags.html
            os.remove("mp3_tags.html")
        # Do not remove "logs" as it's a general script directory
        # Do not remove mp3_tags.html here as other tests might generate/use it.

    def test_non_recursive_tagging(self):
        album_name = "NonRecursiveTestAlbum"
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [
            sys.executable, script_path,
            "-f", self.base_dir,
            "-a", album_name
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"Script execution failed for non-recursive test: {e.stderr}")

        root_audio = EasyID3(self.root_mp3_path)
        self.assertIn('album', root_audio, "Album tag not set in root MP3 for non-recursive test.")
        self.assertEqual(root_audio['album'], [album_name])

        try:
            sub_audio = EasyID3(self.sub_mp3_path)
            self.assertNotIn('album', sub_audio, "Album tag WAS SET in sub MP3 for non-recursive test (should not have been).")
        except ID3NoHeaderError:
             # This is an acceptable outcome if the file initially had no tags and wasn't processed.
            pass
        except KeyError:
            # This is also acceptable: key 'album' not found.
            pass


    def test_recursive_tagging(self):
        album_name = "RecursiveTestAlbum"
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')
        cmd = [
            sys.executable, script_path,
            "-f", self.base_dir,
            "-a", album_name,
            "-R" # Recursive flag
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"Script execution failed for recursive test: {e.stderr}")

        root_audio = EasyID3(self.root_mp3_path)
        self.assertIn('album', root_audio, "Album tag not set in root MP3 for recursive test.")
        self.assertEqual(root_audio['album'], [album_name])

        sub_audio = EasyID3(self.sub_mp3_path)
        self.assertIn('album', sub_audio, "Album tag not set in sub MP3 for recursive test.")
        self.assertEqual(sub_audio['album'], [album_name])

    def test_show_tags_plaintext_recursive_via_main_argument(self):
        test_artist = "Recursive Show Artist"
        test_album = "Recursive Show Album"
        test_year = "2028"

        # Set tags on both MP3 files
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try:
                audio = EasyID3(mp3_path)
            except ID3NoHeaderError:
                audio_id3 = ID3()
                audio_id3.save(mp3_path)
                audio = EasyID3(mp3_path) # Reload
            
            audio['artist'] = test_artist
            audio['album'] = test_album
            audio['date'] = test_year
            audio.save()

        # Construct the path to tag_album.py
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        # Prepare the command
        cmd = [
            sys.executable,
            script_path,
            "-f", self.base_dir,
            "--show",
            "-R" # Recursive flag
        ]

        # Execute the command
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            output = result.stdout
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed for --show -R: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify the output
        self.assertIn("Artist", output, "The 'Artist' header is missing from --show -R output.")
        self.assertIn("Album", output, "The 'Album' header is missing from --show -R output.")
        self.assertIn("Year", output, "The 'Year' header is missing from --show -R output.")

        # Verify tags for root MP3
        self.assertIn(test_artist, output, f"The artist '{test_artist}' is missing for root MP3 in --show -R output.")
        self.assertIn(test_album, output, f"The album '{test_album}' is missing for root MP3 in --show -R output.")
        self.assertIn(test_year, output, f"The year '{test_year}' is missing for root MP3 in --show -R output.")
        self.assertIn(os.path.basename(self.root_mp3_path), output, f"The filename '{os.path.basename(self.root_mp3_path)}' is missing from --show -R output.")
        
        # Verify tags for sub MP3
        self.assertIn(test_artist, output, f"The artist '{test_artist}' is missing for sub MP3 in --show -R output.")
        self.assertIn(test_album, output, f"The album '{test_album}' is missing for sub MP3 in --show -R output.")
        self.assertIn(test_year, output, f"The year '{test_year}' is missing for sub MP3 in --show -R output.")
        self.assertIn(os.path.basename(self.sub_mp3_path), output, f"The filename '{os.path.basename(self.sub_mp3_path)}' is missing from --show -R output.")

        # Check that the values appear at least twice (once for each file)
        # This is a simplified check; more robust would be to parse the table and check rows.
        self.assertTrue(output.count(test_artist) >= 2, f"Artist '{test_artist}' not found for both files.")
        self.assertTrue(output.count(test_album) >= 2, f"Album '{test_album}' not found for both files.")
        self.assertTrue(output.count(test_year) >= 2, f"Year '{test_year}' not found for both files.")

    def test_show_tags_html_recursive_via_main_argument(self):
        test_artist = "Recursive HTML Artist"
        test_album = "Recursive HTML Album"
        test_year = "2029"
        html_report_path = "mp3_tags.html"

        # Set tags on both MP3 files
        for mp3_path in [self.root_mp3_path, self.sub_mp3_path]:
            try:
                audio = EasyID3(mp3_path)
            except ID3NoHeaderError:
                audio_id3 = ID3()
                audio_id3.save(mp3_path)
                audio = EasyID3(mp3_path) # Reload
            
            audio['artist'] = test_artist
            audio['album'] = test_album
            audio['date'] = test_year
            audio.save()

        # Construct the path to tag_album.py
        script_path = os.path.join(os.path.dirname(__file__), '..', 'tag_album.py')

        # Prepare the command
        cmd = [
            sys.executable,
            script_path,
            "-f", self.base_dir,
            "--show",
            "--html",
            "-R" # Recursive flag
        ]

        # Execute the command
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.fail(f"tag_album.py script execution failed for --show --html -R: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        except FileNotFoundError:
            self.fail(f"tag_album.py script not found at {script_path}. Check path and script name.")

        # Verify HTML file creation
        self.assertTrue(os.path.exists(html_report_path), f"HTML report file '{html_report_path}' was not generated.")

        # Read and verify HTML content
        with open(html_report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        self.assertIn("<th>Artist</th>", html_content, "The 'Artist' table header is missing from HTML output.")
        self.assertIn("<th>Album</th>", html_content, "The 'Album' table header is missing from HTML output.")
        self.assertIn("<th>Year</th>", html_content, "The 'Year' table header is missing from HTML output.")
        
        # Verify tags for both MP3s
        # Check that the values appear at least twice (once for each file)
        self.assertTrue(html_content.count(f"<td>{test_artist}</td>") >= 2, f"Artist '{test_artist}' not found for both files in HTML.")
        self.assertTrue(html_content.count(f"<td>{test_album}</td>") >= 2, f"Album '{test_album}' not found for both files in HTML.")
        self.assertTrue(html_content.count(f"<td>{test_year}</td>") >= 2, f"Year '{test_year}' not found for both files in HTML.")

        # Verify filenames are present
        expected_root_path_in_html = os.path.join("/app", self.root_mp3_path)
        expected_sub_path_in_html = os.path.join("/app", self.sub_mp3_path)
        self.assertIn(f"<td>{expected_root_path_in_html}</td>", html_content, f"The filename '{expected_root_path_in_html}' is missing from HTML output.")
        self.assertIn(f"<td>{expected_sub_path_in_html}</td>", html_content, f"The filename '{expected_sub_path_in_html}' is missing from HTML output.")
        
        # Cleanup of mp3_tags.html is handled by tearDown method in this class
