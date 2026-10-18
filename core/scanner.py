import os
import winreg
import subprocess
import datetime
from typing import List, Dict, Optional, Any

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

class InstalledProgram:
    def __init__(self, **kwargs):
        self.key_name: str = kwargs.get("key_name", "")
        self.name: str = kwargs.get("name", "")
        self.version: str = kwargs.get("version", "")
        self.publisher: str = kwargs.get("publisher", "")
        self.install_date: str = kwargs.get("install_date", "")
        self.install_location: str = kwargs.get("install_location", "")
        self.uninstall_string: str = kwargs.get("uninstall_string", "")
        self.quiet_uninstall_string: str = kwargs.get("quiet_uninstall_string", "")
        self.size_kb: int = kwargs.get("size_kb", 0)
        self.icon_path: str = kwargs.get("icon_path", "")
        self.root_name: str = kwargs.get("root_name", "")
        self.subkey: str = kwargs.get("subkey", "")
        self.is_64bit: bool = kwargs.get("is_64bit", True)
        self.is_system_component: bool = kwargs.get("is_system_component", False)

    @property
    def formatted_size(self) -> str:
        if self.size_kb <= 0:
            return "Bilinmiyor"
        if self.size_kb < 1024:
            return f"{self.size_kb} KB"
        elif self.size_kb < 1024 * 1024:
            return f"{self.size_kb / 1024:.1f} MB"
        else:
            return f"{self.size_kb / (1024 * 1024):.2f} GB"

    @property
    def formatted_date(self) -> str:
        if not self.install_date:
            return "Bilinmiyor"
        d = str(self.install_date).strip()
        if len(d) == 8 and d.isdigit():
            return f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
        return d

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_name": self.key_name,
            "name": self.name,
            "version": self.version,
            "publisher": self.publisher,
            "install_date": self.formatted_date,
            "install_location": self.install_location,
            "size": self.formatted_size,
            "size_kb": self.size_kb,
            "uninstall_string": self.uninstall_string,
            "quiet_uninstall_string": self.quiet_uninstall_string
        }

def scan_installed_programs(include_system: bool = False) -> List[InstalledProgram]:
    registry_targets = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM", True),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM (32-bit)", False),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU", True),
    ]

    programs = []
    seen_names = set()

    for root, subkey, root_name, is_64 in registry_targets:
        try:
            with winreg.OpenKey(root, subkey) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        kname = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, kname) as appkey:
                            try:
                                name, _ = winreg.QueryValueEx(appkey, "DisplayName")
                                name = str(name).strip()
                                if not name:
                                    continue
                            except OSError:
                                continue

                            # System component check
                            sys_comp = False
                            try:
                                sc, _ = winreg.QueryValueEx(appkey, "SystemComponent")
                                if sc == 1:
                                    sys_comp = True
                            except OSError:
                                pass

                            if sys_comp and not include_system:
                                continue

                            # Parent / child component check
                            try:
                                parent, _ = winreg.QueryValueEx(appkey, "ParentKeyName")
                                if parent and not include_system:
                                    continue
                            except OSError:
                                pass

                            def get_str(val_name):
                                try:
                                    v, _ = winreg.QueryValueEx(appkey, val_name)
                                    return str(v).strip()
                                except OSError:
                                    return ""

                            def get_int(val_name):
                                try:
                                    v, _ = winreg.QueryValueEx(appkey, val_name)
                                    return int(v)
                                except (OSError, ValueError):
                                    return 0

                            version = get_str("DisplayVersion")
                            publisher = get_str("Publisher")
                            install_date = get_str("InstallDate")
                            install_loc = get_str("InstallLocation")
                            uninstall_str = get_str("UninstallString")
                            quiet_uninstall_str = get_str("QuietUninstallString")
                            size_kb = get_int("EstimatedSize")
                            icon_path = get_str("DisplayIcon")

                            if size_kb == 0 and install_loc and os.path.isdir(install_loc):
                                try:
                                    total_b = 0
                                    for entry in os.scandir(install_loc):
                                        if entry.is_file(follow_symlinks=False):
                                            total_b += entry.stat().st_size
                                    size_kb = total_b // 1024
                                except OSError:
                                    pass

                            unique_key = (name.lower(), version.lower())
                            if unique_key in seen_names:
                                continue
                            seen_names.add(unique_key)

                            prog = InstalledProgram(
                                key_name=kname,
                                name=name,
                                version=version,
                                publisher=publisher,
                                install_date=install_date,
                                install_location=install_loc,
                                uninstall_string=uninstall_str,
                                quiet_uninstall_string=quiet_uninstall_str,
                                size_kb=size_kb,
                                icon_path=icon_path,
                                root_name=root_name,
                                subkey=f"{subkey}\\{kname}",
                                is_64bit=is_64,
                                is_system_component=sys_comp
                            )
                            programs.append(prog)
                    except OSError:
                        continue
        except OSError:
            continue

    programs.sort(key=lambda x: x.name.lower())
    return programs

def run_uninstaller_command(uninstall_string: str, quiet: bool = False) -> subprocess.Popen:
    """Launches the uninstaller command line properly handling quotes and arguments."""
    cmd = uninstall_string.strip()
    if quiet:
        lower_cmd = cmd.lower()
        if "msiexec" in lower_cmd:
            if "/qn" not in lower_cmd and "/quiet" not in lower_cmd:
                cmd += " /qn"
        elif "/s" not in lower_cmd and "/silent" not in lower_cmd and "--silent" not in lower_cmd:
            cmd += " /S"

    return subprocess.Popen(cmd, shell=True)
