
import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json
from datetime import datetime
from ddgs import DDGS
from ddgs.exceptions import DDGSException
import uuid

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\uff0b"
SIDEBAR_GLYPH = "\uff1d"
SETTINGS_GLYPH = "\u2699"

if "chats" not in st.session_state:
    st.session_state.chats = {}
if "current_chat_id" not in st.session_state:
    cid = str(uuid.uuid4())[:8]
    st.session_state.chats[cid] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
    st.session_state.current_chat_id = cid
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False
if "settings_open" not in st.session_state:
    st.session_state.settings_open = False
if "settings_tab" not in st.session_state:
    st.session_state.settings_tab = "account"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "language" not in st.session_state:
    st.session_state.language = "en"
if "operator" not in st.session_state:
    st.session_state.operator = "groq"
if "delete_confirm" not in st.session_state:
    st.session_state.delete_confirm = None
if "login_popup" not in st.session_state:
    st.session_state.login_popup = False
if "failed_keys" not in st.session_state:
    st.session_state.failed_keys = set()

def get_current_chat():
    return st.session_state.chats.get(st.session_state.current_chat_id, {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()})

def save_current_chat(messages):
    st.session_state.chats[st.session_state.current_chat_id]["messages"] = messages
    if messages and messages[0].get("content"):
        name = messages[0]["content"][:30].strip()
        if name:
            st.session_state.chats[st.session_state.current_chat_id]["name"] = name

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
    let searchActive=false;
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
            wrap.appendChild(img);wrap.appendChild(x);atts.appendChild(wrap);
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
            wrap.appendChild(name);wrap.appendChild(x);atts.appendChild(wrap);
        });
    }
    function stopCamera(){
        if(camStream){camStream.getTracks().forEach(function(t){t.stop();});camStream=null;}
        camOverlay.classList.remove('active');
    }
    async function openCamera(){
        try{camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});camVideo.srcObject=camStream;camOverlay.classList.add('active');menu.classList.remove('open');}catch(e){setTriggerValue('menu_action','camera_error');}
    }
    async function capturePhoto(){
        if(!camStream)return;
        camCanvas.width=camVideo.videoWidth;camCanvas.height=camVideo.videoHeight;
        camCanvas.getContext('2d').drawImage(camVideo,0,0);
        const dataUrl=camCanvas.toDataURL('image/jpeg',0.9);
        stopCamera();
        const resized=await resizeImage(dataUrl,1024);
        attachments.push(resized);renderAtts();
    }
    function updateLabels(){
        btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';
        btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';
    }
    async function send(){
        const val=input.value.trim();
        if(!val&&!attachments.length&&!fileAttachments.length)return;
        const resized=[];
        for(let i=0;i<attachments.length;i++){resized.push(await resizeImage(attachments[i],1024));}
        setTriggerValue('submitted',{text:val,search:searchActive,think:thinkActive,images:resized,files:fileAttachments.slice()});
        input.value='';attachments=[];fileAttachments=[];renderAtts();
    }
    btn.onclick=send;
    input.onkeydown=function(e){if(e.key==='Enter')send();};
    if(plusBtn&&menu){plusBtn.onclick=function(){menu.classList.toggle('open');};}
    if(photoBtn){photoBtn.onclick=function(){menu.classList.remove('open');imageInput.click();};}
    if(cameraBtn){cameraBtn.onclick=openCamera;}
    if(fileBtn){fileBtn.onclick=function(){menu.classList.remove('open');fileInput.click();};}
    if(camClose){camClose.onclick=stopCamera;}
    if(camCapture){camCapture.onclick=capturePhoto;}
    imageInput.onchange=function(){const f=imageInput.files[0];if(!f)return;const reader=new FileReader();reader.onload=function(){attachments.push(reader.result);renderAtts();};reader.readAsDataURL(f);imageInput.value='';};
    fileInput.onchange=function(){const f=fileInput.files[0];if(!f)return;const ext=f.name.split('.').pop().toLowerCase();if(!TEXT_EXTS.includes(ext)&&!f.type.startsWith('text/')){setTriggerValue('menu_action','unsupported_file');fileInput.value='';return;}if(f.size>500000){setTriggerValue('menu_action','file_too_large');fileInput.value='';return;}const reader=new FileReader();reader.onload=function(){fileAttachments.push({name:f.name,content:reader.result});renderAtts();};reader.readAsText(f);fileInput.value='';};
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

CSS = """
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
section.main,section[data-testid='stMain'],[data-testid='stAppViewContainer'],[data-testid='stMainBlockContainer'],[data-testid='stAppView'],[data-testid='stVerticalBlockBorderWrapper']{overflow-x:hidden !important;max-width:100vw !important;width:100% !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding:0 1rem 160px 1rem !important;max-width:760px;overflow-x:hidden;}
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
.top-bar{display:flex;align-items:center;justify-content:space-between;padding:8px 4px 2px 4px;position:relative;}
.sidebar-toggle{background:transparent;border:none;color:#7a7a7a;font-size:1.4rem;cursor:pointer;padding:4px 8px;}
.sidebar-toggle:hover{color:#fff;}
.brand{font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.settings-btn{background:transparent;border:none;color:#7a7a7a;font-size:1.3rem;cursor:pointer;padding:4px 8px;}
.settings-btn:hover{color:#fff;}
.sidebar-overlay{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.6);z-index:1000000;display:none;}
.sidebar-overlay.open{display:block;}
.sidebar{position:fixed;top:0;left:-300px;width:280px;height:100vh;background:#111;border-right:1px solid #2a2a2a;z-index:1000001;transition:left 0.3s ease;display:flex;flex-direction:column;padding:16px;box-sizing:border-box;overflow-y:auto;}
.sidebar.open{left:0;}
.sidebar-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
.sidebar-title{font-size:1rem;font-weight:600;color:#ececec;}
.sidebar-close{background:transparent;border:none;color:#7a7a7a;font-size:1.2rem;cursor:pointer;}
.sidebar-close:hover{color:#fff;}
.sidebar-user{display:flex;flex-direction:column;gap:2px;padding:12px;background:#1a1a1a;border-radius:12px;margin-bottom:16px;cursor:pointer;border:1px solid #2a2a2a;}
.sidebar-user:hover{border-color:#4f8dff;}
.sidebar-user-name{font-size:0.9rem;color:#ececec;font-weight:600;}
.sidebar-user-email{font-size:0.75rem;color:#7a7a7a;}
.new-chat-btn{width:100%;padding:10px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;cursor:pointer;margin-bottom:12px;font-family:'Space Grotesk',sans-serif;text-align:left;}
.new-chat-btn:hover{border-color:#4f8dff;}
.chat-list{display:flex;flex-direction:column;gap:4px;flex:1;overflow-y:auto;}
.chat-item{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-radius:10px;cursor:pointer;font-size:0.85rem;color:#bdbdbd;transition:background 0.15s;}
.chat-item:hover{background:#1a1a1a;}
.chat-item.active{background:#1a1a1a;color:#fff;border:1px solid #2a2a2a;}
.chat-item-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.chat-item-del{background:transparent;border:none;color:#7a7a7a;font-size:0.8rem;cursor:pointer;padding:2px 6px;border-radius:6px;}
.chat-item-del:hover{color:#ef4444;background:rgba(239,68,68,0.1);}
.settings-overlay{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.6);z-index:1000002;display:none;align-items:center;justify-content:center;}
.settings-overlay.open{display:flex;}
.settings-panel{background:#111;border:1px solid #2a2a2a;border-radius:16px;width:90%;max-width:420px;max-height:80vh;overflow-y:auto;padding:20px;position:relative;}
.settings-close{position:absolute;top:12px;right:12px;background:transparent;border:none;color:#7a7a7a;font-size:1.2rem;cursor:pointer;}
.settings-close:hover{color:#fff;}
.settings-tabs{display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap;}
.settings-tab{padding:8px 14px;border-radius:10px;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:0.8rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;}
.settings-tab.active{background:#4f8dff;color:#fff;border-color:#4f8dff;}
.settings-section{display:flex;flex-direction:column;gap:10px;}
.settings-row{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:#1a1a1a;border-radius:10px;font-size:0.9rem;color:#ececec;}
.settings-row-desc{font-size:0.75rem;color:#7a7a7a;margin-top:2px;}
.settings-btn-action{padding:8px 16px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.85rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;}
.settings-btn-action:hover{border-color:#4f8dff;}
.settings-btn-danger{padding:8px 16px;border-radius:10px;border:1px solid #7f1d1d;background:#1a1a1a;color:#ef4444;font-size:0.85rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;}
.settings-btn-danger:hover{background:#7f1d1d;color:#fff;}
.settings-radio{display:flex;flex-direction:column;gap:6px;}
.settings-radio label{display:flex;align-items:center;gap:8px;padding:10px 12px;background:#1a1a1a;border-radius:10px;cursor:pointer;font-size:0.85rem;color:#bdbdbd;border:1px solid transparent;}
.settings-radio label.selected{border-color:#4f8dff;color:#fff;}
.settings-radio input{accent-color:#4f8dff;}
.popup-overlay{position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.7);z-index:1000003;display:none;align-items:center;justify-content:center;}
.popup-overlay.open{display:flex;}
.popup-box{background:#111;border:1px solid #2a2a2a;border-radius:16px;padding:24px;width:90%;max-width:340px;text-align:center;}
.popup-title{font-size:1rem;font-weight:600;color:#ececec;margin-bottom:8px;}
.popup-msg{font-size:0.85rem;color:#7a7a7a;margin-bottom:16px;}
.popup-actions{display:flex;gap:8px;justify-content:center;}
.popup-btn{padding:8px 20px;border-radius:10px;border:none;font-size:0.85rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;}
.popup-btn-cancel{background:#1a1a1a;color:#bdbdbd;border:1px solid #2a2a2a;}
.popup-btn-cancel:hover{color:#fff;border-color:#4f8dff;}
.popup-btn-confirm{background:#ef4444;color:#fff;}
.popup-btn-confirm:hover{background:#dc2626;}
.login-input{width:100%;padding:10px 14px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#fff;font-size:0.9rem;font-family:'Space Grotesk',sans-serif;margin-bottom:12px;box-sizing:border-box;}
.login-input:focus{outline:none;border-color:#4f8dff;}
.about-text{font-size:0.85rem;color:#bdbdbd;line-height:1.6;}
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
</style>
"""

st.html(CSS)

LANG_LABELS = {"en": "English", "ru": "Russian", "uk": "Ukrainian"}

top_col1, top_col2, top_col3 = st.columns([1, 3, 1])
with top_col1:
    if st.button(SIDEBAR_GLYPH, key="sidebar_toggle_btn"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()
with top_col2:
    st.html("<div class='brand' style='text-align:center'>STRAFE AI</div>")
with top_col3:
    if st.button(SETTINGS_GLYPH, key="settings_toggle_btn"):
        st.session_state.settings_open = not st.session_state.settings_open
        st.rerun()

if st.session_state.sidebar_open:
    st.html('<div class="sidebar-overlay open"></div>')
else:
    st.html('<div class="sidebar-overlay"></div>')

sidebar_class = "sidebar open" if st.session_state.sidebar_open else "sidebar"
user_name = "Guest" if not st.session_state.logged_in else st.session_state.user_email.split("@")[0]
user_email_display = st.session_state.user_email if st.session_state.logged_in else "@no_email.gmail.com"

sidebar_html = f'<div class="{sidebar_class}"><div class="sidebar-header"><span class="sidebar-title">Chats</span><button class="sidebar-close" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"close_sidebar\\",value:true}},\\"*\\")">{CLOSE_GLYPH}</button></div>'
sidebar_html += f'<div class="sidebar-user" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"login_click\\",value:true}},\\"*\\")"><span class="sidebar-user-name">{H.escape(user_name)}</span><span class="sidebar-user-email">{H.escape(user_email_display)}</span></div>'
sidebar_html += '<button class="new-chat-btn" onclick="window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"new_chat\\",value:true},\\"*\\')">+ New Chat</button>'
sidebar_html += '<div class="chat-list">'
for cid, cdata in sorted(st.session_state.chats.items(), key=lambda x: x[1].get("created", ""), reverse=True):
    active = " active" if cid == st.session_state.current_chat_id else ""
    cname = H.escape(cdata.get("name", "New Chat"))
    sidebar_html += f'<div class="chat-item{active}" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"switch_chat\\",value:\\"{cid}\\"}},\\"*\\")"><span class="chat-item-name">{cname}</span><button class="chat-item-del" onclick="event.stopPropagation();window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"delete_chat\\",value:\\"{cid}\\"}},\\"*\\")">{CLOSE_GLYPH}</button></div>'
sidebar_html += '</div></div>'
st.html(sidebar_html)

if st.session_state.settings_open:
    tab = st.session_state.settings_tab
    tabs_html = '<div class="settings-overlay open"><div class="settings-panel"><button class="settings-close" onclick="window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"close_settings\\",value:true},\\"*\\")">' + CLOSE_GLYPH + '</button>'
    tabs_html += '<div class="settings-tabs">'
    for t_key, t_label in [("account", "Account"), ("language", "Language"), ("models", "Models/Operators"), ("about", "About")]:
        active_cls = " active" if tab == t_key else ""
        tabs_html += f'<button class="settings-tab{active_cls}" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"settings_tab\\",value:\\"{t_key}\\"}},\\"*\\")">{t_label}</button>'
    tabs_html += '</div><div class="settings-section">'
    
    if tab == "account":
        if st.session_state.logged_in:
            tabs_html += f'<div class="settings-row"><span>{H.escape(st.session_state.user_email)}</span></div>'
            tabs_html += '<button class="settings-btn-action" onclick="window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"logout\\",value:true},\\"*\\")">Log Out</button>'
        else:
            tabs_html += '<div class="settings-row"><span>Not logged in</span></div>'
        tabs_html += '<button class="settings-btn-danger" onclick="window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"delete_all_chats\\",value:true},\\"*\\")">Delete All Chats</button>'
    elif tab == "language":
        tabs_html += '<div class="settings-radio">'
        for lang_code, lang_name in LANG_LABELS.items():
            sel = " selected" if st.session_state.language == lang_code else ""
            chk = "checked" if st.session_state.language == lang_code else ""
            tabs_html += f'<label class="{sel.strip()}"><input type="radio" name="lang" {chk} onchange="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"set_lang\\",value:\\"{lang_code}\\"}},\\"*\\")"/> {lang_name}</label>'
        tabs_html += '</div>'
    elif tab == "models":
        groq_sel = " selected" if st.session_state.operator == "groq" else ""
        cel_sel = " selected" if st.session_state.operator == "celeris" else ""
        tabs_html += '<div class="settings-radio">'
        tabs_html += f'<label class="{groq_sel.strip()}"><input type="radio" name="op" {"checked" if st.session_state.operator=="groq" else ""} onchange="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"set_operator\\",value:\\"groq\\"}},\\"*\\")"/> Groq<div class="settings-row-desc">Strong coding/math skills. Known for fast responses.</div></label>'
        tabs_html += f'<label class="{cel_sel.strip()}"><input type="radio" name="op" {"checked" if st.session_state.operator=="celeris" else ""} onchange="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"set_operator\\",value:\\"celeris\\"}},\\"*\\")"/> Celeris<div class="settings-row-desc">Considered the fastest model, outruns Groq. Skills currently unknown.</div></label>'
        tabs_html += '</div>'
    elif tab == "about":
        tabs_html += '<div class="about-text">Strafe is a project made for your use. No data can be seen by anyone, even by the owner.</div>'
    
    tabs_html += '</div></div></div>'
    st.html(tabs_html)
else:
    st.html('<div class="settings-overlay"></div>')

if st.session_state.delete_confirm:
    dc_id = st.session_state.delete_confirm
    dc_name = H.escape(st.session_state.chats.get(dc_id, {}).get("name", "this chat"))
    popup_html = f'<div class="popup-overlay open"><div class="popup-box"><div class="popup-title">Delete Chat?</div><div class="popup-msg">Are you sure you want to delete "{dc_name}"? This cannot be undone.</div><div class="popup-actions"><button class="popup-btn popup-btn-cancel" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"cancel_delete\\",value:true}},\\"*\\")">Cancel</button><button class="popup-btn popup-btn-confirm" onclick="window.parent.postMessage({{type:\\"streamlit:setComponentValue\\",key:\\"confirm_delete\\",value:\\"{dc_id}\\"}},\\"*\\")">Delete</button></div></div></div>'
    st.html(popup_html)
else:
    st.html('<div class="popup-overlay"></div>')

if st.session_state.login_popup:
    login_html = '<div class="popup-overlay open"><div class="popup-box"><div class="popup-title">Login</div><div class="popup-msg">Enter your email to save chats and settings.</div><form onsubmit="event.preventDefault();window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"do_login\\",value:this.email.value},\\"*\\")"><input class="login-input" name="email" type="email" placeholder="you@example.com" required/><div class="popup-actions"><button type="button" class="popup-btn popup-btn-cancel" onclick="window.parent.postMessage({type:\\"streamlit:setComponentValue\\",key:\\"cancel_login\\",value:true},\\"*\\")">Cancel</button><button type="submit" class="popup-btn popup-btn-confirm" style="background:#4f8dff">Login</button></div></form></div></div>'
    st.html(login_html)

KEYS = [st.secrets.get(f"GROQ_API_KEY_{i}") for i in range(1, 7)]
KEYS = [k for k in KEYS if k]
if not KEYS:
    st.error("No GROQ_API_KEY_1..6 found in secrets. Add at least one.")
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
        if not results:
            return [{"title": "No results", "link": "", "snippet": "Search returned empty. Tell the user."}]
        return results
    except DDGSException:
        return [{"title": "Rate Limited", "link": "", "snippet": "Rate limit reached. Tell the user."}]
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}. Tell the user."}]

def msg_to_api(m, distance_from_latest=None, full_res=False):
    imgs = m.get("images") or []
    files = m.get("files") or []
    if not imgs and not files:
        return {"role": m["role"], "content": m["content"]}
    parts = [{"type": "text", "text": m["content"]}]
    for f in files:
        parts.insert(0, {"type": "text", "text": f"[Attached file: {f.get('name','file')}]\n```\n{f.get('content','')}\n```"})
    if imgs:
        if distance_from_latest is not None and not full_res:
            if distance_from_latest >= 15:
                pass
            elif distance_from_latest >= 3:
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
    tried = set()
    last_err = None
    while len(tried) < len(KEYS):
        key = get_working_key()
        if key in tried:
            continue
        tried.add(key)
        try:
            return Groq(api_key=key).chat.completions.create(**kwargs), None
        except NotFoundError:
            st.session_state.pop("model", None)
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

def ask(use_search=False, use_think=False, look_back=False, clearer_image_back=False):
    t0 = time.time()
    current_msgs = get_current_chat()["messages"]
    if look_back or clearer_image_back:
        slice_msgs = current_msgs
    else:
        slice_msgs = current_msgs[-HISTORY_LIMIT:]
    total = len(slice_msgs)
    history = []
    for idx, m in enumerate(slice_msgs):
        distance = total - 1 - idx
        history.append(msg_to_api(m, distance_from_latest=distance, full_res=clearer_image_back))
    tools = None
    if use_search:
        tools = [{"type": "function", "function": {"name": "web_search", "description": "Search the web for current info. DO NOT fake the search. If search returns 'No results', tell the user.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Clean keywords ONLY. Fix spelling."}}, "required": ["query"]}}}]
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
            assistant_msg = {"role": "assistant", "content": msg.content or "", "tool_calls": []}
            for tc in msg.tool_calls:
                assistant_msg["tool_calls"].append({"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}})
            history.append(assistant_msg)
            for tc in msg.tool_calls:
                if tc.function.name == "web_search":
                    args = json.loads(tc.function.arguments)
                    results = web_search(args.get("query", ""))
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
    raise RuntimeError(last_err or "All API keys failed")

def info_html(m):
    sent = m.get("sent", "?")
    secs = m.get("secs", "?")
    tps = m.get("tok", "?")
    flags = []
    if m.get("search"): flags.append("\u2315")
    if m.get("think"): flags.append("\u269b")
    flag_str = " ".join(flags) + " " if flags else ""
    return f'<div class="info-line">{flag_str}sent <span>{sent}</span> &nbsp;\u00b7&nbsp; {secs}s &nbsp;\u00b7&nbsp; {tps}</div>'

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0:
        chat = get_current_chat()
        msgs = chat["messages"]
        if i - 1 < len(msgs) and msgs[i - 1]["role"] == "user":
            prev_msg = msgs[i - 1]
            chat["messages"] = msgs[:i]
            save_current_chat(chat["messages"])
            try:
                result = ask(use_search=prev_msg.get("search", False), use_think=prev_msg.get("think", False))
                chat["messages"].append({"role": "assistant", **result})
                save_current_chat(chat["messages"])
            except Exception as e:
                chat["messages"].append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": False, "think": False, "reasoning": None})
                save_current_chat(chat["messages"])
    elif kind == "edit":
        st.session_state["editing"] = i
    elif kind == "close":
        pass

pending = st.session_state.pop("pending", None)
if pending is not None:
    text = pending.get("text", "") if isinstance(pending, dict) else pending
    use_search = pending.get("search", False) if isinstance(pending, dict) else False
    use_think = pending.get("think", False) if isinstance(pending, dict) else False
    images = pending.get("images", []) if isinstance(pending, dict) else []
    files = pending.get("files", []) if isinstance(pending, dict) else []
    raw = text.strip().lower()
    is_look_back = raw == "look_back"
    is_clearer = raw == "clearer_image_back"
    chat = get_current_chat()
    chat["messages"].append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "images": images, "files": files})
    save_current_chat(chat["messages"])
    try:
        result = ask(use_search=use_search, use_think=use_think, look_back=is_look_back, clearer_image_back=is_clearer)
        chat["messages"].append({"role": "assistant", **result})
        save_current_chat(chat["messages"])
    except Exception as e:
        chat["messages"].append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": None})
        save_current_chat(chat["messages"])
    st.session_state["editing"] = None
    st.rerun()

editing = st.session_state.get("editing")
current_msgs = get_current_chat()["messages"]

for i, m in enumerate(current_msgs):
    if m["role"] == "user":
        if editing == i:
            new = st.text_area("Edit", value=m["content"], key=f"ed{i}", height=100)
            sc, sk = st.columns([1, 6])
            with sc:
                if st.button("Save", key=f"sv{i}"):
                    chat = get_current_chat()
                    chat["messages"] = chat["messages"][:i]
                    save_current_chat(chat["messages"])
                    st.session_state["pending"] = {"text": new, "search": m.get("search", False), "think": m.get("think", False), "images": m.get("images", []), "files": m.get("files", [])}
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
        st.toast("Unsupported file type. Text/code files only.")
    elif ma == "file_too_large":
        st.toast("File too large. Max 500KB.")
    else:
        st.toast(f"{ma} selected")

qp = st.query_params
for key in ["close_sidebar", "new_chat", "switch_chat", "delete_chat", "close_settings", "settings_tab", "set_lang", "set_operator", "logout", "delete_all_chats", "cancel_delete", "confirm_delete", "login_click", "do_login", "cancel_login"]:
    val = qp.get(key)
    if val:
        if key == "close_sidebar":
            st.session_state.sidebar_open = False
        elif key == "new_chat":
            cid = str(uuid.uuid4())[:8]
            st.session_state.chats[cid] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
            st.session_state.current_chat_id = cid
            st.session_state.sidebar_open = False
        elif key == "switch_chat":
            if val in st.session_state.chats:
                st.session_state.current_chat_id = val
                st.session_state.sidebar_open = False
        elif key == "delete_chat":
            st.session_state.delete_confirm = val
        elif key == "close_settings":
            st.session_state.settings_open = False
        elif key == "settings_tab":
            st.session_state.settings_tab = val
        elif key == "set_lang":
            st.session_state.language = val
        elif key == "set_operator":
            st.session_state.operator = val
        elif key == "logout":
            st.session_state.logged_in = False
            st.session_state.user_email = ""
        elif key == "delete_all_chats":
            cid = str(uuid.uuid4())[:8]
            st.session_state.chats = {cid: {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}}
            st.session_state.current_chat_id = cid
            st.session_state.settings_open = False
        elif key == "cancel_delete":
            st.session_state.delete_confirm = None
        elif key == "confirm_delete":
            if val in st.session_state.chats:
                del st.session_state.chats[val]
                if not st.session_state.chats:
                    nc = str(uuid.uuid4())[:8]
                    st.session_state.chats[nc] = {"name": "New Chat", "messages": [], "created": datetime.now().isoformat()}
                    st.session_state.current_chat_id = nc
                elif st.session_state.current_chat_id == val:
                    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
            st.session_state.delete_confirm = None
        elif key == "login_click":
            st.session_state.login_popup = True
            st.session_state.sidebar_open = False
        elif key == "do_login":
            if val and "@" in val:
                st.session_state.user_email = val
                st.session_state.logged_in = True
            st.session_state.login_popup = False
        elif key == "cancel_login":
            st.session_state.login_popup = False
        st.query_params.clear()
        st.rerun()