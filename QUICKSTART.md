# QUICKSTART

## Overview
`tag_album.py` is a Python CLI tool for batch editing MP3 metadata (album, artist, genre, rating, cover art, etc.). This guide shows how to set up the development environment, install dependencies, and run the most common commands.

## Prerequisites
- Python **3.9+** installed (run `python --version`).
- macOS (or Linux) terminal with **git**.
- Optional: `fpcalc` (Chromaprint) for AcoustID look‑ups. Install via:
  ```sh
  brew install chromaprint
  ```

## 1️⃣ Clone the repository (if you haven't already)
```sh
git clone https://github.com/yourusername/mp3tagging.git
cd mp3tagging
```

## 2️⃣ Create and activate a virtual environment
```sh
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate   # Windows
```

## 3️⃣ Install required Python packages
```sh
pip install -r requirements.txt
```

> **Tip**: Keep the virtual environment isolated; you can deactivate later with `deactivate`.

## 4️⃣ Running the tool
The basic syntax is:
```sh
python tag_album.py -f <folder> [options]
```

### 📦 Example commands

#### Set album, artist and genre for all MP3s in a folder
```sh
python tag_album.py -f /path/to/music \
    -a "My Awesome Album" \
    -r "My Artist" \
    -g "Rock"
```

#### Give every file a 5‑star rating
```sh
python tag_album.py -f /path/to/music --rating 5
```

#### Embed cover art into every MP3
```sh
python tag_album.py -f /path/to/music --cover-art /path/to/cover.jpg
```

#### Set the release year
```sh
python tag_album.py -f /path/to/music -y "2023"
```

#### Show metadata (plain text)
```sh
python tag_album.py -f /path/to/music --show
```

#### Show metadata (HTML)
```sh
python tag_album.py -f /path/to/music --show --html
```

#### Recursively update a folder and its sub‑folders
```sh
python tag_album.py -f /path/to/music -a "New Album" -R
```

#### Fetch missing metadata from MusicBrainz (requires existing artist/album tags)
```sh
python tag_album.py -f /path/to/music --fetch-metadata
```

#### Fetch metadata from AcoustID and set specific fields (needs `fpcalc`)
```sh
python tag_album.py -f /path/to/music \
    --fetch-and-set-acoustid-tags \
    --fields "title,artist,album"
```

## 5️⃣ Testing the installation
A quick sanity check:
```sh
python tag_album.py -h   # prints the help message
```
If the help text displays without errors, the installation succeeded.

## 6️⃣ Deactivating the environment
When you are done:
```sh
deactivate
```

---
*Feel free to adapt the commands to your workflow. For a full list of options, run `python tag_album.py --help`.*
