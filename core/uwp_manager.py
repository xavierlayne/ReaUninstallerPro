import os
import subprocess
import json
from typing import List, Dict, Any

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

class UwpApp:
    def __init__(self, name: str, package_full_name: str, publisher: str = "", version: str = "", is_framework: bool = False):
        self.name = name
        self.package_full_name = package_full_name
        self.publisher = publisher
        self.version = version
        self.is_framework = is_framework

    @property
    def display_name(self) -> str:
        cleaned = self.name.replace("Microsoft.", "").replace("Windows.", "")
        import re
        spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
        return spaced or self.name

    @property
    def is_recommended_removal(self) -> bool:
        """Returns True if the app is unnecessary bloatware safely recommended for removal."""
        bloatware_names = {
            "bingweather", "bingnews", "bingfinance", "bingsports",
            "xbox", "gethelp", "yourphone", "zunemusic", "zunevideo", "people",
            "windowsfeedbackhub", "skypeapp", "solitairecollection", "clipchamp",
            "mixedreality", "officehub", "getstarted", "oneconnect", "3dbuilder",
            "todos", "powerautomatedesktop", "cortana", "news"
        }
        lower_name = self.name.lower()
        return any(b in lower_name for b in bloatware_names)

    @property
    def is_critical_system(self) -> bool:
        """Returns True if this is an essential Windows system runtime/framework that should NOT be removed."""
        if self.is_framework:
            return True
        critical_names = {
            "xaml", "vclibs", "winappruntime", "shellexperiencehost",
            "startmenuexperiencehost", "oobe", "client.cbs", "client.core",
            "client.fileexp", "client.photon", "client.webexperience",
            "printdialog", "printqueue", "sechealthui", "windowsstore",
            "storepurchaseapp", "immersivecontrolpanel", "lockapp",
            "undockeddevkit", "rawimageextension", "webpimageextension",
            "vp9videoextensions", "mpeg2videoextension", "windows.terminal",
            "windowsterminal", "secassessmentbrowser", "parentalcontrols",
            "windowstcui", "crossdevice"
        }
        lower_name = self.name.lower()
        return any(c in lower_name for c in critical_names)

    @property
    def category_status(self) -> str:
        if self.is_critical_system:
            return "Önerilmez (Sistem Dosyası)"
        elif self.is_recommended_removal:
            return "Önerilen (Gereksiz Bloatware)"
        else:
            return "İsteğe Bağlı (Standart Uygulama)"

    @property
    def is_bloatware(self) -> bool:
        return self.is_recommended_removal

def scan_uwp_apps(include_frameworks: bool = False) -> List[UwpApp]:
    ps_cmd = (
        "Get-AppxPackage | "
        "Select-Object Name, PackageFullName, Publisher, Version, IsFramework | "
        "ConvertTo-Json -Compress"
    )
    apps = []
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW
        )
        if res.stdout.strip():
            raw_data = json.loads(res.stdout)
            if isinstance(raw_data, dict):
                raw_data = [raw_data]
            for item in raw_data:
                is_fw = bool(item.get("IsFramework", False))
                if is_fw and not include_frameworks:
                    continue
                name = item.get("Name") or ""
                pkg_full = item.get("PackageFullName") or ""
                pub = item.get("Publisher") or ""
                ver = item.get("Version") or ""
                if name and pkg_full:
                    apps.append(UwpApp(name=name, package_full_name=pkg_full, publisher=pub, version=ver, is_framework=is_fw))
    except Exception:
        pass

    apps.sort(key=lambda a: (not a.is_bloatware, a.display_name.lower()))
    return apps

def remove_uwp_app(package_full_name: str, all_users: bool = True) -> Dict[str, Any]:
    cmd = f'Remove-AppxPackage -Package "{package_full_name}"'
    if all_users:
        cmd += " -AllUsers"

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            creationflags=NO_WINDOW
        )
        if res.returncode == 0:
            return {"success": True, "error": None}
        else:
            # If -AllUsers failed, fallback without -AllUsers
            if all_users:
                retry_cmd = f'Remove-AppxPackage -Package "{package_full_name}"'
                res2 = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", retry_cmd],
                    capture_output=True,
                    text=True,
                    creationflags=NO_WINDOW
                )
                if res2.returncode == 0:
                    return {"success": True, "error": None}
            return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}
