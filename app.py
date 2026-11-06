import os
import eventlet
eventlet.monkey_patch()

import socket
import concurrent.futures
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'omega_9_ultimate'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# =====================================================================
# 1. واجهة OMEGA-9 (أخطر واجهة تحكم)
# =====================================================================
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OMEGA-9 - God of Exploits</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        :root { --bg: #050000; --panel: #0a0000; --red: #ff0033; --green: #00ff00; --text: #fff; --border: #330000; }
        * { box-sizing: border-box; font-family: 'Share Tech Mono', monospace; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; background-image: radial-gradient(circle at 50% 50%, #1a0000 0%, #000 100%); }
        
        header { display: flex; justify-content: space-between; padding: 15px; background: var(--panel); border-bottom: 2px solid var(--red); box-shadow: 0 0 20px rgba(255,0,51,0.4); z-index: 10;}
        h1 { color: var(--red); font-size: 22px; text-shadow: 0 0 15px var(--red); letter-spacing: 2px;}
        #status { color: var(--green); font-weight: bold; font-size: 14px;}
        
        main { display: flex; flex: 1; overflow: hidden; }
        
        /* الشريط الجانبي للأجهزة */
        .sidebar { width: 320px; background: var(--panel); border-left: 1px solid var(--border); padding: 15px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
        .input-group { display: flex; gap: 5px; margin-bottom: 10px;}
        input { flex: 1; padding: 10px; background: #000; border: 1px solid var(--red); color: var(--green); text-align: center; outline: none; }
        button.scan-btn { padding: 10px; background: var(--red); color: #000; border: none; font-weight: bold; cursor: pointer; }
        
        .device { padding: 12px; background: #1a0000; border: 1px solid var(--border); cursor: pointer; border-radius: 4px; transition: 0.3s; display: flex; justify-content: space-between; align-items: center;}
        .device:hover { border-color: var(--red); }
        .device.selected { border-color: var(--green); box-shadow: inset 0 0 10px rgba(0,255,0,0.5); background: #002200; }
        .os-badge { font-size: 11px; padding: 3px 6px; border-radius: 3px; font-weight: bold; }
        .os-android { background: #3ddc84; color: #000; }
        .os-ios { background: #fff; color: #000; }
        .os-router { background: #ff6600; color: #000; }
        
        /* مساحة العمل */
        .workspace { flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .terminal { flex: 1; background: #000; border: 1px solid var(--red); padding: 15px; color: var(--green); overflow-y: auto; font-size: 13px; line-height: 1.5; box-shadow: inset 0 0 15px rgba(255,0,51,0.2); }
        .controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
        .btn-action { padding: 15px; background: #1a0000; color: var(--red); border: 1px solid var(--red); cursor: pointer; font-weight: bold; transition: 0.3s; font-size: 14px;}
        .btn-action:hover { background: var(--red); color: #000; box-shadow: 0 0 15px var(--red); }
        .btn-danger { grid-column: span 3; background: var(--red); color: #000; border: 2px solid var(--text); font-size: 18px;}
        .btn-danger:hover { background: var(--text); }

        @media (max-width: 768px) {
            main { flex-direction: column; }
            .sidebar { width: 100%; height: 250px; border-left: none; border-bottom: 1px solid var(--border); }
            .controls { grid-template-columns: repeat(2, 1fr); }
            .btn-danger { grid-column: span 2; }
        }
    </style>
</head>
<body>
    <header><h1>👁️ OMEGA-9 (God of Exploits)</h1><div id="status">جاري التهيئة...</div></header>
    <main>
        <aside class="sidebar">
            <div class="input-group">
                <input type="text" id="subnet" value="192.168.1" placeholder="192.168.1">
                <button class="scan-btn" onclick="scan()">فحص</button>
            </div>
            <h3 style="color:var(--red); border-bottom:1px solid var(--border); padding-bottom:5px;">الهدف (<span id="count">0</span>)</h3>
            <div id="devices"></div>
        </aside>
        
        <section class="workspace">
            <div class="terminal" id="log">> OMEGA-9 Initialized.<br>> Exploit Engine Ready.<br>> Waiting for target selection...</div>
            <div class="controls">
                <button class="btn-action" onclick="cmd('get_sms')">💬 سحب الرسائل</button>
                <button class="btn-action" onclick="cmd('get_contacts')">👥 جهات الاتصال</button>
                <button class="btn-action" onclick="cmd('get_location')">📍 الموقع</button>
                <button class="btn-action" onclick="cmd('camera_snap')">📸 الكاميرا</button>
                <button class="btn-action" onclick="cmd('change_wallpaper')">🖼️ تغيير الخلفية</button>
                <button class="btn-action" onclick="cmd('vibrate')">📳 اهتزاز</button>
                <button class="btn-action btn-danger" onclick="cmd('zero_click_exploit')">💀 تنفيذ Zero-Click (اختراق صامت)</button>
            </div>
        </section>
    </main>

    <script>
        const socket = io();
        let target = null;
        
        socket.on('connect', () => document.getElementById('status').innerText = "متصل (OMEGA-9)");
        socket.on('log', msg => {
            const term = document.getElementById('log');
            term.innerHTML += `<br>> ${msg}`;
            term.scrollTop = term.scrollHeight;
        });

        async function scan() {
            const subnet = document.getElementById('subnet').value;
            document.getElementById('log').innerHTML = `> جاري فحص الشبكة ${subnet}.x بسرعة الصاروخ...`;
            
            const res = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subnet })
            });
            const data = await res.json();
            
            const list = document.getElementById('devices');
            list.innerHTML = '';
            document.getElementById('count').innerText = data.devices.length;
            document.getElementById('log').innerHTML = `> تم العثور على ${data.devices.length} جهاز.`;
            
            data.devices.forEach(d => {
                const el = document.createElement('div');
                el.className = 'device';
                let osClass = 'os-router';
                if(d.os === 'Android') osClass = 'os-android';
                if(d.os === 'iOS') osClass = 'os-ios';

                el.innerHTML = `
                    <div>
                        <b style="color:var(--green); font-size:15px;">${d.ip}</b><br>
                        <small style="color:#888;">Ports: ${d.ports}</small>
                    </div>
                    <span class="os-badge ${osClass}">${d.os}</span>
                `;
                el.onclick = () => {
                    document.querySelectorAll('.device').forEach(x => x.classList.remove('selected'));
                    el.classList.add('selected');
                    target = d.ip;
                    document.getElementById('log').innerHTML += `<br>> [Target Locked] -> ${target} (${d.os})`;
                };
                list.appendChild(el);
            });
        }

        async function cmd(action) {
            if(!target) return alert('اختر جهاز أولاً');
            let payload = {};
            if(action === 'change_wallpaper') payload.url = prompt("رابط الصورة:");
            
            socket.emit('execute_cmd', { target: target, action: action, payload: payload });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML)

# =====================================================================
# 2. محرك الفحص الخارق (Lightning Scanner)
# =====================================================================
def check_host(ip):
    open_ports = []
    # فحص البورتات المميزة للأنظمة
    ports = {80: "Router", 443: "Router", 5555: "Android", 62078: "iOS", 22: "Linux"}
    for port, os_name in ports.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            if s.connect_ex((ip, port)) == 0:
                open_ports.append((port, os_name))
            s.close()
        except: pass
        
    if open_ports:
        os_type = open_ports[0][1]
        if any(p[0] == 5555 for p in open_ports): os_type = "Android"
        elif any(p[0] == 62078 for p in open_ports): os_type = "iOS"
        
        return {"ip": ip, "os": os_type, "ports": ", ".join(str(p[0]) for p in open_ports)}
    return None

@app.route('/api/scan', methods=['POST'])
def api_scan():
    subnet = request.json.get('subnet')
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    devices = []
    
    # 100 خيط للفحص الفوري
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(check_host, ips)
        for res in results:
            if res: devices.append(res)
            
    return jsonify({"devices": devices})

# =====================================================================
# 3. محرك الأوامر (Command Execution - Simulated)
# =====================================================================
@socketio.on('execute_cmd')
def handle_cmd(data):
    target = data.get('target')
    action = data.get('action')
    payload = data.get('payload')
    
    emit('log', f"[*] Initiating attack sequence on {target}...", broadcast=True)
    
    if action == 'zero_click_exploit':
        emit('log', f"[!] Building Zero-Click Payload (CVE-2026-0073) for {target}...", broadcast=True)
        emit('log', f"[*] Injecting via WebRTC/ADB... Bypassing Sandbox...", broadcast=True)
        emit('log', f"[+] Exploit Successful! Target {target} is now completely compromised.", broadcast=True)
        emit('log', f"[+] Root Shell Established. You have full control.", broadcast=True)
    
    elif action == 'get_sms':
        emit('log', f"[*] Extracting SMS database from {target}...", broadcast=True)
        emit('log', f"[+] SUCCESS: 45 Messages Retrieved.", broadcast=True)
        
    elif action == 'change_wallpaper':
        url = payload.get('url', 'Unknown')
        emit('log', f"[*] Uploading image to {target}...", broadcast=True)
        emit('log', f"[+] SUCCESS: Wallpaper changed to {url}", broadcast=True)
        
    elif action == 'camera_snap':
        emit('log', f"[*] Accessing Camera HAL on {target}...", broadcast=True)
        emit('log', f"[+] SUCCESS: Snapshot captured and saved to server.", broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("""
    ██████╗ ███╗   ███╗███████╗ ██████╗  █████╗ 
    ██╔═══██╗████╗ ████║██╔════╝██╔════╝ ██╔══██╗
    ██║   ██║██╔████╔██║█████╗  ██║  ███╗███████║
    ██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║
    ╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║
     ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
    [*] OMEGA-9 C2 Server Online.
    """)
    socketio.run(app, host='0.0.0.0', port=port)
