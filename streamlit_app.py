from groq import Groq
import streamlit as st

for i in range(1, 7):
    try:
        key = st.secrets[f"GROQ_API_KEY_{i}"]
        models = [m.id for m in Groq(api_key=key).models.list()]
        st.write(f"Key {i}: {len(models)} models", models[:5])
    except Exception as e:
        st.write(f"Key {i}: FAILED - {e}")