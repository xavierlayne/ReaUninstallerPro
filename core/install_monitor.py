import os
import winreg
import json
import time
from typing import Dict, Any, List, Set
from .residual_cleaner import delete_registry_key_recursive

class InstallSnapshot:
    @staticmethod
    def _collect_registry_keys(root_key: Any, subkey: str, depth: int = 3) -> Set[str]:
        keys = set()
        if depth <= 0:
            return keys
        try:
            with winreg.OpenKey(root_key, subkey) as k:
                num_subkeys = winreg.QueryInfoKey(k)[0]
                for i in range(num_subkeys):
                    try:
                        sname = winreg.EnumKey(k, i)
                        full = f"{subkey}\\{sname}"
                        keys.add(full.lower())
                        keys.update(InstallSnapshot._collect_registry_keys(root_key, full, depth - 1))
                    except OSError:
                        pass
        except OSError:
            pass
        return keys

    @staticmethod
    def _collect_filesystem_state(roots: List[str]) -> Dict[str, float]:
        files_state = {}
        for r in roots:
            if not r or not os.path.isdir(r):
                continue
            try:
                for root_dir, dirs, files in os.walk(r):
                    for f in files:
                        fp = os.path.join(root_dir, f)
                        try:
                            files_state[fp] = os.path.getmtime(fp)
                        except OSError:
                            pass
            except OSError:
                pass
        return files_state

    @classmethod
    def take_snapshot(cls) -> Dict[str, Any]:
        """Captures current system registry and filesystem state."""
        hklm_keys = cls._collect_registry_keys(winreg.HKEY_LOCAL_MACHINE, r"Software", depth=2)
        hkcu_keys = cls._collect_registry_keys(winreg.HKEY_CURRENT_USER, r"Software", depth=2)

        dirs_to_watch = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("APPDATA"),
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("ProgramData")
        ]
        fs_state = cls._collect_filesystem_state(dirs_to_watch)

        return {
            "timestamp": time.time(),
            "hklm_keys": list(hklm_keys),
            "hkcu_keys": list(hkcu_keys),
            "files": fs_state
        }

    @classmethod
    def compare_snapshots(cls, pre_snap: Dict[str, Any], post_snap: Dict[str, Any]) -> Dict[str, Any]:
        """Generates difference log of newly created items."""
        pre_hklm = set(pre_snap.get("hklm_keys", []))
        post_hklm = set(post_snap.get("hklm_keys", []))
        new_hklm = list(post_hklm - pre_hklm)

        pre_hkcu = set(pre_snap.get("hkcu_keys", []))
        post_hkcu = set(post_snap.get("hkcu_keys", []))
        new_hkcu = list(post_hkcu - pre_hkcu)

        pre_files = pre_snap.get("files", {})
        post_files = post_snap.get("files", {})

        new_files = [f for f in post_files if f not in pre_files]

        return {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "new_hklm_keys": new_hklm,
            "new_hkcu_keys": new_hkcu,
            "new_files": new_files
        }

    @classmethod
    def revert_logged_install(cls, log_data: Dict[str, Any]) -> Dict[str, int]:
        """Deletes all recorded files and registry keys from an install log."""
        deleted_files = 0
        deleted_reg = 0

        # Delete new files
        for f in log_data.get("new_files", []):
            try:
                if os.path.isfile(f):
                    os.remove(f)
                    deleted_files += 1
            except OSError:
                pass

        # Delete new registry keys
        for k in log_data.get("new_hklm_keys", []):
            if delete_registry_key_recursive(winreg.HKEY_LOCAL_MACHINE, k):
                deleted_reg += 1

        for k in log_data.get("new_hkcu_keys", []):
            if delete_registry_key_recursive(winreg.HKEY_CURRENT_USER, k):
                deleted_reg += 1

        return {
            "deleted_files": deleted_files,
            "deleted_registry_keys": deleted_reg
        }
