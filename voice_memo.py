#!/usr/bin/env python3
import argparse
import datetime
import glob
import os
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
ROOT = Path("~/Library/Group Containers/group.com.apple.VoiceMemos.shared").expanduser()
AUDIO_DIR = ROOT / "Recordings"
DB_PATH = AUDIO_DIR / "CloudRecordings.db"
DESKTOP = Path("~/Desktop").expanduser()
# Added TRANSCRIPT_DIR
TRANSCRIPT_DIR = Path("/Volumes/ExDrive/Data/env/script/python/merge_voicememo/transcript")

def ensure_dirs():
    """Ensure necessary directories exist."""
    if not TRANSCRIPT_DIR.exists():
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed. Please install it via Homebrew: brew install ffmpeg")
        sys.exit(1)

def merge_recordings():
    check_ffmpeg()
    
    # Get all .m4a files
    all_m4a = list(AUDIO_DIR.glob("*.m4a"))
    
    # Separate merge files and normal files
    merge_files = sorted([f for f in all_m4a if f.name.startswith("merge_")], key=lambda f: f.stat().st_birthtime)
    normal_files = [f for f in all_m4a if not f.name.startswith("merge_")]
    
    # Only use the latest merge file to avoid duplication in subsequent merges
    files_to_merge = []
    if merge_files:
        files_to_merge.append(merge_files[-1]) # Use only the most recent merge
    files_to_merge.extend(normal_files)
    
    # Sort by birthtime to maintain chronological order
    files_to_merge.sort(key=lambda f: f.stat().st_birthtime)
    
    if not files_to_merge:
        print("No recordings found to merge.")
        return
    
    # If there's only one file and it's already a merge file, nothing to do
    if len(files_to_merge) == 1 and files_to_merge[0].name.startswith("merge_"):
        print(f"Only the existing merge file found: {files_to_merge[0].name}. No new recordings to add.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"merge_{timestamp}.m4a"
    output_path = AUDIO_DIR / output_filename
    
    # Create temp file list for ffmpeg concat
    list_file = AUDIO_DIR / "concat_list.txt"
    try:
        with open(list_file, "w") as f:
            for m4a in files_to_merge:
                # ffmpeg requires escaped paths or single quotes for files
                f.write(f"file '{m4a.absolute()}'\n")
        
        print(f"Merging {len(files_to_merge)} files into {output_filename}...")
        
        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", 
            "-i", str(list_file), 
            "-c", "copy", 
            str(output_path),
            "-y" # Overwrite if exists
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Success! Output: {output_path}")
        
        # Open in Finder and highlight
        subprocess.run(["open", "-R", str(output_path)])
        
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg execution: {e.stderr.decode()}")
    finally:
        if list_file.exists():
            list_file.unlink()

def process_transcripts():
    """Transcribe recent recordings and merge the text files."""
    ensure_dirs()
    
    # 1. Target Files
    normal_files = [f for f in AUDIO_DIR.glob("*.m4a") if "merge_" not in f.name]
    normal_files.sort(key=lambda f: f.stat().st_birthtime)
    
    if not normal_files:
        print("No recordings found to transcribe.")
        return

    env = os.environ.copy()
    env["UV_CACHE_DIR"] = "/Volumes/ExDrive/Users/mkatsjp/.cache/uv"
    env["HF_HOME"] = "/Volumes/ExDrive/Users/mkatsjp/.cache/huggingface"

    for m4a in normal_files:
        print(f"Transcribing {m4a.name}...")
        
        # 2. Individual Transcription
        # We use a single-quoted string for the path in the python command to handle spaces
        py_cmd = f'import mlx_whisper; res = mlx_whisper.transcribe(r"""{m4a.absolute()}""", path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="ja"); print(res["text"])'
        cmd = [
            "uv", "run", "--with", "mlx-whisper", "python", "-c", py_cmd
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
            transcript_text = result.stdout.strip()
            
            # 3. Save Individual Text
            txt_filename = f"{m4a.stem}.txt"
            txt_path = TRANSCRIPT_DIR / txt_filename
            
            header = f"【録音日時】 {m4a.stem}\n"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(header + transcript_text + "\n")
            
            print(f"Saved: {txt_filename}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error transcribing {m4a.name}: {e.stderr}")

    # 4. Merge Text
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_filename = f"merged_transcript_{timestamp}.txt"
    merged_path = TRANSCRIPT_DIR / merged_filename
    
    all_txt_files = sorted(list(TRANSCRIPT_DIR.glob("*.txt")), key=lambda f: f.stat().st_mtime)
    # Exclude previously merged files
    all_txt_files = [f for f in all_txt_files if not f.name.startswith("merged_transcript_")]

    if all_txt_files:
        print(f"Merging {len(all_txt_files)} transcript files...")
        with open(merged_path, "w", encoding="utf-8") as outfile:
            for i, txt_f in enumerate(all_txt_files):
                with open(txt_f, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
                    if i < len(all_txt_files) - 1:
                        outfile.write("\n" + "="*40 + "\n\n")
        
        print(f"Success! Merged transcript: {merged_path}")
        
        # 5. Highlight in Finder
        subprocess.run(["open", "-R", str(merged_path)])

def kill_voicememos():
    try:
        # Check if the process is running first to avoid "no process found" error message in some environments
        subprocess.run(["killall", "VoiceMemos"], capture_output=True)
        print("Closed VoiceMemos app.")
    except Exception:
        pass

def delete_intermediates():
    # Delete .m4a and .waveform files not starting with 'merge_'
    targets = list(AUDIO_DIR.glob("*.m4a")) + list(AUDIO_DIR.glob("*.waveform"))
    count = 0
    for f in targets:
        if not f.name.startswith("merge_"):
            f.unlink()
            count += 1
    print(f"Deleted {count} intermediate files.")

    # Kill app before deleting DB
    kill_voicememos()

    # Also delete DB files to refresh view in app
    db_files = [
        DB_PATH,
        AUDIO_DIR / "CloudRecordings.db-shm",
        AUDIO_DIR / "CloudRecordings.db-wal"
    ]
    for db_f in db_files:
        if db_f.exists():
            db_f.unlink()
            print(f"Deleted {db_f.name}")

def reset_all():
    print("Resetting VoiceMemos (deleting EVERYTHING)...")
    
    # 1. Kill VoiceMemos app
    kill_voicememos()
    
    # 2. Delete all files in Recordings (including merge_ files)
    targets = list(AUDIO_DIR.glob("*"))
    count = 0
    for f in targets:
        if f.is_file():
            f.unlink()
            count += 1
    print(f"Cleared {count} files from Recordings folder.")
    
    # 3. Delete any legacy merge files on Desktop
    desktop_merges = list(DESKTOP.glob("merge_*.m4a"))
    for f in desktop_merges:
        f.unlink()
        print(f"Deleted from Desktop: {f.name}")

    # 4. Delete DB files
    db_files = [
        DB_PATH,
        AUDIO_DIR / "CloudRecordings.db-shm",
        AUDIO_DIR / "CloudRecordings.db-wal"
    ]

    # 5. Delete all transcript text files
    if TRANSCRIPT_DIR.exists():
        txt_targets = list(TRANSCRIPT_DIR.glob("*.txt"))
        txt_count = 0
        for f in txt_targets:
            f.unlink()
            txt_count += 1
        print(f"Cleared {txt_count} files from Transcript folder.")    

    for db_f in db_files:
        if db_f.exists():
            db_f.unlink()
            print(f"Deleted {db_f.name}")

def list_files():
    """List all current audio recordings and transcribed text files."""
    # 1. Audio Recordings
    print("=== Audio Recordings ===")
    total_audio_size = 0
    if AUDIO_DIR.exists():
        m4a_files = sorted(list(AUDIO_DIR.glob("*.m4a")), key=lambda f: f.stat().st_birthtime)
        if not m4a_files:
            print("No .m4a files found.")
        else:
            for f in m4a_files:
                birth_time = datetime.datetime.fromtimestamp(f.stat().st_birthtime).strftime("%Y-%m-%d %H:%M:%S")
                size = f.stat().st_size
                total_audio_size += size
                label = " (Merged Audio)" if f.name.startswith("merge_") else ""
                print(f"[{birth_time}] {f.name}{label}")
    else:
        print("No .m4a files found.")

    # 2. Transcribed Texts
    print("\n=== Transcribed Texts ===")
    total_txt_size = 0
    if TRANSCRIPT_DIR.exists():
        txt_files = sorted(list(TRANSCRIPT_DIR.glob("*.txt")), key=lambda f: f.stat().st_birthtime)
        if not txt_files:
            print("No .txt files found.")
        else:
            for f in txt_files:
                birth_time = datetime.datetime.fromtimestamp(f.stat().st_birthtime).strftime("%Y-%m-%d %H:%M:%S")
                size = f.stat().st_size
                total_txt_size += size
                label = " (Merged Text)" if f.name.startswith("merged_transcript_") else ""
                print(f"[{birth_time}] {f.name}{label}")
    else:
        print("No .txt files found.")
        
    # 3. Total Sizes
    print(f"\nTotal Audio Size: {total_audio_size / (1024 * 1024):.2f} MB")
    print(f"Total Transcript Size: {total_txt_size / (1024 * 1024):.2f} MB")

def main():
    parser = argparse.ArgumentParser(description="voiceMemo: Voice Memos helper tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--merge", action="store_true", help="Merge all recent recordings")
    group.add_argument("--transcribe", action="store_true", help="Transcribe recent recordings and merge the text files")
    group.add_argument("--list", action="store_true", help="List all current audio recordings and transcribed text files")
    group.add_argument("--del", dest="delete", action="store_true", help="Delete intermediate files")
    group.add_argument("--delall", action="store_true", help="Reset all recordings and database")
    group.add_argument("--open", choices=["voice", "v", "text", "t"], help="Open directory in Finder (voice/v or text/t)")
    
    args = parser.parse_args()
    
    if not AUDIO_DIR.exists():
        print(f"Error: Recordings directory not found at {AUDIO_DIR}")
        sys.exit(1)
        
    if args.merge:
        merge_recordings()
    elif args.transcribe:
        process_transcripts()
    elif args.list:
        list_files()
    elif args.delete:
        delete_intermediates()
    elif args.delall:
        reset_all()
    elif args.open:
        if args.open in ["voice", "v"]:
            print(f"Opening audio directory: {AUDIO_DIR}")
            subprocess.run(["open", str(AUDIO_DIR)])
        elif args.open in ["text", "t"]:
            ensure_dirs()
            print(f"Opening transcript directory: {TRANSCRIPT_DIR}")
            subprocess.run(["open", str(TRANSCRIPT_DIR)])

if __name__ == "__main__":
    main()
