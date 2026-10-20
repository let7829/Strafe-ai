import streamlit as st
import streamlit.components.v1 as components
from groq import Groq, NotFoundError
import random, time, html as H, json
from datetime import datetime
from ddgs import DDGS
from ddgs.exceptions import DDGSException

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\uff0b"
HAMBURGER_GLYPH = "\uff1d"
SETTINGS_GLYPH = "\u2699"

INPUT_HTML = '''
<div id="bar">
    <div id="atts"></div>
    <div id="cb">
        <input id="ci" type="text" placeholder="Ask something" autocomplete="off"/>
        <button id="pb" type="button" class="icon-btn">''' + PLUS_GLYPH + '''</button>
        <button id="sb" type="button">''' + SEND_GLYPH + '''</button>
    </div>
    <div id="tools">
        <button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button>
        <button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button>
    </div>
    <div id="menu">
        <button id="mb-photo" type="button" class="menu-btn">Photo</button>
        <button id="mb-camera" type="button" class="menu-btn">Camera</button>
        <button id="mb-file" type="button" class="menu-btn">\u2399 File</button>
    </div>
</div>

<div id="cam-overlay">
    <video id="cam-video" autoplay playsinline muted></video>
    <button id="cam-close" type="button">''' + CLOSE_GLYPH + '''</button>
    <button id="cam-capture" type="button"></button>
    <canvas id="cam-canvas" style="display:none"></canvas>
</div>

<button id="side-menu-btn" type="button">''' + HAMBURGER_GLYPH + '''</button>
<button id="settings-btn" type="button">''' + SETTINGS_GLYPH + '''</button>

<div id="side-menu">
    <div id="sm-header">
        <div id="sm-user">
            <span id="sm-user-name">Guest</span>
            <span id="sm-user-email">@no_email.gmail.com</span>
        </div>
        <button id="sm-close" type="button">''' + CLOSE_GLYPH + '''</button>
    </div>
    <button id="sm-new-chat" type="button">New Chat</button>
    <div id="sm-chats"></div>
</div>

<div id="settings-overlay">
    <div id="settings-box">
        <div id="settings-header">
            <span>Settings</span>
            <button id="settings-close" type="button">''' + CLOSE_GLYPH + '''</button>
        </div>
        <div id="settings-tabs">
            <button class="s-tab active" data-tab="account">Account</button>
            <button class="s-tab" data-tab="language">Language</button>
            <button class="s-tab" data-tab="models">Models</button>
            <button class="s-tab" data-tab="about">About</button>
        </div>
        <div id="settings-content">
            <div class="s-panel active" data-panel="account">
                <button id="set-logout" class="danger-btn">Log Out</button>
                <button id="set-delete-all" class="danger-btn">Delete All Chats</button>
            </div>
            <div class="s-panel" data-panel="language">
                <label class="radio-opt"><input type="radio" name="lang" value="en" checked><span>English</span></label>
                <label class="radio-opt"><input type="radio" name="lang" value="ru"><span>Russian</span></label>
                <label class="radio-opt"><input type="radio" name="lang" value="uk"><span>Ukrainian</span></label>
            </div>
            <div class="s-panel" data-panel="models">
                <div class="model-card">
                    <label class="radio-opt"><input type="radio" name="provider" value="groq" checked><span>Groq</span></label>
                    <p class="desc">Groq has strong coding/math skills. Also known for fast responses.</p>
                </div>
                <div class="model-card">
                    <label class="radio-opt"><input type="radio" name="provider" value="celeris"><span>Celeris</span></label>
                    <p class="desc">Celeris is considered to be fastest model, outrun Groq. The skills are currently unknown.</p>
                </div>
            </div>
            <div class="s-panel" data-panel="about">
                <p class="about-text">Strafe is a project made for your use. No data can be seen by anyone, even by the owner.</p>
            </div>
        </div>
    </div>
</div>

<div id="confirm-overlay">
    <div id="confirm-box">
        <p id="confirm-msg"></p>
        <div class="confirm-actions">
            <button id="cfm-yes">Yes</button>
            <button id="cfm-no">No</button>
        </div>
    </div>
</div>

<div id="login-overlay">
    <div id="login-box">
        <h3>Login</h3>
        <input id="login-email" type="email" placeholder="Enter your email" />
        <button id="login-submit">Continue</button>
        <button id="login-cancel" class="ghost-btn">Cancel</button>
    </div>
</div>
'''

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
#side-menu-btn{position:fixed;top:16px;left:16px;width:40px;height:40px;border-radius:50%;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:999998;transition:all 0.2s;}
#side-menu-btn:hover{color:#fff;border-color:#4f8dff;}
#settings-btn{position:fixed;bottom:16px;right:16px;width:40px;height:40px;border-radius:50%;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:999998;transition:all 0.2s;}
#settings-btn:hover{color:#fff;border-color:#4f8dff;}
#side-menu{position:fixed;top:0;left:-300px;width:300px;height:100vh;background:#0a0a0a;border-right:1px solid #2a2a2a;z-index:9999999;display:flex;flex-direction:column;transition:left 0.3s ease;padding:16px;box-sizing:border-box;}
#side-menu.open{left:0;}
#sm-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}
#sm-user{display:flex;flex-direction:column;gap:4px;}
#sm-user-name{color:#fff;font-size:1.1rem;font-weight:600;font-family:'Space Grotesk',sans-serif;}
#sm-user-email{color:#7a7a7a;font-size:0.8rem;font-family:'Space Grotesk',sans-serif;cursor:pointer;}
#sm-user-email:hover{color:#4f8dff;}
#sm-close{width:32px;height:32px;border-radius:50%;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;}
#sm-close:hover{color:#fff;border-color:#4f8dff;}
#sm-new-chat{width:100%;height:44px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.95rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;margin-bottom:16px;transition:all 0.2s;}
#sm-new-chat:hover{border-color:#4f8dff;color:#fff;}
#sm-chats{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:8px;}
.sm-chat{display:flex;align-items:center;gap:8px;padding:12px;border-radius:10px;background:#1a1a1a;cursor:pointer;transition:all 0.2s;}
.sm-chat:hover{background:#2a2a2a;}
.sm-chat.active{background:#2563eb33;border:1px solid #4f8dff;}
.sm-chat-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#ececec;font-size:0.9rem;font-family:'Space Grotesk',sans-serif;}
.sm-chat-del{width:24px;height:24px;border-radius:50%;border:none;background:transparent;color:#7a7a7a;font-size:0.8rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.sm-chat-del:hover{color:#ef4444;background:rgba(239,68,68,0.1);}
#settings-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.8);z-index:9999999;align-items:center;justify-content:center;}
#settings-overlay.active{display:flex;}
#settings-box{width:90%;max-width:500px;background:#0a0a0a;border:1px solid #2a2a2a;border-radius:16px;overflow:hidden;display:flex;flex-direction:column;max-height:80vh;}
#settings-header{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #2a2a2a;}
#settings-header span{color:#fff;font-size:1.2rem;font-weight:600;font-family:'Space Grotesk',sans-serif;}
#settings-close{width:32px;height:32px;border-radius:50%;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;}
#settings-close:hover{color:#fff;border-color:#4f8dff;}
#settings-tabs{display:flex;gap:4px;padding:12px 20px;border-bottom:1px solid #2a2a2a;overflow-x:auto;}
.s-tab{padding:8px 16px;border-radius:8px;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:0.85rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;white-space:nowrap;transition:all 0.2s;}
.s-tab:hover{color:#fff;border-color:#4f8dff;}
.s-tab.active{background:#4f8dff;color:#fff;border-color:#4f8dff;}
#settings-content{padding:20px;overflow-y:auto;flex:1;}
.s-panel{display:none;}
.s-panel.active{display:flex;flex-direction:column;gap:12px;}
.danger-btn{width:100%;height:44px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.95rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
.danger-btn:hover{border-color:#ef4444;color:#ef4444;background:#1a0505;}
.radio-opt{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;background:#1a1a1a;cursor:pointer;transition:all 0.2s;}
.radio-opt:hover{background:#2a2a2a;}
.radio-opt input[type="radio"]{width:18px;height:18px;cursor:pointer;}
.radio-opt span{color:#ececec;font-size:0.95rem;font-family:'Space Grotesk',sans-serif;}
.model-card{display:flex;flex-direction:column;gap:8px;}
.desc{color:#7a7a7a;font-size:0.8rem;font-family:'Space Grotesk',sans-serif;margin:0;padding-left:28px;}
.about-text{color:#bdbdbd;font-size:0.9rem;line-height:1.6;font-family:'Space Grotesk',sans-serif;margin:0;}
#confirm-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.85);z-index:10000002;align-items:center;justify-content:center;}
#confirm-overlay.active{display:flex;}
#confirm-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:24px;max-width:320px;display:flex;flex-direction:column;gap:16px;}
#confirm-msg{color:#ececec;font-size:1rem;font-family:'Space Grotesk',sans-serif;margin:0;text-align:center;}
.confirm-actions{display:flex;gap:12px;}
.confirm-actions button{flex:1;height:40px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
#cfm-yes:hover{background:#ef4444;border-color:#ef4444;color:#fff;}
#cfm-no:hover{border-color:#4f8dff;color:#fff;}
#login-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.85);z-index:10000002;align-items:center;justify-content:center;}
#login-overlay.active{display:flex;}
#login-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:24px;max-width:320px;display:flex;flex-direction:column;gap:12px;}
#login-box h3{color:#fff;margin:0 0 8px 0;font-family:'Space Grotesk',sans-serif;}
#login-email{width:100%;height:44px;border-radius:10px;border:1px solid #2a2a2a;background:#0a0a0a;color:#fff;font-size:0.95rem;padding:0 14px;box-sizing:border-box;font-family:'Space Grotesk',sans-serif;}
#login-email:focus{outline:none;border-color:#4f8dff;}
#login-box button{width:100%;height:40px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
#login-submit:hover{background:#4f8dff;border-color:#4f8dff;color:#fff;}
.ghost-btn:hover{border-color:#7a7a7a;color:#fff;}
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
    const sideMenuBtn=parentElement.querySelector('#side-menu-btn');
    const sideMenu=parentElement.querySelector('#side-menu');
    const smClose=parentElement.querySelector('#sm-close');
    const smNewChat=parentElement.querySelector('#sm-new-chat');
    const smChats=parentElement.querySelector('#sm-chats');
    const smUserEmail=parentElement.querySelector('#sm-user-email');
    const smUserName=parentElement.querySelector('#sm-user-name');
    const settingsBtn=parentElement.querySelector('#settings-btn');
    const settingsOverlay=parentElement.querySelector('#settings-overlay');
    const settingsClose=parentElement.querySelector('#settings-close');
    const sTabs=parentElement.querySelectorAll('.s-tab');
    const sPanels=parentElement.querySelectorAll('.s-panel');
    const setLogout=parentElement.querySelector('#set-logout');
    const setDeleteAll=parentElement.querySelector('#set-delete-all');
    const confirmOverlay=parentElement.querySelector('#confirm-overlay');
    const confirmMsg=parentElement.querySelector('#confirm-msg');
    const cfmYes=parentElement.querySelector('#cfm-yes');
    const cfmNo=parentElement.querySelector('#cfm-no');
    const loginOverlay=parentElement.querySelector('#login-overlay');
    const loginEmail=parentElement.querySelector('#login-email');
    const loginSubmit=parentElement.querySelector('#login-submit');
    const loginCancel=parentElement.querySelector('#login-cancel');

    if(!input||!btn)return;

    let searchActive=false;
    let thinkActive=false;
    let attachments=[];
    let fileAttachments=[];
    let camStream=null;
    let chats=JSON.parse(localStorage.getItem('strafe_chats')||'[]');
    let currentChatId=localStorage.getItem('strafe_current_chat')||null;
    let userEmail=localStorage.getItem('strafe_user_email')||'';
    let settings={
        lang:localStorage.getItem('strafe_lang')||'en',
        provider:localStorage.getItem('strafe_provider')||'groq'
    };

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

    function saveState(){
        localStorage.setItem('strafe_chats',JSON.stringify(chats));
        localStorage.setItem('strafe_current_chat',currentChatId||'');
    }

    function renderChatList(){
        smChats.innerHTML='';
        chats.forEach(chat=>{
            const div=document.createElement('div');
            div.className='sm-chat'+(chat.id===currentChatId?' active':'');
            
            const name=document.createElement('span');
            name.className='sm-chat-name';
            name.textContent=chat.name;
            
            const del=document.createElement('button');
            del.type='button';
            del.className='sm-chat-del';
            del.textContent='\\u2715';
            del.onclick=(ev)=>{
                ev.stopPropagation();
                showConfirm('Are you sure you want to delete this chat?',()=>{
                    chats=chats.filter(c=>c.id!==chat.id);
                    if(currentChatId===chat.id)currentChatId=null;
                    saveState();
                    renderChatList();
                    setTriggerValue('chat_action',{action:'delete',id:chat.id});
                });
            };
            
            div.onclick=()=>{
                currentChatId=chat.id;
                saveState();
                renderChatList();
                setTriggerValue('chat_action',{action:'load',id:chat.id});
                closeSideMenu();
            };
            
            div.appendChild(name);
            div.appendChild(del);
            smChats.appendChild(div);
        });
    }

    function updateUserDisplay(){
        if(userEmail){
            smUserName.textContent=userEmail.split('@')[0];
            smUserEmail.textContent=userEmail;
        }else{
            smUserName.textContent='Guest';
            smUserEmail.textContent='@no_email.gmail.com';
        }
    }

    function showConfirm(msg,onYes){
        confirmMsg.textContent=msg;
        confirmOverlay.classList.add('active');
        cfmYes.onclick=()=>{
            confirmOverlay.classList.remove('active');
            onYes();
        };
        cfmNo.onclick=()=>confirmOverlay.classList.remove('active');
    }

    function closeSideMenu(){sideMenu.classList.remove('open');}

    function resizeImage(dataUrl,maxSize){
        return new Promise(resolve=>{
            const img=new Image();
            img.onload=()=>{
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
        attachments.forEach((item,idx)=>{
            const wrap=document.createElement('div');
            wrap.className='att';
            const img=document.createElement('img');
            img.src=item;
            const x=document.createElement('button');
            x.type='button';
            x.className='att-x';
            x.textContent='\\u2715';
            x.onclick=(ev)=>{ev.stopPropagation();attachments.splice(idx,1);renderAtts();};
            wrap.appendChild(img);
            wrap.appendChild(x);
            atts.appendChild(wrap);
        });
        fileAttachments.forEach((item,idx)=>{
            const wrap=document.createElement('div');
            wrap.className='att-file';
            const name=document.createElement('span');
            name.className='att-file-name';
            name.textContent='\\u2399 '+item.name;
            const x=document.createElement('button');
            x.type='button';
            x.className='att-file-x';
            x.textContent='\\u2715';
            x.onclick=(ev)=>{ev.stopPropagation();fileAttachments.splice(idx,1);renderAtts();};
            wrap.appendChild(name);
            wrap.appendChild(x);
            atts.appendChild(wrap);
        });
    }

    function stopCamera(){
        if(camStream){camStream.getTracks().forEach(t=>t.stop());camStream=null;}
        camOverlay.classList.remove('active');
    }

    async function openCamera(){
        try{
            camStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});
            camVideo.srcObject=camStream;
            camOverlay.classList.add('active');
            menu.classList.remove('open');
        }catch(e){setTriggerValue('menu_action','camera_error');}
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

    function updateLabels(){
        btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';
        btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';
    }

    async function send(){
        const val=input.value.trim();
        if(!val&&!attachments.length&&!fileAttachments.length)return;
        const resized=[];
        for(let i=0;i<attachments.length;i++)resized.push(await resizeImage(attachments[i],1024));
        setTriggerValue('submitted',{
            text:val,
            search:searchActive,
            think:thinkActive,
            images:resized,
            files:fileAttachments.slice(),
            chatId:currentChatId
        });
        input.value='';
        attachments=[];
        fileAttachments=[];
        renderAtts();
    }

    btn.onclick=send;
    input.onkeydown=e=>{if(e.key==='Enter')send();};
    
    if(plusBtn&&menu)plusBtn.onclick=()=>menu.classList.toggle('open');
    if(photoBtn)photoBtn.onclick=()=>{menu.classList.remove('open');imageInput.click();};
    if(cameraBtn)cameraBtn.onclick=openCamera;
    if(fileBtn)fileBtn.onclick=()=>{menu.classList.remove('open');fileInput.click();};
    if(camClose)camClose.onclick=stopCamera;
    if(camCapture)camCapture.onclick=capturePhoto;

    imageInput.onchange=()=>{
        const f=imageInput.files[0];
        if(!f)return;
        const reader=new FileReader();
        reader.onload=()=>{attachments.push(reader.result);renderAtts();};
        reader.readAsDataURL(f);
        imageInput.value='';
    };

    fileInput.onchange=()=>{
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
        reader.onload=()=>{fileAttachments.push({name:f.name,content:reader.result});renderAtts();};
        reader.readAsText(f);
        fileInput.value='';
    };

    btnSearch.onclick=function(){searchActive=!searchActive;this.classList.toggle('active',searchActive);updateLabels();};
    btnThink.onclick=function(){thinkActive=!thinkActive;this.classList.toggle('active',thinkActive);updateLabels();};
    
    sideMenuBtn.onclick=()=>{sideMenu.classList.toggle('open');renderChatList();};
    smClose.onclick=closeSideMenu;
    
    smNewChat.onclick=()=>{
        const id='chat_'+Date.now();
        chats.unshift({id:id,name:'New Chat',messages:[]});
        currentChatId=id;
        saveState();
        renderChatList();
        setTriggerValue('chat_action',{action:'new',id:id});
        closeSideMenu();
    };

    smUserEmail.onclick=()=>{
        if(!userEmail){
            loginOverlay.classList.add('active');
            loginEmail.value='';
            loginEmail.focus();
        }
    };

    settingsBtn.onclick=()=>{
        settingsOverlay.classList.add('active');
        parentElement.querySelectorAll('input[name="lang"]').forEach(r=>r.checked=r.value===settings.lang);
        parentElement.querySelectorAll('input[name="provider"]').forEach(r=>r.checked=r.value===settings.provider);
    };
    
    settingsClose.onclick=()=>settingsOverlay.classList.remove('active');
    
    sTabs.forEach(tab=>{
        tab.onclick=()=>{
            sTabs.forEach(t=>t.classList.remove('active'));
            sPanels.forEach(p=>p.classList.remove('active'));
            tab.classList.add('active');
            parentElement.querySelector(`.s-panel[data-panel="${tab.dataset.tab}"]`).classList.add('active');
        };
    });

    setLogout.onclick=()=>showConfirm('Log out?',()=>{
        userEmail='';
        localStorage.removeItem('strafe_user_email');
        updateUserDisplay();
    });

    setDeleteAll.onclick=()=>showConfirm('Delete all chats?',()=>{
        chats=[];
        currentChatId=null;
        saveState();
        renderChatList();
        setTriggerValue('chat_action',{action:'delete_all'});
    });

    parentElement.querySelectorAll('input[name="lang"]').forEach(radio=>{
        radio.onchange=function(){
            settings.lang=this.value;
            localStorage.setItem('strafe_lang',this.value);
            setTriggerValue('settings_change',{lang:settings.lang,provider:settings.provider});
        };
    });

    parentElement.querySelectorAll('input[name="provider"]').forEach(radio=>{
        radio.onchange=function(){
            settings.provider=this.value;
            localStorage.setItem('strafe_provider',this.value);
            setTriggerValue('settings_change',{lang:settings.lang,provider:settings.provider});
        };
    });

    loginSubmit.onclick=()=>{
        const email=loginEmail.value.trim();
        if(email&&email.includes('@')){
            userEmail=email;
            localStorage.setItem('strafe_user_email',email);
            updateUserDisplay();
            loginOverlay.classList.remove('active');
            setTriggerValue('login',email);
        }
    };
    
    loginCancel.onclick=()=>loginOverlay.classList.remove('active');

    updateUserDisplay();
    renderChatList();
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
    ca = getattr(result, "chat_action", None)
    if ca:
        st.session_state["chat_action"] = ca
    sc = getattr(result, "settings_change", None)
    if sc:
        st.session_state["settings_change"] = sc
    login = getattr(result, "login", None)
    if login:
        st.session_state["login"] = login
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
</style>
"""

st.html(CSS)
st.html("<div class='brand'>STRAFE AI</div>")

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

if "messages" not in st.session_state:
    st.session_state.messages = []

def get_working_key():
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    available = [k for k in KEYS if k not in st.session_state.failed_keys]
    if not available:
        st.session_state.failed_keys.clear()
        available = KEYS
    return random.choice(available)

def mark_key_failed(key):
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    st.session_state.failed_keys.add(key)

def web_search(query, num_results=3):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results, backend="brave,google,duckduckgo"):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        if not results:
            return [{"title": "No results", "link": "", "snippet": "Search returned empty. Tell the user."}]
        return results
    except DDGSException as e:
        return [{"title": "Rate Limited", "link": "", "snippet": "Rate limit reached. Tell the user."}]
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}. Tell the user."}]

def msg_to_api(m, distance_from_latest=None, full_res=False):
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
    if look_back or clearer_image_back:
        slice_msgs = st.session_state.messages
    else:
        slice_msgs = st.session_state.messages[-HISTORY_LIMIT:]
    
    total = len(slice_msgs)
    history = []
    for idx, m in enumerate(slice_msgs):
        distance = total - 1 - idx
        history.append(msg_to_api(m, distance_from_latest=distance, full_res=clearer_image_back))

    tools = None
    if use_search:
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current info. DO NOT fake the search. If search returns 'No results', tell the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Clean keywords ONLY. Fix spelling. (e.g., 'Elon Musk first trillionaire 2026', NOT 'who is the first trillionare')."
                        }
                    },
                    "required": ["query"]
                }
            }
        }]

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
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                })
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
            return {
                "content": content,
                "secs": round(secs, 1),
                "tok": f"{tps} tok/s",
                "sent": datetime.now().strftime("%H:%M"),
                "search": use_search,
                "think": use_think,
                "reasoning": reasoning if use_think else None
            }

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

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0 and st.session_state.messages[i - 1]["role"] == "user":
        prev_msg = st.session_state.messages[i - 1]
        st.session_state.messages = st.session_state.messages[:i]
        try:
            result = ask(use_search=prev_msg.get("search", False), use_think=prev_msg.get("think", False))
            st.session_state.messages.append({"role": "assistant", **result})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": False, "think": False, "reasoning": None})
        st.session_state["show"] = None
    elif kind == "edit":
        st.session_state["editing"] = i
        st.session_state["show"] = None
    elif kind == "close":
        st.session_state["show"] = None

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
    st.session_state.messages.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "images": images, "files": files})
    try:
        result = ask(use_search=use_search, use_think=use_think, look_back=is_look_back, clearer_image_back=is_clearer)
        st.session_state.messages.append({"role": "assistant", **result})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": None})
    st.session_state["editing"] = None
    st.rerun()

ca = st.session_state.pop("chat_action", None)
if ca:
    action = ca.get("action")
    if action == "new":
        st.session_state.messages = []
        st.rerun()
    elif action == "load":
        st.session_state.messages = []
        st.rerun()
    elif action == "delete" or action == "delete_all":
        if action == "delete_all":
            st.session_state.messages = []
        st.rerun()

sc = st.session_state.pop("settings_change", None)
if sc:
    st.toast(f"Settings updated: {sc}")

login = st.session_state.pop("login", None)
if login:
    st.toast(f"Logged in as {login}")

show = st.session_state.get("show")
editing = st.session_state.get("editing")

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        if editing == i:
            new = st.text_area("Edit", value=m["content"], key=f"ed{i}", height=100)
            sc, sk = st.columns([1, 6])
            with sc:
                if st.button("Save", key=f"sv{i}"):
                    st.session_state.messages = st.session_state.messages[:i]
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
        st.toast("Unsupported file type. Use text/code files only.")
    elif ma == "file_too_large":
        st.toast("File too large. Max 500KB for text files.")
    else:
        st.toast(f"{ma} selected")