import yt_dlp
import os
import glob
import json
import static_ffmpeg

def load_config():
    """Loads configuration from config.json."""
    config_path = 'config.json'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config: {e}")
    return {}

def load_queries():
    """Reads all .txt files in the input directory and returns a list of search queries."""
    queries = []
    input_dir = 'input'
    
    if not os.path.exists(input_dir):
        print(f"Directory '{input_dir}' not found. Creating it...")
        os.makedirs(input_dir)
        return []

    txt_files = glob.glob(os.path.join(input_dir, '*.txt'))
    
    for file_path in txt_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                queries.extend(lines)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
    return queries

def date_filter(info, *, incomplete=False):
    """Filters videos based on upload date being exactly in 2025."""
    upload_date = info.get('upload_date')
    if upload_date:
        year = upload_date[:4]
        if year < '2025':
            return 'Video is too old (before 2025)'
        if year > '2025':
            return 'Video is too new (after 2025)'
    return None

def download_audio(query_list):
    # Ensure ffmpeg is available
    print("Initializing FFmpeg...")
    static_ffmpeg.add_paths()
    
    config = load_config()
    filter_after_2025 = config.get('filter_after_2025', False)

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
        # Using >%d-%m-%Y for Brazilian format Day-Month-Year
        'outtmpl': 'output/%(title)s - %(upload_date>%d-%m-%Y)s.%(ext)s',
        # Search top 10 results to find one that matches the date filter
        'default_search': 'ytsearch10',
        'max_downloads': 1, # Stop after downloading 1 matching video per query
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'restrictfilenames': True,
    }
    
    if filter_after_2025:
        print("Date filter enabled: strict check for > 2025-01-01")
        ydl_opts['match_filter'] = date_filter

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in query_list:
            # Check if it's a direct URL or a search query
            if query.startswith('http://') or query.startswith('https://'):
                # Direct URL - download as-is
                search_query = query
                print(f"\n--- Downloading direct URL: {search_query} ---")
            else:
                # Search query - prepend with search
                search_query = query
                print(f"\n--- Searching and downloading: {search_query} ---")
            
            try:
                ydl.download([search_query])
            except Exception as e:
                print(f"Error downloading {search_query}: {e}")


HISTORY_FILE = 'history.json'

def load_history():
    """Loads download history from history.json."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('downloaded', [])
        except Exception as e:
            print(f"Error reading history: {e}")
    return []

def save_history_entry(entry):
    """Appends a new entry to history.json."""
    history = load_history()
    # Check for duplicates before appending (by ID or URL)
    if not any(item.get('id') == entry.get('id') for item in history):
        history.append(entry)
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({'downloaded': history}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")

def populate_history_from_disk():
    """Scans output directory and populates history with existing files."""
    history = load_history()
    existing_titles = {item.get('title') for item in history}
    
    config = load_config()
    output_dir = config.get('output_dir', 'output')
    
    if not os.path.exists(output_dir):
        return

    # Pattern: title - date.mp3 (roughly)
    # We'll just take the filename root as title for simplicity if verifying presence
    # Ideally we'd map filename back to video ID, but that's hard without metadata in filename.
    # For now, let's just use filenames as a "title" proxy to avoid re-downloading exact matches?
    # Better approach: We can't easily rebuild ID/URL from filename. 
    # But we can check if a file with similar name exists. 
    
    # Actually, user request said: "olhe os nomes dos videos... crie um dicionário... caso tenha a url correspondente"
    # "se o video tiver incluso ou na url ou se tiverem o mesmo nome, deve escolher outro"
    
    # So we should load filenames into history as titles if not present.
    files = glob.glob(os.path.join(output_dir, '*.mp3'))
    new_entries = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        # remove extension
        name_only = os.path.splitext(filename)[0]
        # remove split part suffix if present
        if "_part" in name_only:
             continue
             
        if name_only not in existing_titles:
            print(f"Adding existing file to history: {name_only}")
            new_entries.append({'title': name_only, 'source': 'disk_scan'})
            existing_titles.add(name_only)
            
    if new_entries:
        history.extend(new_entries)
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({'downloaded': history}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history from disk: {e}")

def check_history(info_dict):
    """Check if video is in history."""
    history = load_history()
    title = info_dict.get('title')
    webpage_url = info_dict.get('webpage_url')
    video_id = info_dict.get('id')
    
    for item in history:
        # Check ID match
        if video_id and item.get('id') == video_id:
            return True
        # Check URL match
        if webpage_url and item.get('url') == webpage_url:
            return True
        # Check Title match (fuzzy or exact? User said "mesmo nome")
        # Existing files on disk don't have ID/URL, only Title (filename).
        # We need to compare title with filename history.
        # But yt-dlp 'title' might differ from filename (due to sanitization).
        # Let's try simple inclusion or exact match.
        if title and item.get('title') and (title in item.get('title') or item.get('title') in title):
             return True
             
    return False

def progress_hook(d):
    """Hook to save history after successful download."""
    if d['status'] == 'finished':
        info = d.get('info_dict')
        if info:
            entry = {
                'title': info.get('title'),
                'id': info.get('id'),
                'url': info.get('webpage_url'),
                'filename': os.path.basename(d.get('filename'))
            }
            print(f"\n[History] Saving verified download: {entry['title']}")
            save_history_entry(entry)

def download_audio(query_list):
    # Ensure ffmpeg is available
    print("Initializing FFmpeg...")
    static_ffmpeg.add_paths()
    
    # Populate history from existing files first
    populate_history_from_disk()
    
    config = load_config()
    filter_after_2025 = config.get('filter_after_2025', False)
    output_dir = config.get('output_dir', 'output')

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # Using >%d-%m-%Y for Brazilian format Day-Month-Year
        'outtmpl': f'{output_dir}/%(title)s - %(upload_date>%d-%m-%Y)s.%(ext)s',
        # Search top 10 results to find one that matches the date filter
        'default_search': 'ytsearch10',
        'max_downloads': 1, # Stop after downloading 1 matching video per query
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'restrictfilenames': True,
        'progress_hooks': [progress_hook],
        'match_filter': lambda info, incomplete=False: 'Video already in history' if check_history(info) else None
    }
    
    if filter_after_2025:
        print("Date filter enabled: strict check for > 2025-01-01")
        # Chain filters not easily supported in simple config, let's wrap logic
        # Or just add logic inside match_filter
        pass

    allowed_channels = config.get('allowed_channels', [])

    # Wrap filters
    def combined_filter(info, *, incomplete=False):
        if check_history(info):
            return 'Video already in history'
        if filter_after_2025:
            result = date_filter(info, incomplete=incomplete)
            if result:
                return result
        if allowed_channels:
            channel = info.get('channel') or info.get('uploader') or ''
            if not any(ch.lower() in channel.lower() for ch in allowed_channels):
                return f'Channel "{channel}" not in allowed list'
        return None
        
    ydl_opts['match_filter'] = combined_filter

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in query_list:
            # Check if it's a direct URL or a search query
            if query.startswith('http://') or query.startswith('https://'):
                # Direct URL - download as-is
                search_query = query
                print(f"\n--- Downloading direct URL: {search_query} ---")
            else:
                # Search query - prepend with search
                search_query = query
                print(f"\n--- Searching and downloading: {search_query} ---")
            
            try:
                ydl.download([search_query])
            except Exception as e:
                print(f"Error downloading {search_query}: {e}")

if __name__ == "__main__":
    import sys
    # Handle Unicode characters in console output
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Fallback for older python versions
            pass

    print("Reading queries from 'input' directory...")
    queries = load_queries()
    
    if not queries:
        print("No queries found in 'input/*.txt'. Please add some search terms to download.")
    else:
        print(f"Found {len(queries)} queries: {queries}")
        print(f"Starting download...")
        download_audio(queries)
        print("\nAll downloads processed. Check the 'output' folder.")
