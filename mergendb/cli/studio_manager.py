import os
import sys
import subprocess
import shutil

STUDIO_CACHE_DIR = os.path.expanduser(os.path.join("~", ".mergendb", "studio"))
STUDIO_CACHE_FILE = os.path.join(STUDIO_CACHE_DIR, "index.html")

def is_studio_installed() -> bool:
    """Checks whether the optional Mergen Studio Web UI is available."""
    try:
        import mergendb_studio
        return True
    except ImportError:
        return False

def get_studio_status() -> dict:
    installed = is_studio_installed()
    source = "not installed"
    if installed:
        try:
            import mergendb_studio
            source = f"package: mergendb_studio (v{getattr(mergendb_studio, '__version__', 'unknown')})"
        except ImportError:
            pass

    return {
        "installed": installed,
        "source": source
    }

def install_studio():
    """Installs or enables the optional Mergen Studio addon."""
    print("=" * 70)
    print("   [+] MERGEN STUDIO INSTALLER")
    print("=" * 70)

    # Try pip install mergendb-studio
    print("[*] Attempting to install 'mergendb-studio' via pip...")
    python_exe = sys.executable or "python"
    try:
        res = subprocess.run([python_exe, "-m", "pip", "install", "mergendb-studio"], capture_output=True, text=True)
        if res.returncode == 0:
            print("[+] Successfully installed 'mergendb-studio' package!")
            print("[+] Mergen Studio is now active and ready on http://localhost:8765/studio")
            return True
        else:
            print(f"[-] pip install failed: {res.stderr.strip() if res.stderr else res.stdout.strip()}")
    except Exception as e:
        print(f"[-] pip installation error: {e}")

    print("[-] Could not install automatically. Please run:")
    print("    pip install mergendb-studio")
    return False

def handle_studio_cli(action: str = "status"):
    action = action.lower().strip()
    if action in ("install", "setup", "upgrade"):
        install_studio()
    elif action in ("status", "check", "info"):
        st = get_studio_status()
        print("=" * 60)
        print("   [+] MERGEN STUDIO STATUS")
        print("=" * 60)
        print(f"  * Installed : {st['installed']}")
        print(f"  * Source    : {st['source']}")
        print("=" * 60)
        if not st['installed']:
            print("\nTo install Mergen Studio, run: mergen studio install\n")
    else:
        print(f"Unknown studio action: '{action}'. Valid actions: install, status")
