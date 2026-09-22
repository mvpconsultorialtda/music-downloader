import os
import subprocess
import glob
import static_ffmpeg

def get_duration(file_path):
    """Returns the duration of an audio file in seconds using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return 0

def split_audio():
    print("Initializing FFmpeg...")
    static_ffmpeg.add_paths()
    
    import json
    
    config_path = 'config.json'
    config = {}
    output_dir = 'output'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                output_dir = config.get('output_dir', 'output')
        except Exception as e:
            print(f"Error reading config: {e}")

    split_enabled = config.get('split_enabled', True)
    if not split_enabled:
        print("Split is disabled in config.json (split_enabled: false). Skipping.")
        return

    split_threshold = config.get('split_threshold_minutes', 20) * 60
    split_max = config.get('split_max_minutes', 15) * 60
    split_min = config.get('split_min_minutes', 5) * 60

    if not os.path.exists(output_dir):
        print(f"Directory '{output_dir}' not found.")
        return

    # Find all mp3 files in the output directory
    files = glob.glob(os.path.join(output_dir, '*.mp3'))
    files = [f for f in files if "_part" not in os.path.basename(f)]
    
    if not files:
        print("No .mp3 files found in output directory.")
        return

    print(f"Found {len(files)} files to process.")

    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"\nProcessing: {filename}")
        
        duration = get_duration(file_path)
        if duration == 0:
            continue
            
        print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
        if duration <= split_threshold:
            print(f"File is {split_threshold/60:.0f} minutes or less. Skipping split.")
            continue
            
        file_root, ext = os.path.splitext(filename)
        
        # Logic for parts:
        # We want to split into max 15m (900s) chunks.
        # But ensure every part is min 5m (300s).
        
        current_start = 0
        part_idx = 0
        
        while current_start < duration:
            remaining = duration - current_start
            
            if remaining <= split_max:
                target_duration = remaining
            else:
                if (remaining - split_max) < split_min:
                    target_duration = remaining - split_min
                else:
                    target_duration = split_max
            
            # Perform the split for this chunk
            output_file = os.path.join(output_dir, f"{file_root}_part{part_idx:03d}{ext}")
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(current_start),
                '-t', str(target_duration),
                '-i', file_path,
                '-c', 'copy',
                output_file
            ]
            
            try:
                print(f"Creating part {part_idx} ({target_duration/60:.2f} min)...")
                subprocess.run(cmd, check=True, capture_output=True)
                current_start += target_duration
                part_idx += 1
            except subprocess.CalledProcessError as e:
                print(f"Error splitting {filename} at {current_start}: {e}")
                break
                
        print(f"Successfully split {filename} into {part_idx} parts.")
            
if __name__ == "__main__":
    import sys
    # Handle Unicode characters in console output
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Fallback for older python versions
            pass
    split_audio()
