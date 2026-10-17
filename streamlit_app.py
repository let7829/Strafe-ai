import streamlit as st
from groq import Groq
import random

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0a0a0f; }
#MainMenu, footer, header { visibility: hidden; }

.hero { text-align: center; padding: 40px 0 10px 0; }
.brand {
    font-size: 3.5rem;
    font-weight: 700;
    letter-spacing: -2px;
    background: linear-gradient(90deg, #00f0ff, #a855f7, #ec4899);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin: 0;
    line-height: 1;
}
.tag {
    color: #6b7280;
    font-size: 0.8rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 8px;
}
.status {
    display: inline-block;
    margin-top: 14px;
    padding: 4px 14px;
    border-radius: 999px;
    border: 1px solid #00f0ff44;
    background: #00f0ff11;
    color: #00f0ff;
    font-size: 0.75rem;
    letter-spacing: 1px;
}

/* chat bubbles */
div[data-testid="stChatMessage"] {
    background: #13131a;
    border: 1px solid #1f1f2b;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
div[data-testid="stChatMessage"] .stMarkdown p { color: #e5e7eb; font-size: 1rem; }

/* input */
div[data-testid="stChatInput"] {
    border-radius: 999px !important;
    border: 1px solid #2a2a3a !important;
    background: #13131a !important;
    box-shadow: 0 0 0 1px #00f0ff22;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #fff !important;
}

/* avatars */
div[data-testid="stChatMessage"] [data-testid="stAvatar"] {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

keys = [
    st.secrets["GROQ_API_KEY_1"], st.secrets["GROQ_API_KEY_2"],
    st.secrets["GROQ_API_KEY_3"], st.secrets["GROQ_API_KEY_4"],
    st.secrets["GROQ_API_KEY_5"], st.secrets["GROQ_API_KEY_6"],
]
client = Groq(api_key=random.choice(keys))

st.markdown("""
<div class="hero">
    <div class="brand">STRAFE AI</div>
    <div class="tag">fast · lean · direct</div>
    <div class="status">● online</div>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="⚡" if m["role"] == "assistant" else "🧑"):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⚡"):
        with st.spinner("Thinking..."):
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Be direct. No fluff."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            ).choices[0].message.content
        st.markdown(resp)

    st.session_state.messages.append({"role": "assistant", "content": resp})
