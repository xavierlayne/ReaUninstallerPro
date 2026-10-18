import os
import winreg
from typing import List, Dict, Any

class StartupItem:
    def __init__(self, name: str, command: str, location_type: str, raw_location: str, root_key: Any = None, is_enabled: bool = True):
        self.name = name
        self.command = command
        self.location_type = location_type  # 'Registry (HKCU)', 'Registry (HKLM)', 'Startup Folder'
        self.raw_location = raw_location
        self.root_key = root_key
        self.is_enabled = is_enabled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "location": self.location_type,
            "enabled": self.is_enabled
        }

def scan_startup_items() -> List[StartupItem]:
    items: List[StartupItem] = []

    reg_targets = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registry (HKCU)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "Registry (HKLM)"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run", "Registry (HKLM 32-bit)")
    ]

    for root, subkey, label in reg_targets:
        try:
            with winreg.OpenKey(root, subkey) as key:
                num_values = winreg.QueryInfoKey(key)[1]
                for i in range(num_values):
                    try:
                        vname, vval, _ = winreg.EnumValue(key, i)
                        items.append(StartupItem(
                            name=vname,
                            command=str(vval),
                            location_type=label,
                            raw_location=subkey,
                            root_key=root,
                            is_enabled=True
                        ))
                    except OSError:
                        pass
        except OSError:
            pass

    # Startup folders
    user_startup = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    common_startup = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), r"Microsoft\Windows\Start Menu\Programs\Startup")

    for sdir, label in [(user_startup, "Başlangıç Klasörü (Kullanıcı)"), (common_startup, "Başlangıç Klasörü (Ortak)")]:
        if os.path.isdir(sdir):
            try:
                for entry in os.scandir(sdir):
                    if entry.is_file():
                        enabled = not entry.name.endswith(".disabled")
                        items.append(StartupItem(
                            name=entry.name,
                            command=entry.path,
                            location_type=label,
                            raw_location=entry.path,
                            root_key=None,
                            is_enabled=enabled
                        ))
            except OSError:
                pass

    return items

def delete_startup_item(item: StartupItem) -> bool:
    try:
        if item.root_key and item.raw_location:
            with winreg.OpenKey(item.root_key, item.raw_location, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, item.name)
                return True
        elif os.path.isfile(item.raw_location):
            os.remove(item.raw_location)
            return True
        return False
    except Exception:
        return False
