import streamlit as st
import streamlit.components.v2 as components
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

INPUT_HTML = '<div id="bar"><div id="atts"></div><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="pb" type="button" class="icon-btn">' + PLUS_GLYPH + '</button><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button></div><div id="menu"><button id="mb-photo" type="button" class="menu-btn">Photo</button><button id="mb-camera" type="button" class="menu-btn">Camera</button><button id="mb-file" type="button" class="menu-btn">\u2399 File</button></div></div><div id="cam-overlay"><video id="cam-video" autoplay playsinline muted></video><button id="cam-close" type="button">\u2715</button><button id="cam-capture" type="button"></button><canvas id="cam-canvas" style="display:none"></canvas></div><button id="side-menu-btn" type="button">' + HAMBURGER_GLYPH + '</button><button id="top-user" type="button"><span id="tu-name">Guest</span><span id="tu-email">@no_email.gmail.com</span></button><button id="settings-btn" type="button">' + SETTINGS_GLYPH + '</button><div id="side-menu"><div id="sm-header"><div id="sm-user"><span id="sm-user-name">Guest</span><span id="sm-user-email">@no_email.gmail.com</span></div><button id="sm-close" type="button">\u2715</button></div><button id="sm-new-chat" type="button">New Chat</button><div id="sm-chats"></div></div><div id="settings-overlay"><div id="settings-modal"><div id="settings-header"><span>Settings</span><button id="settings-close" type="button">\u2715</button></div><div id="settings-tabs"><button class="settings-tab active" data-tab="account">Account</button><button class="settings-tab" data-tab="language">Language</button><button class="settings-tab" data-tab="models">Models</button><button class="settings-tab" data-tab="about">About</button></div><div id="settings-content"><div class="settings-panel active" data-panel="account"><button id="settings-logout">Log Out</button><button id="settings-delete-all">Delete All Chats</button></div><div class="settings-panel" data-panel="language"><label class="settings-radio"><input type="radio" name="lang" value="en" checked><span>English</span></label><label class="settings-radio"><input type="radio" name="lang" value="ru"><span>Russian</span></label><label class="settings-radio"><input type="radio" name="lang" value="uk"><span>Ukrainian</span></label></div><div class="settings-panel" data-panel="models"><div class="model-option"><label class="settings-radio"><input type="radio" name="provider" value="groq" checked><span>Groq</span></label><p class="model-desc">Groq has strong coding/math skills. Also known for fast responses.</p></div><div class="model-option"><label class="settings-radio"><input type="radio" name="provider" value="celeris"><span>Celeris</span></label><p class="model-desc">Celeris is considered to be fastest model, outrun Groq. The skills are currently unknown.</p></div></div><div class="settings-panel" data-panel="about"><p>Strafe is a project made for your use. No data can be seen by anyone, even by the owner.</p></div></div></div></div><div id="confirm-overlay"><div id="confirm-box"><p id="confirm-text"></p><div id="confirm-buttons"><button id="confirm-yes">Yes</button><button id="confirm-no">No</button></div></div></div><div id="login-overlay"><div id="login-box"><input id="login-email" type="email" placeholder="Enter your email"><button id="login-submit">Login</button><button id="login-cancel">Cancel</button></div></div>'

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
#top-user{position:fixed;top:20px;left:64px;display:flex;align-items:center;gap:6px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:20px;padding:6px 12px;cursor:pointer;z-index:999998;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;max-width:220px;overflow:hidden;}
#top-user:hover{border-color:#4f8dff;}
#tu-name{color:#ececec;font-size:0.8rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
#tu-email{color:#7a7a7a;font-size:0.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
@media (max-width:560px){#tu-email{display:none;}#top-user{padding:5px 10px;}}
#settings-btn{position:fixed;bottom:16px;right:16px;width:40px;height:40px;border-radius:50%;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:999998;transition:all 0.2s;}
#settings-btn:hover{color:#fff;border-color:#4f8dff;}
#side-menu{position:fixed;top:0;left:-300px;width:300px;height:100vh;background:#0a0a0a;border-right:1px solid #2a2a2a;z-index:9999999;display:flex;flex-direction:column;transition:left 0.3s ease;padding:16px;box-sizing:border-box;}
#side-menu.open{left:0;}
#sm-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}
#sm-user{display:flex;flex-direction:column;gap:4px;overflow:hidden;}
#sm-user-name{color:#fff;font-size:1.1rem;font-weight:600;font-family:'Space Grotesk',sans-serif;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
#sm-user-email{color:#7a7a7a;font-size:0.8rem;font-family:'Space Grotesk',sans-serif;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
#sm-user-email:hover{color:#4f8dff;}
#sm-close{width:32px;height:32px;border-radius:50%;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
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
#settings-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.8);z-index:9999999;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;}
#settings-overlay.active{display:flex;}
#settings-modal{background:#0a0a0a;border:1px solid #2a2a2a;border-radius:16px;width:100%;max-width:520px;max-height:85vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.8);}
#settings-header{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #2a2a2a;flex-shrink:0;}
#settings-header span{color:#fff;font-size:1.2rem;font-weight:600;font-family:'Space Grotesk',sans-serif;}
#settings-close{width:32px;height:32px;border-radius:50%;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;}
#settings-close:hover{color:#fff;border-color:#4f8dff;}
#settings-tabs{display:flex;gap:4px;padding:12px 20px;border-bottom:1px solid #2a2a2a;overflow-x:auto;flex-shrink:0;}
.settings-tab{padding:8px 16px;border-radius:8px;border:1px solid #2a2a2a;background:transparent;color:#7a7a7a;font-size:0.85rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;white-space:nowrap;transition:all 0.2s;}
.settings-tab:hover{color:#fff;border-color:#4f8dff;}
.settings-tab.active{background:#4f8dff;color:#fff;border-color:#4f8dff;}
#settings-content{padding:20px;overflow-y:auto;flex:1;}
.settings-panel{display:none;}
.settings-panel.active{display:flex;flex-direction:column;gap:12px;}
.settings-panel button{width:100%;height:44px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.95rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
.settings-panel button:hover{border-color:#4f8dff;color:#fff;}
.settings-radio{display:flex;align-items:center;gap:10px;padding:12px;border-radius:10px;background:#1a1a1a;cursor:pointer;transition:all 0.2s;}
.settings-radio:hover{background:#2a2a2a;}
.settings-radio input[type="radio"]{width:18px;height:18px;cursor:pointer;}
.settings-radio span{color:#ececec;font-size:0.95rem;font-family:'Space Grotesk',sans-serif;}
.model-option{display:flex;flex-direction:column;gap:8px;}
.model-desc{color:#7a7a7a;font-size:0.8rem;font-family:'Space Grotesk',sans-serif;margin:0;padding-left:28px;}
.settings-panel[data-panel="about"] p{color:#bdbdbd;font-size:0.9rem;line-height:1.5;font-family:'Space Grotesk',sans-serif;margin:0;}
#confirm-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.85);z-index:10000002;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;}
#confirm-overlay.active{display:flex;}
#confirm-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:24px;max-width:320px;width:100%;display:flex;flex-direction:column;gap:16px;}
#confirm-text{color:#ececec;font-size:1rem;font-family:'Space Grotesk',sans-serif;margin:0;text-align:center;}
#confirm-buttons{display:flex;gap:12px;}
#confirm-buttons button{flex:1;height:40px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
#confirm-yes:hover{background:#ef4444;border-color:#ef4444;color:#fff;}
#confirm-no:hover{border-color:#4f8dff;color:#fff;}
#login-overlay{display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.85);z-index:10000002;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;}
#login-overlay.active{display:flex;}
#login-box{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:16px;padding:24px;max-width:320px;width:100%;display:flex;flex-direction:column;gap:12px;}
#login-email{width:100%;height:44px;border-radius:10px;border:1px solid #2a2a2a;background:#0a0a0a;color:#fff;font-size:0.95rem;padding:0 14px;box-sizing:border-box;font-family:'Space Grotesk',sans-serif;}
#login-email:focus{outline:none;border-color:#4f8dff;}
#login-box button{width:100%;height:40px;border-radius:10px;border:1px solid #2a2a2a;background:#1a1a1a;color:#ececec;font-size:0.9rem;cursor:pointer;font-family:'Space Grotesk',sans-serif;transition:all 0.2s;}
#login-submit:hover{background:#4f8dff;border-color:#4f8dff;color:#fff;}
#login-cancel:hover{border-color:#7a7a7a;color:#fff;}
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
    const topUser=parentElement.querySelector('#top-user');
    const tuName=parentElement.querySelector('#tu-name');
    const tuEmail=parentElement.querySelector('#tu-email');
    const sideMenu=parentElement.querySelector('#side-menu');
    const smClose=parentElement.querySelector('#sm-close');
    const smNewChat=parentElement.querySelector('#sm-new-chat');
    const smChats=parentElement.querySelector('#sm-chats');
    const smUserEmail=parentElement.querySelector('#sm-user-email');
    const smUserName=parentElement.querySelector('#sm-user-name');
    const settingsBtn=parentElement.querySelector('#settings-btn');
    const settingsOverlay=parentElement.querySelector('#settings-overlay');
    const settingsClose=parentElement.querySelector('#settings-close');
    const settingsTabs=parentElement.querySelectorAll('.settings-tab');
    const settingsPanels=parentElement.querySelectorAll('.settings-panel');
    const settingsLogout=parentElement.querySelector('#settings-logout');
    const settingsDeleteAll=parentElement.querySelector('#settings-delete-all');
    const confirmOverlay=parentElement.querySelector('#confirm-overlay');
    const confirmText=parentElement.querySelector('#confirm-text');
    const confirmYes=parentElement.querySelector('#confirm-yes');
    const confirmNo=parentElement.querySelector('#confirm-no');
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
    let userEmail=localStorage.getItem('strafe_user_email')||'';
    let chats=userEmail?JSON.parse(localStorage.getItem('strafe_chats')||'[]'):[];
    let currentChatId=userEmail?(localStorage.getItem('strafe_current_chat')||null):null;
    let settings={
        lang:userEmail?(localStorage.getItem('strafe_lang')||'en'):'en',
        provider:userEmail?(localStorage.getItem('strafe_provider')||'groq'):'groq'
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

    function saveChats(){
        if(!userEmail)return;
        localStorage.setItem('strafe_chats',JSON.stringify(chats));
        localStorage.setItem('strafe_current_chat',currentChatId||'');
    }
    function saveSettings(){
        if(!userEmail)return;
        localStorage.setItem('strafe_lang',settings.lang);
        localStorage.setItem('strafe_provider',settings.provider);
    }
    function renderChatList(){
        smChats.innerHTML='';
        chats.forEach(function(chat){
            const div=document.createElement('div');
            div.className='sm-chat'+(chat.id===currentChatId?' active':'');
            const name=document.createElement('span');
            name.className='sm-chat-name';
            name.textContent=chat.name;
            const del=document.createElement('button');
            del.type='button';
            del.className='sm-chat-del';
            del.textContent='\\u2715';
            del.onclick=function(ev){
                ev.stopPropagation();
                showConfirm('Delete this chat?',function(){
                    chats=chats.filter(function(c){return c.id!==chat.id;});
                    if(currentChatId===chat.id)currentChatId=null;
                    saveChats();
                    renderChatList();
                    setTriggerValue('chat_action',{action:'delete',id:chat.id});
                });
            };
            div.onclick=function(){
                currentChatId=chat.id;
                saveChats();
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
            const name=userEmail.split('@')[0];
            smUserName.textContent=name;
            smUserEmail.textContent=userEmail;
            if(tuName)tuName.textContent=name;
            if(tuEmail)tuEmail.textContent=userEmail;
        }else{
            smUserName.textContent='Guest';
            smUserEmail.textContent='@no_email.gmail.com';
            if(tuName)tuName.textContent='Guest';
            if(tuEmail)tuEmail.textContent='@no_email.gmail.com';
        }
    }
    function showConfirm(text,onYes){
        confirmText.textContent=text;
        confirmOverlay.classList.add('active');
        confirmYes.onclick=function(){
            confirmOverlay.classList.remove('active');
            onYes();
        };
        confirmNo.onclick=function(){
            confirmOverlay.classList.remove('active');
        };
    }
    function closeSideMenu(){
        sideMenu.classList.remove('open');
    }
    function openLogin(){
        loginOverlay.classList.add('active');
        loginEmail.value='';
        setTimeout(function(){loginEmail.focus();},50);
    }
    function openSettings(tab){
        settingsOverlay.classList.add('active');
        if(tab){
            settingsTabs.forEach(function(t){t.classList.toggle('active',t.dataset.tab===tab);});
            settingsPanels.forEach(function(p){p.classList.toggle('active',p.dataset.panel===tab);});
        }
        parentElement.querySelectorAll('input[name="lang"]').forEach(function(r){
            r.checked=r.value===settings.lang;
        });
        parentElement.querySelectorAll('input[name="provider"]').forEach(function(r){
            r.checked=r.value===settings.provider;
        });
    }
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
    function updateLabels(){
        btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';
        btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';
    }
    async function send(){
        const val=input.value.trim();
        if(!val&&!attachments.length&&!fileAttachments.length)return;
        if(!currentChatId){
            const id='chat_'+Date.now();
            chats.unshift({id:id,name:'New Chat',messages:[]});
            currentChatId=id;
        }
        const chat=chats.find(function(c){return c.id===currentChatId;});
        if(chat&&chat.name==='New Chat'&&val){
            chat.name=val.length>30?val.slice(0,30)+'\\u2026':val;
        }
        saveChats();
        renderChatList();
        const resized=[];
        for(let i=0;i<attachments.length;i++){
            resized.push(await resizeImage