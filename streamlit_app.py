import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

COPY_GLYPH = "\u29C9"
RETRY_GLYPH = "\u21BB"
SEND_GLYPH = "\u2794"
FILE_GLYPH = "\u2399"
ADD_GLYPH = "\uFF0B"
SEARCH_GLYPH = "\u2315"
GEAR_GLYPH = "\u2699"

INPUT_HTML = '<div id="bar"><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="sb" type="button">' + SEND_GLYPH + '</button></div></div>'

INPUT_CSS = """
#bar{position:fixed;bottom:16px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;}
#cb{display:flex;align-items:center;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:28px;padding:10px 14px;gap:10px;width:100%;max-width:760px;margin:0 auto;box-sizing:border-box;box-shadow:0 4px 20px rgba(0,0,0,0.5);}
#ci{flex:1;background:transparent;border:none;outline:none;color:#fff;font-size:1rem;font-family:'Space Grotesk',sans-serif;padding:8px 4px;}
#ci::placeholder{color:#6b7280;}
#sb{width:38px;height:38px;border-radius:50%;border:none;background:#3b82f6;color:#fff;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
#sb:hover{background:#2563eb;}
"""

INPUT_JS = "export default function(component){const{parentElement,setTriggerValue}=component;const input=parentElement.querySelector('#ci');const btn=parentElement.querySelector('#sb');if(!input||!btn)return;function send(){const val=input.value.trim();if(!val)return;setTriggerValue('submitted',val);input.value='';}btn.onclick=send;input.onkeydown=function(e){if(e.key==='Enter')send();};}"

chat_input = components.component("strafe_chat_input", html=INPUT_HTML, css=INPUT_CSS, js=INPUT_JS)

def get_prompt():
    result = chat_input(key="strafe_inp", on_submitted_change=lambda: None)
    if result and result.submitted:
        return result.submitted
    return None

CSS = """
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding:12px 1rem 130px 1rem !important;max-width:760px;overflow-x:hidden;}
div[data-testid='stChatMessage']{background:transparent !important;border:none !important;padding:6px 0;overflow:visible !important;}
div[data-testid^='stChatMessageAvatar']{display:none !important;}
div[data-testid='stChatMessage'] div[data-testid='stChatMessageContent']{background:transparent !important;max-width:100%;padding:0;overflow:visible !important;}
div[data-testid='stChatMessage'] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;overflow-wrap:anywhere;}
div[data-testid='stHorizontalBlock']{gap:0.25rem !important;flex-wrap:nowrap !important;}
div[data-testid='stHorizontalBlock']>div{flex:0 0 auto !important;width:auto !important;}
div[data-testid='stChatMessage'] button{background:transparent !important;border:none !important;color:#8a8a8a !important;font-size:1.2rem !important;padding:4px 12px !important;min-width:0 !important;height:auto !important;}
div[data-testid='stChatMessage'] button:hover{color:#fff !important;}
div[data-testid='stChatMessage'] button p{margin:0 !important;}
.brand{text-align:center;padding:6px 0 10px 0;font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.user-bubble{display:flex;justify-content:flex-end;width:100%;margin:12px 0;}
.user-bubble-inner{background:#3a3a3a;color:#fff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}
</style>
"""

st.html(CSS)
st.html("<div class='brand'>STRAFE AI</div>")

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

def build_payload(prompt):
    model = pick_model()
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    if "gpt-oss" in model:
        if history and history[0]["role"] == "user":
            history[0] = {"role": "user", "content": SYSTEM + "\n\n" + history[0]["content"]}
        else:
            history.insert(0, {"role": "user", "content": SYSTEM})
        history.append({"role": "user", "content": prompt})
        return dict(model=model, messages=history, max_completion_tokens=1024, temperature=0.6, top_p=0.95, include_reasoning=False)
    msgs = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": prompt}]
    kw = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
    if "qwen" in model:
        kw["reasoning_effort"] = "none"
        kw["reasoning_format"] = "hidden"
    return kw

def ask(prompt):
    t0 = time.time()
    last_err = None
    for _ in range(2):
        kwargs = build_payload(prompt)
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

regen = st.session_state.pop("regen", None)
if regen is not None:
    p = st.session_state.messages[regen - 1]["content"]
    st.session_state.messages = st.session_state.messages[:regen]
    c, s, t = ask(p)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        safe = H.escape(m["content"]).replace("\n", "<br>")
        st.html(f'<div class="user-bubble"><div class="user-bubble-inner">{safe}</div></div>')
    else:
        with st.chat_message("assistant"):
            st.markdown(m["content"])
            c1, c2, _ = st.columns([1, 1, 18])
            with c1:
                if st.button(COPY_GLYPH, key=f"c{i}"):
                    st.session_state["copy"] = None if st.session_state.get("copy") == i else i
            with c2:
                if st.button(RETRY_GLYPH, key=f"r{i}"):
                    st.session_state["regen"] = i
                    st.rerun()
            if st.session_state.get("copy") == i:
                st.code(m["content"])

prompt = get_prompt()

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    c, s, t = ask(prompt)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.rerun()