import streamlit as st
from groq import Groq
import random

st.set_page_config(page_title="Strafe AI", page_icon="⚡", layout="centered")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp { background: #0a0a0f; }
#MainMenu, footer { visibility: hidden; }

.brand {
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: -2px;
    background: linear-gradient(90deg, #00f0ff, #a855f7);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin-bottom: 0;
}
.tag {
    color: #6b7280;
    font-size: 0.85rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-top: -10px;
}
section[data-testid="stSidebar"] { display: none; }

/* chat bubbles */
.stChatMessage {
    background: #13131a;
    border: 1px solid #1f1f2b;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.stTextInput > div > div > input {
    background: #13131a;
    border: 1px solid #2a2a3a;
    color: #fff;
    border-radius: 999px;
}
div[data-testid="stChatInput"] {
    border-radius: 999px !important;
    border: 1px solid #2a2a3a !important;
    background: #13131a !important;
}
.stMarkdown p { color: #e5e7eb; }
</style>
""", unsafe_allow_html=True)

keys = [
    st.secrets["GROQ_API_KEY_1"], st.secrets["GROQ_API_KEY_2"],
    st.secrets["GROQ_API_KEY_3"], st.secrets["GROQ_API_KEY_4"],
    st.secrets["GROQ_API_KEY_5"], st.secrets["GROQ_API_KEY_6"],
]
client = Groq(api_key=random.choice(keys))

st.markdown('<div class="brand">STRAFE AI</div>', unsafe_allow_html=True)
st.markdown('<div class="tag">fast · lean · direct</div>', unsafe_allow_html=True)
st.write("")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Be direct. No fluff."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        ).choices[0].message.content
        st.markdown(resp)

    st.session_state.messages.append({"role": "assistant", "content": resp})
