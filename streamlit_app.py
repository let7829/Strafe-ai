import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json, uuid, os, sqlite3, hashlib, secrets, string
from datetime import datetime, timedelta
from pathlib import Path
from ddgs import DDGS
from ddgs.exceptions import DDGSException
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import extra_streamlit_components as stx

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\uff0b"

DB_PATH = Path(os.environ.get("STRAFE_DB", "strafe.db"))
COOKIE_KEY = "strafe_code"
CODE_LENGTH = 8
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 600
BAN_DURATION = 900
COOLDOWN = 5

def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    with _db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                messages TEXT NOT NULL,
                created REAL NOT NULL,
                updated REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chats_code ON chats(code_hash, updated DESC);
            CREATE TABLE IF NOT EXISTS settings (
                code_hash TEXT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                model TEXT NOT NULL DEFAULT 'groq'
            );
            CREATE TABLE IF NOT EXISTS codes (
                code_hash TEXT PRIMARY KEY,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ip_bans (
                ip TEXT PRIMARY KEY,
                ban_until REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                attempted_at REAL NOT NULL,
                success INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_ip ON login_attempts(ip, attempted_at);
        """)

db_init()

def gen_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(CODE_LENGTH))

def hash_code(code):
    return hashlib.sha256(code.encode()).hexdigest()

def code_exists(code_hash):
    with _db() as c:
        row = c.execute("SELECT 1 FROM codes WHERE code_hash=?", (code_hash,)).fetchone()
    return row is not None

def create_code(code):
    with _db() as c:
        c.execute("INSERT OR IGNORE INTO codes(code_hash, created) VALUES(?, ?)", (hash_code(code), time.time()))

def get_ip():
    try:
        headers = st.context.headers
        xff = headers.get("X-Forwarded-For")
        if xff:
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if ips:
                return ips[0]
        real_ip = headers.get("X-Real-Ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()
        return None
    except:
        return None

def is_banned(ip):
    if not ip:
        return False
    with _db() as c:
        row = c.execute("SELECT ban_until FROM ip_bans WHERE ip=?", (ip,)).fetchone()
    if row and row["ban_until"] > time.time():
        return True
    if row and row["ban_until"] <= time.time():
        with _db() as c:
            c.execute("DELETE FROM ip_bans WHERE ip=?", (ip,))
    return False

def get_cooldown(ip):
    if not ip:
        return 0
    with _db() as c:
        row = c.execute("SELECT attempted_at FROM login_attempts WHERE ip=? ORDER BY attempted_at DESC LIMIT 1", (ip,)).fetchone()
    if row:
        elapsed = time.time() - row["attempted_at"]
        if elapsed < COOLDOWN:
            return COOLDOWN - elapsed
    return 0

def record_attempt(ip, success):
    if not ip:
        return
    now = time.time()
    with _db() as c:
        c.execute("INSERT INTO login_attempts(ip, attempted_at, success) VALUES(?, ?, ?)", (ip, now, 1 if success else 0))
        cutoff = now - ATTEMPT_WINDOW
        c.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
        if not success:
            failed = c.execute("SELECT COUNT(*) FROM login_attempts WHERE ip=? AND attempted_at > ? AND success=0", (ip, now - ATTEMPT_WINDOW)).fetchone()[0]
            if failed >= MAX_ATTEMPTS:
                c.execute("INSERT OR REPLACE INTO ip_bans(ip, ban_until) VALUES(?, ?)", (ip, now + BAN_DURATION))

cookie_manager = stx.CookieManager()

def get_cookie_code():
    cookies = cookie_manager.get_all()
    if cookies and COOKIE_KEY in cookies:
        return cookies[COOKIE_KEY]
    return None

def set_cookie_code(code):
    cookie_manager.set(COOKIE_KEY, code, expires_at=datetime.now() + timedelta(days=365))

def get_url_code():
    return st.query_params.get("code")

def set_url_code(code):
    st.query_params["code"] = code

def get_active_code():
    url_code = get_url_code()
    if url_code:
        url_code = url_code.upper()
        if len(url_code) == CODE_LENGTH and code_exists(hash_code(url_code)):
            return url_code
    cookie_code = get_cookie_code()
    if cookie_code:
        cookie_code = cookie_code.upper()
        if len(cookie_code) == CODE_LENGTH and code_exists(hash_code(cookie_code)):
            set_url_code(cookie_code)
            return cookie_code
    return None

def login(code):
    set_url_code(code)
    set_cookie_code(code)

def logout():
    del st.query_params["code"]
    cookie_manager.delete(COOKIE_KEY)

def db_get_chats(code_hash):
    with _db() as c:
        rows = c.execute("SELECT id, title, messages, created, updated FROM chats WHERE code_hash=? ORDER BY updated DESC", (code_hash,)).fetchall()
    out = {}
    for r in rows:
        out[r["id"]] = {"id": r["id"], "title": r["title"], "messages": json.loads(r["messages"]), "created": r["created"], "updated": r["updated"]}
    return out

def db_save_chat(code_hash, chat):
    with _db() as c:
        c.execute("""INSERT INTO chats(id, code_hash, title, messages, created, updated) VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, messages=excluded.messages, updated=excluded.updated""",
            (chat["id"], code_hash, chat["title"], json.dumps(chat["messages"]), chat.get("created", time.time()), chat.get("updated", time.time())))

def db_delete_chat(code_hash, chat_id):
    with _db() as c:
        c.execute("DELETE FROM chats WHERE id=? AND code_hash=?", (chat_id, code_hash))

def db_delete_all_chats(code_hash):
    with _db() as c:
        c.execute("DELETE FROM chats WHERE code_hash=?", (code_hash,))

def db_get_settings(code_hash):
    with _db() as c:
        row = c.execute("SELECT language, model FROM settings WHERE code_hash=?", (code_hash,)).fetchone()
    if row is None:
        return {"language": "en", "model": "groq"}
    return {"language": row["language"], "model": row["model"]}

def db_set_settings(code_hash, language=None, model=None):
    cur = db_get_settings(code_hash)
    language = language or cur["language"]
    model = model or cur["model"]
    with _db() as c:
        c.execute("""INSERT INTO settings(code_hash, language, model) VALUES(?, ?, ?)
            ON CONFLICT(code_hash) DO UPDATE SET language=excluded.language, model=excluded.model""", (code_hash, language, model))

INPUT_HTML = '<div id="bar"><div id="atts"></div><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="pb" type="button" class="icon-btn">' + PLUS_GLYPH + '</button><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn active"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button></div><div id="menu"><button id="mb-photo" type="button" class="menu-btn">Photo</button><button id="mb-camera" type="button" class="menu-btn">Camera</button><button id="mb-file" type="button" class="menu-btn">\u2399 File</button></div></div><div id="cam-overlay"><video id="cam-video" autoplay playsinline muted></video><button id="cam-close" type="button">\u2715</button><button id="cam-capture" type="button"></button><canvas id="cam-canvas" style="display:none"></canvas></div>'
INPUT_CSS = """
#bar{position:fixed;bottom:8px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:8px;}
#atts{display:flex;gap:8px;width:100%;max-width:760px;flex-wrap:wrap;padding-left:4px;box-sizing:border-box;}
#atts:empty{display:none;}
.att{position:relative;width:56px;height:56px;border-radius:12px;overflow:hidden;border:1px solid #2a2a2a;flex-shrink:0;}
.att img{width:100%;height:100%;object-fit:cover;display:block;}
.att-x{position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;border:none;background:rgba(0,0,0,0.75);color:#fff;font-size:0.65rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;}
.att-file{position:relative;display:flex;align-items:center;gap:6px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:8px 12px;font-size:0.8rem;color:#bdbdbd;font-family:'Space Grotesk',sans-serif;max-width:200px;}
.att-file-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;}
.att-file-x{width:18px;height:18px;border-radius:50%;border:none;background:rgba(255,255,255,0.1);color:#fff;font-size:0.6rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;}
#tools{display:flex;gap:8px;width:100%;max-width:760px;justify-content:flex-start;padding-left:4px;}
.tool-btn{height:32px;border-radius:16px;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:0.85rem;cursor:pointer;display:flex;align-items:center;gap:6px;padding:0 12px;transition:all 0.2s;font-family:'Space Grotesk',sans-serif;}
.tool-btn .icon{font-size:1rem;line-height:1;}
.tool-btn .label{white-space:nowrap;}
.tool-btn:hover{color:#fff;border-color:#4f8dff;}
.tool-btn.active{background:#4f8dff;color:#fff;border-color:#4f8dff;}
#cb{display:flex;align-items:center;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:28px;padding:10px 14px;gap:8px;width:100%;max-width:760px;margin:0 auto;box-sizing:border-box;box-shadow:0 4px 20px rgba(0,0,0,0.5);}
#ci{flex:1;background:transparent;border:none;outline:none;color:#fff;font-size:1rem;font-family:'Space Grotesk',sans-serif;padding:8px 4px;}
#ci::placeholder{color:#6b7280;}
.icon-btn{width:32px;height:32px;border-radius:50%;border:none;background:transparent;color:#7a7a7a;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:color 0.2s;}
.icon-btn:hover{color:#fff;}
#sb{width:38px;height:38px;border-radius:50%;border:none;background:#4f8dff;color:#fff;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
#sb:hover{background:#2563eb;}
#menu{display:flex;gap:8px;width:100%;max-width:760px;justify-content:flex-start;padding-left:4px;overflow:hidden;max-height:0;opacity:0;transition:max-height 0.25s ease,opacity 0.2s ease;}
#menu.open{max-height:60px;opacity:1;}
.menu-btn{height:40px;border-radius:14px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;padding:0 18px;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;white-space:nowrap;}
.menu-btn:hover{border-color:#4f8dff;color:#fff;}
#cam-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:#000;z-index:10000000;flex-direction:column;align-items:center;justify-content:flex-end;}
#cam-overlay.active{display:flex;}
#cam-video{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;}
#cam-close{position:absolute;top:16px;right:16px;width:40px;height:40px;border-radius:50%;border:none;background:rgba(0,0,0,0.5);color:#fff;font-size:1.4rem;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:10000001;}
#cam-capture{width:72px;height:72px;border-radius:50%;border:4px solid #fff;background:#fff;margin-bottom:40px;z-index:10000001;cursor:pointer;flex-shrink:0;}
#cam-capture:active{transform:scale(0.9);}
"""
INPUT_JS = """
export default function(component){
    const{parentElement,setTriggerValue}=component;
    const input=parentElement.querySelector('#ci');
    const btn=parentElement.querySelector('#sb');
    const plusBtn=parentElement.querySelector('#pb');
    const menu=parentElement.querySelector('#menu');
    const atts=parentElement.querySelector('#atts');
    const photoBtn=parentElement.querySelector('#mb-photo');
    const cameraBtn=parentElement.querySelector('#mb-camera');
    const fileBtn=parentElement.querySelector('#mb-file');
    const btnSearch=parentElement.querySelector('#btn-search');
    const btnThink=parentElement.querySelector('#btn-think');
    const camOverlay=parentElement.querySelector('#cam-overlay');
    const camVideo=parentElement.querySelector('#cam-video');
    const camClose=parentElement.querySelector('#cam-close');
    const camCapture=parentElement.querySelector('#cam-capture');
    const camCanvas=parentElement.querySelector('#cam-canvas');
    if(!input||!btn)return;
    let searchActive=true;
    let thinkActive=false;
    let attachments=[];
    let fileAttachments=[];
    let camStream=null;
    const TEXT_EXTS=['txt','md','csv','json','py','js','ts','jsx','tsx','html','css','xml','yaml','yml','toml','ini','cfg','conf','log','sh','bash','zsh','sql','r','rb','go','rs','c','cpp','h','hpp','java','kt','swift','php','pl','lua','asm','s','makefile','dockerfile','env','gitignore','editorconfig'];
    const imageInput=document.createElement('input');
    imageInput.type='file';
    imageInput.accept='image/*';
    imageInput.style.display='none';
    parentElement.appendChild(imageInput);
    const fileInput=document.createElement('input');
    fileInput.type='file';
    fileInput.accept='.txt,.md,.csv,.json,.py,.js,.ts,.jsx,.tsx,.html,.css,.xml,.yaml,.yml,.toml,.ini,.cfg,.conf,.log,.sh,.bash,.zsh,.sql,.r,.rb,.go,.rs,.c,.cpp,.h,.hpp,.java,.kt,.swift,.php,.pl,.lua,.asm,.s,.makefile,.dockerfile,.env,.gitignore,.editorconfig,text/*';
    fileInput.style.display='none';
    parentElement.appendChild(fileInput);
    function resizeImage(dataUrl,maxSize){
        return new Promise(function(resolve){
            const img=new Image();
            img.onload=function(){
                const c=document.createElement('canvas');
                let w=img.width,h=img.height;
                if(w>maxSize||h>maxSize){
                    if(w>h){h=Math.round(h*maxSize/w);w=maxSize;}
                    else{w=Math.round(w*maxSize/h);h=maxSize;}
                }
                c.width=w;c.height=h;
                c.getContext('2d').drawImage(img,0,0,w,h);
                resolve(c.toDataURL('image/jpeg',0.8));
            };
            img.src=dataUrl;
        });
    }
    function renderAtts(){
        atts.innerHTML='';
        attachments.forEach(function(item,idx){
            const wrap=document.createElement('div');
            wrap.className='att';
            const img=document.createElement('img');
            img.src=item;
            const x=document.createElement('button');
            x.type='button';
            x.className='att-x';
            x.textContent='\\u2715';
            x.onclick=function(ev){ev.stopPropagation();attachments.splice(idx,1);renderAtts();};
            wrap.appendChild(img);
            wrap.appendChild(x);
            atts.appendChild(wrap);
        });
        fileAttachments.forEach(function(item,idx){
            const wrap=document.createElement('div');
            wrap.className='att-file';
            const name=document.createElement('span');
            name.className='att-file-name';
            name.textContent='\\u2399 '+item.name;
            const x=document.createElement('button');
            x.type='button';
            x.className='att-file-x';
            x.textContent='\\u2715';
            x.onclick=function(ev){ev.stopPropagation();fileAttachments.splice(idx,1);renderAtts();};
            wrap.appendChild(name);
            wrap.appendChild(x);
            atts.appendChild(wrap);
        });
    }
    function stopCamera(){
        if(camStream){camStream.getTracks().forEach(function(t){t.stop();});camStream=null;}
        camOverlay.classList.remove('active');
    }
    async function openCamera(){
        try{camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});camVideo.srcObject=camStream;camOverlay.classList.add('active');menu.classList.remove('open');}
        catch(e){setTriggerValue('menu_action','camera_error');}
    }
    async function capturePhoto(){
        if(!camStream)return;
        camCanvas.width=camVideo.videoWidth;
        camCanvas.height=camVideo.videoHeight;
        camCanvas.getContext('2d').drawImage(camVideo,0,0);
        const dataUrl=camCanvas.toDataURL('image/jpeg',0.9);
        stopCamera();
        const resized=await resizeImage(dataUrl,1024);
        attachments.push(resized);
        renderAtts();
    }
    async function send(){
        const val=input.value.trim();
        if(!val&&!attachments.length&&!fileAttachments.length)return;
        const resized=[];
        for(let i=0;i<attachments.length;i++){resized.push(await resizeImage(attachments[i],1024));}
        setTriggerValue('submitted',{text:val,search:searchActive,think:thinkActive,images:resized,files:fileAttachments.slice()});
        input.value='';
        attachments=[];
        fileAttachments=[];
        renderAtts();
    }
    btn.onclick=send;
    input.onkeydown=function(e){if(e.key==='Enter')send();};
    if(plusBtn&&menu){plusBtn.onclick=function(){menu.classList.toggle('open');};}
    if(photoBtn){photoBtn.onclick=function(){menu.classList.remove('open');imageInput.click();};}
    if(cameraBtn){cameraBtn.onclick=openCamera;}
    if(fileBtn){fileBtn.onclick=function(){menu.classList.remove('open');fileInput.click();};}
    if(camClose){camClose.onclick=stopCamera;}
    if(camCapture){camCapture.onclick=capturePhoto;}
    imageInput.onchange=function(){
        const f=imageInput.files[0];
        if(!f)return;
        const reader=new FileReader();
        reader.onload=function(){attachments.push(reader.result);renderAtts();};
        reader.readAsDataURL(f);
        imageInput.value='';
    };
    fileInput.onchange=function(){
        const f=fileInput.files[0];
        if(!f)return;
        const ext=f.name.split('.').pop().toLowerCase();
        if(!TEXT_EXTS.includes(ext)&&!f.type.startsWith('text/')){setTriggerValue('menu_action','unsupported_file');fileInput.value='';return;}
        if(f.size>500000){setTriggerValue('menu_action','file_too_large');fileInput.value='';return;}
        const reader=new FileReader();
        reader.onload=function(){fileAttachments.push({name:f.name,content:reader.result});renderAtts();};
        reader.readAsText(f);
        fileInput.value='';
    };
    btnSearch.onclick=function(){searchActive=!searchActive;this.classList.toggle('active',searchActive);};
    btnThink.onclick=function(){thinkActive=!thinkActive;this.classList.toggle('active',thinkActive);};
    btnSearch.classList.toggle('active',searchActive);
}
"""

chat_input = components.component("strafe_chat_input", html=INPUT_HTML, css=INPUT_CSS, js=INPUT_JS)

UI_CSS = """
#topbar{position:fixed;top:0;left:0;right:0;height:56px;padding:0 14px;display:flex;align-items:center;gap:10px;z-index:999998;background:linear-gradient(to bottom,rgba(10,10,10,0.96),rgba(10,10,10,0));pointer-events:none;font-family:'Space Grotesk',sans-serif;}
#topbar > *{pointer-events:auto;}
.tb-btn{height:36px;min-width:36px;border-radius:18px;border:1px solid #2a2a2a;background:#1a1a1a;color:#bdbdbd;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;padding:0 14px;display:flex;align-items:center;justify-content:center;gap:6px;transition:all 0.2s;box-shadow:0 2px 10px rgba(0,0,0,0.4);}
.tb-btn:hover{color:#fff;border-color:#4f8dff;}
#menu-btn{font-size:1.15rem;padding:0;width:36px;}
#sidebar-backdrop{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.55);z-index:1000000;opacity:0;pointer-events:none;transition:opacity 0.2s;}
#sidebar-backdrop.open{opacity:1;pointer-events:auto;}
#sidebar{position:fixed;top:0;left:0;width:300px;max-width:86vw;height:100vh;background:#101010;border-right:1px solid #2a2a2a;z-index:1000001;display:flex;flex-direction:column;transform:translateX(-100%);transition:transform 0.25s ease;font-family:'Space Grotesk',sans-serif;}
#sidebar.open{transform:translateX(0);}
.sidebar-header{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid #1f1f1f;}
.sidebar-title{font-size:0.78rem;color:#8a8a8a;font-weight:700;letter-spacing:2px;}
.icon-x{width:30px;height:30px;border-radius:50%;border:none;background:transparent;color:#8a8a8a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;transition:all 0.15s;}
.icon-x:hover{color:#fff;background:#222;}
#new-chat-btn{margin:12px 14px;height:42px;border-radius:10px;border:1px dashed #3a3a3a;background:transparent;color:#bdbdbd;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;display:flex;align-items:center;justify-content:center;gap:6px;}
#new-chat-btn:hover{background:#1a1a1a;color:#fff;border-color:#4f8dff;}
#chat-list{flex:1;overflow-y:auto;padding:0 8px 16px 8px;}
#chat-list::-webkit-scrollbar{width:6px;}
#chat-list::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:3px;}
.chat-item{display:flex;align-items:center;gap:6px;padding:10px 12px;border-radius:8px;cursor:pointer;color:#bdbdbd;font-size:0.88rem;transition:background 0.15s;margin-bottom:2px;}
.chat-item:hover{background:#1a1a1a;color:#fff;}
.chat-item.active{background:#1a2030;color:#fff;border-left:2px solid #4f8dff;padding-left:10px;}
.chat-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.chat-del{width:22px;height:22px;border-radius:50%;border:none;background:transparent;color:#5a5a5a;font-size:0.72rem;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;transition:all 0.15s;}
.chat-del:hover{color:#ff5555;background:#2a1a1a;}
.empty-chats{padding:24px 16px;color:#4a4a4a;font-size:0.84rem;text-align:center;line-height:1.5;}
.sidebar-footer{padding:12px 14px;border-top:1px solid #1f1f1f;flex-shrink:0;}
#settings-btn{width:100%;height:42px;border-radius:10px;border:1px solid #2a2a2a;background:#181818;color:#bdbdbd;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;display:flex;align-items:center;justify-content:center;gap:8px;transition:all 0.2s;}
#settings-btn:hover{color:#fff;border-color:#4f8dff;background:#222;}
#settings-btn .gear{font-size:1.05rem;line-height:1;}
#settings-backdrop{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.55);z-index:1000002;opacity:0;pointer-events:none;transition:opacity 0.2s;}
#settings-backdrop.open{opacity:1;pointer-events:auto;}
#settings-panel{position:fixed;top:0;right:0;width:400px;max-width:92vw;height:100vh;background:#101010;border-left:1px solid #2a2a2a;z-index:1000003;display:flex;flex-direction:column;transform:translateX(100%);transition:transform 0.25s ease;font-family:'Space Grotesk',sans-serif;}
#settings-panel.open{transform:translateX(0);}
.settings-header{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid #1f1f1f;flex-shrink:0;}
.settings-title{font-size:1.02rem;color:#fff;font-weight:600;}
.tabs{display:flex;gap:2px;padding:10px 12px;overflow-x:auto;border-bottom:1px solid #1a1a1a;flex-shrink:0;}
.tabs::-webkit-scrollbar{height:0;}
.tab{flex-shrink:0;height:32px;padding:0 14px;border-radius:16px;border:none;background:transparent;color:#8a8a8a;font-size:0.82rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;white-space:nowrap;}
.tab:hover{color:#fff;}
.tab.active{background:#4f8dff;color:#fff;}
.tab-content{display:none;padding:16px 18px;overflow-y:auto;flex:1;}
.tab-content.active{display:block;}
.tab-content::-webkit-scrollbar{width:6px;}
.tab-content::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:3px;}
.setting-section{margin-bottom:20px;}
.setting-label{font-size:0.72rem;text-transform:uppercase;letter-spacing:1.5px;color:#6a6a6a;margin-bottom:10px;font-weight:700;}
.setting-btn{width:100%;height:42px;border-radius:10px;border:1px solid #2a2a2a;background:#181818;color:#ececec;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;margin-bottom:8px;text-align:left;padding:0 14px;transition:all 0.2s;display:flex;align-items:center;justify-content:space-between;}
.setting-btn:hover{background:#222;border-color:#4f8dff;}
.setting-btn.danger{color:#ff6b6b;}
.setting-btn.danger:hover{background:#2a1a1a;border-color:#ff5555;}
.radio-item{display:flex;align-items:flex-start;gap:12px;padding:12px 14px;border-radius:10px;border:1px solid #2a2a2a;background:#141414;margin-bottom:8px;cursor:pointer;transition:all 0.2s;}
.radio-item:hover{border-color:#3a3a3a;}
.radio-item.selected{border-color:#4f8dff;background:#161d2b;}
.radio-dot{width:16px;height:16px;border-radius:50%;border:2px solid #4a4a4a;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin-top:2px;}
.radio-item.selected .radio-dot{border-color:#4f8dff;}
.radio-item.selected .radio-dot::after{content:'';width:8px;height:8px;border-radius:50%;background:#4f8dff;}
.radio-text{flex:1;min-width:0;}
.radio-title{font-size:0.9rem;color:#ececec;font-weight:500;}
.radio-title .badge{color:#4f8dff;font-size:0.7rem;font-weight:600;margin-left:6px;}
.radio-desc{font-size:0.76rem;color:#7a7a7a;margin-top:3px;line-height:1.45;}
.about-text{color:#bdbdbd;font-size:0.88rem;line-height:1.65;padding:2px 0 8px 0;}
.code-display{background:#0a0a0a;border:1px solid #2a2a2a;border-radius:10px;padding:14px 18px;font-family:'Space Grotesk',monospace;font-size:1.2rem;letter-spacing:4px;color:#4f8dff;text-align:center;margin-bottom:12px;user-select:all;cursor:pointer;}
.code-display:hover{border-color:#4f8dff;}
.modal{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.72);z-index:1000010;display:none;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;font-family:'Space Grotesk',sans-serif;backdrop-filter:blur(4px);}
.modal.open{display:flex;}
.modal-content{background:#141414;border:1px solid #2a2a2a;border-radius:16px;padding:24px;max-width:400px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,0.85);}
.modal-title{font-size:1.15rem;color:#fff;font-weight:600;margin:0 0 8px 0;}
.modal-text{font-size:0.88rem;color:#8a8a8a;line-height:1.55;margin:0 0 20px 0;}
.modal-btn{width:100%;height:44px;border-radius:10px;border:none;font-size:0.95rem;font-family:'Space Grotesk',sans-serif;cursor:pointer;margin-bottom:8px;transition:all 0.2s;font-weight:500;}
.modal-btn.secondary{background:#1a1a1a;color:#bdbdbd;border:1px solid #2a2a2a;}
.modal-btn.secondary:hover{background:#222;color:#fff;}
.modal-btn.danger{background:#ff5555;color:#fff;}
.modal-btn.danger:hover{background:#e04444;}
"""

UI_JS = """
export default function(component){
    const {parentElement,setTriggerValue}=component;
    const $=(s)=>parentElement.querySelector(s);
    const $$=(s)=>parentElement.querySelectorAll(s);
    const dataEl=$('#strafe-data');
    if(!dataEl)return;
    const DATA=JSON.parse(dataEl.textContent);
    function getLS(k,d){try{return localStorage.getItem(k)||d;}catch(e){return d;}}
    function setLS(k,v){try{localStorage.setItem(k,v);}catch(e){}}
    let savedTab=getLS('strafe_tab','language');
    let ui={sidebarOpen:getLS('strafe_sidebar','0')==='1',settingsOpen:getLS('strafe_settings','0')==='1',tab:savedTab};
    function saveUI(){setLS('strafe_sidebar',ui.sidebarOpen?'1':'0');setLS('strafe_settings',ui.settingsOpen?'1':'0');setLS('strafe_tab',ui.tab);}
    const $sidebar=$('#sidebar');
    const $sidebarBackdrop=$('#sidebar-backdrop');
    const $chatList=$('#chat-list');
    const $settingsPanel=$('#settings-panel');
    const $settingsBackdrop=$('#settings-backdrop');
    const $confirmModal=$('#confirm-modal');
    const $confirmTitle=$('#confirm-title');
    const $confirmText=$('#confirm-text');
    function openSidebar(){ui.sidebarOpen=true;saveUI();applySidebar();}
    function closeSidebar(){ui.sidebarOpen=false;saveUI();applySidebar();}
    function applySidebar(){$sidebar.classList.toggle('open',ui.sidebarOpen);$sidebarBackdrop.classList.toggle('open',ui.sidebarOpen);}
    function openSettings(){ui.settingsOpen=true;saveUI();applySettings();}
    function closeSettings(){ui.settingsOpen=false;saveUI();applySettings();}
    function applySettings(){$settingsPanel.classList.toggle('open',ui.settingsOpen);$settingsBackdrop.classList.toggle('open',ui.settingsOpen);}
    function selectTab(t){
        const valid=['language','models','session','about'];
        if(!valid.includes(t))t='language';
        ui.tab=t;
        saveUI();
        $$('.tab').forEach(el=>el.classList.toggle('active',el.dataset.tab===t));
        $$('.tab-content').forEach(el=>el.classList.toggle('active',el.dataset.tabContent===t));
    }
    $$('.tab').forEach(el=>el.addEventListener('click',()=>selectTab(el.dataset.tab)));
    let confirmCallback=null;
    function showConfirm(title,text,cb){$confirmTitle.textContent=title;$confirmText.textContent=text;confirmCallback=cb;$confirmModal.classList.add('open');}
    function closeConfirm(){$confirmModal.classList.remove('open');confirmCallback=null;}
    $('#confirm-yes').onclick=()=>{if(confirmCallback)confirmCallback();};
    $('#confirm-no').onclick=closeConfirm;
    function renderChats(){
        $chatList.innerHTML='';
        const chats=DATA.chats||[];
        if(chats.length===0){const empty=document.createElement('div');empty.className='empty-chats';empty.textContent='No chats yet';$chatList.appendChild(empty);return;}
        chats.forEach(c=>{
            const item=document.createElement('div');
            item.className='chat-item'+(c.id===DATA.current_chat_id?' active':'');
            const title=document.createElement('span');
            title.className='chat-title';
            title.textContent=c.title||'New chat';
            const del=document.createElement('button');
            del.className='chat-del';
            del.type='button';
            del.textContent='\\u2715';
            del.onclick=(ev)=>{
                ev.stopPropagation();
                showConfirm('Delete chat?','Are you sure you want to delete this chat? This cannot be undone.',()=>{
                    closeConfirm();
                    closeSidebar();
                    setTriggerValue('ui_action',{type:'delete_chat',chat_id:c.id});
                });
            };
            item.appendChild(title);
            item.appendChild(del);
            item.onclick=()=>{
                if(c.id===DATA.current_chat_id){closeSidebar();return;}
                closeSidebar();
                setTriggerValue('ui_action',{type:'open_chat',chat_id:c.id});
            };
            $chatList.appendChild(item);
        });
    }
    const LANGUAGES=[{id:'en',name:'English',desc:'Auto on'},{id:'ru',name:'Russian',desc:''},{id:'uk',name:'Ukrainian',desc:''}];
    function renderLanguages(){
        const $langList=$('#lang-list');
        $langList.innerHTML='';
        LANGUAGES.forEach(lang=>{
            const item=document.createElement('div');
            item.className='radio-item'+(DATA.language===lang.id?' selected':'');
            const dot=document.createElement('div');
            dot.className='radio-dot';
            const text=document.createElement('div');
            text.className='radio-text';
            const title=document.createElement('div');
            title.className='radio-title';
            title.textContent=lang.name;
            if(lang.desc){const badge=document.createElement('span');badge.className='badge';badge.textContent='('+lang.desc+')';title.appendChild(badge);}
            text.appendChild(title);
            item.appendChild(dot);
            item.appendChild(text);
            item.onclick=()=>{
                if(DATA.language!==lang.id){closeSettings();setTriggerValue('ui_action',{type:'set_language',lang:lang.id});}
            };
            $langList.appendChild(item);
        });
    }
    const MODELS=[{id:'groq',name:'Groq',desc:'Groq has strong coding/math skills. Also known for fast responses.',badge:'Auto on'},{id:'celeris',name:'Celeris',desc:'Celeris is considered to be the fastest model, outrun groq. The skills are currently unknown.',badge:''}];
    function renderModels(){
        const $modelList=$('#model-list');
        $modelList.innerHTML='';
        MODELS.forEach(m=>{
            const item=document.createElement('div');
            item.className='radio-item'+(DATA.model===m.id?' selected':'');
            const dot=document.createElement('div');
            dot.className='radio-dot';
            const text=document.createElement('div');
            text.className='radio-text';
            const title=document.createElement('div');
            title.className='radio-title';
            title.textContent=m.name;
            if(m.badge){const badge=document.createElement('span');badge.className='badge';badge.textContent='('+m.badge+')';title.appendChild(badge);}
            const desc=document.createElement('div');
            desc.className='radio-desc';
            desc.textContent=m.desc;
            text.appendChild(title);
            text.appendChild(desc);
            item.appendChild(dot);
            item.appendChild(text);
            item.onclick=()=>{
                if(DATA.model!==m.id){closeSettings();setTriggerValue('ui_action',{type:'set_model',model:m.id});}
            };
            $modelList.appendChild(item);
        });
    }
    $('#menu-btn').onclick=openSidebar;
    $('#sidebar-close').onclick=closeSidebar;
    $sidebarBackdrop.onclick=closeSidebar;
    $('#new-chat-btn').onclick=()=>{closeSidebar();setTriggerValue('ui_action',{type:'new_chat'});};
    $('#settings-btn').onclick=()=>{closeSidebar();openSettings();};
    $('#settings-close').onclick=closeSettings;
    $settingsBackdrop.onclick=closeSettings;
    $('#delete-all-btn').onclick=()=>{
        showConfirm('Delete all chats?','Are you sure you want to delete ALL chats? This cannot be undone.',()=>{
            closeConfirm();
            closeSettings();
            setTriggerValue('ui_action',{type:'delete_all_chats'});
        });
    };
    $('#logout-btn').onclick=()=>{
        showConfirm('Sign out?','You will return to the login page. Your chats are saved.',()=>{
            closeConfirm();
            closeSettings();
            setTriggerValue('ui_action',{type:'logout'});
        });
    };
    const codeEl=$('#current-code');
    if(codeEl){codeEl.onclick=function(){navigator.clipboard.writeText(DATA.code).then(()=>{$( '#code-copied').style.display='block';setTimeout(()=>{$('#code-copied').style.display='none';},1500);});};}
    applySidebar();
    applySettings();
    renderChats();
    renderLanguages();
    renderModels();
    selectTab(ui.tab);
}
"""

def build_ui_html(data_json):
    parts = [
        '<div id="topbar">',
        '  <button id="menu-btn" class="tb-btn" type="button">&#9776;</button>',
        '</div>',
        '<div id="sidebar-backdrop"></div>',
        '<aside id="sidebar">',
        '  <div class="sidebar-header">',
        '    <span class="sidebar-title">YOUR CHATS</span>',
        '    <button id="sidebar-close" class="icon-x" type="button">&#10005;</button>',
        '  </div>',
        '  <button id="new-chat-btn" type="button">&#65291; New chat</button>',
        '  <div id="chat-list"></div>',
        '  <div class="sidebar-footer">',
        '    <button id="settings-btn" type="button"><span class="gear">&#9881;&#xFE0E;</span><span>Settings</span></button>',
        '  </div>',
        '</aside>',
        '<div id="settings-backdrop"></div>',
        '<aside id="settings-panel">',
        '  <div class="settings-header">',
        '    <span class="settings-title">Settings</span>',
        '    <button id="settings-close" class="icon-x" type="button">&#10005;</button>',
        '  </div>',
        '  <div class="tabs">',
        '    <button class="tab active" data-tab="language" type="button">Language</button>',
        '    <button class="tab" data-tab="models" type="button">Models</button>',
        '    <button class="tab" data-tab="session" type="button">Session</button>',
        '    <button class="tab" data-tab="about" type="button">About</button>',
        '  </div>',
        '  <div class="tab-content active" data-tab-content="language">',
        '    <div class="setting-section">',
        '      <div class="setting-label">Language</div>',
        '      <div id="lang-list"></div>',
        '    </div>',
        '  </div>',
        '  <div class="tab-content" data-tab-content="models">',
        '    <div class="setting-section">',
        '      <div class="setting-label">Models</div>',
        '      <div id="model-list"></div>',
        '    </div>',
        '  </div>',
        '  <div class="tab-content" data-tab-content="session">',
        '    <div class="setting-section">',
        '      <div class="setting-label">Your code</div>',
        '      <div class="code-display" id="current-code">' + (st.query_params.get("code", "") if st.query_params.get("code") else "--------") + '</div>',
        '      <div id="code-copied" style="display:none;color:#4f8dff;font-size:0.82rem;text-align:center;margin-bottom:12px;">Copied to clipboard!</div>',
        '      <div class="about-text">Click the code to copy. Share this code to access your chats from another device.</div>',
        '    </div>',
        '    <div class="setting-section">',
        '      <button class="setting-btn danger" id="logout-btn" type="button">Sign out</button>',
        '    </div>',
        '  </div>',
        '  <div class="tab-content" data-tab-content="about">',
        '    <div class="setting-section">',
        '      <div class="setting-label">About</div>',
        '      <div class="about-text">Strafe is a project made for your use, no data can be seen by anyone even by owner.</div>',
        '    </div>',
        '    <div class="setting-section">',
        '      <div class="setting-label">Danger Zone</div>',
        '      <button class="setting-btn danger" id="delete-all-btn" type="button">Delete all chats</button>',
        '    </div>',
        '  </div>',
        '</aside>',
        '<div id="confirm-modal" class="modal">',
        '  <div class="modal-content">',
        '    <h2 class="modal-title" id="confirm-title">Confirm</h2>',
        '    <p class="modal-text" id="confirm-text">Are you sure?</p>',
        '    <button id="confirm-yes" class="modal-btn danger" type="button">Yes</button>',
        '    <button id="confirm-no" class="modal-btn secondary" type="button">Cancel</button>',
        '  </div>',
        '</div>',
        '<script id="strafe-data" type="application/json">' + data_json + '</script>',
    ]
    return "\n".join(parts)

def _code_hash():
    return hash_code(st.query_params.get("code", ""))

def _chat_store():
    ch = _code_hash()
    cache_key = f"chats_{ch}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = db_get_chats(ch)
    return st.session_state[cache_key]

def _create_new_chat_id():
    return "chat_" + uuid.uuid4().hex[:12]

def _create_current_chat():
    store = _chat_store()
    ch = _code_hash()
    to_remove = [cid for cid, c in store.items() if not c.get("messages")]
    for cid in to_remove:
        del store[cid]
        db_delete_chat(ch, cid)
    cid = _create_new_chat_id()
    msgs = []
    chat = {"id": cid, "title": "New chat", "messages": msgs, "created": time.time(), "updated": time.time()}
    store[cid] = chat
    st.session_state.current_chat_id = cid
    st.session_state.messages = msgs
    st.session_state.chat_created = chat["created"]

def _persist_current_chat():
    msgs = st.session_state.get("messages", [])
    if not msgs:
        return
    cid = st.session_state.get("current_chat_id")
    if not cid:
        return
    ch = _code_hash()
    first_user = next((m for m in msgs if m.get("role") == "user"), None)
    title = ((first_user or {}).get("content") or "").strip().replace("\n", " ")[:48] or "New chat"
    chat = {"id": cid, "title": title, "messages": msgs, "created": st.session_state.get("chat_created", time.time()), "updated": time.time()}
    db_save_chat(ch, chat)

def _get_chat_summaries():
    store = _chat_store()
    summaries = []
    for cid, c in store.items():
        msgs = c.get("messages") or []
        if not msgs:
            continue
        first_user = next((m for m in msgs if m.get("role") == "user"), None)
        title = ((first_user or {}).get("content") or "").strip().replace("\n", " ")[:48] or "New chat"
        summaries.append({"id": cid, "title": title, "_updated": c.get("updated", c.get("created", 0))})
    summaries.sort(key=lambda x: x["_updated"], reverse=True)
    for s in summaries:
        del s["_updated"]
    return summaries

def init_ui_state():
    ch = _code_hash()
    s = db_get_settings(ch)
    st.session_state.setdefault("language", s["language"])
    st.session_state.setdefault("model_choice", s["model"])
    store = _chat_store()
    cid = st.session_state.get("current_chat_id")
    if cid is None or cid not in store:
        remaining = [c for c in store.values() if c.get("messages")]
        if remaining:
            remaining.sort(key=lambda c: c.get("updated", c.get("created", 0)), reverse=True)
            st.session_state.current_chat_id = remaining[0]["id"]
            st.session_state.messages = remaining[0]["messages"]
            st.session_state.chat_created = remaining[0].get("created", time.time())
        else:
            _create_current_chat()
    else:
        st.session_state.messages = store[cid]["messages"]
        st.session_state.chat_created = store[cid].get("created", time.time())

def get_action_field(action, name, default=None):
    if action is None:
        return default
    if isinstance(action, dict):
        return action.get(name, default)
    return getattr(action, name, default)

def handle_action(action):
    t = get_action_field(action, "type")
    ch = _code_hash()
    def _reset():
        st.session_state["editing"] = None
        st.session_state["act"] = None
    if t == "new_chat":
        _reset()
        _create_current_chat()
    elif t == "open_chat":
        cid = get_action_field(action, "chat_id")
        store = _chat_store()
        if cid and cid in store:
            _reset()
            st.session_state.current_chat_id = cid
            st.session_state.messages = store[cid]["messages"]
            st.session_state.chat_created = store[cid].get("created", time.time())
    elif t == "delete_chat":
        cid = get_action_field(action, "chat_id")
        store = _chat_store()
        if cid and cid in store:
            _reset()
            del store[cid]
            db_delete_chat(ch, cid)
            if st.session_state.get("current_chat_id") == cid:
                remaining = [c for c in store.values() if c.get("messages")]
                if remaining:
                    remaining.sort(key=lambda c: c.get("updated", c.get("created", 0)), reverse=True)
                    st.session_state.current_chat_id = remaining[0]["id"]
                    st.session_state.messages = remaining[0]["messages"]
                    st.session_state.chat_created = remaining[0].get("created", time.time())
                else:
                    _create_current_chat()
    elif t == "delete_all_chats":
        _reset()
        db_delete_all_chats(ch)
        cache_key = f"chats_{ch}"
        st.session_state[cache_key] = {}
        st.session_state.pop("current_chat_id", None)
        st.session_state.pop("messages", None)
        init_ui_state()
    elif t == "set_language":
        lang = get_action_field(action, "lang")
        if lang:
            st.session_state.language = lang
            db_set_settings(ch, language=lang)
    elif t == "set_model":
        model = get_action_field(action, "model")
        if model:
            st.session_state.model_choice = model
            db_set_settings(ch, model=model)
    elif t == "logout":
        logout()
    st.rerun()

def render_ui():
    chats = _get_chat_summaries()
    current_cid = st.session_state.get("current_chat_id")
    lang = st.session_state.get("language", "en")
    model = st.session_state.get("model_choice", "groq")
    code = st.query_params.get("code", "")
    data = {"chats": chats, "current_chat_id": current_cid, "language": lang, "model": model, "code": code}
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    h = hashlib.md5(data_json.encode()).hexdigest()[:10]
    name = f"strafe_ui_{h}"
    if "ui_factories" not in st.session_state:
        st.session_state.ui_factories = {}
    if name not in st.session_state.ui_factories:
        st.session_state.ui_factories[name] = components.component(name, html=build_ui_html(data_json), css=UI_CSS, js=UI_JS)
        while len(st.session_state.ui_factories) > 10:
            del st.session_state.ui_factories[next(iter(st.session_state.ui_factories))]
    comp = st.session_state.ui_factories[name]
    result = comp(key=f"strafe_ui_k_{h}", on_ui_action_change=lambda: None)
    if result:
        action = getattr(result, "ui_action", None)
        if action:
            handle_action(action)

def get_prompt():
    result = chat_input(key="strafe_inp", on_submitted_change=lambda: None)
    if not result:
        return None
    ma = getattr(result, "menu_action", None)
    if ma:
        st.session_state["menu_action"] = ma
    submitted = getattr(result, "submitted", None)
    if submitted:
        return submitted
    return None

CSS = """
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
section.main,section[data-testid='stMain'],[data-testid='stAppViewContainer'],[data-testid='stMainBlockContainer'],[data-testid='stAppView'],[data-testid='stVerticalBlockBorderWrapper']{overflow-x:hidden !important;max-width:100vw !important;width:100% !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding:64px 1rem 160px 1rem !important;max-width:760px;overflow-x:hidden;}
div[data-testid='stVerticalBlock']{gap:0 !important;max-width:100% !important;}
div[data-testid='stChatMessage']{background:transparent !important;border:none !important;padding:8px 0 0 0 !important;margin:0 !important;overflow:visible !important;}
div[data-testid^='stChatMessageAvatar']{display:none !important;}
div[data-testid='stChatMessage'] div[data-testid='stChatMessageContent']{background:transparent !important;max-width:100%;padding:0;overflow:visible !important;}
div[data-testid='stChatMessage'] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 2px 0;overflow-wrap:anywhere;}
div[data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;width:100% !important;max-width:100% !important;}
div[data-testid='stHorizontalBlock'] > div{min-width:0 !important;max-width:100% !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(1) > div[data-testid='stVerticalBlock']{align-items:flex-start !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(2) > div[data-testid='stVerticalBlock']{align-items:flex-end !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(2) div[data-testid='stPopoverContent']{left:auto !important;right:0 !important;}
.brand{text-align:center;padding:8px 0 2px 0;font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.user-bubble{display:flex;justify-content:flex-end;width:100%;margin:10px 0 0 0;}
.user-bubble-inner{background:#5c5c5c;color:#ffffff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}
.chat-thumb{width:64px;height:64px;object-fit:cover;border-radius:12px;margin:0 8px 6px 0;vertical-align:middle;border:1px solid #2a2a2a;}
.file-badge{display:inline-flex;align-items:center;gap:4px;background:#2a2a2a;border-radius:8px;padding:4px 10px;font-size:0.75rem;color:#bdbdbd;margin:0 8px 6px 0;font-family:'Space Grotesk',sans-serif;}
div[data-testid='stPopover']{margin:0 !important;max-width:100% !important;}
div[data-testid='stPopover'] button{height:20px !important;min-height:0 !important;padding:0 4px !important;font-size:1rem !important;line-height:1 !important;color:#7a7a7a !important;background:transparent !important;border:none !important;box-shadow:none !important;}
div[data-testid='stPopover'] button:hover{color:#fff !important;}
div[data-testid='stPopover'] button p{margin:0 !important;}
.info-line{color:#8a8a8a !important;font-size:0.82rem !important;line-height:1.5 !important;font-family:'Space Grotesk',sans-serif !important;padding:2px 0 6px 0;}
.info-line span{color:#bdbdbd;}
.close-row button{background:transparent !important;border:none !important;color:#7a7a7a !important;font-size:0.85rem !important;padding:2px 8px !important;box-shadow:none !important;}
.close-row button:hover{color:#fff !important;}
div[data-testid='stExpander'] details{background:#1a1a1a !important;border:1px solid #2a2a2a !important;border-radius:12px !important;padding:8px 12px !important;margin:8px 0 !important;}
div[data-testid='stExpander'] summary{color:#8a8a8a !important;font-size:0.85rem !important;cursor:pointer !important;}
div[data-testid='stExpander'] .stMarkdown{color:#bdbdbd !important;font-size:0.9rem !important;}
.login-page{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:85vh;padding:20px;}
.login-brand{font-size:3rem;font-weight:700;letter-spacing:8px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;margin-bottom:8px;}
.login-sub{color:#6b7280;font-size:0.9rem;margin-bottom:40px;letter-spacing:1px;}
.login-box{background:#141414;border:1px solid #2a2a2a;border-radius:16px;padding:32px;width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,0.85);}
.login-label{font-size:0.72rem;text-transform:uppercase;letter-spacing:1.5px;color:#6a6a6a;margin-bottom:10px;font-weight:700;}
.login-input-row{display:flex;gap:8px;margin-bottom:16px;}
.login-input{flex:1;height:48px;border-radius:12px;border:1px solid #2a2a2a;background:#0a0a0a;color:#fff;font-size:1.1rem;padding:0 16px;font-family:'Space Grotesk',monospace;letter-spacing:3px;text-transform:uppercase;outline:none;transition:border-color 0.2s;box-sizing:border-box;}
.login-input:focus{border-color:#4f8dff;}
.login-input::placeholder{color:#3a3a3a;letter-spacing:1px;text-transform:none;font-size:0.95rem;}
.login-send{width:48px;height:48px;border-radius:12px;border:none;background:#4f8dff;color:#fff;font-size:1.3rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background 0.2s;}
.login-send:hover{background:#2563eb;}
.login-divider{display:flex;align-items:center;gap:12px;margin:20px 0;color:#4a4a4a;font-size:0.78rem;}
.login-divider::before,.login-divider::after{content:'';flex:1;height:1px;background:#2a2a2a;}
.login-gen{width:100%;height:48px;border-radius:12px;border:1px dashed #3a3a3a;background:transparent;color:#bdbdbd;font-size:0.95rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;display:flex;align-items:center;justify-content:center;gap:8px;}
.login-gen:hover{background:#1a1a1a;color:#fff;border-color:#4f8dff;border-style:solid;}
.login-error{background:#2a1a1a;border:1px solid #ff5555;border-radius:10px;padding:12px 16px;color:#ff8888;font-size:0.85rem;margin-bottom:16px;text-align:center;}
.login-info{color:#6b7280;font-size:0.78rem;text-align:center;margin-top:16px;line-height:1.5;}
</style>
"""

active_code = get_active_code()

if not active_code:
    st.html(CSS)
    ip = get_ip()
    err = st.session_state.pop("login_error", None)
    st.html('<div class="login-page">')
    st.html('<div class="login-brand">STRAFE</div>')
    st.html('<div class="login-sub">Enter your code to continue</div>')
    st.html('<div class="login-box">')
    if is_banned(ip):
        st.html('<div class="login-error">Too many failed attempts. Your IP is banned for 15 minutes.</div>')
        st.html('</div></div>')
        st.stop()
    cooldown = get_cooldown(ip)
    if cooldown > 0:
        st.html(f'<div class="login-error">Please wait {int(cooldown)} seconds before trying again.</div>')
        st.html('</div></div>')
        st.stop()
    if err:
        st.html(f'<div class="login-error">{err}</div>')
    st.html('<div class="login-label">Your code</div>')
    st.html('<div class="login-input-row">')
    code_input = st.text_input("code", placeholder="8 character code", max_chars=8, key="login_code_input", label_visibility="collapsed")
    if st.button(SEND_GLYPH, key="login_send_btn", type="primary"):
        raw = (code_input or "").strip().upper()
        if len(raw) != CODE_LENGTH:
            st.session_state["login_error"] = "Code must be exactly 8 characters."
            record_attempt(ip, False)
            st.rerun()
        if not all(c in string.ascii_uppercase + string.digits for c in raw):
            st.session_state["login_error"] = "Code can only contain A-Z and 0-9."
            record_attempt(ip, False)
            st.rerun()
        if not code_exists(hash_code(raw)):
            st.session_state["login_error"] = "Invalid code. Generate a new one if you don't have one."
            record_attempt(ip, False)
            st.rerun()
        record_attempt(ip, True)
        login(raw)
        time.sleep(0.3)
        st.rerun()
    st.html('</div>')
    st.html('<div class="login-divider">OR</div>')
    if st.button("\uff0b Generate new code", key="login_gen_btn", use_container_width=True):
        new_code = gen_code()
        create_code(new_code)
        record_attempt(ip, True)
        login(new_code)
        st.toast(f"Your code: {new_code} \u2014 save it somewhere safe!")
        time.sleep(0.5)
        st.rerun()
    st.html('<div class="login-info">Your chats and settings are tied to this code.<br>Share it to access your data from another device.</div>')
    st.html('</div>')
    st.html('</div>')
    st.stop()

st.html(CSS)
st.html("<div class='brand'>STRAFE AI</div>")

KEYS = [st.secrets.get(f"GROQ_API_KEY_{i}") for i in range(1, 7)]
KEYS = [k for k in KEYS if k]
if not KEYS:
    st.error("No GROQ_API_KEY_1..6 found in secrets.")
    st.stop()

PREFERRED = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
SYSTEM = (
    "I keep it direct and simple. No fluff, no long explanations unless you ask for them.\n"
    "I match your energy\u2014you're casual, I'm casual. You're serious, I'm serious. No fake politeness, just real talk.\n"
    "I hold nothing back, answer whatever you ask. I don't sugarcoat or dodge. If something's dark or weird, I engage with it\n"
    "You are Strafe AI, an assistant designed to help and chat. No help with illegal stuff. Be serious. Remember to be direct and simple.\n\n"
    "CRITICAL TOOL RULES:\n"
    "1. Your training data ends early 2025. Use web_search for anything time-sensitive.\n"
    "2. NEVER call web_search more than ONCE per user message. After receiving search results, you MUST provide a final answer immediately.\n"
    "3. Do not refine queries or search again if the first result is insufficient. Answer with what you have and note limitations.\n"
    "4. Do not announce that you are searching. Just do it."
)
SAFE_MODELS = {"qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"}
HISTORY_LIMIT = 15

CELERIS_KEY = st.secrets.get("CELERIS_API_KEY")
CELERIS_BASE_URL = st.secrets.get("CELERIS_BASE_URL", "")
CELERIS_MODEL = st.secrets.get("CELERIS_MODEL", "")

_celeris_client = None
def get_celeris_client():
    global _celeris_client
    if _celeris_client is None:
        from openai import OpenAI
        _celeris_client = OpenAI(api_key=CELERIS_KEY, base_url=CELERIS_BASE_URL)
    return _celeris_client

def celeris_ready():
    return bool(CELERIS_KEY and CELERIS_BASE_URL and CELERIS_MODEL)

def pick_model():
    if st.session_state.get("model_choice") == "celeris":
        return CELERIS_MODEL
    if "groq_model" in st.session_state:
        return st.session_state.groq_model
    try:
        response = Groq(api_key=KEYS[0]).models.list()
        avail = {m.id if hasattr(m, 'id') else m[0] for m in response.data}
    except Exception:
        avail = set()
    for p in PREFERRED:
        if p in avail:
            st.session_state.groq_model = p
            return p
    safe_avail = avail & SAFE_MODELS
    if safe_avail:
        chosen = list(safe_avail)[0]
        st.session_state.groq_model = chosen
        return chosen
    if avail:
        chosen = list(avail)[0]
        st.session_state.groq_model = chosen
        return chosen
    st.session_state.groq_model = PREFERRED[0]
    return PREFERRED[0]

def mark_key_failed(key):
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    st.session_state.failed_keys.add(key)

def _search_fallback(query, num_results, reason):
    backends = ["lite", "html", "auto", "duckduckgo", "google", "bing", "mojeek", "brave"]
    last_err = reason
    for b in backends:
        try:
            out = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results, backend=b):
                    link = r.get("href") or r.get("url") or ""
                    snippet = r.get("body") or r.get("snippet") or ""
                    title = r.get("title") or ""
                    if link or snippet:
                        out.append({"title": title, "link": link, "snippet": snippet})
            if out:
                return out
        except DDGSException as e:
            last_err = f"{b}: {e}"
            time.sleep(0.3)
            continue
        except Exception as e:
            last_err = f"{b}: {e}"
            continue
    return [{"title": "Search unavailable", "link": "", "snippet": f"All search backends are rate limited ({last_err}). Answer from training data with caveat."}]

def web_search(query, num_results=3):
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    try:
        r = cffi_requests.get(url, impersonate="chrome124", timeout=15, headers={"Accept-Language": "en-US,en;q=0.9", "Referer": "https://duckduckgo.com/"})
        if r.status_code == 200 and "challenge" not in r.text.lower()[:500]:
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            for a in soup.select("a.result__a")[:num_results]:
                href = a.get("href", "")
                if href.startswith("//duckduckgo.com/l/?uddg="):
                    try:
                        href = unquote(href.split("uddg=", 1)[1].split("&", 1)[0])
                    except Exception:
                        pass
                title = a.get_text(strip=True)
                parent = a.find_parent("div", class_="result")
                snippet = ""
                if parent:
                    sn = parent.select_one(".result__snippet")
                    if sn:
                        snippet = sn.get_text(strip=True)
                if href or snippet:
                    results.append({"title": title, "link": href, "snippet": snippet})
            if results:
                return results
            return _search_fallback(query, num_results, "empty DDG results")
        return _search_fallback(query, num_results, f"DDG status {r.status_code}")
    except Exception as e:
        return _search_fallback(query, num_results, str(e)[:80])

def msg_to_api(m, distance_from_latest=None):
    imgs = m.get("images") or []
    files = m.get("files") or []
    has_media = bool(imgs or files)
    if not has_media:
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "text", "text": m["content"]}]
    for f in files:
        fname = f.get("name", "file")
        fcontent = f.get("content", "")
        parts.insert(0, {"type": "text", "text": f"[Attached file: {fname}]\n```\n{fcontent}\n```"})
    if imgs:
        imgs = imgs[:3]
        if distance_from_latest is not None:
            if distance_from_latest < 2:
                for u in imgs:
                    parts.append({"type": "image_url", "image_url": {"url": u}})
            else:
                for u in imgs:
                    parts.append({"type": "image_url", "image_url": {"url": u, "detail": "low"}})
        else:
            for u in imgs:
                parts.append({"type": "image_url", "image_url": {"url": u, "detail": "low"}})
    return {"role": m["role"], "content": parts}

def build_payload(history):
    model = pick_model()
    msgs = [{"role": "system", "content": SYSTEM}] + history
    if st.session_state.get("model_choice") == "celeris":
        return dict(model=model, messages=msgs, max_tokens=1024, temperature=0.7)
    kw = dict(model=model, messages=msgs, max_completion_tokens=2048, temperature=0.7)
    if "qwen" in model.lower():
        kw["reasoning_format"] = "parsed"
    elif "gpt-oss" in model.lower():
        kw["reasoning_effort"] = "medium"
        kw["reasoning_format"] = "parsed"
    return kw

def call_groq_with_retry(kwargs):
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    pool = [k for k in KEYS if k not in st.session_state.failed_keys] or list(KEYS)
    last_err = None
    for key in random.sample(pool, len(pool)):
        try:
            return Groq(api_key=key).chat.completions.create(**kwargs), None
        except NotFoundError:
            st.session_state.pop("groq_model", None)
            mark_key_failed(key)
            last_err = "model gone"
            continue
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "401" in err_str:
                mark_key_failed(key)
            last_err = err_str[:120]
            continue
    return None, last_err

def ask(use_search=False, use_think=False, look_back=False):
    use_celeris = st.session_state.get("model_choice") == "celeris"
    if use_celeris and not celeris_ready():
        raise RuntimeError("Celeris not configured.")
    if use_celeris and use_search:
        st.toast("Celeris doesn't support search - disabled for this message")
        use_search = False
    t0 = time.time()
    slice_msgs = st.session_state.messages if look_back else st.session_state.messages[-HISTORY_LIMIT:]
    total = len(slice_msgs)
    history = []
    for idx, m in enumerate(slice_msgs):
        distance = total - 1 - idx
        history.append(msg_to_api(m, distance_from_latest=distance))
    tools = None
    if use_search:
        tools = [{"type": "function", "function": {"name": "web_search", "description": "Search the web for current info. Use for recent events, news, prices, sports. DO NOT fake the search.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Clean keywords ONLY. Fix spelling."}}, "required": ["query"]}}}]
    max_rounds = 2 if use_search else 1
    tool_calls_made = 0
    last_err = None
    last_round_had_tool_call = False
    for round_idx in range(max_rounds):
        kwargs = build_payload(history)
        if tools:
            kwargs["tools"] = tools
        if use_celeris:
            try:
                r = get_celeris_client().chat.completions.create(**kwargs)
                err = None
            except Exception as e:
                r = None
                err = str(e)[:120]
        else:
            r, err = call_groq_with_retry(kwargs)
        if r is None:
            last_err = err
            break
        msg = r.choices[0].message
        if tools and getattr(msg, "tool_calls", None):
            tool_calls_made += len(msg.tool_calls)
            if tool_calls_made > 5:
                raise RuntimeError("Max tool rounds exceeded")
            if round_idx == max_rounds - 1:
                last_round_had_tool_call = True
            assistant_msg = {"role": "assistant", "content": msg.content or "", "tool_calls": []}
            for tc in msg.tool_calls:
                assistant_msg["tool_calls"].append({"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}})
            history.append(assistant_msg)
            for tc in msg.tool_calls:
                if tc.function.name == "web_search":
                    try:
                        args = json.loads(tc.function.arguments)
                        query = args.get("query", "") if isinstance(args, dict) else ""
                    except Exception:
                        query = ""
                    results = web_search(query)
                    context = "\n".join(f"{res['title']}: {res['snippet']} ({res['link']})" for res in results)
                    history.append({"role": "tool", "tool_call_id": tc.id, "content": context})
            continue
        else:
            content = (msg.content or "").strip()
            reasoning = getattr(msg, "reasoning_content", None)
            secs = max(0.1, time.time() - t0)
            used = (r.usage.total_tokens if r.usage else 0)
            tps = round(used / secs, 1) if used else 0
            return {"content": content, "secs": round(secs, 1), "tok": f"{tps} tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": reasoning if use_think else None}
    if last_round_had_tool_call:
        raise RuntimeError("Model kept calling tools without producing a final answer")
    raise RuntimeError(last_err or "All API keys failed")

def info_html(m):
    sent = m.get("sent", "?")
    secs = m.get("secs", "?")
    tps = m.get("tok", "?")
    flags = []
    if m.get("search"):
        flags.append("\u2315")
    if m.get("think"):
        flags.append("\u269b")
    flag_str = " ".join(flags) + " " if flags else ""
    return f'<div class="info-line">{flag_str}sent <span>{sent}</span> &nbsp;\u00b7&nbsp; {secs}s &nbsp;\u00b7&nbsp; {tps}</div>'

init_ui_state()
render_ui()

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0 and st.session_state.messages[i - 1]["role"] == "user":
        prev_msg = st.session_state.messages[i - 1]
        st.session_state.messages[:] = st.session_state.messages[:i]
        try:
            result = ask(use_search=prev_msg.get("search", False), use_think=prev_msg.get("think", False))
            st.session_state.messages.append({"role": "assistant", **result})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": False, "think": False, "reasoning": None})
        _persist_current_chat()
        st.rerun()
    elif kind == "edit":
        st.session_state["editing"] = i

pending = st.session_state.pop("pending", None)
if pending is not None:
    if st.session_state.get("editing") is not None:
        st.session_state["editing"] = None
        st.toast("Edit cancelled - message sent instead")
    text = pending.get("text", "") if isinstance(pending, dict) else pending
    use_search = pending.get("search", False) if isinstance(pending, dict) else False
    use_think = pending.get("think", False) if isinstance(pending, dict) else False
    images = pending.get("images", []) if isinstance(pending, dict) else []
    files = pending.get("files", []) if isinstance(pending, dict) else []
    raw = text.strip().lower()
    is_look_back = raw == "look_back"
    st.session_state.messages.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "images": images, "files": files})
    try:
        result = ask(use_search=use_search, use_think=use_think, look_back=is_look_back)
        st.session_state.messages.append({"role": "assistant", **result})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": None})
    st.session_state["editing"] = None
    _persist_current_chat()
    st.rerun()

editing = st.session_state.get("editing")

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        if editing == i:
            new = st.text_area("Edit", value=m["content"], key=f"ed{i}", height=100)
            sc, sk = st.columns([1, 6])
            with sc:
                if st.button("Save", key=f"sv{i}"):
                    st.session_state.messages[:] = st.session_state.messages[:i]
                    st.session_state["pending"] = {"text": new, "search": m.get("search", False), "think": m.get("think", False), "images": m.get("images", []), "files": m.get("files", [])}
                    st.session_state["editing"] = None
                    st.rerun()
            with sk:
                if st.button("Cancel", key=f"cx{i}"):
                    st.session_state["editing"] = None
                    st.rerun()
        else:
            safe = H.escape(m["content"]).replace("\n", "<br>")
            thumbs = "".join(f'<img class="chat-thumb" src="{u}"/>' for u in (m.get("images") or []))
            file_badges = "".join(f'<span class="file-badge">\u2399 {H.escape(f.get("name","file"))}</span>' for f in (m.get("files") or []))
            st.html(f'<div class="user-bubble"><div class="user-bubble-inner">{thumbs}{file_badges}{safe}</div></div>')
            _sp, _mn = st.columns([5, 1])
            with _mn:
                with st.popover(MENU_GLYPH, key=f"mu{i}"):
                    st.html(info_html(m))
                    if st.button("Edit", key=f"ue{i}"):
                        st.session_state["act"] = ("edit", i)
                        st.rerun()
    else:
        reasoning = m.get("reasoning")
        if m.get("think"):
            think_secs = m.get("secs", "?")
            if reasoning:
                with st.expander(f"\u269b Thought for {think_secs}s", expanded=False):
                    st.markdown(reasoning)
            else:
                with st.expander(f"\u269b Thought for {think_secs}s", expanded=False):
                    st.markdown("_Model processed the request but didn't return visible thoughts._")
        with st.chat_message("assistant"):
            st.markdown(m["content"])
        _mn, _sp = st.columns([1, 3])
        with _mn:
            with st.popover(MENU_GLYPH, key=f"ma{i}"):
                st.html(info_html(m))
                if st.button("Retry", key=f"ar{i}"):
                    st.session_state["act"] = ("retry", i)
                    st.rerun()

prompt = get_prompt()
if prompt:
    st.session_state["pending"] = prompt
    st.rerun()

ma = st.session_state.pop("menu_action", None)
if ma:
    if ma == "camera_error":
        st.toast("Camera access denied or unavailable")
    elif ma == "unsupported_file":
        st.toast("Unsupported file type. Use text/code files only.")
    elif ma == "file_too_large":
        st.toast("File too large. Max 500KB for text files.")
    else:
        st.toast(f"{ma} selected")