from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from .engine import QREngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QRServer")

tags_metadata = [
    {
        "name": "1. 🔍 Đọc mã (Scan QR)",
        "description": "👉 Tải một bức ảnh lên để máy tính đọc ra nội dung. <br><br>👉 *Upload an image so the machine can read out the content.*",
    },
    {
        "name": "2. 🪄 Tạo mã (Generate QR)",
        "description": "👉 Nhập đường link hoặc văn bản để vẽ nên một hình ảnh mã QR. <br><br>👉 *Enter a url or text content to generate a QR image.*",
    },
]

openapi_description = """
### 🇻🇳 Tiếng Việt
Chào mừng đến với hệ thống **Đọc và Tạo mã QR** siêu tốc.
Giao diện này giúp bạn dễ dàng trải nghiệm các tính năng ngay trên trình duyệt:
1. Nhấn vào thanh **Màu Xanh Dương (POST)** hoặc **Màu Xanh Lá (GET)** bên dưới để mở rộng cấu hình.
2. Tiếp tục nhấn nút **Try it out** ở góc phải màn hình.
3. Nhập dữ liệu hoặc tải ảnh lên, sau đó nhấn **Execute** để xem kết quả!

---

### 🇬🇧 English
Welcome to the lightning-fast **QR Code Scanner & Generator** system.
This interface allows you to easily test the features directly in your browser:
1. Click on the **Blue (POST)** or **Green (GET)** endpoint bars below to expand.
2. Click the **Try it out** button on the right side.
3. Input your data or upload an image, then click **Execute** to view the results!
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = QREngine("/app/app/models")
    logger.info("QR Server initialized.")
    yield

app = FastAPI(
    title="Hệ thống QR Code API 🚀",
    description=openapi_description,
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # SECURITY PATCH: Không cho phép gửi Cookie/Token chéo domain
    allow_methods=["GET", "POST"], # SECURITY PATCH: Giới hạn chỉ nhận GET/POST
    allow_headers=["*"],
)

engine = None

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Máy Chủ QR Code</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        /* Modern Glassmorphism UI */
        :root { --primary: #6366f1; --secondary: #a855f7; --bg: #0f172a; --surface: rgba(30, 41, 59, 0.7); --text: #f8fafc; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: radial-gradient(circle at top left, #1e1b4b, var(--bg)); color: var(--text); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 2rem; }
        .container { max-width: 800px; width: 100%; background: var(--surface); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 3rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        h1 { font-size: 2.5rem; font-weight: 800; text-align: center; margin-bottom: 0.5rem; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 2rem; }
        
        /* Tabs */
        .tabs { display: flex; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem; }
        .tab-btn { flex: 1; padding: 1rem; background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: var(--text); font-weight: 600; cursor: pointer; transition: 0.3s; font-size: 1.1rem; }
        .tab-btn:hover { background: rgba(255,255,255,0.05); }
        .tab-btn.active { background: linear-gradient(135deg, var(--primary), var(--secondary)); border-color: transparent; }
        
        .tab-content { display: none; animation: fadeIn 0.4s; }
        .tab-content.active { display: block; }
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Forms */
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; margin-bottom: 0.5rem; color: #cbd5e1; font-weight: 600; }
        input[type="text"], input[type="number"] { width: 100%; padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.2); color: white; font-family: inherit; font-size: 1rem; }
        input[type="text"]:focus { outline: none; border-color: var(--primary); }
        
        input[type="file"] { display: none; }
        .file-drop { border: 2px dashed rgba(255,255,255,0.2); padding: 3rem; text-align: center; border-radius: 12px; cursor: pointer; transition: 0.3s; background: rgba(0,0,0,0.2); }
        .file-drop:hover { border-color: var(--primary); background: rgba(99,102,241,0.1); }
        
        .btn { width: 100%; padding: 1.2rem; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; border-radius: 12px; font-weight: 800; font-size: 1.2rem; cursor: pointer; transition: 0.3s; box-shadow: 0 4px 15px rgba(16,185,129,0.3); margin-top: 1rem;}
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(16,185,129,0.4); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Results */
        .result-box { margin-top: 2rem; padding: 1.5rem; border-radius: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); display: none; text-align: center; }
        .result-text { font-family: monospace; color: #34d399; font-size: 1.1rem; word-break: break-all; margin-top: 1rem; padding: 1rem; background: #020617; border-radius: 8px; }
        .qr-preview { max-width: 250px; border-radius: 8px; display: inline-block; margin-top: 1rem;}
        #img-preview { max-width: 200px; max-height: 200px; display: none; margin: 1rem auto; border-radius: 8px; border: 2px solid var(--primary); }
    </style>
</head>
<body>
    <div class="container">
        <h1>Máy Chủ QR Code 🚀</h1>
        <p class="subtitle">Thao tác trực tiếp với ảnh nén & dữ liệu siêu tốc ngay tại đây (Offline 100%)</p>

        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('scan', event)">🔍 Đọc mã QR</button>
            <button class="tab-btn" onclick="switchTab('generate', event)">🪄 Tạo mã QR</button>
        </div>

        <!-- Tab quét mã -->
        <div id="tab-scan" class="tab-content active">
            <div class="form-group">
                <label>Tải một tấm ảnh lên đây để máy tính bóc tách dữ liệu:</label>
                <div class="file-drop" onclick="document.getElementById('file-input').click()">
                    <span id="file-name" style="font-size:1.1rem; color:#818cf8">+ NHẤN VÀO ĐÂY ĐỂ CHỌN ẢNH TỪ MÁY (.png, .jpg)</span>
                    <input type="file" id="file-input" accept="image/*" onchange="previewFile()">
                </div>
                <img id="img-preview" src="" alt="Preview">
            </div>
            <div style="display: flex; gap: 1rem;">
                <button class="btn" id="scan-btn" onclick="scanQR()" style="flex: 2;">ĐỌC MÃ NGAY</button>
                <button class="btn" onclick="resetData()" style="flex: 1; background: rgba(255,255,255,0.1); box-shadow: none;">LÀM MỚI (RESET)</button>
            </div>
            
            <div id="scan-result" class="result-box">
                <h3 style="color: #cbd5e1">Kết quả giải mã:</h3>
                <div id="scan-text" class="result-text">Hệ thống đang quét...</div>
            </div>
        </div>

        <!-- Tab tạo mã -->
        <div id="tab-generate" class="tab-content">
            <div class="form-group">
                <label>Nội dung cần giấu (Văn bản, link website, số điện thoại...):</label>
                <input type="text" id="qr-content" placeholder="VD: https://google.com hoặc Xin chào thế giới">
            </div>
            <div style="display: flex; gap: 1rem">
                <div class="form-group" style="flex: 1">
                    <label>Kích thước (px):</label>
                    <input type="number" id="qr-size" value="10" min="1" max="40">
                </div>
                <div class="form-group" style="flex: 1">
                    <label>Độ dày viền trắng:</label>
                    <input type="number" id="qr-border" value="4" min="0" max="10">
                </div>
            </div>
            <div style="display: flex; gap: 1rem;">
                <button class="btn" onclick="generateQR()" style="flex: 2; background: linear-gradient(135deg, #3b82f6, #2563eb); box-shadow: 0 4px 15px rgba(59,130,246,0.3);">TẠO ẢNH MÃ QR</button>
                <button class="btn" onclick="resetData()" style="flex: 1; background: rgba(255,255,255,0.1); box-shadow: none;">LÀM MỚI (RESET)</button>
            </div>

            <div id="gen-result" class="result-box">
                <h3 style="color: #cbd5e1">Mã QR của bạn đã sẵn sàng:</h3>
                <img id="gen-img" class="qr-preview" src="">
                <button class="btn" onclick="downloadQR()" style="background: rgba(255,255,255,0.1); box-shadow: none; margin-top: 1.5rem; padding: 0.8rem 1.5rem; display: block; margin-left: auto; margin-right: auto; width: 60%; border: 1px solid rgba(255,255,255,0.2); transition: all 0.3s;">⬇️ TẢI ẢNH XUỐNG TỰ ĐỘNG</button>
            </div>
        </div>

        <div style="margin-top: 4rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1);">
            <h3 style="color: #cbd5e1; margin-bottom: 1rem;">💻 Hướng dẫn điền Link giải mã (Dành cho Lập trình viên)</h3>
            
            <div style="background: rgba(0,0,0,0.3); padding: 1.2rem; border-radius: 12px; margin-bottom: 1rem; border: 1px solid rgba(255,255,255,0.05);">
                <p style="margin-bottom: 0.5rem; color: #e2e8f0;"><strong>👉 Link giải/Đọc mã QR (POST)</strong> - <i>Gửi <code style="color: #fbbf24; background: rgba(0,0,0,0.5); padding: 2px 6px; border-radius: 4px;">Form-data</code> chứa thuộc tính <code style="color: #fbbf24; background: rgba(0,0,0,0.5); padding: 2px 6px; border-radius: 4px;">file</code></i></p>
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <code id="scan-api-link" style="color: #34d399; font-family: monospace; background: #020617; padding: 0.8rem 1rem; border-radius: 8px; flex: 1; overflow-x: auto; white-space: nowrap; border: 1px solid rgba(52,211,153,0.3);"></code>
                    <button onclick="copyAPI(this, 'scan-api-link')" style="background: rgba(255,255,255,0.1); color: white; border: none; padding: 0.8rem 1.2rem; border-radius: 8px; cursor: pointer; white-space: nowrap; font-weight: 600; border: 1px solid rgba(255,255,255,0.2);">COPY LINK /SCAN</button>
                </div>
            </div>

            <div style="background: rgba(0,0,0,0.3); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                <p style="margin-bottom: 0.5rem; color: #e2e8f0;"><strong>👉 Link Tạo mã QR (GET)</strong> - <i>Trỏ thẳng trình duyệt và truyền biến <code style="color: #fbbf24; background: rgba(0,0,0,0.5); padding: 2px 6px; border-radius: 4px;">content</code></i></p>
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <code id="gen-api-link" style="color: #38bdf8; font-family: monospace; background: #020617; padding: 0.8rem 1rem; border-radius: 8px; flex: 1; overflow-x: auto; white-space: nowrap; border: 1px solid rgba(56,189,248,0.3);"></code>
                    <button onclick="copyAPI(this, 'gen-api-link')" style="background: rgba(255,255,255,0.1); color: white; border: none; padding: 0.8rem 1.2rem; border-radius: 8px; cursor: pointer; white-space: nowrap; font-weight: 600; border: 1px solid rgba(255,255,255,0.2);">COPY LINK /GENERATE</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function downloadQR() {
            const img = document.getElementById('gen-img');
            if (!img.src || img.src.endsWith(window.location.pathname)) return;
            const a = document.createElement('a');
            a.href = img.src;
            a.download = `QR_Code_${new Date().getTime()}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        document.addEventListener('DOMContentLoaded', () => {
            const baseUrl = window.location.origin;
            document.getElementById('scan-api-link').innerText = baseUrl + '/scan';
            document.getElementById('gen-api-link').innerText = baseUrl + '/generate?content=Nội_dung_cần_tạo';
        });

        function copyAPI(btn, elementId) {
            const url = document.getElementById(elementId).innerText;
            const textArea = document.createElement("textarea");
            textArea.value = url;
            textArea.style.position = "fixed";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try { document.execCommand('copy'); } catch (err) {}
            document.body.removeChild(textArea);
            
            const originalText = btn.innerText;
            btn.innerText = 'ĐÃ COPY !';
            btn.style.background = '#10b981';
            btn.style.borderColor = '#10b981';
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.background = 'rgba(255,255,255,0.1)';
                btn.style.borderColor = 'rgba(255,255,255,0.2)';
            }, 2000);
        }

        function resetData() {
            // Reset tab Quét
            document.getElementById('file-input').value = "";
            document.getElementById('file-name').innerHTML = '<span style="font-size:1.1rem; color:#818cf8">+ NHẤN VÀO ĐÂY ĐỂ CHỌN ẢNH TỪ MÁY (.png, .jpg)</span>';
            document.getElementById('img-preview').src = "";
            document.getElementById('img-preview').style.display = "none";
            document.getElementById('scan-result').style.display = "none";
            document.getElementById('scan-text').innerText = "Hệ thống đang quét...";

            // Reset tab Tạo
            document.getElementById('qr-content').value = "";
            document.getElementById('qr-size').value = "10";
            document.getElementById('qr-border').value = "4";
            document.getElementById('gen-result').style.display = "none";
            document.getElementById('gen-img').src = "";
        }
        function switchTab(tabId, event) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
        }

        function previewFile() {
            const file = document.getElementById('file-input').files[0];
            if (file) {
                document.getElementById('file-name').innerText = file.name;
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('img-preview').src = e.target.result;
                    document.getElementById('img-preview').style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        }

        async function scanQR() {
            const file = document.getElementById('file-input').files[0];
            if (!file) { alert("Thiếu dữ liệu: Vui lòng tải bức ảnh lên trước!"); return; }
            
            const btn = document.getElementById('scan-btn');
            btn.disabled = true; btn.innerText = "Đang phân tích...";
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const res = await fetch('/scan', { method: 'POST', body: formData });
                const text = await res.text();
                document.getElementById('scan-result').style.display = 'block';
                const rsBox = document.getElementById('scan-text');
                rsBox.innerText = text;
                
                if (text.startsWith("ERROR:")) {
                    rsBox.style.color = "#ef4444";
                } else {
                    rsBox.style.color = "#34d399";
                }
            } catch(e) {
                alert("Có lỗi kết nối đến Server!");
            } finally {
                btn.disabled = false; btn.innerText = "ĐỌC MÃ NGAY";
            }
        }

        function generateQR() {
            const content = document.getElementById('qr-content').value;
            if(!content) { alert("Thiếu dữ liệu: Vui lòng nhập nội dung!"); return; }
            const size = document.getElementById('qr-size').value || 10;
            const border = document.getElementById('qr-border').value || 4;
            
            const url = `/generate?content=${encodeURIComponent(content)}&size=${size}&border=${border}`;
            document.getElementById('gen-result').style.display = 'block';
            
            const img = document.getElementById('gen-img');
            img.style.opacity = '0.5';
            img.onload = () => img.style.opacity = '1';
            img.src = url;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_CONTENT

# [QUAN TRỌNG]: Thêm response_class=PlainTextResponse
@app.post("/scan", 
    tags=["1. 🔍 Đọc mã (Scan QR)"], 
    response_class=PlainTextResponse,
    summary="Quét mã từ hình ảnh | Scan code from image",
    description="**🇻🇳 Hướng dẫn:** Bấm nút hộp thoại góc trên, nhấp `Chose File` chọn một tệp hình ảnh (.png, .jpg), sau đó bấm nút màu xanh khổng lồ `Execute`.\n\n**🇬🇧 Info:** Click `Choose File` to select an image, then explicitly click `Execute`."
)
async def scan(file: UploadFile = File(..., description="Tệp hình ảnh chứa mã QR / Image file")):
    # SECURITY PATCH: Ngăn chặn DOS bằng file rác khổng lồ (Giới hạn 10MB)
    MAX_SIZE = 10 * 1024 * 1024
    if file.size and file.size > MAX_SIZE:
        return "ERROR: Kích thước ảnh quá lớn. Vui lòng tải ảnh dưới 10MB."
    
    content = await file.read()
    if len(content) > MAX_SIZE:
        return "ERROR: Kích thước ảnh quá lớn. Vui lòng tải ảnh dưới 10MB."

    if engine:
        result = await engine.decode(content)
        # Nếu thành công, CHỈ trả về đúng nội dung đã giải mã
        if result.get("status") == "success":
            return result.get("data")
        # Nếu thất bại, trả về chuỗi báo lỗi để hệ thống ngoài nhận biết
        else:
            return "ERROR: " + result.get("message", "No QR found")
    return "ERROR: Engine not initialized"

@app.get("/generate", 
    tags=["2. 🪄 Tạo mã (Generate QR)"], 
    responses={200: {"content": {"image/png": {}}}},
    summary="Tạo hình ảnh mã QR | Generate QR image",
    description="**🇻🇳 Hướng dẫn:** Bấm vào đây để mở ra thông tin, điền đường chữ bị ẩn thuật hoặc URL vào ô `content` bên dưới. Sau đó bấm `Execute` để lấy ảnh.\n\n**🇬🇧 Info:** Fill text or URL into the `content` field. Then click `Execute` to get image."
)
async def generate_qr_code(
    # SECURITY PATCH: Giới hạn độ dài content tránh bị vắt kiệt CPU
    content: str = Query(..., max_length=2048, description="Dữ liệu cần mã hoá (Vd: https://google.com) / Data to encode"),
    # SECURITY PATCH: Giới hạn size/border tránh tạo ma trận ảnh vượt RAM (OOM)
    size: int = Query(10, ge=1, le=40, description="Kích thước điểm ảnh (Mặc định: 10) / Box size"),
    border: int = Query(4, ge=0, le=10, description="Độ dày viền trắng (Mặc định: 4) / White border")
):
    if engine:
        img_buffer = engine.generate_qr(content, box_size=size, border=border)
        return StreamingResponse(img_buffer, media_type="image/png")
    return "ERROR: Engine not initialized"
