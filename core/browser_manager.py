import os
import glob
import json
import shutil
from typing import List, Dict, Any

class BrowserExtension:
    def __init__(self, browser: str, name: str, version: str, ext_id: str, folder_path: str, description: str = ""):
        self.browser = browser
        self.name = name
        self.version = version
        self.ext_id = ext_id
        self.folder_path = folder_path
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "browser": self.browser,
            "name": self.name,
            "version": self.version,
            "id": self.ext_id,
            "path": self.folder_path
        }

def _resolve_manifest_name(manifest_path: str, ext_dir: str) -> Tuple_Name_Desc:
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_name = data.get("name", "")
        raw_desc = data.get("description", "")
        version = data.get("version", "")

        # Handle __MSG_name__ localization
        if raw_name.startswith("__MSG_") and raw_name.endswith("__"):
            key = raw_name[6:-2]
            locales_dir = os.path.join(ext_dir, "_locales")
            # Try tr, then en, then first available
            for loc in ["tr", "en", "en_US", "en_GB"]:
                msg_file = os.path.join(locales_dir, loc, "messages.json")
                if os.path.isfile(msg_file):
                    try:
                        with open(msg_file, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            if key in mdata:
                                raw_name = mdata[key].get("message", raw_name)
                                break
                    except Exception:
                        pass
        return raw_name, version, raw_desc
    except Exception:
        return os.path.basename(os.path.dirname(ext_dir)), "", ""

def scan_browser_extensions() -> List[BrowserExtension]:
    extensions: List[BrowserExtension] = []

    local_app = os.environ.get("LOCALAPPDATA", "")
    roaming_app = os.environ.get("APPDATA", "")

    chromium_targets = [
        ("Google Chrome", os.path.join(local_app, r"Google\Chrome\User Data")),
        ("Microsoft Edge", os.path.join(local_app, r"Microsoft\Edge\User Data")),
        ("Brave", os.path.join(local_app, r"BraveSoftware\Brave-Browser\User Data")),
        ("Opera GX", os.path.join(roaming_app, r"Opera Software\Opera GX Stable")),
        ("Opera", os.path.join(roaming_app, r"Opera Software\Opera Stable"))
    ]

    for browser_name, user_data in chromium_targets:
        if not os.path.isdir(user_data):
            continue

        # Look in Default, Profile 1..10, etc.
        profile_folders = [user_data] if "Opera" in browser_name else glob.glob(os.path.join(user_data, "Default")) + glob.glob(os.path.join(user_data, "Profile *"))

        for prof in profile_folders:
            ext_root = os.path.join(prof, "Extensions")
            if not os.path.isdir(ext_root):
                continue

            try:
                for ext_id in os.listdir(ext_root):
                    ext_id_dir = os.path.join(ext_root, ext_id)
                    if not os.path.isdir(ext_id_dir):
                        continue

                    # Each extension ID has version directories
                    for ver in os.listdir(ext_id_dir):
                        ver_dir = os.path.join(ext_id_dir, ver)
                        manifest_file = os.path.join(ver_dir, "manifest.json")
                        if os.path.isfile(manifest_file):
                            name, version_str, desc = _resolve_manifest_name(manifest_file, ver_dir)
                            extensions.append(BrowserExtension(
                                browser=browser_name,
                                name=name or ext_id,
                                version=version_str or ver,
                                ext_id=ext_id,
                                folder_path=ext_id_dir,
                                description=desc
                            ))
                            break
            except OSError:
                continue

    return extensions

def delete_browser_extension(folder_path: str) -> bool:
    try:
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            return True
        return False
    except Exception:
        return False
