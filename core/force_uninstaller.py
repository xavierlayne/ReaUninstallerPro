import os
import shutil
import subprocess
import winreg
from typing import Dict, List, Any
from .residual_cleaner import ResidualScanner, delete_registry_key_recursive

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

class ForceUninstaller:
    @staticmethod
    def kill_processes_in_directory(target_dir: str) -> List[str]:
        killed = []
        target_norm = os.path.normpath(target_dir).lower()

        ps_cmd = (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId, ExecutablePath | "
            "Where-Object { $_.ExecutablePath } | "
            "ConvertTo-Json"
        )
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=NO_WINDOW
            )
            if res.stdout.strip():
                import json
                try:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for proc in data:
                        exe_path = proc.get("ExecutablePath") or ""
                        if exe_path and os.path.normpath(exe_path).lower().startswith(target_norm):
                            pid = proc.get("ProcessId")
                            if pid:
                                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
                                killed.append(f"{os.path.basename(exe_path)} (PID: {pid})")
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        return killed

    @staticmethod
    def take_ownership_and_unlock(target_path: str):
        try:
            if os.path.isdir(target_path):
                subprocess.run(["takeown", "/F", target_path, "/R", "/D", "Y"], capture_output=True, creationflags=NO_WINDOW)
                subprocess.run(["icacls", target_path, "/grant", "*S-1-5-32-544:F", "/T", "/C", "/Q"], capture_output=True, creationflags=NO_WINDOW)
            elif os.path.isfile(target_path):
                subprocess.run(["takeown", "/F", target_path], capture_output=True, creationflags=NO_WINDOW)
                subprocess.run(["icacls", target_path, "/grant", "*S-1-5-32-544:F", "/Q"], capture_output=True, creationflags=NO_WINDOW)
        except Exception:
            pass

    @classmethod
    def force_delete_target(cls, target_path: str) -> Dict[str, Any]:
        target_path = os.path.abspath(target_path)
        result = {
            "path": target_path,
            "success": False,
            "killed_processes": [],
            "error": None,
            "purged_registry_keys": 0
        }

        if not os.path.exists(target_path):
            result["error"] = "Belirtilen hedef dosya veya klasör bulunamadı."
            return result

        norm_lower = os.path.normpath(target_path).lower()
        if norm_lower in ResidualScanner.SAFE_PROTECTED_PATHS or len(norm_lower.split("\\")) <= 2:
            result["error"] = "Güvenlik Engeli: Kritik sistem veya kök dizin silinemez!"
            return result

        # 1. Kill locking processes
        if os.path.isdir(target_path):
            result["killed_processes"] = cls.kill_processes_in_directory(target_path)
        elif os.path.isfile(target_path):
            result["killed_processes"] = cls.kill_processes_in_directory(os.path.dirname(target_path))

        # 2. Take ownership
        cls.take_ownership_and_unlock(target_path)

        # 3. Delete from filesystem
        try:
            if os.path.isdir(target_path):
                shutil.rmtree(target_path, ignore_errors=False)
            else:
                os.remove(target_path)
            result["success"] = True
        except Exception as e:
            if os.path.isdir(target_path):
                try:
                    shutil.rmtree(target_path, ignore_errors=True)
                    if not os.path.exists(target_path):
                        result["success"] = True
                    else:
                        result["error"] = f"Dosyalar silinemedi: {e}"
                except Exception as ex:
                    result["error"] = str(ex)
            else:
                result["error"] = str(e)

        # 4. Search and purge registry references if base name is informative
        base_name = os.path.basename(target_path)
        if len(base_name) > 3 and result["success"]:
            residuals = ResidualScanner.scan_for_program(base_name, install_location=target_path)
            for item in residuals:
                if item.item_type == "registry_key" and item.root_key and item.subkey:
                    if delete_registry_key_recursive(item.root_key, item.subkey):
                        result["purged_registry_keys"] += 1

        return result
