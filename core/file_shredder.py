import os
import random
import string
from typing import Tuple, List

class FileShredder:
    @staticmethod
    def shred_file(file_path: str, passes: int = 3) -> bool:
        """Securely shreds a file using multi-pass overwriting and metadata scrambling."""
        if not os.path.isfile(file_path):
            return False

        try:
            file_size = os.path.getsize(file_path)
            chunk_size = 64 * 1024  # 64 KB chunks

            with open(file_path, "r+b") as f:
                fd = f.fileno()
                for p in range(passes):
                    f.seek(0)
                    bytes_written = 0
                    if p % 3 == 0:
                        pattern = b"\x00" * chunk_size
                    elif p % 3 == 1:
                        pattern = b"\xFF" * chunk_size
                    else:
                        pattern = None

                    while bytes_written < file_size:
                        to_write = min(chunk_size, file_size - bytes_written)
                        if pattern:
                            f.write(pattern[:to_write])
                        else:
                            f.write(os.urandom(to_write))
                        bytes_written += to_write
                    f.flush()
                    try:
                        os.fsync(fd)
                    except OSError:
                        pass

                # Truncate to 0
                f.seek(0)
                f.truncate(0)

            # Scramble filename to remove directory entry trails
            dir_name = os.path.dirname(file_path)
            random_name = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            scrambled_path = os.path.join(dir_name, random_name)
            try:
                os.rename(file_path, scrambled_path)
                os.remove(scrambled_path)
            except OSError:
                os.remove(file_path)

            return True
        except Exception:
            return False

    @classmethod
    def shred_target(cls, target_path: str, passes: int = 3) -> Tuple[int, int]:
        """Shreds a single file or entire directory recursively. Returns (success_files, fail_files)."""
        success = 0
        failed = 0

        if os.path.isfile(target_path):
            if cls.shred_file(target_path, passes):
                return 1, 0
            else:
                return 0, 1

        elif os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path, topdown=False):
                for f in files:
                    fp = os.path.join(root, f)
                    if cls.shred_file(fp, passes):
                        success += 1
                    else:
                        failed += 1
                for d in dirs:
                    dp = os.path.join(root, d)
                    try:
                        os.rmdir(dp)
                    except OSError:
                        pass
            try:
                os.rmdir(target_path)
            except OSError:
                pass

        return success, failed
