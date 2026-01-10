import yt_dlp
import os
import static_ffmpeg

def download_songs(song_list):
    # Ensure ffmpeg is available
    print("Initializing FFmpeg...")
    static_ffmpeg.add_paths()

    # Create output directory if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'output/%(title)s.%(ext)s',
        'default_search': 'ytsearch',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for song in song_list:
            try:
                print(f"\n--- Searching and downloading: {song} ---")
                ydl.download([song])
            except Exception as e:
                print(f"Error downloading {song}: {e}")

if __name__ == "__main__":
    songs = [
        # NEFFEX Tracks
        "NEFFEX - Destiny",
        "NEFFEX - Fight Back",
        "NEFFEX - Grateful",
        "NEFFEX - Best of Me",
        "NEFFEX - Careless",
        "NEFFEX - Cold",
        "NEFFEX - Failure",
        "NEFFEX - Soldier",
        "NEFFEX - Rumors",
        
        # Basketball / Hype Tracks
        "Eminem - Lose Yourself",
        "Fort Minor - Remember the Name",
        "Kanye West - Power",
        "Quad City DJ's - Space Jam",
        "Alan Parsons Project - Sirius (Chicago Bulls Theme)",
        "Kurtis Blow - Basketball",
        "Nelly - Heart of a Champion",
        "Kanye West - Amazing",
        "Survivor - Eye of the Tiger",
        "Drake - Forever"
    ]
    
    print(f"Starting download of {len(songs)} songs...")
    download_songs(songs)
    print("\nAll downloads processed. Check the 'output' folder.")
