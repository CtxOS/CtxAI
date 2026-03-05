import os
import shutil
import time

# import psutil  <-- Removed to avoid dependency
from backend.utils import files
from backend.utils.print_style import PrintStyle


def get_disk_usage(path="/"):
    """Returns disk usage percentage for the given path using os.statvfs."""
    try:
        # usage = psutil.disk_usage(path)
        # return usage.percent
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = total - free
        return int((used / total) * 100)
    except Exception as e:
        PrintStyle.error(f"Error checking disk usage: {e}")
        return 0


def clean_disk_space(threshold=90, max_age_days=7, dry_run=False):
    """
    Cleans up logs and temporary files if disk usage is above threshold.

    Args:
        threshold (int): Disk usage percentage to trigger cleaning.
        max_age_days (int): Files older than this will be deleted.
        dry_run (bool): If True, only log what would be deleted.
    """
    usage = get_disk_usage()
    PrintStyle.info(f"Current disk usage: {usage}% (Threshold: {threshold}%)")

    if usage < threshold:
        PrintStyle.info("Disk usage is within limits. No cleaning needed.")
        return

    PrintStyle.warning(f"Disk usage {usage}% exceeds threshold {threshold}%. Starting cleanup...")

    # Target directories
    targets = [
        files.get_abs_path("logs"),
        files.get_abs_path("tmp"),
        files.get_abs_path("usr/temp") if files.exists("usr/temp") else None,
    ]
    targets = [t for t in targets if t and os.path.exists(t)]

    now = time.time()
    seconds_in_day = 86400
    total_deleted = 0
    total_size = 0

    for target_dir in targets:
        PrintStyle.info(f"Cleaning directory: {target_dir}")
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
                            PrintStyle.debug(
                                f"[Dry Run] Would delete: {file_path} ({size} bytes, {age_days:.1f} days old)"
                            )
                        else:
                            os.remove(file_path)
                            PrintStyle.debug(f"Deleted: {file_path} ({size} bytes)")
                except Exception as e:
                    PrintStyle.error(f"Error processing {file_path}: {e}")

    if not dry_run:
        PrintStyle.success(
            f"Cleanup finished. Deleted {total_deleted} files, total size: {total_size / (1024*1024):.2f} MB"
        )
    else:
        PrintStyle.info(
            f"Dry run finished. Would delete {total_deleted} files, total size: {total_size / (1024*1024):.2f} MB"
        )


def detect_language_simple(text):
    """
    Heuristic-based language detection for common language families.
    """
    if not text or not isinstance(text, str):
        return "unknown"

    # Sample first 1000 characters
    sample = text[:1000]

    # Character set counts
    counts = {"latin": 0, "cyrillic": 0, "arabic": 0, "hebrew": 0, "cjk": 0, "greek": 0, "other": 0}

    for char in sample:
        cp = ord(char)
        if 0x0041 <= cp <= 0x005A or 0x0061 <= cp <= 0x007A:
            counts["latin"] += 1
        elif 0x0400 <= cp <= 0x04FF:
            counts["cyrillic"] += 1
        elif 0x0600 <= cp <= 0x06FF:
            counts["arabic"] += 1
        elif 0x0590 <= cp <= 0x05FF:
            counts["hebrew"] += 1
        elif (
            0x4E00 <= cp <= 0x9FFF
            or 0x3040 <= cp <= 0x309F
            or 0x30A0 <= cp <= 0x30FF
            or 0xAC00 <= cp <= 0xD7AF
        ):
            counts["cjk"] += 1
        elif 0x0370 <= cp <= 0x03FF:
            counts["greek"] += 1
        elif not char.isspace() and not char.isdigit() and char not in ".,!?;:\"'()[]{}":
            counts["other"] += 1

    # Determine the most frequent script
    # We normalize Latin because it's used in many languages and code
    total_alphabetic = sum(counts.values())
    if total_alphabetic == 0:
        return "unknown"

    # Heuristic for English/Latin based on common words if Latin is dominant
    if counts["latin"] > total_alphabetic * 0.5:
        # Check for very common English words
        common_en = {
            " the ",
            " is ",
            " and ",
            " of ",
            " to ",
            " in ",
            " that ",
            " it ",
            " with ",
            " as ",
        }
        lower_text = " " + text.lower() + " "
        en_matches = sum(1 for word in common_en if word in lower_text)
        if en_matches >= 2:
            return "en"

        # Other common European languages can be added here
        common_es = {
            " el ",
            " la ",
            " de ",
            " que ",
            " y ",
            " en ",
            " un ",
            " set ",
            " se ",
            " no ",
        }
        es_matches = sum(1 for word in common_es if word in lower_text)
        if es_matches >= 2:
            return "es"

        common_fr = {
            " le ",
            " la ",
            " de ",
            " et ",
            " que ",
            " un ",
            " dans ",
            " est ",
            " ce ",
            " il ",
        }
        fr_matches = sum(1 for word in common_fr if word in lower_text)
        if fr_matches >= 2:
            return "fr"

        return "latin-family"

    if counts["cyrillic"] > total_alphabetic * 0.3:
        return "ru/cyrillic"
    if counts["cjk"] > total_alphabetic * 0.1:
        return "cjk"
    if counts["arabic"] > total_alphabetic * 0.3:
        return "ar"
    if counts["hebrew"] > total_alphabetic * 0.3:
        return "he"
    if counts["greek"] > total_alphabetic * 0.3:
        return "el"

    return "unknown"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "clean":
            threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 90
            clean_disk_space(threshold=threshold)
        elif sys.argv[1] == "detect":
            if len(sys.argv) > 2:
                print(f"Detected language: {detect_language_simple(sys.argv[2])}")
            else:
                print("Please provide text to detect.")
    else:
        print("Usage: python maintenance.py [clean|detect] [args]")
