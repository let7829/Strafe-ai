from groq import Groq
import streamlit as st

for i in range(1, 7):
    try:
        key = st.secrets[f"GROQ_API_KEY_{i}"]
        response = Groq(api_key=key).models.list()
        models = [m.id if hasattr(m, 'id') else m[0] for m in response.data]
        st.write(f"Key {i}: {len(models)} models", models[:5])
    except Exception as e:
        st.write(f"Key {i}: FAILED - {type(e).__name__}: {e}")