import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json, sqlite3
from datetime import datetime
from ddgs import DDGS
from ddgs.exceptions import DDGSException
import uuid

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered", initial_sidebar_state="collapsed")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\uff0b"
SIDEBAR_GLYPH = "\uff1d"
SETTINGS_GLYPH = "\u2699"

DB_PATH = "strafe_data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, created TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, email TEXT, name TEXT, messages TEXT, created TEXT)")
    conn.commit()
    return conn

def load_chats(email):
    db = get_db()
    rows = db.execute("SELECT * FROM chats WHERE email=? ORDER BY created DESC", (email,)).fetchall()
    db.close()
    return {r["id"]: {"name": r["name"], "messages": json.loads(r["messages"]), "created": r["created"]} for r in rows}

def save_chat(email, chat_id, name, messages):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO chats (id,email,name,messages,created) VALUES (?,?,?,?,?)",
               (chat_id, email, name, json.dumps(messages), datetime.now().isoformat()))
    db.commit()
    db.close()

def delete_chat(chat_id):
    db = get_db()
    db.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    db.commit()
    db.close()

def delete_all_chats(email):
    db = get_db()
    db.execute("DELETE FROM chats WHERE email=?", (email,))
    db.commit()
    db.close()

def ensure_chat(email):
    chats = load_chats(email)
    if not chats:
        cid = str(uuid.uuid4())[:8]
        chats[cid] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
        save_chat(email, cid, "New Chat", [])
    return chats

if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "language" not in st.session_state:
    st.session_state.language = "en"
if "operator" not in st.session_state:
    st.session_state.operator = "groq"
if "failed_keys" not in st.session_state:
    st.session_state.failed_keys = set()
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False
if "settings_open" not in st.session_state:
    st.session_state.settings_open = False

guest_email = "__guest__"
active_email = st.session_state.user_email if st.session_state.logged_in else guest_email
chats = ensure_chat(active_email)
if st.session_state.current_chat_id not in chats:
    st.session_state.current_chat_id = list(chats.keys())[0]

def get_current_messages():
    return chats.get(st.session_state.current_chat_id, {}).get("messages", [])

def save_current_messages(msgs):
    chat = chats.get(st.session_state.current_chat_id)
    if chat:
        name = chat["name"]
        if msgs and msgs[0].get("content"):
            n = msgs[0]["content"][:30].strip()
            if n:
                name = n
        chat["messages"] = msgs
        chat["name"] = name
        save_chat(active_email, st.session_state.current_chat_id, name, msgs)

INPUT_HTML = '<div id="bar"><div id="atts"></div><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="pb" type="button" class="icon-btn">' + PLUS_GLYPH + '</button><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button></div><div id="menu"><button id="mb-photo" type="button" class="menu-btn">Photo</button><button id="mb-camera" type="button" class="menu-btn">Camera</button><button id="mb-file" type="button" class="menu-btn">\u2399 File</button></div></div><div id="cam-overlay"><video id="cam-video" autoplay playsinline muted></video><button id="cam-close" type="button">\u2715</button><button id="cam-capture" type="button"></button><canvas id="cam-canvas" style="display:none"></canvas></div>'
INPUT_CSS = """
#bar{position:fixed;bottom:16px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:8px;}
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
    let searchActive=false,thinkActive=false,attachments=[],fileAttachments=[],camStream=null;
    const TEXT_EXTS=['txt','md','csv','json','py','js','ts','jsx','tsx','html','css','xml','yaml','yml','toml','ini','cfg','conf','log','sh','bash','zsh','sql','r','rb','go','rs','c','cpp','h','hpp','java','kt','swift','php','pl','lua','asm','s','makefile','dockerfile','env','gitignore','editorconfig'];
    const imageInput=document.createElement('input');imageInput.type='file';imageInput.accept='image/*';imageInput.style.display='none';parentElement.appendChild(imageInput);
    const fileInput=document.createElement('input');fileInput.type='file';fileInput.accept='.txt,.md,.csv,.json,.py,.js,.ts,.jsx,.tsx,.html,.css,.xml,.yaml,.yml,.toml,.ini,.cfg,.conf,.log,.sh,.bash,.zsh,.sql,.r,.rb,.go,.rs,.c,.cpp,.h,.hpp,.java,.kt,.swift,.php,.pl,.lua,.asm,.s,.makefile,.dockerfile,.env,.gitignore,.editorconfig,text/*';fileInput.style.display='none';parentElement.appendChild(fileInput);
    function resizeImage(d,m){return new Promise(function(r){const i=new Image();i.onload=function(){const c=document.createElement('canvas');let w=i.width,h=i.height;if(w>m||h>m){if(w>h){h=Math.round(h*m/w);w=m;}else{w=Math.round(w*m/h);h=m;}}c.width=w;c.height=h;c.getContext('2d').drawImage(i,0,0,w,h);r(c.toDataURL('image/jpeg',0.8));};i.src=d;});}
    function renderAtts(){atts.innerHTML='';attachments.forEach(function(item,idx){const w=document.createElement('div');w.className='att';const img=document.createElement('img');img.src=item;const x=document.createElement('button');x.type='button';x.className='att-x';x.textContent='\\u2715';x.onclick=function(e){e.stopPropagation();attachments.splice(idx,1);renderAtts();};w.appendChild(img);w.appendChild(x);atts.appendChild(w);});fileAttachments.forEach(function(item,idx){const w=document.createElement('div');w.className='att-file';const n=document.createElement('span');n.className='att-file-name';n.textContent='\\u2399 '+item.name;const x=document.createElement('button');x.type='button';x.className='att-file-x';x.textContent='\\u2715';x.onclick=function(e){e.stopPropagation();fileAttachments.splice(idx,1);renderAtts();};w.appendChild(n);w.appendChild(x);atts.appendChild(w);});}
    function stopCamera(){if(camStream){camStream.getTracks().forEach(function(t){t.stop();});camStream=null;}camOverlay.classList.remove('active');}
    async function openCamera(){try{camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});camVideo.srcObject=camStream;camOverlay.classList.add('active');menu.classList.remove('open');}catch(e){setTriggerValue('menu_action','camera_error');}}
    async function capturePhoto(){if(!camStream)return;camCanvas.width=camVideo.videoWidth;camCanvas.height=camVideo.videoHeight;camCanvas.getContext('2d').drawImage(camVideo,0,0);const d=camCanvas.toDataURL('image/jpeg',0.9);stopCamera();const r=await resizeImage(d,1024);attachments.push(r);renderAtts();}
    function updateLabels(){btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';}
    async function send(){const v=input.value.trim();if(!v&&!attachments.length&&!fileAttachments.length)return;const r=[];for(let i=0;i<attachments.length;i++){r.push(await resizeImage(attachments[i],1024));}setTriggerValue('submitted',{text:v,search:searchActive,think:thinkActive,images:r,files:fileAttachments.slice()});input.value='';attachments=[];fileAttachments=[];renderAtts();}
    btn.onclick=send;input.onkeydown=function(e){if(e.key==='Enter')send();};
    if(plusBtn&&menu){plusBtn.onclick=function(){menu.classList.toggle('open');};}
    if(photoBtn){photoBtn.onclick=function(){menu.classList.remove('open');imageInput.click();};}
    if(cameraBtn){cameraBtn.onclick=openCamera;}
    if(fileBtn){fileBtn.onclick=function(){menu.classList.remove('open');fileInput.click();};}
    if(camClose){camClose.onclick=stopCamera;}
    if(camCapture){camCapture.onclick=capturePhoto;}
    imageInput.onchange=function(){const f=imageInput.files[0];if(!f)return;const r=new FileReader();r.onload=function(){attachments.push(r.result);renderAtts();};r.readAsDataURL(f);imageInput.value='';};
    fileInput.onchange=function(){const f=fileInput.files[0];if(!f)return;const ext=f.name.split('.').pop().toLowerCase();if(!TEXT_EXTS.includes(ext)&&!f.type.startsWith('text/')){setTriggerValue('menu_action','unsupported_file');fileInput.value='';return;}if(f.size>500000){setTriggerValue('menu_action','file_too_large');fileInput.value='';return;}const r=new FileReader();r.onload=function(){fileAttachments.push({name:f.name,content:r.result});renderAtts();};r.readAsText(f);fileInput.value='';};
    btnSearch.onclick=function(){searchActive=!searchActive;this.classList.toggle('active',searchActive);updateLabels();};
    btnThink.onclick=function(){thinkActive=!thinkActive;this.classList.toggle('active',thinkActive);updateLabels();};
}
"""

chat_input = components.component("strafe_chat_input", html=INPUT_HTML, css=INPUT_CSS, js=INPUT_JS)

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

sidebar_css = "section[data-testid='stSidebar']{display:none !important;}" if not st.session_state.sidebar_open else "section[data-testid='stSidebar']{display:block !important;}"
PAGE_CSS = f"""
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}}
html,body,.stApp,#root{{overflow-x:hidden !important;max-width:100vw !important;}}
section.main .block-container{{padding:0 1rem 160px 1rem !important;max-width:760px;overflow-x:hidden;}}
#MainMenu,footer,header{{visibility:hidden;}}
div[data-testid='stChatMessage']{{background:transparent !important;border:none !important;padding:8px 0 0 0 !important;margin:0 !important;}}
div[data-testid^='stChatMessageAvatar']{{display:none !important;}}
div[data-testid='stChatMessage'] .stMarkdown p{{color:#ececec !important;font-size:1.08rem;line-height:1.6;}}
.brand{{font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}}
.top-bar{{display:flex;align-items:center;justify-content:space-between;padding:8px 4px 2px 4px;}}
.top-btn{{background:transparent;border:none;color:#7a7a7a;font-size:1.4rem;cursor:pointer;padding:4px 8px;}}
.top-btn:hover{{color:#fff;}}
.user-bubble{{display:flex;justify-content:flex-end;width:100%;margin:10px 0 0 0;}}
.user-bubble-inner{{background:#5c5c5c;color:#fff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}}
.chat-thumb{{width:64px;height:64px;object-fit:cover;border-radius:12px;margin:0 8px 6px 0;vertical-align:middle;border:1px solid #2a2a2a;}}
.file-badge{{display:inline-flex;align-items:center;gap:4px;background:#2a2a2a;border-radius:8px;padding:4px 10px;font-size:0.75rem;color:#bdbdbd;margin:0 8px 6px 0;}}
.info-line{{color:#8a8a8a !important;font-size:0.82rem !important;padding:2px 0 6px 0;}}
.info-line span{{color:#bdbdbd;}}
div[data-testid='stExpander'] details{{background:#1a1a1a !important;border:1px solid #2a2a2a !important;border-radius:12px !important;padding:8px 12px !important;margin:8px 0 !important;}}
div[data-testid='stExpander'] summary{{color:#8a8a8a !important;font-size:0.85rem !important;}}
div[data-testid='stExpander'] .stMarkdown{{color:#bdbdbd !important;font-size:0.9rem !important;}}
section[data-testid='stSidebar']{{background:#111 !important;border-right:1px solid #2a2a2a !important;}}
section[data-testid='stSidebar'] .stMarkdown{{color:#ececec !important;}}
{sidebar_css}
</style>
"""
st.html(PAGE_CSS)

tc1, tc2, tc3 = st.columns([1, 3, 1])
with tc1:
    if st.button(SIDEBAR_GLYPH, key="toggle_sidebar"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()
with tc2:
    st.html("<div class='brand' style='text-align:center'>STRAFE AI</div>")
with tc3:
    if st.button(SETTINGS_GLYPH, key="toggle_settings"):
        st.session_state.settings_open = not st.session_state.settings_open
        st.rerun()

if st.session_state.settings_open:
    with st.dialog("Settings"):
        tab1, tab2, tab3, tab4 = st.tabs(["Account", "Language", "Models/Operators", "About"])
        with tab1:
            if st.session_state.logged_in:
                st.caption(st.session_state.user_email)
                if st.button("Log Out", key="dlg_logout"):
                    st.session_state.logged_in = False
                    st.session_state.user_email = ""
                    st.session_state.current_chat_id = None
                    st.session_state.settings_open = False
                    st.rerun()
            else:
                dlg_email = st.text_input("Email", placeholder="you@example.com", key="dlg_login_email")
                if st.button("Login", key="dlg_login_btn"):
                    if dlg_email and "@" in dlg_email:
                        st.session_state.user_email = dlg_email
                        st.session_state.logged_in = True
                        st.session_state.current_chat_id = None
                        st.session_state.settings_open = False
                        st.rerun()
            st.divider()
            if st.button("Delete All Chats", key="dlg_delete_all", type="secondary"):
                delete_all_chats(active_email)
                nc = str(uuid.uuid4())[:8]
                save_chat(active_email, nc, "New Chat", [])
                chats.clear()
                chats[nc] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
                st.session_state.current_chat_id = nc
                st.session_state.settings_open = False
                st.rerun()
        with tab2:
            lang_map = {"English": "en", "Russian": "ru", "Ukrainian": "uk"}
            rev_lang = {v: k for k, v in lang_map.items()}
            cur = rev_lang.get(st.session_state.language, "English")
            chosen = st.radio("Language", list(lang_map.keys()), index=list(lang_map.keys()).index(cur), key="dlg_lang")
            if lang_map[chosen] != st.session_state.language:
                st.session_state.language = lang_map[chosen]
        with tab3:
            op_labels = {"Groq": "groq", "Celeris": "celeris"}
            rev_op = {v: k for k, v in op_labels.items()}
            cur_op = rev_op.get(st.session_state.operator, "Groq")
            chosen_op = st.radio("Operator", list(op_labels.keys()), index=list(op_labels.keys()).index(cur_op), key="dlg_op",
                                 captions=["Strong coding/math. Fast responses.", "Fastest model. Skills unknown."])
            if op_labels[chosen_op] != st.session_state.operator:
                st.session_state.operator = op_labels[chosen_op]
        with tab4:
            st.markdown("Strafe is a project made for your use. No data can be seen by anyone, even by the owner.")

with st.sidebar:
    st.markdown("### Chats")
    if st.button("+ New Chat", key="sb_new_chat"):
        cid = str(uuid.uuid4())[:8]
        save_chat(active_email, cid, "New Chat", [])
        st.session_state.current_chat_id = cid
        chats[cid] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
        st.rerun()
    
    sorted_chats = sorted(chats.items(), key=lambda x: x[1].get("created", ""), reverse=True)
    for cid, cdata in sorted_chats:
        cols = st.columns([5, 1])
        with cols[0]:
            if st.button(cdata.get("name", "New Chat"), key=f"chat_{cid}"):
                st.session_state.current_chat_id = cid
                st.rerun()
        with cols[1]:
            if st.button(CLOSE_GLYPH, key=f"del_{cid}"):
                st.session_state["delete_confirm"] = cid
    
    if st.session_state.get("delete_confirm"):
        dc_id = st.session_state["delete_confirm"]
        dc_name = chats.get(dc_id, {}).get("name", "this chat")
        st.warning(f'Delete "{dc_name}"?')
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cancel", key="cancel_del"):
                del st.session_state["delete_confirm"]
                st.rerun()
        with c2:
            if st.button("Delete", key="confirm_del", type="primary"):
                delete_chat(dc_id)
                if dc_id in chats:
                    del chats[dc_id]
                if not chats:
                    nc = str(uuid.uuid4())[:8]
                    save_chat(active_email, nc, "New Chat", [])
                    chats[nc] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
                    st.session_state.current_chat_id = nc
                elif st.session_state.current_chat_id == dc_id:
                    st.session_state.current_chat_id = list(chats.keys())[0]
                del st.session_state["delete_confirm"]
                st.rerun()
    
    if not st.session_state.logged_in:
        st.divider()
        st.caption("Guest mode. Login via ⚙︎ to save chats.")

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
    "CRITICAL: Your internal training data ends in early 2025. If the user asks about recent events, YOU MUST USE the web_search TOOL. Do not guess."
)
SAFE_MODELS = {"qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"}
HISTORY_LIMIT = 30

def pick_model():
    if "model" in st.session_state:
        return st.session_state.model
    try:
        response = Groq(api_key=KEYS[0]).models.list()
        avail = {m.id if hasattr(m, 'id') else m[0] for m in response.data}
    except Exception:
        avail = set()
    for p in PREFERRED:
        if p in avail:
            st.session_state.model = p
            return p
    safe_avail = avail & SAFE_MODELS
    if safe_avail:
        chosen = list(safe_avail)[0]
        st.session_state.model = chosen
        return chosen
    if avail:
        chosen = list(avail)[0]
        st.session_state.model = chosen
        return chosen
    st.session_state.model = PREFERRED[0]
    return PREFERRED[0]

def get_working_key():
    available = [k for k in KEYS if k not in st.session_state.failed_keys]
    if not available:
        st.session_state.failed_keys.clear()
        available = KEYS
    return random.choice(available)

def mark_key_failed(key):
    st.session_state.failed_keys.add(key)

def web_search(query, num_results=3):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results, backend="brave,google,duckduckgo"):
                results.append({"title": r.get("title", ""), "link": r.get("href", ""), "snippet": r.get("body", "")})
        return results if results else [{"title": "No results", "link": "", "snippet": "Search returned empty. Tell the user."}]
    except DDGSException:
        return [{"title": "Rate Limited", "link": "", "snippet": "Rate limit reached. Tell the user."}]
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}. Tell the user."}]

def msg_to_api(m, distance=None, full_res=False):
    imgs = m.get("images") or []
    files = m.get("files") or []
    if not imgs and not files:
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "text", "text": m["content"]}]
    for f in files:
        parts.insert(0, {"type": "text", "text": f"[Attached file: {f.get('name','file')}]\n```\n{f.get('content','')}\n```"})
    if imgs:
        if distance is not None and not full_res:
            if distance >= 15:
                pass
            elif distance >= 3:
                for u in imgs:
                    parts.append({"type": "image_url", "image_url": {"url": u, "detail": "low"}})
            else:
                for u in imgs:
                    parts.append({"type": "image_url", "image_url": {"url": u}})
        else:
            for u in imgs:
                parts.append({"type": "image_url", "image_url": {"url": u}})
    return {"role": m["role"], "content": parts}

def build_payload(history):
    model = pick_model()
    msgs = [{"role": "system", "content": SYSTEM}] + history
    kw = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
    if "qwen" in model.lower():
        kw["reasoning_format"] = "parsed"
    elif "gpt-oss" in model.lower():
        kw["reasoning_effort"] = "medium"
        kw["reasoning_format"] = "parsed"
    return kw

def call_groq_with_retry(kwargs):
    last_err = None
    keys_to_try = list(KEYS)
    random.shuffle(keys_to_try)
    for key in keys_to_try:
        if key in st.session_state.failed_keys:
            continue
        try:
            return Groq(api_key=key).chat.completions.create(**kwargs), None
        except NotFoundError:
            st.session_state.pop("model", None)
            mark_key_failed(key)
            last_err = "model gone"
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "401" in err_str:
                mark_key_failed(key)
            last_err = err_str[:120]
    for key in KEYS:
        if key not in st.session_state.failed_keys:
            continue
        try:
            return Groq(api_key=key).chat.completions.create(**kwargs), None
        except Exception as e:
            last_err = str(e)[:120]
    return None, last_err

def ask(use_search=False, use_think=False, look_back=False, clearer_image_back=False):
    t0 = time.time()
    current_msgs = get_current_messages()
    slice_msgs = current_msgs if (look_back or clearer_image_back) else current_msgs[-HISTORY_LIMIT:]
    total = len(slice_msgs)
    history = [msg_to_api(m, distance=total - 1 - idx, full_res=clearer_image_back) for idx, m in enumerate(slice_msgs)]
    tools = None
    if use_search:
        tools = [{"type": "function", "function": {"name": "web_search", "description": "Search the web for current info. DO NOT fake the search.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Clean keywords ONLY. Fix spelling."}}, "required": ["query"]}}}]
    max_rounds = 5 if use_search else 1
    tool_calls_made = 0
    last_err = None
    for round_idx in range(max_rounds):
        kwargs = build_payload(history)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "required" if round_idx == 0 and tool_calls_made == 0 else "auto"
        r, err = call_groq_with_retry(kwargs)
        if r is None:
            last_err = err
            break
        msg = r.choices[0].message
        if tools and getattr(msg, "tool_calls", None):
            tool_calls_made += len(msg.tool_calls)
            if tool_calls_made > 5:
                raise RuntimeError("Max tool rounds exceeded")
            am = {"role": "assistant", "content": msg.content or "", "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.tool_calls]}
            history.append(am)
            for tc in msg.tool_calls:
                if tc.function.name == "web_search":
                    args = json.loads(tc.function.arguments)
                    results = web_search(args.get("query", ""))
                    context = "\n".join(f"{res['title']}: {res['snippet']} ({res['link']})" for res in results)
                    history.append({"role": "tool", "tool_call_id": tc.id, "content": context})
        else:
            content = (msg.content or "").strip()
            reasoning = getattr(msg, "reasoning_content", None)
            secs = max(0.1, time.time() - t0)
            used = (r.usage.total_tokens if r.usage else 0)
            tps = round(used / secs, 1) if used else 0
            return {"content": content, "secs": round(secs, 1), "tok": f"{tps} tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": reasoning if use_think else None}
    raise RuntimeError(last_err or "All API keys failed")

def info_html(m):
    flags = []
    if m.get("search"): flags.append("\u2315")
    if m.get("think"): flags.append("\u269b")
    fs = " ".join(flags) + " " if flags else ""
    return f'<div class="info-line">{fs}sent <span>{m.get("sent","?")}</span> &nbsp;\u00b7&nbsp; {m.get("secs","?")}s &nbsp;\u00b7&nbsp; {m.get("tok","?")}</div>'

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0:
        msgs = get_current_messages()
        if i - 1 < len(msgs) and msgs[i - 1]["role"] == "user":
            prev = msgs[i - 1]
            msgs = msgs[:i]
            save_current_messages(msgs)
            try:
                result = ask(use_search=prev.get("search", False), use_think=prev.get("think", False))
                msgs.append({"role": "assistant", **result})
            except Exception as e:
                msgs.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": False, "think": False, "reasoning": None})
            save_current_messages(msgs)
    elif kind == "edit":
        st.session_state["editing"] = i

pending = st.session_state.pop("pending", None)
if pending is not None:
    text = pending.get("text", "") if isinstance(pending, dict) else pending
    use_search = pending.get("search", False) if isinstance(pending, dict) else False
    use_think = pending.get("think", False) if isinstance(pending, dict) else False
    images = pending.get("images", []) if isinstance(pending, dict) else []
    files = pending.get("files", []) if isinstance(pending, dict) else []
    raw = text.strip().lower()
    msgs = get_current_messages()
    msgs.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "images": images, "files": files})
    save_current_messages(msgs)
    try:
        result = ask(use_search=use_search, use_think=use_think, look_back=(raw == "look_back"), clearer_image_back=(raw == "clearer_image_back"))
        msgs.append({"role": "assistant", **result})
    except Exception as e:
        msgs.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": None})
    save_current_messages(msgs)
    st.session_state["editing"] = None
    st.rerun()

editing = st.session_state.get("editing")
current_msgs = get_current_messages()

for i, m in enumerate(current_msgs):
    if m["role"] == "user":
        if editing == i:
            new = st.text_area("Edit", value=m["content"], key=f"ed{i}", height=100)
            c1, c2 = st.columns([1, 6])
            with c1:
                if st.button("Save", key=f"sv{i}"):
                    msgs = get_current_messages()[:i]
                    save_current_messages(msgs)
                    st.session_state["pending"] = {"text": new, "search": m.get("search", False), "think": m.get("think", False), "images": m.get("images", []), "files": m.get("files", [])}
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"cx{i}"):
                    st.session_state["editing"] = None
                    st.rerun()
        else:
            safe = H.escape(m["content"]).replace("\n", "<br>")
            thumbs = "".join(f'<img class="chat-thumb" src="{u}"/>' for u in (m.get("images") or []))
            fb = "".join(f'<span class="file-badge">\u2399 {H.escape(f.get("name","file"))}</span>' for f in (m.get("files") or []))
            st.html(f'<div class="user-bubble"><div class="user-bubble-inner">{thumbs}{fb}{safe}</div></div>')
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
            ts = m.get("secs", "?")
            if reasoning:
                with st.expander(f"\u269b Thought for {ts}s", expanded=False):
                    st.markdown(reasoning)
            else:
                with st.expander(f"\u269b Thought for {ts}s", expanded=False):
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
    if ma == "camera_error": st.toast("Camera access denied")
    elif ma == "unsupported_file": st.toast("Unsupported file type")
    elif ma == "file_too_large": st.toast("File too large. Max 500KB")
    else: st.toast(f"{ma} selected")