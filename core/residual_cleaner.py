import os
import shutil
import winreg
import re
from typing import List, Dict, Any, Tuple

class ResidualItem:
    def __init__(self, item_type: str, path: str, details: str = "", root_key: Any = None, subkey: str = "", value_name: str = ""):
        self.item_type = item_type  # 'file', 'directory', 'registry_key', 'registry_value'
        self.path = path
        self.details = details
        self.root_key = root_key
        self.subkey = subkey
        self.value_name = value_name
        self.selected = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.item_type,
            "path": self.path,
            "details": self.details,
            "selected": self.selected
        }

class ResidualScanner:
    SAFE_PROTECTED_PATHS = {
        os.environ.get("WINDIR", "C:\\Windows").lower(),
        os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
        os.environ.get("APPDATA", "").lower(),
        os.environ.get("LOCALAPPDATA", "").lower(),
        os.environ.get("ProgramData", "C:\\ProgramData").lower(),
        os.path.expanduser("~").lower(),
        os.path.join(os.path.expanduser("~"), "Desktop").lower()
    }

    PROTECTED_REG_KEYS = {
        r"software\microsoft",
        r"software\wow6432node\microsoft",
        r"software\classes",
        r"software",
        r"software\wow6432node"
    }

    @classmethod
    def clean_keyword(cls, text: str) -> str:
        """Strip version numbers, build numbers, architecture strings to isolate root product name."""
        if not text:
            return ""
        # Remove version numbers like 1.2.3 or v2.0
        cleaned = re.sub(r'v?\d+(\.\d+)+[a-zA-Z0-9_-]*', '', text)
        cleaned = re.sub(r'\b(x64|x86|64-bit|32-bit|community|enterprise|professional|edition)\b', '', cleaned, flags=re.I)
        cleaned = re.sub(r'[^\w\s-]', '', cleaned).strip()
        return cleaned

    @classmethod
    def scan_for_program(cls, app_name: str, publisher: str = "", install_location: str = "") -> List[ResidualItem]:
        residuals: List[ResidualItem] = []
        app_clean = cls.clean_keyword(app_name)
        if len(app_clean) < 3:
            return residuals

        search_tokens = [t.lower() for t in app_clean.split() if len(t) > 2]
        pub_clean = cls.clean_keyword(publisher)

        # 1. Filesystem scan in known app storage directories
        base_dirs = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("APPDATA"),
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("ProgramData"),
            os.path.join(os.path.expanduser("~"), "AppData", "LocalLow")
        ]

        # Explicit install location check
        if install_location and os.path.isdir(install_location):
            if install_location.lower().rstrip("\\/") not in cls.SAFE_PROTECTED_PATHS:
                residuals.append(ResidualItem("directory", install_location, "Kurulum Ana Klasörü (Kalıntı)"))

        for bdir in base_dirs:
            if not bdir or not os.path.isdir(bdir):
                continue
            try:
                for entry in os.scandir(bdir):
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    folder_name_lower = entry.name.lower()

                    # Exact or strong match with app name
                    if app_clean.lower() in folder_name_lower or any(tok in folder_name_lower for tok in search_tokens):
                        fpath = entry.path
                        if fpath.lower().rstrip("\\/") not in cls.SAFE_PROTECTED_PATHS:
                            residuals.append(ResidualItem("directory", fpath, f"Dosya Kalıntısı ({entry.name})"))

                    # If publisher folder exists, check inside it
                    elif pub_clean and pub_clean.lower() in folder_name_lower:
                        try:
                            for subentry in os.scandir(entry.path):
                                if subentry.is_dir(follow_symlinks=False):
                                    sub_lower = subentry.name.lower()
                                    if any(tok in sub_lower for tok in search_tokens):
                                        residuals.append(ResidualItem("directory", subentry.path, f"Yayıncı Klasörü İçi Kalıntı ({entry.name}\\{subentry.name})"))
                        except OSError:
                            pass
            except OSError:
                continue

        # 2. Desktop and Start Menu Shortcuts
        shortcut_locations = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), r"Microsoft\Windows\Start Menu\Programs")
        ]

        for sdir in shortcut_locations:
            if not os.path.isdir(sdir):
                continue
            try:
                for root, _, files in os.walk(sdir):
                    for f in files:
                        if f.lower().endswith(".lnk"):
                            f_lower = f.lower()
                            if any(tok in f_lower for tok in search_tokens):
                                full_path = os.path.join(root, f)
                                residuals.append(ResidualItem("file", full_path, f"Artık Kısayol Dosyası ({f})"))
            except OSError:
                continue

        # 3. Registry scan
        reg_roots = [
            (winreg.HKEY_CURRENT_USER, "HKCU", [r"Software"]),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", [r"Software", r"Software\Wow6432Node"])
        ]

        for root_handle, root_name, base_subkeys in reg_roots:
            for base_sub in base_subkeys:
                try:
                    with winreg.OpenKey(root_handle, base_sub) as base_key:
                        num_subkeys = winreg.QueryInfoKey(base_key)[0]
                        for i in range(num_subkeys):
                            try:
                                key_name = winreg.EnumKey(base_key, i)
                                kname_lower = key_name.lower()

                                full_subkey = f"{base_sub}\\{key_name}"
                                if full_subkey.lower() in cls.PROTECTED_REG_KEYS:
                                    continue

                                # Match app name in software keys
                                if any(tok in kname_lower for tok in search_tokens):
                                    residuals.append(ResidualItem(
                                        "registry_key",
                                        f"{root_name}\\{full_subkey}",
                                        f"Kayıt Defteri Anahtarı ({key_name})",
                                        root_key=root_handle,
                                        subkey=full_subkey
                                    ))
                                # Match publisher folder, scan inside
                                elif pub_clean and pub_clean.lower() in kname_lower:
                                    try:
                                        with winreg.OpenKey(root_handle, full_subkey) as pub_key:
                                            num_pub_sub = winreg.QueryInfoKey(pub_key)[0]
                                            for j in range(num_pub_sub):
                                                sub_app_key = winreg.EnumKey(pub_key, j)
                                                if any(tok in sub_app_key.lower() for tok in search_tokens):
                                                    nested_subkey = f"{full_subkey}\\{sub_app_key}"
                                                    residuals.append(ResidualItem(
                                                        "registry_key",
                                                        f"{root_name}\\{nested_subkey}",
                                                        f"Yayıncı Alt Kayıt Anahtarı ({key_name}\\{sub_app_key})",
                                                        root_key=root_handle,
                                                        subkey=nested_subkey
                                                    ))
                                    except OSError:
                                        pass
                            except OSError:
                                continue
                except OSError:
                    continue

        return residuals

def delete_registry_key_recursive(root_key: Any, subkey: str) -> bool:
    """Recursively deletes a Windows registry key and all its subkeys."""
    try:
        with winreg.OpenKey(root_key, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    delete_registry_key_recursive(root_key, f"{subkey}\\{sub}")
                except OSError:
                    break
        winreg.DeleteKey(root_key, subkey)
        return True
    except OSError:
        return False

def clean_residual_items(items: List[ResidualItem]) -> Tuple[int, int, List[str]]:
    """Cleans given residual items. Returns (success_count, fail_count, errors)."""
    success_count = 0
    fail_count = 0
    errors = []

    for item in items:
        if not item.selected:
            continue

        if item.item_type == "file":
            try:
                if os.path.isfile(item.path):
                    os.remove(item.path)
                    success_count += 1
            except Exception as e:
                fail_count += 1
                errors.append(f"Dosya silinemedi: {item.path} ({e})")

        elif item.item_type == "directory":
            try:
                if os.path.isdir(item.path):
                    shutil.rmtree(item.path, ignore_errors=False)
                    success_count += 1
            except Exception as e:
                fail_count += 1
                errors.append(f"Klasör silinemedi: {item.path} ({e})")

        elif item.item_type == "registry_key":
            if item.root_key and item.subkey:
                if delete_registry_key_recursive(item.root_key, item.subkey):
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Kayıt defteri anahtarı silinemedi: {item.path}")

    return success_count, fail_count, errors
