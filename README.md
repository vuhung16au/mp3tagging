# tag_album.py

`tag_album.py` is a tool for batch updating the album and artist metadata of MP3 files in a specified folder.

# How to Use

You can use `tag_album.py` to update the album and artist tags of all MP3 files in a folder, or to simply display the current metadata. The script supports both short and long options for flexibility.

## Options and Arguments

| Argument         | Description                                                      |
|------------------|------------------------------------------------------------------|
| `-f`, `--folder` | Specifies the folder containing MP3 files                        |
| `-a`, `--album`  | Sets the album name for the MP3 files                            |
| `-r`, `--artist` | Sets the artist name for the MP3 files                           |
| `-g`, `--genre`  | Sets the genre (e.g., Rock, Jazz, Classical) for the MP3 files   |
| `--rating`       | Sets a user-defined rating (1-5 stars) for the MP3 files         |
| `--cover-art`    | Embeds a cover art image (JPG or PNG) into the MP3 files         |
| `-y`, `--year`  | Sets the year (e.g., 2023) for the MP3 files |
| `--show`         | Displays the current metadata of the MP3 files                   |
| `--html`         | Outputs the metadata in HTML format                              |
| `--fetch-metadata` | Fetches metadata (album artist, track numbers, year, cover art) from MusicBrainz for MP3 files. Uses existing artist and album tags to search. |
| `-R`, `--recursive` | Recursively process files in subdirectories. If not set, only files in the specified folder (non-recursive) are processed. |
| `-h`, `--help`   | Shows the help message and exits.                                |

### Examples

- **Update album, artist, and genre for all MP3s in a folder:**
  ```sh
  python tag_album.py -f /path/to/folder -a "Album Name" -r "Artist Name" -g "Rock"
  ```
- **Set a 5-star rating for all MP3s in a folder:**
  ```sh
  python tag_album.py -f /path/to/folder --rating 5
  ```
- **Embed cover art into all MP3s in a folder:**
  ```sh
  python tag_album.py -f /path/to/folder --cover-art /path/to/cover.jpg
  ```
- **Set the year for all MP3s in a folder:**
  ```sh
  python tag_album.py -f /path/to/folder -y "2023"
  ```
- **Show all MP3 files and their metadata in plain text:**
  ```sh
  python tag_album.py -f /music/rock/ --show
  ```
- **Show all MP3 files and their metadata in HTML:**
  ```sh
  python tag_album.py -f /music/rock/ --show --html
  ```
- **Recursively update album for all MP3s in a folder and its subfolders:**
  ```sh
  python tag_album.py -f /path/to/folder -a "New Album for All" -R
  ```
- **Show the help message:**
  ```sh
  python3 tag_album.py --help
  ```

# How to Install and Run

## Fetching Metadata from MusicBrainz

The script can fetch metadata for your MP3 files from MusicBrainz, an open music encyclopedia. This requires the files to have existing, reasonably accurate artist and album tags for the search to be effective.

### Fetching All Standard Metadata (`--fetch-metadata`)

This option attempts to fetch a comprehensive set of standard metadata from MusicBrainz and update your files. This includes:
- Album Artist
- Track Number and Total Tracks
- Year
- Cover Art

**Usage Example:**
```sh
python3 tag_album.py --folder /path/to/music --fetch-metadata
```
To process recursively:
```sh
python3 tag_album.py --folder /path/to/music --fetch-metadata -R
```

### Fetching Specific Metadata Fields (`--fetch-and-set-from-mb`)

This option allows you to fetch and update only specific metadata fields from MusicBrainz.

-   **Purpose**: To selectively update your MP3 tags with information from MusicBrainz.
-   **Supported Fields**: `artist`, `album`, `genre`, `year`, `coverart`, `tracknumber`, `albumartist`.
-   **Providing Fields**: Supply the fields as a comma-separated string.
-   **Quoting**: If your list of fields contains spaces (e.g., around the commas), you **must** quote the entire string. For example: `--fetch-and-set-from-mb "artist, album, genre"`.

**Usage Example:**
To fetch and set only the album, artist, and genre for all MP3s in a folder (and its subfolders recursively):
```sh
python3 tag_album.py --folder /path/to/music --fetch-and-set-from-mb "album, artist, genre" -R
```

### Automatic Field Fetching (`--auto`)

The `--auto` option provides a convenient way to fetch a predefined set of common tags.

-   **Purpose**: Acts as a shortcut for `--fetch-and-set-from-mb "artist, genre, album, title"`.
-   **Behavior**: If `--auto` is used, the script will attempt to fetch and set `artist`, `genre`, `album`, and `title` for your MP3 files.
-   **Precedence**: If you provide specific fields via `--fetch-and-set-from-mb`, those will be used instead, even if `--auto` is also present.

**Usage Example:**
To automatically fetch and set the default fields (artist, genre, album, title) for all MP3s in a folder and its subfolders:
```sh
python3 tag_album.py --folder /path/to/music --auto -R
```

## Setting up the Environment

To set up a virtual environment and install the required packages for `tag_album.py`, follow these steps:

1. **Create a virtual environment named `.venv`:**
    ```sh
    python -m venv .venv
    ```

2. **Activate the Virtual Environment:**
    - On Windows:
      ```sh
      .venv\Scripts\activate
      ```
    - On Unix or MacOS:
      ```sh
      source .venv/bin/activate
      ```

3. **Install the Required Packages:**
    ```sh
    pip install -r requirements.txt
    ```

Make sure you have a `requirements.txt` file in the same directory as `tag_album.py` with all the necessary dependencies listed.

Once the virtual environment is set up and the packages are installed, you can run the script as shown in the example usage sections.
