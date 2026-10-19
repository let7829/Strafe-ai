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

INPUT_HTML = '<div id="bar"><div id="atts"></div><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="pb" type="button" class="icon-btn">' + PLUS_GLYPH + '</button><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button></div><div id="menu"><button id="mb-photo" type="button" class="menu-btn">Photo</button><button id="mb-camera" type="button" class="menu-btn">Camera</button><button id="mb-file" type="button" class="menu-btn">\u2399 File</button></div></div>'
INPUT_CSS = """
#bar{position:fixed;bottom:16px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:8px;}
#atts{display:flex;gap:8px;width:100%;max-width:760px;flex-wrap:wrap;padding-left:4px;box-sizing:border-box;}
#atts:empty{display:none;}
.att{position:relative;width:56px;height:56px;border-radius:12px;overflow:hidden;border:1px solid #2a2a2a;flex-shrink:0;}
.att img{width:100%;height:100%;object-fit:cover;display:block;}
.att-x{position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;border:none;background:rgba(0,0,0,0.75);color:#fff;font-size:0.65rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0;}
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
    const btnSearch=parentElement.querySelector('#btn-search');
    const btnThink=parentElement.querySelector('#btn-think');
    if(!input||!btn)return;
    let searchActive=false;
    let thinkActive=false;
    let attachments=[];
    const fileInput=document.createElement('input');
    fileInput.type='file';
    fileInput.accept='image/*';
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
    }
    function updateLabels(){
        btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';
        btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';
    }
    async function send(){
        const val=input.value.trim();
        if(!val&&!attachments.length)return;
        const resized=[];
        for(let i=0;i<attachments.length;i++){
            resized.push(await resizeImage(attachments[i],1024));
        }
        setTriggerValue('submitted',{text:val,search:searchActive,think:thinkActive,images:resized});
        input.value='';
        attachments=[];
        renderAtts();
    }
    btn.onclick=send;
    input.onkeydown=function(e){if(e.key==='Enter')send();};
    if(plusBtn&&menu){
        plusBtn.onclick=function(){
            menu.classList.toggle('open');
        };
        const actions={'mb-camera':'camera','mb-file':'file'};
        Object.keys(actions).forEach(function(id){
            const b=parentElement.querySelector('#'+id);
            if(b){
                b.onclick=function(){
                    setTriggerValue('menu_action',actions[id]);
                    menu.classList.remove('open');
                };
            }
        });
    }
    if(photoBtn){
        photoBtn.onclick=function(){
            menu.classList.remove('open');
            fileInput.click();
        };
    }
    fileInput.onchange=function(){
        const f=fileInput.files[0];
        if(!f)return;
        const reader=new FileReader();
        reader.onload=function(){
            attachments.push(reader.result);
            renderAtts();
        };
        reader.readAsDataURL(f);
        fileInput.value='';
    };
    btnSearch.onclick=function(){
        searchActive=!searchActive;
        this.classList.toggle('active',searchActive);
        updateLabels();
    };
    btnThink.onclick=function(){
        thinkActive=!thinkActive;
        this.classList.toggle('active',thinkActive);
        updateLabels();
    };
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
.brand{text-align:center;padding:8px 0 2px 0;font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.user-bubble{display:flex;justify-content:flex-end;width:100%;margin:10px 0 0 0;}
.user-bubble-inner{background:#5c5c5c;color:#ffffff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}
.chat-thumb{width:64px;height:64px;object-fit:cover;border-radius:12px;margin:0 8px 6px 0;vertical-align:middle;border:1px solid #2a2a2a;}
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
    if not imgs:
        return {"role": m["role"], "content": m["content"]}
    if distance_from_latest is not None and not full_res:
        if distance_from_latest >= 15:
            return {"role": m["role"], "content": m["content"]}
        elif distance_from_latest >= 3:
            parts = [{"type": "text", "text": m["content"]}]
            for u in imgs:
                parts.append({"type": "image_url", "image_url": {"url": u, "detail": "low"}})
            return {"role": m["role"], "content": parts}
    parts = [{"type": "text", "text": m["content"]}]
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
    raw = text.strip().lower()
    is_look_back = raw == "look_back"
    is_clearer = raw == "clearer_image_back"
    st.session_state.messages.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "images": images})
    try:
        result = ask(use_search=use_search, use_think=use_think, look_back=is_look_back, clearer_image_back=is_clearer)
        st.session_state.messages.append({"role": "assistant", **result})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}", "secs": 0, "tok": "0 tok/s", "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think, "reasoning": None})
    st.session_state["editing"] = None
    st.rerun()

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
                    st.session_state["pending"] = {"text": new, "search": m.get("search", False), "think": m.get("think", False), "images": m.get("images", [])}
                    st.rerun()
            with sk:
                if st.button("Cancel", key=f"cx{i}"):
                    st.session_state["editing"] = None
                    st.rerun()
        else:
            safe = H.escape(m["content"]).replace("\n", "<br>")
            thumbs = "".join(f'<img class="chat-thumb" src="{u}"/>' for u in (m.get("images") or []))
            st.html(f'<div class="user-bubble"><div class="user-bubble-inner">{thumbs}{safe}</div></div>')
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
    st.toast(f"{ma} selected")