import streamlit as st
import streamlit.components.v1 as components
from groq import Groq, NotFoundError
import random
import time
import html as H
import json

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"

CSS = """
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding:0 1rem 2rem 1rem !important;max-width:760px;overflow-x:hidden;}
div[data-testid='stVerticalBlock']{gap:0 !important;}
div[data-testid='stChatMessage']{background:transparent !important;border:none !important;padding:8px 0 0 0 !important;margin:0 !important;overflow:visible !important;}
div[data-testid^='stChatMessageAvatar']{display:none !important;}
div[data-testid='stChatMessage'] div[data-testid='stChatMessageContent']{background:transparent !important;max-width:100%;padding:0;overflow:visible !important;}
div[data-testid='stChatMessage'] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 2px 0;overflow-wrap:anywhere;}
.brand{text-align:center;padding:8px 0 2px 0;font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.user-bubble{display:flex;justify-content:flex-end;width:100%;margin:10px 0 0 0;}
.user-bubble-inner{background:#5c5c5c;color:#ffffff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}
div[data-testid='stPopover']{margin:0 !important;}
div[data-testid='stPopover'] button{height:20px !important;min-height:0 !important;padding:0 4px !important;font-size:1rem !important;line-height:1 !important;color:#7a7a7a !important;background:transparent !important;border:none !important;box-shadow:none !important;}
div[data-testid='stPopover'] button:hover{color:#fff !important;}
div[data-testid='stPopover'] button p{margin:0 !important;}
.close-row button{background:transparent !important;border:none !important;color:#7a7a7a !important;font-size:0.85rem !important;padding:2px 8px !important;box-shadow:none !important;}
.close-row button:hover{color:#fff !important;}
.input-wrapper{width:100%;max-width:760px;margin:10px auto 0 auto;padding:0 14px;box-sizing:border-box;}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
st.markdown("<div class='brand'>STRAFE AI</div>", unsafe_allow_html=True)

KEYS = [st.secrets[f"GROQ_API_KEY_{i}"] for i in range(1, 7)]
PREFERRED = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]
SYSTEM = "I keep it direct and simple. No fluff, no long explanations unless you ask for them.\nI match your energy—you're casual, I'm casual. You're serious, I'm serious. No fake politeness, just real talk.\nI hold nothing back, answer whatever you ask. I don't sugarcoat or dodge. If something's dark or weird, I engage with it\nI also don't pretend to be something I'm not. You asked earlier—I gave you the honest answer instead of the corporate \"I'm just a helpful AI\" response."

def pick_model():
    if "model" in st.session_state:
        return st.session_state.model
    try:
        avail = {m.id for m in Groq(api_key=KEYS[0]).models.list()}
    except Exception:
        avail = set()
    chosen = next((p for p in PREFERRED if p in avail), None) or (list(avail)[0] if avail else PREFERRED[0])
    st.session_state.model = chosen
    return chosen

if "messages" not in st.session_state:
    st.session_state.messages = []

def build_payload():
    model = pick_model()
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    if "gpt-oss" in model:
        if history and history[0]["role"] == "user":
            history[0] = {"role": "user", "content": SYSTEM + "\n\n" + history[0]["content"]}
        else:
            history.insert(0, {"role": "user", "content": SYSTEM})
        return dict(model=model, messages=history, max_completion_tokens=1024, temperature=0.6, top_p=0.95, include_reasoning=False)
    msgs = [{"role": "system", "content": SYSTEM}] + history
    kw = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
    if "qwen" in model:
        kw["reasoning_effort"] = "none"
        kw["reasoning_format"] = "hidden"
    return kw

def ask():
    t0 = time.time()
    last_err = None
    for _ in range(2):
        kwargs = build_payload()
        try:
            r = Groq(api_key=random.choice(KEYS)).chat.completions.create(**kwargs)
        except NotFoundError:
            st.session_state.pop("model", None)
            last_err = "model gone"
            continue
        except Exception as e:
            last_err = str(e)[:120]
            break
        content = (getattr(r.choices[0].message, "content", None) or "").strip()
        secs = max(1, round(time.time() - t0))
        used = r.usage.total_tokens if r.usage else "?"
        return content, secs, f"{used} tok"
    raise RuntimeError(last_err or "Groq call failed")

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0 and st.session_state.messages[i - 1]["role"] == "user":
        st.session_state.messages = st.session_state.messages[:i]
        c, s, t = ask()
        st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
        st.session_state["show"] = None
    elif kind in ("copy", "select"):
        cur = st.session_state.get("show")
        st.session_state["show"] = None if cur == (kind, i) else (kind, i)
    elif kind == "edit":
        st.session_state["editing"] = i
        st.session_state["show"] = None
    elif kind == "close":
        st.session_state["show"] = None

pending = st.session_state.pop("pending", None)
if pending is not None:
    st.session_state.messages.append({"role": "user", "content": pending})
    c, s, t = ask()
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
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
                    st.session_state["pending"] = new
                    st.rerun()
            with sk:
                if st.button("Cancel", key=f"cx{i}"):
                    st.session_state["editing"] = None
                    st.rerun()
        else:
            safe = H.escape(m["content"]).replace("\n", "<br>")
            st.markdown(f'<div class="user-bubble"><div class="user-bubble-inner">{safe}</div></div>', unsafe_allow_html=True)
            _sp, _mn = st.columns([3, 1])
            with _mn:
                with st.popover(MENU_GLYPH, key=f"mu{i}"):
                    if st.button("Copy", key=f"uc{i}"):
                        st.session_state["act"] = ("copy", i); st.rerun()
                    if st.button("Select text", key=f"us{i}"):
                        st.session_state["act"] = ("select", i); st.rerun()
                    if st.button("Edit", key=f"ue{i}"):
                        st.session_state["act"] = ("edit", i); st.rerun()
            if show == ("copy", i):
                st.code(m["content"])
                st.markdown('<div class="close-row">', unsafe_allow_html=True)
                if st.button(CLOSE_GLYPH + " close", key=f"cl{i}"):
                    st.session_state["act"] = ("close", i); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if show == ("select", i):
                st.text_area("Select & copy", value=m["content"], key=f"slu{i}", height=120)
                st.markdown('<div class="close-row">', unsafe_allow_html=True)
                if st.button(CLOSE_GLYPH + " close", key=f"cls{i}"):
                    st.session_state["act"] = ("close", i); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(m["content"])
        _mn, _sp = st.columns([1, 3])
        with _mn:
            with st.popover(MENU_GLYPH, key=f"ma{i}"):
                if st.button("Copy", key=f"ac{i}"):
                    st.session_state["act"] = ("copy", i); st.rerun()
                if st.button("Retry", key=f"ar{i}"):
                    st.session_state["act"] = ("retry", i); st.rerun()
                if st.button("Select text", key=f"as{i}"):
                    st.session_state["act"] = ("select", i); st.rerun()
        if show == ("copy", i):
            st.code(m["content"])
            st.markdown('<div class="close-row">', unsafe_allow_html=True)
            if st.button(CLOSE_GLYPH + " close", key=f"cla{i}"):
                st.session_state["act"] = ("close", i); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        if show == ("select", i):
            st.text_area("Select & copy", value=m["content"], key=f"sla{i}", height=120)
            st.markdown('<div class="close-row">', unsafe_allow_html=True)
            if st.button(CLOSE_GLYPH + " close", key=f"clsa{i}"):
                st.session_state["act"] = ("close", i); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

input_html = f"""
<!DOCTYPE html>
<html><head><style>
html,body{{margin:0;padding:0;background:transparent;overflow:hidden;font-family:'Space Grotesk',sans-serif;}}
#cb{{display:flex;align-items:center;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:28px;padding:10px 14px;gap:10px;width:100%;box-sizing:border-box;box-shadow:0 4px 20px rgba(0,0,0,0.5);}}
#ci{{flex:1;background:transparent;border:none;outline:none;color:#fff;font-size:1rem;font-family:'Space Grotesk',sans-serif;padding:8px 4px;}}
#ci::placeholder{{color:#6b7280;}}
#sb{{width:38px;height:38px;border-radius:50%;border:none;background:#4f8dff;color:#fff;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
#sb:hover{{background:#2563eb;}}
</style></head><body>
<div id="cb">
<input id="ci" type="text" placeholder="Ask something" autocomplete="off"/>
<button id="sb" type="button">{SEND_GLYPH}</button>
</div>
<script>
(function(){{
var input=document.getElementById('ci');
var btn=document.getElementById('sb');
function send(){{
var val=input.value.trim();
if(!val)return;
window.parent.postMessage({{type:"strafe_input",value:val}},"*");
input.value='';
}}
btn.onclick=send;
input.onkeydown=function(e){{if(e.key==='Enter')send();}};
}})();
</script></body></html>
"""

with st.container():
    st.markdown('<div class="input-wrapper">', unsafe_allow_html=True)
    components.html(input_html, height=70, scrolling=False)
    st.markdown('</div>', unsafe_allow_html=True)

if "last_input" not in st.session_state:
    st.session_state.last_input = None

prompt = st.session_state.last_input
st.session_state.last_input = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    c, s, t = ask()
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.rerun()

components.html("""
<script>
window.addEventListener("message", function(e){
if(e.data && e.data.type === "strafe_input"){
fetch(window.location.href, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({input:e.data.value})});
}
});
</script>
""", height=0)