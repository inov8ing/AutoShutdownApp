# AutoShutdown Widget ⚡

An open-source Windows floating widget that automatically shuts down your computer based on system resource usage (CPU, RAM, Disk) and user inactivity.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Language](https://img.shields.io/badge/language-Python-blue.svg)

## 🚀 Overview
**AutoShutdown Widget** is designed for users who want their PC to turn off automatically once heavy tasks (like rendering, compiling, or downloading) are finished and they have gone to sleep. Unlike simple timers, this app "really checks" your system resource usage to ensure it doesn't shut down while your computer is still working.

## ✨ Features
- **Floating Widget UI**: A modern, circular iconic UI that stays on top.
- **Interactive Expansion**: Click to expand into a full control panel; shrinks back when you move the mouse away.
- **Resource Thresholds**: Manually set CPU, RAM, and Disk MB/s limits to define what "Idle" means for your machine.
- **Mouse & Keyboard Tracking**: Detects user presence to prevent shutdown while you are reading or working.
- **Instant Shutdown**: Uses forced shutdown (`/f /t 0`) to ensure the PC turns off without hesitation.
- **Auto-Startup**: Option to run automatically when Windows starts.
- **Portable**: Can be compiled into a single `.exe` file for easy distribution.

## 🛠️ Installation

### 1. Prerequisites
- **Python 3.x**
- **pip**

### 2. Clone the Repository
```bash
git clone https://github.com/inov8ing/AutoShutdownApp.git
cd AutoShutdownApp
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the App
```bash
pythonw AutoShutdownApp.pyw
```

## 📦 How to Build (.exe)
If you want to create a standalone executable that you can share with others:
1. Run `python build_exe.py`
2. Your `.exe` will be in the `dist/` folder.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---
Created with ❤️ by Rizwan Ali.
