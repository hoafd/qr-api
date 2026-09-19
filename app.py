"""
QR API Server — Windows Desktop Control App
Quản lý config, bật/tắt server, ẩn xuống khay hệ thống.
"""
import asyncio
import importlib
import logging
import os
import socket
import sys
import threading
import webbrowser
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext

def handle_exception(exc_type, exc_value, exc_traceback):
    with open("crash.txt", "a", encoding="utf-8") as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

sys.excepthook = handle_exception

def handle_thread_exception(args):
    with open("crash.txt", "a", encoding="utf-8") as f:
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=f)

threading.excepthook = handle_thread_exception

# Fix for uvicorn logging in PyInstaller --noconsole mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Đường dẫn gốc
if hasattr(sys, "_MEIPASS"):
    BASE_DIR = os.path.dirname(sys.executable)   # Cạnh .exe
    SRC_DIR  = sys._MEIPASS                       # Python libs + bundled files
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SRC_DIR  = BASE_DIR

# Thêm SRC_DIR vào path để import server, config, qr_engine
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import load_config, save_config, generate_api_key

# ── Pystray (optional) ────────────────────────────────────────────────────────
try:
    import pystray
    from PIL import Image as PILImage, ImageDraw, ImageTk
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    try:
        from PIL import ImageTk
    except ImportError:
        ImageTk = None

# ── Colors ────────────────────────────────────────────────────────────────────
C_BG      = "#0f172a"
C_SURFACE = "#1e293b"
C_SURF2   = "#334155"
C_BORDER  = "#475569"
C_ACCENT  = "#6366f1"
C_ACC2    = "#4f46e5"
C_OK      = "#10b981"
C_ERR     = "#ef4444"
C_WARN    = "#f59e0b"
C_TEXT    = "#f1f5f9"
C_MUTED   = "#94a3b8"
C_CYAN    = "#67e8f9"

FONT      = "Segoe UI"
MONO      = "Consolas"


# ── Logging → Text Widget ─────────────────────────────────────────────────────
class _WidgetHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._widget: tk.Text | None = None
        self._buf: list[tuple[str, str]] = []

    def set_widget(self, w: tk.Text):
        self._widget = w
        for msg, level in self._buf:
            self._append(msg, level)
        self._buf.clear()

    def emit(self, record: logging.LogRecord):
        msg = self.format(record) + "\n"
        tag = record.levelname
        if self._widget:
            self._widget.after(0, self._append, msg, tag)
        else:
            self._buf.append((msg, tag))

    def _append(self, msg: str, tag: str):
        if not self._widget:
            return
        try:
            self._widget.configure(state="normal")
            self._widget.insert("end", msg, tag)
            self._widget.see("end")
            self._widget.configure(state="disabled")
        except tk.TclError:
            pass


_wh = _WidgetHandler()
_wh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(_wh)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("QRApp")


# ── Network ───────────────────────────────────────────────────────────────────
def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── Tray Icon Image ───────────────────────────────────────────────────────────
def _make_tray_img(running: bool):
    sz = 64
    img = PILImage.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (99, 102, 241) if running else (71, 85, 105)
    d.ellipse([0, 0, sz - 1, sz - 1], fill=col)
    # QR dots
    dots = [(1, 1), (1, 2), (2, 0), (2, 2), (0, 0), (0, 2)]
    sq, pad = 10, 17
    for r in range(3):
        for c in range(3):
            if (r, c) in [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)]:
                x, y = pad + c * (sq + 2), pad + r * (sq + 2)
                d.rectangle([x, y, x + sq - 1, y + sq - 1], fill="white")
    return img


# ── Server Manager ────────────────────────────────────────────────────────────
class ServerManager:
    def __init__(self):
        self._srv = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, host: str, port: int) -> tuple[bool, str]:
        if self.is_running:
            self.stop()
            
        # 1. Kiểm tra xem cổng có đang bị sử dụng không
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host, port))
            s.close()
        except OSError:
            return False, f"Cổng {port} đang bị sử dụng bởi tiến trình khác."

        try:
            import uvicorn
            srv_mod = importlib.import_module("server")
            ucfg = uvicorn.Config(
                app=srv_mod.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                log_config=None,
            )
            self._srv = uvicorn.Server(ucfg)
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="uvicorn"
            )
            self._thread.start()
            return True, ""
        except Exception as e:
            logger.error(f"Lỗi khởi động server: {e}", exc_info=True)
            return False, str(e)

    def _run(self):
        try:
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._srv.serve())
        except BaseException:
            with open("crash_serve.txt", "a", encoding="utf-8") as f:
                f.write(traceback.format_exc())

    def stop(self):
        if self._srv:
            self._srv.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=6)
        self._srv = None
        self._thread = None
        self._loop = None
        logger.info("Server đã dừng.")


# ── Helpers UI ────────────────────────────────────────────────────────────────
def _btn(parent, text, cmd, bg, fg, font_w="bold", padx=16, pady=6, **kw):
    b = tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg=fg, bd=0, relief="flat",
        font=(FONT, 9, font_w), padx=padx, pady=pady,
        cursor="hand2", activebackground=bg, activeforeground=fg,
        **kw,
    )
    return b


def _label(parent, text, fg=C_TEXT, bg=C_SURFACE, size=9, weight="normal", **kw):
    return tk.Label(parent, text=text, fg=fg, bg=bg, font=(FONT, size, weight), **kw)


def _entry(parent, textvariable, width=10, mono=False, fg=C_TEXT, **kw):
    f = MONO if mono else FONT
    e = tk.Entry(
        parent, textvariable=textvariable, width=width,
        bg=C_SURF2, fg=fg, insertbackground=C_TEXT,
        font=(f, 10), bd=0, relief="flat",
        highlightthickness=1, highlightcolor=C_ACCENT, highlightbackground=C_BORDER,
        **kw,
    )
    return e


# ── Main App ──────────────────────────────────────────────────────────────────
class QRServerApp:
    def __init__(self):
        self.cfg = load_config()
        self.server = ServerManager()
        self._tray: "pystray.Icon | None" = None
        self._tray_thread: threading.Thread | None = None
        self._poll_id = None
        self._current_url = ""

        # ── Root window ──────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("QR API Server")
        self.root.geometry("500x740")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)

        # ── Tk variables ─────────────────────────────────────────────────────
        self.v_port     = tk.StringVar(value=str(self.cfg.get("port", 8000)))
        self.v_host     = tk.StringVar(value=self.cfg.get("host", "0.0.0.0"))
        self.v_key_on   = tk.BooleanVar(value=self.cfg.get("api_key_enabled", False))
        self.v_key      = tk.StringVar(value=self.cfg.get("api_key", ""))
        self.v_tray     = tk.BooleanVar(value=self.cfg.get("minimize_to_tray", True))
        self.v_autostart= tk.BooleanVar(value=self.cfg.get("auto_start", False))

        self._set_icon()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if TRAY_AVAILABLE:
            self._setup_tray()

        if self.cfg.get("auto_start"):
            self.root.after(600, self.start_server)

        self._poll_status()

    # ── Icon ─────────────────────────────────────────────────────────────────
    def _set_icon(self):
        if TRAY_AVAILABLE and ImageTk:
            try:
                img = _make_tray_img(False)
                self._tk_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._tk_icon)
            except Exception:
                pass

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = self.root

        # ─ Header ─
        hdr = tk.Frame(root, bg=C_BG)
        hdr.pack(fill="x", padx=18, pady=(18, 10))

        tk.Label(hdr, text="⬡  QR API Server", bg=C_BG, fg=C_TEXT,
                 font=(FONT, 15, "bold")).pack(side="left")

        self.lbl_status = tk.Label(hdr, text="● Dừng", bg="#1c1917", fg=C_ERR,
                                    font=(FONT, 9, "bold"), padx=10, pady=4,
                                    relief="flat")
        self.lbl_status.pack(side="right")

        # ─ URL bar ─
        url_card = self._card(pady=(0, 8))
        self._sec_title(url_card, "🌐 ĐỊA CHỈ SERVER")
        url_row = tk.Frame(url_card, bg=C_SURFACE)
        url_row.pack(fill="x")

        self.lbl_url = tk.Label(url_row, text="Chưa khởi động", bg=C_SURFACE,
                                 fg=C_MUTED, font=(FONT, 11), anchor="w")
        self.lbl_url.pack(side="left", fill="x", expand=True)

        _btn(url_row, "🌐", self._open_browser, C_SURF2, C_TEXT, "normal", padx=8, pady=3).pack(side="right", padx=2)
        _btn(url_row, "📋", self._copy_url,     C_SURF2, C_TEXT, "normal", padx=8, pady=3).pack(side="right")

        # ─ Control buttons ─
        ctrl = self._card(pady=(0, 8))
        self._sec_title(ctrl, "⚡ ĐIỀU KHIỂN SERVER")
        btns = tk.Frame(ctrl, bg=C_SURFACE)
        btns.pack(fill="x")

        self.btn_start = _btn(btns, "▶  KHỞI ĐỘNG", self.start_server, C_ACCENT, "white", padx=20, pady=9)
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = _btn(btns, "⏹  DỪNG", self.stop_server, "#1c1917", C_ERR, padx=20, pady=9)
        self.btn_stop.pack(side="left", padx=(0, 8))
        self.btn_stop.configure(state="disabled")

        _btn(btns, "📂 Mở trang web", self._open_browser, C_SURF2, C_TEXT, "normal", padx=12, pady=9
             ).pack(side="right")

        # ─ Config ─
        cfg_c = self._card(pady=(0, 8))
        self._sec_title(cfg_c, "⚙️ CẤU HÌNH SERVER")
        r1 = tk.Frame(cfg_c, bg=C_SURFACE)
        r1.pack(fill="x", pady=(0, 10))

        _label(r1, "Cổng:", fg=C_MUTED).pack(side="left")
        _entry(r1, self.v_port, width=7).pack(side="left", padx=(6, 18), ipady=5, ipadx=4)

        _label(r1, "Host:", fg=C_MUTED).pack(side="left")
        om = tk.OptionMenu(r1, self.v_host, "0.0.0.0", "127.0.0.1", "localhost")
        om.configure(bg=C_SURF2, fg=C_TEXT, activebackground=C_BORDER, activeforeground=C_TEXT,
                     font=(FONT, 9), bd=0, relief="flat", highlightthickness=0, padx=4, pady=3)
        om["menu"].configure(bg=C_SURF2, fg=C_TEXT, activebackground=C_ACCENT, activeforeground="white",
                              font=(FONT, 9), bd=0)
        om.pack(side="left", padx=6)

        r2 = tk.Frame(cfg_c, bg=C_SURFACE)
        r2.pack(fill="x")
        
        _btn(r2, "💾 Lưu", self._save_all, C_ACCENT, "white", padx=12, pady=5).pack(side="right")

        # ─ Security ─
        sec_c = self._card(pady=(0, 8))
        self._sec_title(sec_c, "🔐 BẢO MẬT API KEY")

        tk.Checkbutton(
            sec_c, text=" Bật xác thực API Key (bảo vệ tất cả endpoint /api/*)",
            variable=self.v_key_on, onvalue=True, offvalue=False,
            bg=C_SURFACE, fg=C_TEXT, selectcolor=C_SURF2,
            activebackground=C_SURFACE, activeforeground=C_TEXT,
            font=(FONT, 9), cursor="hand2",
        ).pack(anchor="w", pady=(0, 10))

        kr = tk.Frame(sec_c, bg=C_SURFACE)
        kr.pack(fill="x", pady=(0, 6))

        _label(kr, "Mã:", fg=C_MUTED).pack(side="left")
        self.ent_key = _entry(kr, self.v_key, width=16, mono=True, fg=C_CYAN)
        self.ent_key.pack(side="left", padx=(6, 8), ipady=5, ipadx=4)

        _btn(kr, "🔄", self._regen_key,  C_SURF2, C_TEXT, "normal", padx=8, pady=4).pack(side="left", padx=(0, 4))
        _btn(kr, "📋", self._copy_key,   C_SURF2, C_TEXT, "normal", padx=8, pady=4).pack(side="left", padx=(0, 8))
        _btn(kr, "💾 Lưu", self._save_sec, "#134e4a", "#6ee7b7", padx=10, pady=4).pack(side="right")

        _label(sec_c, "Gửi header:  X-API-Key: <mã>  kèm theo mỗi request /api/*",
               fg=C_MUTED, size=8, bg=C_SURFACE).pack(anchor="w")

        # ─ Options ─
        opt_c = self._card(pady=(0, 8))
        self._sec_title(opt_c, "🔧 TÙY CHỌN")

        for txt, var, cmd in [
            (" Ẩn xuống khay hệ thống khi đóng cửa sổ",  self.v_tray,      self._save_opts),
            (" Tự khởi động server khi mở ứng dụng",     self.v_autostart, self._save_opts),
        ]:
            tk.Checkbutton(
                opt_c, text=txt, variable=var, onvalue=True, offvalue=False,
                bg=C_SURFACE, fg=C_TEXT, selectcolor=C_SURF2,
                activebackground=C_SURFACE, activeforeground=C_TEXT,
                font=(FONT, 9), cursor="hand2", command=cmd,
            ).pack(anchor="w", pady=2)

        if not TRAY_AVAILABLE:
            _label(opt_c, "⚠ pystray không khả dụng — khay hệ thống bị tắt", fg=C_WARN, size=8
                   ).pack(anchor="w", pady=(6, 0))

        # ─ Log console ─
        log_c = self._card(pady=(0, 16))
        log_hdr = tk.Frame(log_c, bg=C_SURFACE)
        log_hdr.pack(fill="x", pady=(0, 6))
        self._sec_title(log_hdr, "📋 NHẬT KÝ (LOG)")
        _btn(log_hdr, "🗑 Xóa", self._clear_log, C_SURF2, C_MUTED, "normal", padx=8, pady=2
             ).pack(side="right")

        self.log_txt = tk.Text(
            log_c, height=9, bg="#020617", fg=C_MUTED, font=(MONO, 8),
            bd=0, relief="flat", state="disabled", wrap="none",
            insertbackground=C_TEXT, selectbackground=C_SURF2,
        )
        self.log_txt.pack(fill="x")
        # Color tags
        self.log_txt.tag_configure("INFO",    foreground=C_MUTED)
        self.log_txt.tag_configure("WARNING", foreground=C_WARN)
        self.log_txt.tag_configure("ERROR",   foreground=C_ERR)
        self.log_txt.tag_configure("DEBUG",   foreground="#475569")

        _wh.set_widget(self.log_txt)

        # ─ Status bar ─
        sb = tk.Frame(root, bg="#0a1628", height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self.lbl_sb = tk.Label(sb, text="Sẵn sàng", bg="#0a1628", fg=C_MUTED, font=(FONT, 8), anchor="w")
        self.lbl_sb.pack(side="left", padx=12)
        tk.Label(sb, text="QR API Server v2.0", bg="#0a1628", fg="#1e293b", font=(FONT, 8)).pack(side="right", padx=12)

    # ── Card helpers ─────────────────────────────────────────────────────────
    def _card(self, pady=(0, 8)):
        outer = tk.Frame(self.root, bg=C_SURFACE)
        outer.pack(fill="x", padx=14, pady=pady)
        inner = tk.Frame(outer, bg=C_SURFACE)
        inner.pack(fill="x", padx=14, pady=12)
        return inner

    def _sec_title(self, parent, text):
        tk.Label(parent, text=text, bg=C_SURFACE, fg=C_MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 8))

    # ── Server control ────────────────────────────────────────────────────────
    def start_server(self):
        if self.server.is_running:
            return
        self._save_all()
        cfg = load_config()
        host = cfg.get("host", "0.0.0.0")
        port = int(cfg.get("port", 8000))

        self.btn_start.configure(state="disabled", text="⏳ Đang khởi động...")
        logger.info(f"Khởi động server tại {host}:{port}...")

        def _go():
            ok, msg = self.server.start(host, port)
            self.root.after(0, self._on_started, ok, host, port, msg)

        threading.Thread(target=_go, daemon=True).start()

    def _on_started(self, ok, host, port, err_msg=""):
        self.btn_start.configure(text="▶  KHỞI ĐỘNG")
        if ok:
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            ip = get_lan_ip()
            self._current_url = f"http://{ip}:{port}"
            self.lbl_url.configure(text=self._current_url, fg="#818cf8")
            self.lbl_sb.configure(text=f"Đang chạy  ●  Cổng {port}  ●  IP: {ip}")
            if self._tray:
                try:
                    self._tray.icon = _make_tray_img(True)
                    self._tray.title = f"QR Server — Đang chạy :{port}"
                except Exception:
                    pass
        else:
            self.btn_start.configure(state="normal")
            err = err_msg or "Lỗi không xác định."
            messagebox.showerror("Lỗi", f"Không khởi động được server trên cổng {port}.\nChi tiết: {err}")

    def stop_server(self):
        if not self.server.is_running:
            return
        self.btn_stop.configure(state="disabled", text="⏳ Đang dừng...")
        logger.info("Đang dừng server...")

        def _stop():
            self.server.stop()
            self.root.after(0, self._on_stopped)

        threading.Thread(target=_stop, daemon=True).start()

    def _on_stopped(self):
        self.btn_start.configure(state="normal", text="▶  KHỞI ĐỘNG")
        self.btn_stop.configure(state="disabled", text="⏹  DỪNG")
        self.lbl_url.configure(text="Chưa khởi động", fg=C_MUTED)
        self.lbl_sb.configure(text="Đã dừng")
        self._current_url = ""
        if self._tray:
            try:
                self._tray.icon  = _make_tray_img(False)
                self._tray.title = "QR API Server — Dừng"
            except Exception:
                pass

    # ── Config save ───────────────────────────────────────────────────────────
    def _save_all(self):
        try:
            port = int(self.v_port.get())
            assert 1 <= port <= 65535
        except (ValueError, AssertionError):
            messagebox.showerror("Lỗi", "Cổng không hợp lệ (phải là 1–65535).")
            return
        self.cfg.update({
            "port":            port,
            "host":            self.v_host.get(),
            "api_key_enabled": self.v_key_on.get(),
            "api_key":         self.v_key.get(),
            "minimize_to_tray":self.v_tray.get(),
            "auto_start":      self.v_autostart.get(),
        })
        save_config(self.cfg)

    def _save_sec(self):
        self.cfg.update({
            "api_key_enabled": self.v_key_on.get(),
            "api_key":         self.v_key.get(),
        })
        save_config(self.cfg)
        tip = "Khởi động lại server để áp dụng." if self.server.is_running else "Đã lưu."
        messagebox.showinfo("Bảo mật đã lưu", tip)

    def _save_opts(self):
        self.cfg.update({
            "minimize_to_tray": self.v_tray.get(),
            "auto_start":       self.v_autostart.get(),
        })
        save_config(self.cfg)

    # ── Key ──────────────────────────────────────────────────────────────────
    def _regen_key(self):
        self.v_key.set(generate_api_key(12))

    def _copy_key(self):
        k = self.v_key.get()
        if k:
            self.root.clipboard_clear()
            self.root.clipboard_append(k)

    # ── URL ──────────────────────────────────────────────────────────────────
    def _copy_url(self):
        if self._current_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._current_url)

    def _open_browser(self):
        url = self._current_url or f"http://localhost:{self.v_port.get()}"
        webbrowser.open(url)

    # ── Log ──────────────────────────────────────────────────────────────────
    def _clear_log(self):
        self.log_txt.configure(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.configure(state="disabled")

    # ── Status polling ────────────────────────────────────────────────────────
    def _poll_status(self):
        if self.server.is_running:
            self.lbl_status.configure(text="● Đang chạy", fg=C_OK, bg="#052e16")
        else:
            self.lbl_status.configure(text="● Dừng", fg=C_ERR, bg="#1c1917")
            if self.btn_stop["state"] == "normal":
                self._on_stopped()
        self._poll_id = self.root.after(2000, self._poll_status)

    # ── System tray ───────────────────────────────────────────────────────────
    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Hiện cửa sổ", self._show_win, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Khởi động server", lambda *_: self.root.after(0, self.start_server)),
            pystray.MenuItem("Dừng server",       lambda *_: self.root.after(0, self.stop_server)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Thoát",             self._quit),
        )
        self._tray = pystray.Icon(
            "QR API Server", _make_tray_img(False), "QR API Server", menu=menu
        )
        self._tray_thread = threading.Thread(target=self._tray.run, daemon=True)
        self._tray_thread.start()

    def _show_win(self, *_):
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ── Window management ─────────────────────────────────────────────────────
    def _on_close(self):
        if self.v_tray.get() and TRAY_AVAILABLE:
            self.root.withdraw()
        else:
            self._quit()

    def _quit(self, *_):
        if self.server.is_running:
            self.server.stop()
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        if self._poll_id:
            try:
                self.root.after_cancel(self._poll_id)
            except Exception:
                pass
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QRServerApp()
    app.run()
