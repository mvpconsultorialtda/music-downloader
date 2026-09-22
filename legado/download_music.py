import yt_dlp
import os
import glob
import json
import static_ffmpeg

# --- PO Token (obrigatorio desde ago/2026) ---------------------------------
# O YouTube passou a exigir um "Proof of Origin Token" nos clientes web. Sem
# ele o yt-dlp cai no cliente android_vr, cujas URLs de midia retornam HTTP 403.
# O token e gerado pelo servidor bgutil, que precisa estar no ar antes do
# download. Ver docs/DOC-TECNICO.md ("Setup do PO Token").
POT_SERVER_URL = 'http://127.0.0.1:4416'
POT_SERVER_HOME = os.path.expanduser('~/bgutil-ytdlp-pot-provider/server')
JS_RUNTIME = 'node'  # necessario para resolver os desafios JS do YouTube


def pot_server_alive(timeout=3):
    """Retorna True se o servidor de PO Token responde no /ping."""
    import urllib.request
    try:
        with urllib.request.urlopen(f'{POT_SERVER_URL}/ping', timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_pot_server(wait_seconds=60):
    """Garante o servidor de PO Token no ar; sobe em background se preciso.

    Retorna True se o servidor esta respondendo ao final.
    """
    import subprocess
    import time

    if pot_server_alive():
        print(f'[POT] Servidor ja ativo em {POT_SERVER_URL}')
        return True

    main_js = os.path.join(POT_SERVER_HOME, 'build', 'main.js')
    if not os.path.exists(main_js):
        print(f'[POT] AVISO: servidor nao encontrado em {main_js}\n'
              f'[POT] Downloads vao falhar com HTTP 403. '
              f'Veja docs/DOC-TECNICO.md para o setup.')
        return False

    print(f'[POT] Subindo servidor: node {main_js}')
    create_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    subprocess.Popen([JS_RUNTIME, main_js],
                     cwd=POT_SERVER_HOME,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=create_flags)

    for _ in range(wait_seconds):
        if pot_server_alive():
            print('[POT] Servidor pronto.')
            return True
        time.sleep(1)

    print('[POT] AVISO: servidor nao respondeu a tempo. Downloads podem falhar.')
    return False

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

def _build_ydl_opts(config, output_dir):
    """Build yt-dlp options dict with all filters."""
    filter_after_2025 = config.get('filter_after_2025', False)
    allowed_channels = config.get('allowed_channels', [])

    def combined_filter(info, *, incomplete=False):
        if check_history(info):
            return 'Video already in history'
        if filter_after_2025:
            result = date_filter(info, incomplete=incomplete)
            if result:
                return result
        if allowed_channels:
            channel = info.get('channel') or info.get('uploader') or ''
            # Skip channel check when channel is empty (search/incomplete phase)
            if channel and not any(ch.lower() in channel.lower() for ch in allowed_channels):
                return f'Channel "{channel}" not in allowed list'
        return None

    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(title)s - %(upload_date>%d-%m-%Y)s.%(ext)s',
        'default_search': 'ytsearch10',
        'max_downloads': 1,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'restrictfilenames': True,
        'progress_hooks': [progress_hook],
        'match_filter': combined_filter,
        # Sem runtime JS o YouTube nao entrega os formatos do cliente web.
        # A API Python espera {runtime: {config}}, nao a lista do CLI.
        'js_runtimes': {JS_RUNTIME: {}},
    }


def download_single(query, config, output_dir):
    """Download a single query using its own yt-dlp instance (thread-safe)."""
    ydl_opts = _build_ydl_opts(config, output_dir)
    label = "direct URL" if query.startswith('http') else "search"
    print(f"\n--- [{label}] {query} ---")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
    except Exception as e:
        print(f"Error downloading '{query}': {e}")


def download_audio(query_list, sequential_first=3, parallel_workers=5):
    """Download sequentially for the first N queries, then in parallel for the rest.

    Args:
        query_list: list of search queries or URLs
        sequential_first: how many to download one-by-one before going parallel
        parallel_workers: max concurrent workers for the parallel batch
    """
    import concurrent.futures

    print("Initializing FFmpeg...")
    static_ffmpeg.add_paths()

    ensure_pot_server()

    populate_history_from_disk()

    config = load_config()
    output_dir = config.get('output_dir', 'output')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if config.get('filter_after_2025', False):
        print("Date filter enabled: strict 2025 only")

    sequential_queries = query_list[:sequential_first]
    parallel_queries = query_list[sequential_first:]

    # --- Sequential phase ---
    print(f"\n=== FASE SEQUENCIAL: {len(sequential_queries)} faixas ===")
    for i, query in enumerate(sequential_queries, 1):
        print(f"\n[{i}/{len(sequential_queries)}] Sequencial:")
        download_single(query, config, output_dir)

    if not parallel_queries:
        return

    # --- Parallel phase ---
    print(f"\n=== FASE PARALELA: {len(parallel_queries)} faixas ({parallel_workers} workers) ===")
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_workers) as executor:
        futures = {
            executor.submit(download_single, q, config, output_dir): q
            for q in parallel_queries
        }
        for future in concurrent.futures.as_completed(futures):
            q = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[Paralelo] Erro em '{q}': {e}")


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    print("Reading queries from 'input' directory...")
    queries = load_queries()

    if not queries:
        print("No queries found in 'input/*.txt'. Please add some search terms to download.")
    else:
        print(f"Found {len(queries)} queries.")
        print("Estrategia: 1 → 2 → 3 sequencial, depois 17 em paralelo (5 workers)\n")
        download_audio(queries, sequential_first=3, parallel_workers=5)
        print("\nAll downloads processed. Check the 'output' folder.")
