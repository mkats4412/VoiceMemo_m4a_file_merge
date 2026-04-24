#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import datetime
import glob
from pathlib import Path

# --- Configuration ---
ROOT = Path("~/Library/Group Containers/group.com.apple.VoiceMemos.shared").expanduser()
AUDIO_DIR = ROOT / "Recordings"
DB_PATH = AUDIO_DIR / "CloudRecordings.db"
DESKTOP = Path("~/Desktop").expanduser()

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
    for db_f in db_files:
        if db_f.exists():
            db_f.unlink()
            print(f"Deleted {db_f.name}")

def main():
    parser = argparse.ArgumentParser(description="voiceMemo: Voice Memos helper tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--merge", action="store_true", help="Merge all recent recordings")
    group.add_argument("--del", dest="delete", action="store_true", help="Delete intermediate files")
    group.add_argument("--delall", action="store_true", help="Reset all recordings and database")
    
    args = parser.parse_args()
    
    if not AUDIO_DIR.exists():
        print(f"Error: Recordings directory not found at {AUDIO_DIR}")
        sys.exit(1)
        
    if args.merge:
        merge_recordings()
    elif args.delete:
        delete_intermediates()
    elif args.delall:
        reset_all()

if __name__ == "__main__":
    main()
