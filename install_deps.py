import sys
import os
import subprocess

def check_imports():
    try:
        import webview
        import winpty
        return True
    except ImportError:
        return False

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True)
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("==================================================")
    print("   WSL Desktop Nexus - Dependency Installer")
    print("==================================================")
    
    if check_imports():
        print("[OK] All dependencies (pywebview, pywinpty) are already installed!")
        sys.exit(0)
        
    deps = ["pywebview", "pywinpty"]
    
    # Method 1: Standard pip install
    print("\n[Method 1] Trying standard pip install...")
    cmd = [sys.executable, "-m", "pip", "install"] + deps
    print(f"Running: {' '.join(cmd)}")
    ok, stdout, stderr = run_cmd(cmd)
    if ok and check_imports():
        print("[OK] Successfully installed dependencies using standard pip install!")
        sys.exit(0)
    else:
        print("[FAIL] Standard pip install was not successful.")
        if stderr:
            print(f"Error info: {stderr.strip()}")

    # Method 2: pip install --user
    print("\n[Method 2] Trying pip install with --user option...")
    cmd = [sys.executable, "-m", "pip", "install", "--user"] + deps
    print(f"Running: {' '.join(cmd)}")
    ok, stdout, stderr = run_cmd(cmd)
    if ok and check_imports():
        print("[OK] Successfully installed dependencies with --user option!")
        sys.exit(0)
    else:
        print("[FAIL] pip install --user was not successful.")
        if stderr:
            print(f"Error info: {stderr.strip()}")

    # Method 3: Try using uv (if available in PATH)
    print("\n[Method 3] Trying to install dependencies using uv...")
    uv_ok, _, _ = run_cmd(["uv", "--version"])
    if uv_ok:
        cmd = ["uv", "pip", "install"] + deps
        if not (os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")):
            cmd.append("--system")
        print(f"Running: {' '.join(cmd)}")
        ok, stdout, stderr = run_cmd(cmd)
        if ok and check_imports():
            print("[OK] Successfully installed dependencies using uv!")
            sys.exit(0)
        else:
            print("[FAIL] uv pip install was not successful.")
            if stderr:
                print(f"Error info: {stderr.strip()}")
    else:
        print("[-] uv package manager is not available in system PATH.")

    # Method 4: Try using python -m uv (if installed in environment)
    print("\n[Method 4] Trying to install dependencies using python -m uv...")
    cmd = [sys.executable, "-m", "uv", "pip", "install"] + deps
    if not (os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")):
        cmd.append("--system")
    print(f"Running: {' '.join(cmd)}")
    ok, stdout, stderr = run_cmd(cmd)
    if ok and check_imports():
        print("[OK] Successfully installed dependencies using python -m uv!")
        sys.exit(0)
    else:
        print("[FAIL] python -m uv was not successful.")
        if stderr:
            print(f"Error info: {stderr.strip()}")

    # Verification fallback check
    if check_imports():
        print("\n[OK] Dependencies successfully installed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Failed to install dependencies using all available methods.")
        print("Please check your internet connection or run the following command manually in an elevated command prompt:")
        print("  pip install pywebview pywinpty")
        sys.exit(1)

if __name__ == "__main__":
    main()
