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

## Logging

This script utilizes Python's standard `logging` module to record its operations and any issues encountered.

-   **Log File**: All log messages are saved to a file named `mp3tagging.log`, which is created in the same directory from where the script is executed.
-   **Information Logged**:
    -   Details of successful operations, such as when tags are successfully set for a file.
    -   Errors that occur during processing, for instance, if a file cannot be loaded or a tag cannot be written.
    -   Summary messages at the end of batch operations (e.g., "Finished artist tagging operation. Processed X files, Y errors.").
-   **Log Levels**:
    -   The console output provides a summary of important events and errors (INFO level and above).
    -   The `mp3tagging.log` file contains more detailed information, including DEBUG level messages, which can be helpful for in-depth troubleshooting.
-   **Purpose**: These logs are useful for tracking the script's activity, verifying changes made to your files, and diagnosing any problems that may arise.

# How to Install and Run

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

Once the virtual environment is set up and the packages are installed, you can run the script as shown in the example usage section.
