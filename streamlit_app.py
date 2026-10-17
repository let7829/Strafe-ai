import streamlit as st
from groq import Groq, NotFoundError
import random, time, html as H

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

HTML = """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;}
.stApp{background:#101010;}
#MainMenu,footer,header{visibility:hidden;}

/* user bubble: plain HTML, pinned LEFT */
.user-bubble-row{display:flex;justify-content:flex-start;margin:10px 0;}
.user-bubble{
    background:#3f3f3f;color:#fff;border-radius:26px;
    padding:12px 20px;max-width:80%;font-size:1.05rem;line-height:1.5;
    word-wrap:break-word;
}

/* assistant: strip Streamlit's default bubble/avatar */
div[data-testid="stChatMessage"]{background:transparent;border:none;padding:6px 0;}
div[data-testid^="stChatMessageAvatar"]{display:none;}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{
    background:transparent;max-width:100%;padding:0;
}
div[data-testid="stChatMessage"] .stMarkdown p{
    color:#ececec;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;
}

/* action buttons: force horizontal, kill gaps */
div[data-testid="stHorizontalBlock"]{gap:0.25rem !important;flex-wrap:nowrap !important;}
div[data-testid="stHorizontalBlock"] > div{flex:0 0 auto !important;width:auto !important;}
div[data-testid="stChatMessage"] button{
    background:transparent !important;border:none !important;color:#8a8a8a !important;
    font-size:1.1rem !important;padding:2px 10px !important;min-width:0 !important;
    height:auto !important;
}
div[data-testid="stChatMessage"] button:hover{color:#fff !important;}
div[data-testid="stChatMessage"] button p{margin:0 !important;}

/* input */
div[data-testid="stChatInput"]{border-radius:999px;border:1px solid #2a2a2a;background:#1a1a1a;}
div[data-testid="stChatInput"] textarea{background:transparent;color:#fff;}

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

def ask(prompt):
    t0 = time.time()
    last_err = None
    for _ in range(2):
        model = pick_model()
        try:
            r = Groq(api_key=random.choice(KEYS)).chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Be direct. No fluff."},
                          {"role": "user", "content": prompt}],
                max_tokens=150)
            secs = max(1, round(time.time() - t0))
            return r.choices[0].message.content, secs, f"{r.usage.total_tokens} tok · {model}"
        except NotFoundError:
            st.session_state.pop("model", None)
            last_err = f"model {model} gone"
        except Exception as e:
            last_err = str(e)[:80]; break
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

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    c, s, t = ask(prompt)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.rerun()
