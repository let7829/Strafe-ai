import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json, uuid, os, sqlite3, hashlib
from datetime import datetime
from pathlib import Path
from ddgs import DDGS
from ddgs.exceptions import DDGSException
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\uff0b"

GUEST_KEY = "__guest__"
DB_PATH = Path(os.environ.get("STRAFE_DB", "strafe.db"))

def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    with _db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                title TEXT NOT NULL,
                messages TEXT NOT NULL,
                created REAL NOT NULL,
                updated REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chats_email_updated ON chats(email, updated DESC);
            CREATE TABLE IF NOT EXISTS settings (
                email TEXT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                model TEXT NOT NULL DEFAULT 'groq'
            );
        """)

def db_get_chats(email):
    with _db() as c:
        rows = c.execute(
            "SELECT id, title, messages, created, updated FROM chats WHERE email=? ORDER BY updated DESC",
            (email,),
        ).fetchall()
    out = {}
    for r in rows:
        out[r["id"]] = {
            "id": r["id"],
            "title": r["title"],
            "messages": json.loads(r["messages"]),
            "created": r["created"],
            "updated": r["updated"],
        }
    return out

def db_save_chat(email, chat):
    with _db() as c:
        c.execute(
            """INSERT INTO chats(id, email, title, messages, created, updated)
               VALUES(?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title,
                 messages=excluded.messages,
                 updated=excluded.updated""",
            (chat["id"], email, chat["title"], json.dumps(chat["messages"]),
             chat.get("created", time.time()), chat.get("updated", time.time())),
        )

def db_delete_chat(email, chat_id):
    with _db() as c:
        c.execute("DELETE FROM chats WHERE id=? AND email=?", (chat_id, email))

def db_delete_all_chats(email):
    with _db() as c:
        c.execute("DELETE FROM chats WHERE email=?", (email,))

def db_get_settings(email):
    with _db() as c:
        row = c.execute("SELECT language, model FROM settings WHERE email=?", (email,)).fetchone()
    if row is None:
        return {"language": "en", "model": "groq"}
    return {"language": row["language"], "model": row["model"]}

def db_set_settings(email, language=None, model=None):
    cur = db_get_settings(email)
    language = language or cur["language"]
    model = model or cur["model"]
    with _db() as c:
        c.execute(
            """INSERT INTO settings(email, language, model) VALUES(?, ?, ?)
               ON CONFLICT(email) DO UPDATE SET language=excluded.language, model=excluded.model""",
            (email, language, model),
        )

db_init()

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
            x.onclick=function(ev){
                ev.stopPropagation();
                attachments.splice(idx,1);
                renderAtts();
            };
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
            x.onclick=function(ev){
                ev.stopPropagation();
                fileAttachments.splice(idx,1);
                renderAtts();
            };
            wrap.appendChild(name);
            wrap.appendChild(x);
            atts.appendChild(wrap);
        });
    }
    function stopCamera(){
        if(camStream){
            camStream.getTracks().forEach(function(t){t.stop();});
            camStream=null;
        }
        camOverlay.classList.remove('active');
    }
    async function openCamera(){
        try{
            camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});
            camVideo.srcObject=camStream;
            camOverlay.classList.add('active');
            menu.classList.remove('open');
        }catch(e){
            setTriggerValue('menu_action','camera_error');
        }
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
        for(let i=0;i<attachments.length;i++){
            resized.push(await resizeImage(attachments[i],1024));
        }
        setTriggerValue('submitted',{text:val,search:searchActive,think:thinkActive,images:resized,files:fileAttachments.slice()});
        input.value='';
        attachments=[];
        fileAttachments=[];
        renderAtts();
    }
    btn.onclick=send;
    input.onkeydown=function(e){if(e.key==='Enter')send();};
    if(plusBtn&&menu){
        plusBtn.onclick=function(){
            menu.classList.toggle('open');
        };
    }
    if(photoBtn){
        photoBtn.onclick=function(){
            menu.classList.remove('open');
            imageInput.click();
        };
    }
    if(cameraBtn){
        cameraBtn.onclick=openCamera;
    }
    if(fileBtn){
        fileBtn.onclick=function(){
            menu.classList.remove('open');
            fileInput.click();
        };
    }
    if(camClose){
        camClose.onclick=stopCamera;
    }
    if(camCapture){
        camCapture.onclick=capturePhoto;
    }
    imageInput.onchange=function(){
        const f=imageInput.files[0];
        if(!f)return;
        const reader=new FileReader();
        reader.onload=function(){
            attachments.push(reader.result);
            renderAtts();
        };
        reader.readAsDataURL(f);
        imageInput.value='';
    };
    fileInput.onchange=function(){
        const f=fileInput.files[0];
        if(!f)return;
        const ext=f.name.split('.').pop().toLowerCase();
        if(!TEXT_EXTS.includes(ext)&&!f.type.startsWith('text/')){
            setTriggerValue('menu_action','unsupported_file');
            fileInput.value='';
            return;
        }
        if(f.size>500000){
            setTriggerValue('menu_action','file_too_large');
            fileInput.value='';
            return;
        }
        const reader=new FileReader();
        reader.onload=function(){
            fileAttachments.push({name:f.name,content:reader.result});
            renderAtts();
        };
        reader.readAsText(f);
        fileInput.value='';
    };
    btnSearch.onclick=function(){
        searchActive=!searchActive;
        this.classList.toggle('active',searchActive);
    };
    btnThink.onclick=function(){
        thinkActive=!thinkActive;
        this.classList.toggle('active',thinkActive);
    };
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
    if(savedTab==='account')savedTab='language';
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
        const valid=['language','models','about'];
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
            del.className='chat-del