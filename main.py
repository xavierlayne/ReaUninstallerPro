import sys
import os
import argparse
import ctypes

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis_uninstaller.core import (
    scan_installed_programs, run_uninstaller_command,
    ResidualScanner, clean_residual_items,
    ForceUninstaller,
    scan_uwp_apps, remove_uwp_app,
    scan_browser_extensions,
    scan_startup_items,
    scan_software_health, fix_health_issues,
    FileShredder
)

def ensure_admin():
    """Relaunches with Windows UAC administrator elevation if not already admin."""
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            if getattr(sys, 'frozen', False):
                exe = sys.executable
                params = " ".join(f'"{a}"' for a in sys.argv[1:])
            else:
                exe = sys.executable
                params = f'"{os.path.abspath(__file__)}" ' + " ".join(f'"{a}"' for a in sys.argv[1:])
            res = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            # If ShellExecute returns > 32, the elevated process was spawned successfully
            if res > 32:
                sys.exit(0)
    except Exception:
        pass

def run_cli(args):
    if args.list:
        print("\n--- KURULU PROGRAMLAR ---")
        progs = scan_installed_programs()
        for idx, p in enumerate(progs, 1):
            print(f"{idx:3d}. {p.name} [{p.version or 'v?'}] ({p.formatted_size}) - {p.publisher or 'Bilinmeyen'}")
        print(f"\nToplam: {len(progs)} program bulundu.")

    elif args.force:
        target = args.force
        print(f"\n[!] ZORLA KALDIRMA BAŞLATILIYOR: {target}")
        res = ForceUninstaller.force_delete_target(target)
        if res["success"]:
            print(f"[+] Başarıyla silindi.")
            print(f"    Sonlandırılan süreçler: {len(res['killed_processes'])}")
            print(f"    Temizlenen kayıt defteri anahtarları: {res['purged_registry_keys']}")
        else:
            print(f"[-] Hata: {res['error']}")

    elif args.shred:
        target = args.shred
        print(f"\n[!] DOSYA PARÇALAYICI ÇALIŞIYOR (DoD 3 Geçişli): {target}")
        s, f = FileShredder.shred_target(target, passes=3)
        print(f"[+] Parçalandı: {s} dosya, Başarısız: {f} dosya")

    elif args.health:
        print("\n[+] SİSTEM SAĞLIĞI & KALINTI TARAMASI YAPILIYOR...")
        issues = scan_software_health()
        print(f"    {len(issues)} sorun tespit edildi.")
        for iss in issues:
            print(f"    - [{iss.category}] {iss.title} ({iss.path})")
        if issues and args.fix:
            fixed = fix_health_issues(issues)
            print(f"[+] {fixed} sorun başarıyla temizlendi.")

    elif args.uwp:
        print("\n--- WINDOWS UWP / BLOATWARE UYGULAMALARI ---")
        apps = scan_uwp_apps()
        for a in apps:
            tag = "[BLOATWARE]" if a.is_bloatware else "[UYGULAMA]"
            print(f"{tag:12s} {a.display_name} ({a.package_full_name})")

    else:
        print("Parametre belirtilmedi. GUI arayüzü başlatılıyor...")
        start_gui()

def start_gui():
    from jarvis_uninstaller.ui.app import ModernUninstallerApp
    app = ModernUninstallerApp()
    app.mainloop()

def main():
    ensure_admin()

    parser = argparse.ArgumentParser(description="ReaUninstallerPro — Gelişmiş Sistem Temizleyici ve Kaldırıcı")
    parser.add_argument("--gui", action="store_true", help="Grafik arayüzü başlat")
    parser.add_argument("--list", action="store_true", help="Kurulu tüm programları listele")
    parser.add_argument("--force", type=str, help="Belirtilen dosya veya klasörü zorla kaldır")
    parser.add_argument("--shred", type=str, help="Belirtilen dosyayı kalıcı olarak parçala (DoD)")
    parser.add_argument("--health", action="store_true", help="Yazılım sağlığı ve bozuk kısayol taraması yap")
    parser.add_argument("--fix", action="store_true", help="Sağlık taraması bulgularını otomatik onar")
    parser.add_argument("--uwp", action="store_true", help="Windows UWP / Bloatware uygulamalarını listele")

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.gui:
        start_gui()
    else:
        run_cli(args)

if __name__ == "__main__":
    main()
