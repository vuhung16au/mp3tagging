#!/bin/bash
# Test script for tag-album.py using files in ./test
set -e

TEST_DIR="./test"
TEST_MP3="$TEST_DIR/test-music.mp3"
TEST_COVER="$TEST_DIR/test-cover.jpeg"

# 1. Show tags (plain)
echo "\n[--show]"
python3 tag-album.py -f "$TEST_DIR" --show

# 2. Show tags (HTML)
echo "\n[--show --html]"
python3 tag-album.py -f "$TEST_DIR" --show --html

# 3. Set artist (short)
echo "\n[-r]"
python3 tag-album.py -f "$TEST_DIR" -r "Test Artist"
python3 tag-album.py -f "$TEST_DIR" --show

# 4. Set artist (long)
echo "\n[--artist]"
python3 tag-album.py -f "$TEST_DIR" --artist "Long Artist"
python3 tag-album.py -f "$TEST_DIR" --show

# 5. Set album (short)
echo "\n[-a]"
python3 tag-album.py -f "$TEST_DIR" -a "Test Album"
python3 tag-album.py -f "$TEST_DIR" --show

# 6. Set album (long)
echo "\n[--album]"
python3 tag-album.py -f "$TEST_DIR" --album "Long Album"
python3 tag-album.py -f "$TEST_DIR" --show

# 7. Set genre (short)
echo "\n[-g]"
python3 tag-album.py -f "$TEST_DIR" -g "Rock"
python3 tag-album.py -f "$TEST_DIR" --show

# 8. Set genre (long)
echo "\n[--genre]"
python3 tag-album.py -f "$TEST_DIR" --genre "Jazz"
python3 tag-album.py -f "$TEST_DIR" --show

# 9. Set rating (long only)
echo "\n[--rating]"
python3 tag-album.py -f "$TEST_DIR" --rating 5
python3 tag-album.py -f "$TEST_DIR" --show

# 10. Set cover art (long only)
echo "\n[--cover-art]"
python3 tag-album.py -f "$TEST_DIR" --cover-art "$TEST_COVER"
python3 tag-album.py -f "$TEST_DIR" --show

# 2. Show tags (HTML)
echo "\n[--show --html]"
python3 tag-album.py -f "$TEST_DIR" --show --html

echo "\nAll tests completed."
