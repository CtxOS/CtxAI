#!/usr/bin/env python3
import os
import time
import sys
import re

def get_disk_usage(path='/'):
    try:
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = total - free
        return int((used / total) * 100)
    except Exception:
        return 0

def clean_disk_space(threshold=90, max_age_days=7, dry_run=False):
    usage = get_disk_usage()
    print(f"Current disk usage: {usage}% (Threshold: {threshold}%, Max Age: {max_age_days} days)")
    
    if usage < threshold:
        print("Disk usage is within limits. No cleaning needed.")
        return

    print(f"Disk usage {usage}% exceeds threshold {threshold}%. Starting cleanup...")
    
    # Base directories relative to current file location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    targets = [
        os.path.join(base_dir, "logs"),
        os.path.join(base_dir, "tmp"),
        os.path.join(base_dir, "usr", "temp"),
        os.path.join(base_dir, ".cache"),  # Added .cache
    ]
    
    now = time.time()
    seconds_in_day = 86400
    total_deleted = 0
    total_size = 0

    for target_dir in targets:
        if not os.path.exists(target_dir):
            continue
            
        print(f"Cleaning directory: {target_dir}")
        for root, dirs, fnames in os.walk(target_dir):
            for name in fnames:
                if name == ".gitkeep":
                    continue
                
                file_path = os.path.join(root, name)
                try:
                    mtime = os.path.getmtime(file_path)
                    age_days = (now - mtime) / seconds_in_day
                    
                    if age_days > max_age_days:
                        size = os.path.getsize(file_path)
                        total_size += size
                        total_deleted += 1
                        
                        if dry_run:
                            print(f"[Dry Run] Would delete: {file_path} ({size} bytes, {age_days:.1f} days old)")
                        else:
                            os.remove(file_path)
                            print(f"Deleted: {file_path} ({size} bytes)")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    if not dry_run:
        print(f"Cleanup finished. Deleted {total_deleted} files, total size: {total_size / (1024*1024):.2f} MB")
    else:
        print(f"Dry run finished. Would delete {total_deleted} files, total size: {total_size / (1024*1024):.2f} MB")

def detect_language(text):
    if not text or not isinstance(text, str):
        return "unknown"
    
    sample = text[:1000]
    counts = {
        'latin': 0, 'cyrillic': 0, 'arabic': 0, 'hebrew': 0, 
        'cjk': 0, 'greek': 0, 'other': 0
    }
    
    for char in sample:
        cp = ord(char)
        if 0x0041 <= cp <= 0x005A or 0x0061 <= cp <= 0x007A:
            counts['latin'] += 1
        elif 0x0400 <= cp <= 0x04FF:
            counts['cyrillic'] += 1
        elif 0x0600 <= cp <= 0x06FF:
            counts['arabic'] += 1
        elif 0x0590 <= cp <= 0x05FF:
            counts['hebrew'] += 1
        elif 0x4E00 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF or 0xAC00 <= cp <= 0xD7AF:
            counts['cjk'] += 1
        elif 0x0370 <= cp <= 0x03FF:
            counts['greek'] += 1
        elif not char.isspace() and not char.isdigit() and char not in '.,!?;:"\'()[]{}':
            counts['other'] += 1
            
    total = sum(counts.values())
    if total == 0: return "unknown"
        
    if counts['latin'] > total * 0.5:
        scores = {'en': 0, 'es': 0, 'fr': 0}
        
        en_words = {'the', 'is', 'and', 'of', 'to', 'in', 'that', 'it', 'with', 'for', 'was', 'are', 'have'}
        es_words = {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'con', 'para', 'por', 'una', 'los', 'las', 'es'}
        fr_words = {'le', 'la', 'de', 'et', 'que', 'un', 'dans', 'est', 'une', 'pour', 'par', 'sur', 'avec'}
        
        text_lower = text.lower()
        for w in en_words:
            if re.search(r'\b' + re.escape(w) + r'\b', text_lower): scores['en'] += 1
        for w in es_words:
            if re.search(r'\b' + re.escape(w) + r'\b', text_lower): scores['es'] += 1
        for w in fr_words:
            if re.search(r'\b' + re.escape(w) + r'\b', text_lower): scores['fr'] += 1
            
        max_score = max(scores.values())
        if max_score >= 2:
            # If scores are equal, prefer the one with most unique matches
            # Here we just pick the first one which is fine for a simple tool
            return [lang for lang, score in scores.items() if score == max_score][0]
        
        return "latin-family"

    if counts['cyrillic'] > total * 0.3: return "ru/cyrillic"
    if counts['cjk'] > total * 0.1: return "cjk"
    if counts['arabic'] > total * 0.3: return "ar"
    if counts['hebrew'] > total * 0.3: return "he"
    
    return "unknown"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "clean":
            threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 90
            max_age = int(sys.argv[3]) if len(sys.argv) > 3 else 7
            clean_disk_space(threshold=threshold, max_age_days=max_age)
        elif cmd == "detect":
            if len(sys.argv) > 2:
                print(f"Detected: {detect_language(sys.argv[2])}")
            else:
                print("Missing text for detection.")
    else:
        print("Usage: python3 maintenance_tool.py [clean|detect] [args]")
        print("Example: python3 maintenance_tool.py clean 90 7 (threshold 90%, max age 7 days)")
        print("Example: python3 maintenance_tool.py detect \"Hello world\"")
