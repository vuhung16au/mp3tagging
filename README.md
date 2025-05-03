# tag-album.py

`tag-album.py` is a tool for batch updating the album and artist metadata of MP3 files in a specified folder.

# How to Use

You can use `tag-album.py` to update the album and artist tags of all MP3 files in a folder, or to simply display the current metadata. The script supports both short and long options for flexibility.

## Options and Arguments

| Argument   | Description                                      |
|------------|--------------------------------------------------|
| `-f`, `--folder` | Specifies the folder containing MP3 files        |
| `-a`, `--album`  | Sets the album name for the MP3 files            |
| `-r`, `--artist` | Sets the artist name for the MP3 files           |
| `--show`   | Displays the current metadata of the MP3 files   |
| `--html`   | Outputs the metadata in HTML format              |

### Examples

- **Update album and artist for all MP3s in a folder:**
  ```sh
  python tag-album.py -f /path/to/folder -a "Album Name" -r "Artist Name"
  ```
- **Show all MP3 files and their metadata in plain text:**
  ```sh
  python tag-album.py -f /music/rock/ --show
  ```
- **Show all MP3 files and their metadata in HTML:**
  ```sh
  python tag-album.py -f /music/rock/ --show --html
  ```

# How to Install and Run

To set up a virtual environment and install the required packages for `tag-album.py`, follow these steps:

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

Make sure you have a `requirements.txt` file in the same directory as `tag-album.py` with all the necessary dependencies listed.

Once the virtual environment is set up and the packages are installed, you can run the script as shown in the example usage section.
