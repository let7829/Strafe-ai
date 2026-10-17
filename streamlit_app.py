import streamlit as st
from groq import Groq
import random, time

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

HTML = """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;}
.stApp{background:#101010;}
#MainMenu,footer,header{visibility:hidden;}
div[data-testid="stChatMessage"]{background:transparent;border:none;padding:6px 0;}
div[data-testid^="stChatMessageAvatar"]{display:none;}
div[data-testid="stChatMessage"]:has(div[data-testid^="stChatMessageAvatarUser"]){flex-direction:row-reverse;}
div[data-testid="stChatMessage"]:has(div[data-testid^="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"]{background:#3f3f3f;border-radius:26px;padding:12px 20px;max-width:80%;flex:0 1 auto;}
div[data-testid="stChatMessage"]:has(div[data-testid^="stChatMessageAvatarUser"]) .stMarkdown p{color:#fff;font-size:1.05rem;margin:0;}
div[data-testid="stChatMessage"]:has(div[data-testid^="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageContent"]{background:transparent;max-width:100%;}
div[data-testid="stChatMessage"]:has(div[data-testid^="stChatMessageAvatarAssistant"]) .stMarkdown p{color:#ececec;font-size:1.08rem;line-height:1.6;}
div[data-testid="stExpander"] details{background:transparent;border:none;padding:0;}
div[data-testid="stExpander"] summary{color:#9a9a9a;font-size:0.95rem;}
div[data-testid="stChatMessage"] button{background:transparent;border:none;color:#8a8a8a;font-size:1rem;padding:2px 8px;}
div[data-testid="stChatMessage"] button:hover{color:#fff;}
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

keys = [st.secrets[f"GROQ_API_KEY_{i}"] for i in range(1, 7)]
client = Groq(api_key=random.choice(keys))

if "messages" not in st.session_state:
    st.session_state.messages = []

def ask(prompt):
    t0 = time.time()
    r = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Be direct. No fluff."},
                  {"role": "user", "content": prompt}],
        max_tokens=150)
    secs = max(1, round(time.time() - t0))
    return r.choices[0].message.content, secs, f"{r.usage.total_tokens} tokens"

regen = st.session_state.pop("regen", None)
if regen is not None:
    p = st.session_state.messages[regen - 1]["content"]
    st.session_state.messages = st.session_state.messages[:regen]
    c, s, t = ask(p)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:
        with st.chat_message("assistant"):
            with st.expander(f"Thought for {m['secs']} seconds"):
                st.caption(f"{m['tok']} · llama-3.1-8b-instant")
            st.markdown(m["content"])
            if st.session_state.get("copy") == i:
                st.code(m["content"])
            c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1, 16])
            if c1.button("⧉", key=f"c{i}"):
                st.session_state["copy"] = None if st.session_state.get("copy") == i else i
            if c2.button("👍", key=f"u{i}"):
                st.session_state["fb"] = (i, "up")
            if c3.button("👎", key=f"d{i}"):
                st.session_state["fb"] = (i, "down")
            if c4.button("🔁", key=f"r{i}"):
                st.session_state["regen"] = i
                st.rerun()
            if st.session_state.get("fb", (None,))[0] == i:
                st.caption("logged " + st.session_state["fb"][1])

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    c, s, t = ask(prompt)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t})
    st.rerun()
