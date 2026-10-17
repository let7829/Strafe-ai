import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

# ─── Custom Chat Input Component ───────────────────────────────────────────────
chat_input_component = components.component(
    "strafe_chat_input",
    html="""
    <div id="chat-box">
        <input id="chat-input" type="text" placeholder="Ask something" autocomplete="off" />
        <button id="send-btn">↑</button>
    </div>
    """,
    css="""
    #chat-box {
        display: flex;
        align-items: center;
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 28px;
        padding: 8px 12px;
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
    }
    #chat-input {
        flex: 1;
        background: transparent;
        border: none;
        outline: none;
        color: #fff;
        font-size: 1rem;
        font-family: 'Space Grotesk', sans-serif;
        padding: 8px 4px;
    }
    #chat-input::placeholder { color: #6b7280; }
    #send-btn {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: none;
        background: #3b82f6;
        color: #fff;
        font-size: 1.1rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: background 0.15s;
    }
    #send-btn:hover { background: #2563eb; }
    #send-btn:disabled { background: #374151; cursor: default; }
    """,
    js="""
    export default function(component) {
        const { setStateValue, parentElement } = component;
        const input = parentElement.querySelector("#chat-input");
        const btn = parentElement.querySelector("#send-btn");

        function send() {
            const val = input.value.trim();
            if (!val) return;
            setStateValue("submitted", val);
            input.value = "";
        }

        btn.onclick = send;
        input.onkeydown = (e) => { if (e.key === "Enter") send(); };
    }
    """
)

def custom_chat_input(key="strafe_input"):
    result = chat_input_component(key=key, default={"submitted": None})
    if result and result.get("submitted"):
        val = result["submitted"]
        # Clear so it doesn't re-fire on rerun
        st.session_state[key] = {"submitted": None}
        return val
    return None

# ─── Page CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
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

/* user bubble: pinned RIGHT */
.user-bubble-row{display:flex;justify-content:flex-end;width:100%;margin:10px 0;overflow:hidden;}
.user-bubble{
    background:#3f3f3f !important;color:#fff !important;border-radius:26px;
    padding:12px 20px;max-width:80%;width:fit-content;
    font-size:1.05rem;line-height:1.5;word-wrap:break-word;overflow-wrap:anywhere;
}

/* assistant: plain left text */
div[data-testid="stChatMessage"]{background:transparent !important;border:none !important;padding:6px 0;overflow:hidden;}
div[data-testid^="stChatMessageAvatar"]{display:none !important;}
div[data-testid="stChatMessage"] div[data-testid="stChatMessageContent"]{
    background:transparent !important;max-width:100%;padding:0;
}
div[data-testid="stChatMessage"] .stMarkdown p{
    color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 6px 0;overflow-wrap:anywhere;
}

/* action buttons horizontal */
div[data-testid="stHorizontalBlock"]{gap:0.25rem !important;flex-wrap:nowrap !important;}
div[data-testid="stHorizontalBlock"] > div{flex:0 0 auto !important;width:auto !important;}
div[data-testid="stChatMessage"] button{
    background:transparent !important;border:none !important;color:#8a8a8a !important;
    font-size:1.1rem !important;padding:2px 10px !important;min-width:0 !important;height:auto !