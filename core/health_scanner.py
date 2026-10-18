import os
import subprocess
import json
import winreg
from typing import List, Dict, Any

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

class HealthIssue:
    def __init__(self, category: str, title: str, path: str, size_bytes: int = 0):
        self.category = category
        self.title = title
        self.path = path
        self.size_bytes = size_bytes
        self.selected = True

    @property
    def formatted_size(self) -> str:
        if self.size_bytes <= 0:
            return ""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"

def scan_software_health() -> List[HealthIssue]:
    issues: List[HealthIssue] = []

    shortcut_roots = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), r"Microsoft\Windows\Start Menu\Programs")
    ]

    ps_cmd = (
        "$sh = New-Object -ComObject WScript.Shell; "
        "$issues = @(); "
        f"$paths = @('{shortcut_roots[0]}', '{shortcut_roots[1]}', '{shortcut_roots[2]}', '{shortcut_roots[3]}'); "
        "foreach ($p in $paths) { "
        "  if (Test-Path $p) { "
        "    Get-ChildItem -Path $p -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { "
        "      try { "
        "        $target = $sh.CreateShortcut($_.FullName).TargetPath; "
        "        if ($target -and (-not (Test-Path $target))) { "
        "          [PSCustomObject]@{ File = $_.FullName; Target = $target } "
        "        } "
        "      } catch {} "
        "    } "
        "  } "
        "} | ConvertTo-Json -Compress"
    )

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW
        )
        if res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                fpath = item.get("File")
                target = item.get("Target")
                if fpath and os.path.isfile(fpath):
                    issues.append(HealthIssue(
                        category="Bozuk Kısayol",
                        title=f"{os.path.basename(fpath)} (Hedef bulunamadı: {os.path.basename(target)})",
                        path=fpath,
                        size_bytes=os.path.getsize(fpath)
                    ))
    except Exception:
        pass

    temp_dir = os.environ.get("TEMP", "")
    if temp_dir and os.path.isdir(temp_dir):
        try:
            for entry in os.scandir(temp_dir):
                try:
                    if entry.is_file() and (entry.name.lower().endswith(".tmp") or entry.name.lower().startswith("is-")):
                        issues.append(HealthIssue(
                            category="Geçici Kalıntı",
                            title=f"Artık Kurulum Dosyası: {entry.name}",
                            path=entry.path,
                            size_bytes=entry.stat().st_size
                        ))
                except OSError:
                    pass
        except OSError:
            pass

    return issues

def fix_health_issues(issues: List[HealthIssue]) -> int:
    import shutil
    fixed = 0
    for iss in issues:
        if not iss.selected:
            continue
        try:
            if os.path.isfile(iss.path):
                os.remove(iss.path)
                fixed += 1
            elif os.path.isdir(iss.path):
                shutil.rmtree(iss.path, ignore_errors=True)
                fixed += 1
        except Exception:
            pass
    return fixed
