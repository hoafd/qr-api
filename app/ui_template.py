HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR Scanner & Generator</title>
    <style>
        :root { --primary: #3b82f6; --bg: #f8fafc; --text: #0f172a; --card: #ffffff; }
        body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { max-width: 600px; width: 100%; background: var(--card); border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 20px; }
        h1 { text-align: center; font-size: 1.5rem; margin-top: 0; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { flex: 1; padding: 10px; text-align: center; background: #e2e8f0; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .tab.active { background: var(--primary); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        video { width: 100%; border-radius: 8px; background: #000; display: none; }
        .btn { display: block; width: 100%; padding: 12px; background: var(--primary); color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 1rem; margin-top: 10px; cursor: pointer; }
        .btn:disabled { opacity: 0.5; }
        .btn-alt { background: #10b981; }
        .btn-stop { background: #ef4444; display: none; }
        #result-box { margin-top: 20px; padding: 15px; background: #f1f5f9; border-radius: 8px; word-break: break-all; font-family: monospace; min-height: 50px; }
        input[type="text"], input[type="file"] { width: 100%; padding: 10px; margin-top: 10px; border-radius: 8px; border: 1px solid #cbd5e1; box-sizing: border-box; }
        img#qr-preview { max-width: 100%; margin-top: 10px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>QR Scanner & Generator</h1>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('scan')">Scan QR</div>
            <div class="tab" onclick="switchTab('generate')">Generate QR</div>
        </div>

        <div id="scan-tab" class="tab-content active">
            <video id="video" autoplay playsinline></video>
            <canvas id="canvas" style="display:none;"></canvas>
            
            <button class="btn" id="btn-camera" onclick="startCamera()">📷 Open Camera</button>
            <button class="btn btn-stop" id="btn-stop-camera" onclick="stopCamera()">🛑 Stop Camera</button>
            
            <div style="text-align: center; margin: 15px 0;">- OR -</div>
            
            <input type="file" id="file-input" accept="image/*" onchange="uploadImage()">
            
            <div id="result-box">Result will appear here...</div>
        </div>

        <div id="generate-tab" class="tab-content">
            <input type="text" id="qr-text" placeholder="Enter text or URL...">
            <button class="btn btn-alt" onclick="generateQR()">Generate QR Code</button>
            <img id="qr-preview" src="">
        </div>
    </div>

    <script>
        let stream = null;
        let scanInterval = null;
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const resultBox = document.getElementById('result-box');

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tab + '-tab').classList.add('active');
            if(tab !== 'scan') stopCamera();
        }

        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                video.srcObject = stream;
                video.style.display = 'block';
                document.getElementById('btn-camera').style.display = 'none';
                document.getElementById('btn-stop-camera').style.display = 'block';
                
                // Start capturing frames
                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    scanInterval = setInterval(captureFrame, 1000); // scan every 1s
                };
            } catch (err) {
                alert("Cannot access camera: " + err.message);
            }
        }

        function stopCamera() {
            if(stream) stream.getTracks().forEach(track => track.stop());
            if(scanInterval) clearInterval(scanInterval);
            video.style.display = 'none';
            document.getElementById('btn-camera').style.display = 'block';
            document.getElementById('btn-stop-camera').style.display = 'none';
        }

        function captureFrame() {
            if(video.readyState === video.HAVE_ENOUGH_DATA) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                canvas.toBlob(blob => {
                    if(blob) sendToAPI(blob);
                }, 'image/jpeg', 0.8);
            }
        }

        async function uploadImage() {
            const file = document.getElementById('file-input').files[0];
            if(file) {
                stopCamera();
                resultBox.innerText = "Scanning...";
                sendToAPI(file);
            }
        }

        async function sendToAPI(fileOrBlob) {
            const formData = new FormData();
            formData.append('file', fileOrBlob, 'image.jpg');
            
            try {
                const res = await fetch('/scan', { method: 'POST', body: formData });
                const text = await res.text();
                if(res.ok) {
                    resultBox.innerText = text;
                    resultBox.style.color = '#10b981';
                    if(scanInterval) stopCamera(); // Stop camera on success
                } else {
                    if(!scanInterval) { // only show error if manually uploaded
                        resultBox.innerText = text;
                        resultBox.style.color = '#ef4444';
                    }
                }
            } catch(e) {
                console.error(e);
            }
        }

        function generateQR() {
            const text = document.getElementById('qr-text').value;
            if(!text) return alert("Please enter text");
            const img = document.getElementById('qr-preview');
            img.style.display = 'block';
            img.src = '/generate?content=' + encodeURIComponent(text);
        }
    </script>
</body>
</html>
"""
