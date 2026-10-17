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

/* user bubble: pinned LEFT */
.user-bubble-row{display:flex;justify-content:flex-start;width:100%;margin:10px 0;overflow:hidden;}
.user-bubble{
    background:#3f3f3f !important;color:#fff !important;border-radius:26px;
    padding:12px 20px;max-width:80%;width:fit-content;
    font-size:1.05rem;line-height:1.5;word-wrap:break-word;overflow-wrap:anywhere;
}

/* assistant: strip avatar + bubble */
div[data-testid="stChatMessage"]{background:transparent !important;border:none !important;padding:6px 0;overflow:hidden;}
div[data-testid^="stChatMessageAvatar"]{display:none !important;}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{
    background:transparent !important;max-width:100%;padding:0;
}
div[data-testid="stChatMessage"] .stMarkdown p{
    color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;overflow-wrap:anywhere;
}

/* action buttons: force horizontal */
div[data-testid="stHorizontalBlock"]{gap:0.25rem !important;flex-wrap:nowrap !important;}
div[data-testid="stHorizontalBlock"] > div{flex:0 0 auto !important;width:auto !important;}
div[data-testid="stChatMessage"] button{
    background:transparent !important;border:none !important;color:#8a8a8a !important;
    font-size:1.1rem !important;padding:2px 10px !important;min-width:0 !important;height:auto !important;
}
div[data-testid="stChatMessage"] button:hover{color:#fff !important;}
div[data-testid="stChatMessage"] button p{margin:0 !important;}

/* input */
div[data-testid="stChatInput"]{border-radius:999px;border:1px solid #2a2a2a;background:#1a1a1a !important;}
div[data-testid="stChatInput"] textarea{background:transparent !important;color:#fff !important;}

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
        # gpt-oss: instructions go in the USER message, not system [[1]]
        if "gpt-oss" in model:
            msgs = [{"role": "user", "content": SYSTEM + "\n\n" + prompt}]
            kwargs = dict(model=model, messages=msgs,
                          max_completion_tokens=1024, temperature=0.6, top_p=0.95,
                          include_reasoning=False)   # kills thinking on gpt-oss [[1]]
        else:
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
            kwargs = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
            if "qwen" in model:
                kwargs["reasoning_effort"] = "none"   # none IS valid for qwen [[1]]
                kwargs["reasoning_format"] = "hidden"
        try:
            r = Groq(api_key=random.choice(KEYS)).chat.completions.create(**kwargs)
        except NotFoundError:
            st.session_state.pop("model", None); last_err = f"model {model} gone"; continue
        except Exception as e:
            last_err = str(e)[:120]; break
        content = (getattr(r.choices[0].message, "content", None) or "").strip()
        secs = max(1, round(time.time() - t0))
        used = r.usage.total_tokens if r.usage else "?"
        return content, secs, f"{used} tok · {model}"
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
