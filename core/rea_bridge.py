import os
import subprocess
from typing import Dict, Any, Optional

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

REA_PATHS = {
    "die": r"C:\Users\KARACA\AppData\Local\Microsoft\WinGet\Packages\horsicq.DIE-engine_Microsoft.Winget.Source_8wekyb3d8bbwe\die\die.exe",
    "dnspy": r"C:\Users\KARACA\AppData\Local\Microsoft\WinGet\Packages\dnSpyEx.dnSpy_Microsoft.Winget.Source_8wekyb3d8bbwe\dnSpy.exe",
    "x64dbg": r"C:\Users\KARACA\AppData\Local\Microsoft\WinGet\Packages\x64dbg.x64dbg_Microsoft.Winget.Source_8wekyb3d8bbwe\release\x64\x64dbg.exe"
}

class REABridge:
    @staticmethod
    def get_tool_status() -> Dict[str, bool]:
        return {name: os.path.isfile(path) for name, path in REA_PATHS.items()}

    @classmethod
    def launch_tool(cls, tool_name: str, target_path: Optional[str] = None) -> bool:
        exe_path = REA_PATHS.get(tool_name.lower())
        if not exe_path or not os.path.isfile(exe_path):
            return False

        args = [exe_path]
        if target_path and os.path.exists(target_path):
            args.append(target_path)

        try:
            subprocess.Popen(args, creationflags=0)
            return True
        except Exception:
            return False

    @staticmethod
    def inspect_binary_quick(file_path: str) -> Dict[str, Any]:
        """Performs fast native PE inspection using pefile for embedded REA telemetry."""
        result = {
            "valid": False,
            "architecture": "Bilinmiyor",
            "subsystem": "Bilinmiyor",
            "sections": [],
            "num_imports": 0,
            "has_dotnet": False,
            "is_packed": False
        }

        if not file_path or not os.path.isfile(file_path):
            return result

        try:
            import pefile
            pe = pefile.PE(file_path, fast_load=True)
            result["valid"] = True

            # Architecture
            if pe.FILE_HEADER.Machine == 0x8664:
                result["architecture"] = "x64 (64-Bit AMD64)"
            elif pe.FILE_HEADER.Machine == 0x14C:
                result["architecture"] = "x86 (32-Bit Intel)"
            elif pe.FILE_HEADER.Machine == 0xAA64:
                result["architecture"] = "ARM64"

            # Subsystem
            sub_id = pe.OPTIONAL_HEADER.Subsystem
            if sub_id == 2:
                result["subsystem"] = "Windows GUI"
            elif sub_id == 3:
                result["subsystem"] = "Windows Console (CUI)"

            # Sections & Entropy check for packing
            for sec in pe.sections:
                s_name = sec.Name.decode("utf-8", "ignore").strip("\x00")
                entropy = sec.get_entropy()
                result["sections"].append(f"{s_name} (Entropi: {entropy:.2f})")
                if entropy > 7.2:
                    result["is_packed"] = True

            # Check .NET (CLR Header)
            for entry in pe.OPTIONAL_HEADER.DATA_DIRECTORY:
                if entry.name == 'IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR' and entry.VirtualAddress > 0:
                    result["has_dotnet"] = True
                    break

            pe.close()
        except Exception:
            pass

        return result
