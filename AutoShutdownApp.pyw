import tkinter as tk
from tkinter import messagebox, ttk
import psutil
import json
import os
import threading
import time
import subprocess
import ctypes
import sys
import winreg

CONFIG_FILE = "config.json"

# --- Windows API Helpers ---

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]

def get_user_idle_time():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return max(0, millis / 1000.0)
    return 0

# --- App Settings & Persistence ---

def set_auto_startup(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "AutoShutdownWidget"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            if getattr(sys, 'frozen', False):
                path = sys.executable
            else:
                path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, path)
        else:
            try: winreg.DeleteValue(key, app_name)
            except FileNotFoundError: pass
        winreg.CloseKey(key)
    except: pass

class AutoShutdownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Shutdown Widget")
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.trans_color = "#abcdef"
        self.root.wm_attributes("-transparentcolor", self.trans_color)
        
        self.monitoring = False
        self.expanded = False
        self.idle_seconds = 0
        self.config = self.load_config()
        
        self._offset_x = 0
        self._offset_y = 0

        self.bg_color = "#1E1E1E"
        self.accent_color = "#2196F3"
        self.text_color = "#FFFFFF"
        self.root.configure(bg=self.trans_color)

        self.setup_ui()
        self.go_mini()
        self.update_metrics_loop()

    def setup_ui(self):
        # --- MINI MODE (CIRCLE) ---
        self.mini_canvas = tk.Canvas(self.root, width=60, height=60, bg=self.trans_color, highlightthickness=0, cursor="hand2")
        self.mini_canvas.create_oval(2, 2, 58, 58, fill="#000000", outline="")
        self.mini_canvas.create_oval(4, 4, 56, 56, fill=self.accent_color, outline="")
        self.mini_canvas.create_text(30, 30, text="⚡", fill="white", font=("Helvetica", 18, "bold"))
        
        self.mini_canvas.bind("<Button-1>", self.on_click)
        self.mini_canvas.bind("<B1-Motion>", self.on_drag)

        # --- EXPANDED MODE (COMPLETE WIDGET) ---
        self.expanded_frame = tk.Frame(self.root, bg=self.bg_color, padx=15, pady=15, highlightthickness=1, highlightbackground=self.accent_color)
        
        # Header
        header = tk.Frame(self.expanded_frame, bg=self.bg_color)
        header.pack(fill="x")
        tk.Label(header, text="SHUTDOWN MONITOR", font=("Helvetica", 11, "bold"), bg=self.bg_color, fg=self.accent_color).pack(side="left")
        close = tk.Label(header, text="✕", font=("Helvetica", 11), bg=self.bg_color, fg="gray", cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.root.destroy())

        # Live Metrics Panel (RETORED)
        metrics_frame = tk.Frame(self.expanded_frame, bg=self.bg_color, pady=10)
        metrics_frame.pack(fill="x")

        self.cpu_label = tk.Label(metrics_frame, text="CPU Usage: --%", bg=self.bg_color, fg=self.text_color, font=("Helvetica", 9))
        self.cpu_label.pack(anchor="w")
        self.cpu_bar = ttk.Progressbar(metrics_frame, mode='determinate')
        self.cpu_bar.pack(fill="x", pady=(0, 5))

        self.disk_label = tk.Label(metrics_frame, text="Disk Activity: -- MB/s", bg=self.bg_color, fg=self.text_color, font=("Helvetica", 9))
        self.disk_label.pack(anchor="w")
        self.disk_bar = ttk.Progressbar(metrics_frame, mode='determinate', maximum=100) # placeholder scale
        self.disk_bar.pack(fill="x", pady=(0, 5))

        self.ram_label = tk.Label(metrics_frame, text="RAM Usage: --%", bg=self.bg_color, fg=self.text_color, font=("Helvetica", 9))
        self.ram_label.pack(anchor="w")
        self.ram_bar = ttk.Progressbar(metrics_frame, mode='determinate')
        self.ram_bar.pack(fill="x", pady=(0, 5))

        self.user_idle_label = tk.Label(metrics_frame, text="User Idle: --s", bg=self.bg_color, fg="gray", font=("Helvetica", 8))
        self.user_idle_label.pack(anchor="w")

        # Threshold Settings (RESTORED)
        settings_frame = tk.LabelFrame(self.expanded_frame, text="Idle Limits (Auto-Saved)", bg=self.bg_color, fg="gray", font=("Helvetica", 8))
        settings_frame.pack(fill="x", pady=10, padx=2)

        # Timeout
        tk.Label(settings_frame, text="Timeout:", bg=self.bg_color, fg="white").grid(row=0, column=0, sticky="w", padx=5)
        self.timeout_var = tk.StringVar(value=self.config.get("timeout", "5 Minutes"))
        self.timeout_cb = ttk.Combobox(settings_frame, textvariable=self.timeout_var, state="readonly", width=10)
        self.timeout_cb['values'] = ("1 Minute", "5 Minutes", "15 Minutes", "30 Minutes", "1 Hour")
        self.timeout_cb.grid(row=0, column=1, pady=5, sticky="w")
        self.timeout_cb.bind("<<ComboboxSelected>>", self.save_config)

        # CPU Thresh
        tk.Label(settings_frame, text="CPU Max %:", bg=self.bg_color, fg="white").grid(row=1, column=0, sticky="w", padx=5)
        self.cpu_thresh = tk.DoubleVar(value=self.config.get("cpu_thresh", 10.0))
        tk.Spinbox(settings_frame, from_=0, to=100, textvariable=self.cpu_thresh, width=6, command=self.save_config).grid(row=1, column=1, sticky="w")

        # Disk Thresh
        tk.Label(settings_frame, text="Disk MB/s:", bg=self.bg_color, fg="white").grid(row=2, column=0, sticky="w", padx=5)
        self.disk_thresh = tk.DoubleVar(value=self.config.get("disk_thresh", 5.0))
        tk.Spinbox(settings_frame, from_=0, to=1000, textvariable=self.disk_thresh, width=6, command=self.save_config).grid(row=2, column=1, sticky="w")

        # RAM Thresh
        tk.Label(settings_frame, text="RAM Max %:", bg=self.bg_color, fg="white").grid(row=3, column=0, sticky="w", padx=5)
        self.ram_thresh = tk.DoubleVar(value=self.config.get("ram_thresh", 85.0))
        tk.Spinbox(settings_frame, from_=0, to=100, textvariable=self.ram_thresh, width=6, command=self.save_config).grid(row=3, column=1, sticky="w")

        self.startup_var = tk.BooleanVar(value=self.config.get("startup", False))
        tk.Checkbutton(settings_frame, text="Run on Startup", variable=self.startup_var, bg=self.bg_color, fg="gray", 
                       selectcolor=self.bg_color, activebackground=self.bg_color, command=self.save_config).grid(row=4, column=0, columnspan=2, sticky="w", padx=5)

        # Footer
        self.idle_timer_label = tk.Label(self.expanded_frame, text="Total Idle Time: 0s", font=("Helvetica", 12, "bold"), bg=self.bg_color, fg=self.accent_color)
        self.idle_timer_label.pack(pady=5)

        self.toggle_btn = tk.Button(self.expanded_frame, text="START MONITORING", command=self.toggle_monitoring, 
                                     bg=self.accent_color, fg="white", font=("Helvetica", 9, "bold"), relief="flat", height=2)
        self.toggle_btn.pack(fill="x")
        
        self.expanded_frame.bind("<Leave>", self.on_mouse_leave)

    def on_click(self, event):
        self._offset_x = event.x
        self._offset_y = event.y
        if not self.expanded: self.go_expanded()

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._offset_x
        y = self.root.winfo_y() + event.y - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    def on_mouse_leave(self, event):
        self.root.after(1000, self._check_collapse)

    def _check_collapse(self):
        x, y = self.root.winfo_pointerxy()
        wx, wy = self.root.winfo_rootx(), self.root.winfo_rooty()
        ww, wh = self.root.winfo_width(), self.root.winfo_height()
        if not (wx <= x <= wx + ww and wy <= y <= wy + wh): self.go_mini()

    def go_mini(self):
        self.expanded = False
        self.expanded_frame.pack_forget()
        self.mini_canvas.pack(expand=True, fill="both")
        self.root.geometry("60x60")

    def go_expanded(self):
        self.expanded = True
        self.mini_canvas.pack_forget()
        self.expanded_frame.pack(expand=True, fill="both")
        self.root.geometry("260x520") # Adjusted for metrics + settings

    def load_config(self):
        defaults = {"timeout": "5 Minutes", "cpu_thresh": 10.0, "disk_thresh": 5.0, "ram_thresh": 85.0, "startup": False}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict): defaults.update(data)
            except: pass
        return defaults

    def save_config(self, event=None):
        try:
            self.config = {
                "timeout": self.timeout_var.get(),
                "cpu_thresh": float(self.cpu_thresh.get()),
                "disk_thresh": float(self.disk_thresh.get()),
                "ram_thresh": float(self.ram_thresh.get()),
                "startup": self.startup_var.get()
            }
            with open(CONFIG_FILE, "w") as f: json.dump(self.config, f)
            set_auto_startup(self.startup_var.get())
        except: pass

    def toggle_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.idle_seconds = 0
            self.toggle_btn.config(text="STOP MONITORING", bg="#FF9800")
            threading.Thread(target=self.monitor_loop, daemon=True).start()
        else:
            self.monitoring = False
            self.toggle_btn.config(text="START MONITORING", bg=self.accent_color)
            self.idle_timer_label.config(text="Total Idle Time: 0s")

    def update_metrics_loop(self):
        def update():
            self.last_disk_io = psutil.disk_io_counters()
            while True:
                try:
                    time.sleep(1)
                    cpu = psutil.cpu_percent(interval=None)
                    ram = psutil.virtual_memory().percent
                    curr_disk = psutil.disk_io_counters()
                    disk_mb = 0
                    if curr_disk and self.last_disk_io:
                        disk_mb = ((curr_disk.read_bytes - self.last_disk_io.read_bytes) + (curr_disk.write_bytes - self.last_disk_io.write_bytes)) / (1024 * 1024)
                    self.last_disk_io = curr_disk
                    idle = get_user_idle_time()
                    
                    if self.expanded:
                        self.root.after(0, self._update_labels, cpu, disk_mb, ram, idle)
                except: time.sleep(1)
        threading.Thread(target=update, daemon=True).start()

    def _update_labels(self, cpu, disk_mb, ram, idle):
        self.cpu_label.config(text=f"CPU Usage: {cpu:.1f}%")
        self.cpu_bar['value'] = cpu
        self.disk_label.config(text=f"Disk Activity: {disk_mb:.2f} MB/s")
        self.disk_bar['value'] = min(100, disk_mb * 10) # scaled for visibility
        self.ram_label.config(text=f"RAM Usage: {ram:.1f}%")
        self.ram_bar['value'] = ram
        self.user_idle_label.config(text=f"User Idle: {int(idle)}s")

    def monitor_loop(self):
        last_disk = psutil.disk_io_counters()
        while self.monitoring:
            time.sleep(2)
            if not self.monitoring: break
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            curr_disk = psutil.disk_io_counters()
            disk_mb = 0
            if curr_disk and last_disk:
                disk_mb = ((curr_disk.read_bytes - last_disk.read_bytes) + (curr_disk.write_bytes - last_disk.write_bytes)) / (1024 * 1024) / 2
            last_disk = curr_disk
            idle = get_user_idle_time()

            is_idle = (cpu < self.cpu_thresh.get()) and (ram < self.ram_thresh.get()) and \
                      (disk_mb < self.disk_thresh.get()) and (idle >= 2.0)

            if is_idle:
                self.idle_seconds += 2
                self.root.after(0, self.idle_timer_label.config, {"text": f"Total Idle Time: {self.idle_seconds}s"})
                if self.idle_seconds >= self.get_timeout_seconds():
                    self.root.after(0, self.trigger_shutdown)
                    break
            else:
                self.idle_seconds = 0
                self.root.after(0, self.idle_timer_label.config, {"text": "Total Idle Time: 0s (Active)"})

    def get_timeout_seconds(self):
        val = self.timeout_var.get()
        if "Minute" in val: return int(val.split()[0]) * 60
        if "Hour" in val: return int(val.split()[0]) * 3600
        return 300

    def trigger_shutdown(self):
        self.monitoring = False
        subprocess.run(["shutdown", "/s", "/f", "/t", "0"], shell=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoShutdownApp(root)
    root.mainloop()
