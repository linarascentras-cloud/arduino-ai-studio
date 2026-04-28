"""Arduino AI Studio v3.0 - Launcher"""
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED = {
    "customtkinter": "customtkinter",
    "serial":        "pyserial",
    "PIL":           "Pillow",
    "requests":      "requests",
}

def check_deps():
    missing = []
    for imp, pkg in REQUIRED.items():
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"📦 Diegiami trūkstami paketai: {', '.join(missing)}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing + ["-q"],
            capture_output=False
        )

def ensure_dirs():
    for d in ["logs", "workspace/sketch", "tools"]:
        (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "core" / "__init__.py").touch(exist_ok=True)
    (PROJECT_ROOT / "gui"  / "__init__.py").touch(exist_ok=True)

def main():
    print("=" * 50)
    print("  🤖 Arduino AI Studio v3.0")
    print("=" * 50)
    ensure_dirs()
    check_deps()
    try:
        from gui.app import launch
        launch()
    except Exception as e:
        print(f"\n[KLAIDA] {e}")
        import traceback
        traceback.print_exc()
        input("\nSpauskite Enter...")
        sys.exit(1)

if __name__ == "__main__":
    main()
