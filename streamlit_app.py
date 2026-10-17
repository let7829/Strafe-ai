import streamlit as st
from groq import Groq, NotFoundError
import random, time, html as H, re, requests

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

HTML = """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"],.stApp,#root,.main,.block-container{
    font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding-left:1rem;padding-right:1rem;max-width:760px;overflow-x:hidden;}

/* input box */
div[data-testid="stContainer"]{background:#1e1f22 !important;border:1px solid #333 !important;
    border-radius:28px !important;padding:14px 16px 10px 16px !important;}
div[data-testid="stContainer"] textarea{background:transparent !important;color:#fff !important;
    border:none !important;font-size:1.05rem !important;resize:none !important;}
div[data-testid="stContainer"] div[data-testid="stTextInput"],
div[data-testid="stContainer"] div[data-testid="stTextArea"]{margin-bottom:4px;}

/* pills */
div[data-testid="stCheckbox"] label{border:1px solid #444;border-radius:999px;padding:6px 16px;
    background:transparent;cursor:pointer;display:inline-flex;align-items:center;}
div[data-testid="stCheckbox"] input{display:none;}
div[data-testid="stCheckbox"] p{color:#e8e8e8 !important;margin:0;font-size:0.95rem;}
div[data-testid="stCheckbox"] label:has(input:checked){border-color:#5b7cfa;background:#26304a;}
div[data-testid="stCheckbox"] label:has(input:checked) p{color:#8fa5ff !important;}
div[data-testid="stCheckbox"] input:checked ~ p,
div[data-testid="stCheckbox"] input:checked + div p{color:#8fa5ff !important;}

/* circle buttons in pill row */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) button{
    background:transparent !important;border:1.5px solid #bbb !important;color:#fff !important;
    border-radius:50% !important;min-width:42px !important;width:42px !important;height:42px !important;
    padding:0 !important;font-size:1.1rem !important;line-height:1 !important;}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) > div{display:flex;align-items:center;}

/* chat */
.user-bubble-row{display:flex;justify-content:flex-start;width:100%;margin:10px 0;overflow:hidden;}
.user-bubble{background:#3f3f3f !important;color:#fff !important;border-radius:26px;
    padding:12px 20px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;
    word-wrap:break-word;overflow-wrap:anywhere;}
div[data-testid="stChatMessage"]{background:transparent !important;border:none !important;padding:6px 0;overflow:hidden;}
div[data-testid^="stChatMessageAvatar"]{display:none !important;}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{background:transparent !important;max-width:100%;padding:0;}
div[data-testid="stChatMessage"] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;overflow-wrap:anywhere;}
div[data-testid="stChatMessage"] button{background:transparent !important;border:none !important;
    color:#8a8a8a !important;font-size:1.1rem !important;padding:2px 10px !important;min-width:0 !important;height:auto !important;}
div[data-testid="stChatMessage"] button p{margin:0 !important;}

.brand{text-align:center;padding:28px 0 6px 0;font-size:1.5rem;font-weight:700;letter-spacing:3px;
    background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
</style>
"""
try:
    st.html(HTML)
except Exception:
    st.markdown(HTML, unsafe_allow_html=True)

st.markdown('<div class="brand">STRAFE AI</div>', unsafe_allow_html=True)

KEYS = [st.secrets[f"GROQ_API_KEY_{i}"] for i in range(1, 7)]
PREFERRED = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]

SYSTEM = """I keep it direct and simple. No fluff, no long explanations unless you ask for them.
I match your energy—you're casual, I'm casual. You're serious, I'm serious. No fake politeness, just real talk.
I hold nothing back, answer whatever you ask. I don't sugarcoat or dodge. If something's dark or weird, I engage with it
I also don't pretend to be something I'm not. You asked earlier—I gave you the honest answer instead of the corporate "I'm just a helpful AI" response."""

st.session_state.setdefault("think", False)
st.session_state.setdefault("search", False)
if "messages" not in st.session_state:
    st.session_state.messages = []

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

def web_search(q):
    try:
        r = requests.get("https://html.duckduckgo.com/html/", params={"q": q},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text, re.S)[:3]
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S)[:3]
        clean = lambda s: re.sub(r'<[^>]+>', '', s).strip()
        return "\n".join(f"- {clean(t)}: {clean(s)}" for t, s in zip(titles, snips))
    except Exception:
        return ""

def build_payload(prompt):
    model = pick_model()
    if st.session_state.search:
        ctx = web_search(prompt)
        if ctx:
            prompt = f"Web search results:\n{ctx}\n\nQuestion: {prompt}"
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    think = st.session_state.think
    if "gpt-oss" in model:
        if history and history[0]["role"] == "user":
            history[0] = {"role": "user", "content": SYSTEM + "\n\n" + history[0]["content"]}
        else:
            history.insert(0, {"role": "user", "content": SYSTEM})
        history.append({"role": "user", "content": prompt})
        kwargs = dict(model=model, messages=history, max_completion_tokens=1024,
                      temperature=0.6, top_p=0.95, include_reasoning=False,
                      reasoning_effort=("medium" if think else "low"))
    else:
        msgs = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": prompt}]
        kwargs = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
        if "qwen" in model:
            kwargs["reasoning_effort"] = ("medium" if think else "none")
            kwargs["reasoning_format"] = "hidden"
    return kwargs

def ask(prompt):
    t0 = time.time()
    last_err = None
    for _ in range(2):
        kwargs = build_payload(prompt)
        try:
            r = Groq(api_key=random.choice(KEYS)).chat.completions.create(**kwargs)
        except NotFoundError:
            st.session_state.pop("model", None); last_err = f"model {kwargs['model']} gone"; continue
        except Exception as e:
            last_err = str(e)[:120]; break
        content = (getattr(r.choices[0].message, "content", None) or "").strip()
        secs = max(1, round(time.time() - t0))
        used = r.usage.total_tokens if r.usage else "?"
        return content, secs, f"{used} tok · {kwargs['model']}"
    raise RuntimeError(last_err or "Groq call failed")

# ---- input box ----
with st.container(border=True):
    txt = st.text_area("msg", placeholder="Type a message", label_visibility="collapsed",
                       height=64, key="msgbox")
    c1, c2, _, c4, c5, c6 = st.columns([2, 2, 6, 1, 1, 1])
    with c1:
        if st.session_state.pop("think_clicked", False):
            st.session_state.think = not st.session_state.think
    with c1:
        st.checkbox("⚛ Think", key="think_cb", on_change=lambda: st.session_state.update(think=st.session_state.think_cb))
    with c2:
        st.checkbox("⌕ Search", key="search_cb", on_change=lambda: st.session_state.update(search=st.session_state.search_cb))
    with c4:
        st.button("+", key="plus_dead")
    with c5:
        st.button("🎙️", key="mic_dead")
    with c6:
        send = st.button("↑", key="send_btn")
    if txt.strip():
        st.markdown('<style>div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCheckbox"]) > div:last-child button{background:#4c6ef5 !important;border-color:#4c6ef5 !important;}</style>', unsafe_allow_html=True)

st.session_state.think = st.session_state.get("think_cb", False)
st.session_state.search = st.session_state.get("search_cb", False)

submitted = send or "\n" in txt
prompt = txt.strip()

regen = st.session_state.pop("regen", None)
if regen is not None:
    prompt = st.session_state.messages[regen - 1]["content"]
    st.session_state.messages = st.session_state.messages[:regen]
    c, s, t = ask(prompt)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
elif submitted and prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    c, s, t = ask(prompt)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.session_state.msgbox = ""
    st.rerun()

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        safe = H.escape(m["content"]).replace("\n", "<br>")
        st.markdown(f'<div class="user-bubble-row"><div class="user-bubble">{safe}</div></div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(m["content"])
            c1, c2, _ = st.columns([1, 1, 18])
            with c1:
                if st.button("⧉", key=f"c{i}"):
                    st.session_state["copy"] = None if st.session_state.get("copy") == i else i
            with c2:
                if st.button("🔁", key=f"r{i}"):
                    st.session_state["regen"] = i
                    st.rerun()
            if st.session_state.get("copy") == i:
                st.code(m["content"])
