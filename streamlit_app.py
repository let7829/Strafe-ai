import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json
from datetime import datetime
from ddgs import DDGS
from ddgs.exceptions import DDGSException

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
PLUS_GLYPH = "\u002b"

INPUT_HTML = '<div id="bar"><div id="cb"><input id="ci" type="text" placeholder="Ask something (type look_back to read full history)" autocomplete="off"/><button id="pb" type="button" class="icon-btn">' + PLUS_GLYPH + '</button><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class