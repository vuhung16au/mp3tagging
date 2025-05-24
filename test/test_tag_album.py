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

class TestTagAlbumYear(unittest.TestCase):
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
        tag_album.set_year_tag(self.test_dir, "2023")
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
            tag_album.show_folder_tags(self.test_dir)
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

        tag_album.show_folder_tags_in_pretty_HTML(self.test_dir)
        
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
            tag_album.show_folder_tags(self.test_dir)
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

if __name__ == '__main__':
    unittest.main()
