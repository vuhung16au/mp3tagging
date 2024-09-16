
# tag-album.py

`tag-album.py` is a tool for batch updating the album and artist metadata of MP3 files in a specified folder.

# Typical Use Cases 

This tool helps MP3 players, such as VLC, organize music files better by:
- Sorting MP3 files into the correct albums
- Sorting MP3 files by the correct artist

# Example usage

```sh
# Basic usage
python tag-album.py -f /path/to/folder -a "Album Name" -r "Artist Name"

# Example with specific folder and album/artist names
python tag-album.py -f /music/rock/ -a "Greatest Hits" -r "Queen"

# Example with a different folder and album/artist names
python tag-album.py -f /music/pop/ -a "Future Nostalgia" -r "Dua Lipa"
```

# Options and Arguments 

| Argument   | Description                                      |
|------------|--------------------------------------------------|
| `-f`       | Specifies the folder containing MP3 files        |
| `-a`       | Sets the album name for the MP3 files            |
| `-r`       | Sets the artist name for the MP3 files           |
| `--folder` | Specifies the folder containing MP3 files        |
| `--album`  | Sets the album name for the MP3 files            |
| `--artist` | Sets the artist name for the MP3 files           |
| `--show`   | Displays the current metadata of the MP3 files   |
| `--html`   | Outputs the metadata in HTML format              |

# How to Install and Run 

To set up a virtual environment and install the required packages for `tag-album.py`, follow these steps:

1. **Create a virtual environment**:
    ```sh
    python -m venv env
    ```

2. **Activate the virtual environment**:
    - On Windows:
      ```sh
      .\env\Scripts\activate
      ```
    - On Unix or MacOS:
      ```sh
      source env/bin/activate
      ```

3. **Install the required packages**:
    ```sh
    pip install -r requirements.txt
    ```

Make sure you have a `requirements.txt` file in the same directory as `tag-album.py` with all the necessary dependencies listed.

Once the virtual environment is set up and the packages are installed, you can run the script as shown in the example usage section.
