import os
import subprocess
import sys

def build():
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("Building Executable...")
    # --noconsole: Hide terminal
    # --onefile: Single .exe file
    # --name: Name of the .exe
    # --add-data: Include config if it exists (though it will be created if missing)
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=AutoShutdown",
        "AutoShutdownApp.pyw"
    ]
    
    subprocess.check_call(cmd)
    
    print("\nSUCCESS!")
    print("Your executable is in the 'dist' folder.")
    print("You can share 'AutoShutdown.exe' with anyone!")

if __name__ == "__main__":
    build()
