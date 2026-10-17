import streamlit as st
from groq import Groq, NotFoundError
import random, time, html as H

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

HTML = """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"],.stApp,#root,.main,.block-container{
    font-family:'Space Grotesk',sans-serif;
    background-color:#0a0a0a !important;
    color:#ececec !important;
}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding-left:1rem;padding-right:1rem;max-width:760px;overflow-x:hidden;}

/* chat bubbles */
.user-bubble-row{display:flex;justify-content:flex-start;width:100%;margin:10px 0;overflow:hidden;}
.user-bubble{
    background:#3f3f3f !important;color:#fff !important;border-radius:26px;
    padding:12px 20px;max-width:80%;width:fit-content;
    font-size:1.05rem;line-height:1.5;word-wrap:break-word;overflow-wrap:anywhere;
}
div[data-testid="stChatMessage"]{background:transparent !important;border:none !important;padding:6px 0;overflow:hidden;}
div[data-testid^="stChatMessageAvatar"]{display:none !important;}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{background:transparent !important;max-width:100%;padding:0;}
div[data-testid="stChatMessage"] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;overflow-wrap:anywhere;}
div[data-testid="stChatMessage"] button{background:transparent !important;border:none !important;color:#8a8a8a !important;font-size:1.1rem !important;padding:2px 10px !important;min-width:0 !important;height:auto !important;}
div[data-testid="stChatMessage"] button p{margin:0 !important;}

/* ===== FIXED BOTTOM INPUT BAR ===== */
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type{
    position:fixed !important;bottom:10px !important;left:10px !important;right:10px !important;
    z-index:999999 !important;
    background:#1c1c1e !important;border-radius:26px !important;
    border:1px solid #333 !important;padding:12px 14px !important;
}
/* strip input chrome — hit wrapper AND input element */
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stTextInput"] > div{
    border:none !important;box-shadow:none !important;background:transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stTextInput"] input{
    border:none !important;box-shadow:none !important;background:transparent !important;
    color:#fff !important;font-size:1.05rem !important;height:40px !important;padding:6px 4px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type input::placeholder{color:#8a8a8a !important;}

/* button row */
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stHorizontalBlock"]{
    gap:6px !important;flex-wrap:nowrap !important;margin-top:4px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stHorizontalBlock"] > div{
    flex-wrap:nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type button{
    height:42px !important;border-radius:999px !important;font-size:0.95rem !important;
    padding:0 14px !important;min-width:42px !important;
}
/* circles for + / voice / send (columns 3,4,5) */
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stHorizontalBlock"] > div:nth-child(3) button,
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stHorizontalBlock"] > div:nth-child(4) button,
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type div[data-testid="stHorizontalBlock"] > div:nth-child(5) button{
    border-radius:50% !important;width:42px !important;padding:0 !important;
}
/* off = outline, on = blue */
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type button[data-testid="stBaseButton-secondary"],
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type button[kind="secondary"]{
    background:transparent !important;color:#ddd !important;border:1px solid #555 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type button[data-testid="stBaseButton-primary"],
div[data-testid="stVerticalBlockBorderWrapper"]:last-of-type button[kind="primary"]{
    background:#243b53 !important;color:#7ea6ff !important;border:1px solid #3b5bdb !important;
}

.brand{text-align:center;padding:28px 0 6px 0;font-size:1.5rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
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

for k, v in [("think_on", False), ("search_on", False), ("messages", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

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

def build_payload(prompt):
    model = pick_model()
    think = st.session_state.think_on
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    if "gpt-oss" in model:
        if history and history[0]["role"] == "user":
            history[0] = {"role": "user", "content": SYSTEM + "\n\n" + history[0]["content"]}
        else:
            history.insert(0, {"role": "user", "content": SYSTEM})
        history.append({"role": "user", "content": prompt})
        kwargs = dict(model=model, messages=history, max_completion_tokens=1024,
                      temperature=0.6, top_p=0.95, include_reasoning=think)
        if think:
            kwargs["reasoning_effort"] = "low"
    else:
        msgs = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": prompt}]
        kwargs = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
        if "qwen" in model:
            kwargs["reasoning_effort"] = "low" if think else "none"
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

# ---- chat history ----
regen = st.session_state.pop("regen", None)
if regen is not None:
    p = st.session_state.messages[regen - 1]["content"]
    st.session_state.messages = st.session_state.messages[:regen]
    c, s, t = ask(p)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})

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

# spacer so chat doesn't hide under the fixed bar
st.markdown('<div style="height:150px"></div>', unsafe_allow_html=True)

# ---- fixed bottom bar ----
with st.container(border=True):
    txt = st.text_input("promptbox", placeholder="Type a message",
                        label_visibility="collapsed", key="msg_input")
    c1, c2, c3, c4, c5 = st.columns([3, 3, 1.4, 1.4, 1.4])
    if c1.button("⚛︎ Think", key="think_btn",
                 type="primary" if st.session_state.think_on else "secondary"):
        st.session_state.think_on = not st.session_state.think_on
        st.rerun()
    if c2.button("⌕ Search", key="search_btn",
                 type="primary" if st.session_state.search_on else "secondary"):
        st.session_state.search_on = not st.session_state.search_on
        st.rerun()
    c3.button("+", key="plus_btn")
    c4.button("🔊", key="voice_btn")
    has_text = bool((txt or "").strip())
    sent = c5.button("↑", key="send_btn", type="primary" if has_text else "secondary")

if sent and has_text:
    st.session_state.messages.append({"role": "user", "content": txt.strip()})
    st.session_state["msg_input"] = ""
    c, s, t = ask(txt.strip())
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.rerun()