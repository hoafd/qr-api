import sys
import os
import ctypes
import threading
import multiprocessing
import tkinter as tk
from tkinter import messagebox
import socket
import uvicorn
import pystray
from PIL import Image, ImageDraw
import app.main # Explicit import for PyInstaller
from app.config import load_config, save_config

# Fix for PyInstaller --noconsole mode: sys.stdout and sys.stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def create_image():
    width = 64
    height = 64
    color1 = "#3b82f6"
    color2 = "#10b981"
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image

class QRRunnerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("QR API Server - Setup")
        self.root.geometry("400x560")
        self.root.configure(bg="#1e293b")
        self.root.resizable(False, False)

        self.font_main = ("Segoe UI", 10)
        self.font_header = ("Segoe UI", 14, "bold")
        self.local_ip = get_local_ip()

        self.config = load_config()
        self.server = None
        self.server_thread = None
        self.is_running = False

        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)

        # Title
        self.label_title = tk.Label(root, text="🚀 MÁY CHỦ QR CODE API", font=self.font_header, fg="#f8fafc", bg="#1e293b", pady=15)
        self.label_title.pack()

        # Detected IP
        ip_info_text = f"💡 IP máy của bạn: {self.local_ip}"
        tk.Label(root, text=ip_info_text, font=("Segoe UI", 9, "italic"), fg="#38bdf8", bg="#1e293b").pack(pady=(0, 10))

        # Host
        frame_host = tk.Frame(root, bg="#1e293b")
        frame_host.pack(pady=5)
        tk.Label(frame_host, text="Host (IP):", font=self.font_main, fg="#cbd5e1", bg="#1e293b", width=12, anchor="w").pack(side="left")
        self.host_entry = tk.Entry(frame_host, font=self.font_main, width=15)
        self.host_entry.insert(0, str(self.config.get("host", "0.0.0.0")))
        self.host_entry.pack(side="left")

        # Port
        frame_port = tk.Frame(root, bg="#1e293b")
        frame_port.pack(pady=5)
        tk.Label(frame_port, text="Port (Cổng):", font=self.font_main, fg="#cbd5e1", bg="#1e293b", width=12, anchor="w").pack(side="left")
        self.port_entry = tk.Entry(frame_port, font=self.font_main, width=15)
        self.port_entry.insert(0, str(self.config.get("port", 8000)))
        self.port_entry.pack(side="left")

        # Max File Size
        frame_size = tk.Frame(root, bg="#1e293b")
        frame_size.pack(pady=5)
        tk.Label(frame_size, text="Giới hạn ảnh (MB):", font=self.font_main, fg="#cbd5e1", bg="#1e293b", width=15, anchor="w").pack(side="left")
        self.size_entry = tk.Entry(frame_size, font=self.font_main, width=12)
        self.size_entry.insert(0, str(self.config.get("max_file_size_mb", 10)))
        self.size_entry.pack(side="left")

        # API Docs Toggle
        self.docs_var = tk.BooleanVar(value=self.config.get("enable_api_docs", False))
        self.docs_check = tk.Checkbutton(root, text="Bật trang tài liệu API (/docs)", variable=self.docs_var, font=self.font_main, fg="#cbd5e1", bg="#1e293b", selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#f8fafc")
        self.docs_check.pack(pady=5)

        # Buttons
        self.toggle_button = tk.Button(root, text="🚀 KHỞI CHẠY SERVER", font=("Segoe UI", 11, "bold"), 
                                     bg="#10b981", fg="white", padx=20, pady=10, 
                                     command=self.toggle_server, borderwidth=0, width=20)
        self.toggle_button.pack(pady=15)

        self.tray_button = tk.Button(root, text="⬇️ ẨN XUỐNG KHAY (CHẠY NGẦM)", font=("Segoe UI", 10, "bold"), 
                                     bg="#3b82f6", fg="white", padx=20, pady=8, 
                                     command=self.hide_to_tray, borderwidth=0, width=22)
        self.tray_button.pack(pady=5)

        self.status_label = tk.Label(root, text="Trạng thái: Đang chờ...", font=self.font_main, fg="#94a3b8", bg="#1e293b")
        self.status_label.pack(pady=10)

        # Copy URL Frame (Hidden initially)
        self.url_frame = tk.Frame(root, bg="#1e293b")
        self.url_entry = tk.Entry(self.url_frame, font=("Segoe UI", 10, "bold"), width=24, justify="center", fg="#10b981", bg="#0f172a", readonlybackground="#0f172a")
        self.url_entry.pack(side="left", padx=5, ipady=4)
        self.copy_btn = tk.Button(self.url_frame, text="📋 Copy", font=("Segoe UI", 9, "bold"), bg="#f59e0b", fg="white", borderwidth=0, padx=10, pady=2, command=self.copy_url)
        self.copy_btn.pack(side="left")

    def copy_url(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.url_entry.get())
        self.root.update()
        
        # Đổi chữ nút tạm thời thay vì hiện popup
        self.copy_btn.config(text="✅ Đã Copy!", bg="#10b981")
        self.root.after(2000, lambda: self.copy_btn.config(text="📋 Copy", bg="#f59e0b"))

    def toggle_server(self):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        host_str = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        size_str = self.size_entry.get().strip()
        
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
            size = int(size_str)
            if size < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Cổng (1-65535) và Giới hạn dung lượng phải là số hợp lệ.")
            return

        # Save config
        self.config["host"] = host_str
        self.config["port"] = port
        self.config["max_file_size_mb"] = size
        self.config["enable_api_docs"] = self.docs_var.get()
        save_config(self.config)

        self.is_running = True
        self.toggle_button.config(text="🛑 TẮT SERVER", bg="#ef4444")
        
        display_ip = self.local_ip if host_str == "0.0.0.0" else host_str
        full_url = f"http://{display_ip}:{port}"
        self.status_label.config(text="Server đang hoạt động tại địa chỉ:", fg="#34d399")
        
        # Hiển thị ô copy URL
        self.url_entry.config(state="normal")
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, full_url)
        self.url_entry.config(state="readonly")
        self.url_frame.pack(pady=5)
        
        self.host_entry.config(state="disabled")
        self.port_entry.config(state="disabled")
        self.size_entry.config(state="disabled")
        self.docs_check.config(state="disabled")
        
        self.server_thread = threading.Thread(target=self.run_uvicorn, args=(host_str, port,), daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if self.server:
            self.server.should_exit = True
        
        self.is_running = False
        self.toggle_button.config(text="🚀 KHỞI CHẠY SERVER", bg="#10b981")
        self.status_label.config(text="Trạng thái: Đã dừng", fg="#cbd5e1")
        self.url_frame.pack_forget() # Ẩn ô copy
        
        self.host_entry.config(state="normal")
        self.port_entry.config(state="normal")
        self.size_entry.config(state="normal")
        self.docs_check.config(state="normal")

    def run_uvicorn(self, host, port):
        # Tải lại module để áp dụng cấu hình Docs mới nhất
        import importlib
        importlib.reload(app.config)
        importlib.reload(app.main)

        LOG_CONFIG = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(message)s",
                    "use_colors": None,
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO"},
                "uvicorn.error": {"level": "INFO"},
            },
        }

        config = uvicorn.Config(app.main.app, host=host, port=port, log_level="info", log_config=LOG_CONFIG)
        self.server = uvicorn.Server(config)
        
        try:
            self.server.run()
        except Exception as e:
            pass
        finally:
            if self.is_running:
                self.root.after(0, self.stop_server)

    def hide_to_tray(self):
        self.root.withdraw()
        
        image = create_image()
        menu = pystray.Menu(
            pystray.MenuItem('Mở Giao Diện', self.show_from_tray, default=True),
            pystray.MenuItem('Thoát Hoàn Toàn', self.exit_from_tray)
        )
        self.icon = pystray.Icon("QRServer", image, "QR API Server", menu)
        
        threading.Thread(target=self.icon.run, daemon=True).start()

    def show_from_tray(self, icon, item):
        self.icon.stop()
        self.root.deiconify()

    def exit_from_tray(self, icon, item):
        self.icon.stop()
        self.on_closing()

    def on_closing(self):
        if self.is_running:
            self.stop_server()
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    gui_runner = QRRunnerGUI(root)
    root.mainloop()
