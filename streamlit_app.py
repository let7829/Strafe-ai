import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H
from datetime import datetime
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"
SEARCH_GLYPH = "\u2315"
THINK_GLYPH = "\u269b"

INPUT_HTML = '<div id="bar"><div id="tools"><button id="btn-search" type="button" class="tool-btn">' + SEARCH_GLYPH + '</button><button id="btn-think" type="button" class="tool-btn">' + THINK_GLYPH + '</button></div><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="sb" type="button">' + SEND_GLYPH + '</button></div></div>'
INPUT_CSS = """
#bar{position:fixed;bottom:16px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:8px;}
#tools{display:flex;gap:8px;width:100%;max-width:760px;justify-content:flex-start;padding-left:4px;}
.tool-btn{width:32px;height:32px;border-radius:50%;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s;}
.tool-btn:hover{color:#fff;border-color:#4f8dff;}
.tool-btn.active{background:#4f8dff;color:#fff;border-color:#4f8dff;}
#cb{display:flex;align-items:center;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:28px;padding:10px 14px;gap:10px;width:100%;max-width:760px;margin:0 auto;box-sizing:border-box;box-shadow:0 4px 20px rgba(0,0,0,0.5);}
#ci{flex:1;background:transparent;border:none;outline:none;color:#fff;font-size:1rem;font-family:'Space Grotesk',sans-serif;padding:8px 4px;}
#ci::placeholder{color:#6b7280;}
#sb{width:38px;height:38px;border-radius:50%;border:none;background:#4f8dff;color:#fff;font-size:1.2rem;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
#sb:hover{background:#2563eb;}
"""
INPUT_JS = """
export default function(component){
    const{parentElement,setTriggerValue}=component;
    const input=parentElement.querySelector('#ci');
    const btn=parentElement.querySelector('#sb');
    const btnSearch=parentElement.querySelector('#btn-search');
    const btnThink=parentElement.querySelector('#btn-think');
    if(!input||!btn)return;
    let searchActive=false;
    let thinkActive=false;
    function send(){
        const val=input.value.trim();
        if(!val)return;
        setTriggerValue('submitted',{text:val,search:searchActive,think:thinkActive});
        input.value='';
    }
    btn.onclick=send;
    input.onkeydown=function(e){if(e.key==='Enter')send();};
    btnSearch.onclick=function(){
        searchActive=!searchActive;
        this.classList.toggle('active',searchActive);
    };
    btnThink.onclick=function(){
        thinkActive=!thinkActive;
        this.classList.toggle('active',thinkActive);
    };
}
"""

chat_input = components.component("strafe_chat_input", html=INPUT_HTML, css=INPUT_CSS, js=INPUT_JS)

def get_prompt():
    result = chat_input(key="strafe_inp", on_submitted_change=lambda: None)
    if result and result.submitted:
        return result.submitted
    return None

CSS = """
<link href='https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap' rel='stylesheet'>
<style>
html,body,[class*='css'],.stApp,#root,.main,.block-container{font-family:'Space Grotesk',sans-serif;background-color:#0a0a0a !important;color:#ececec !important;}
html,body,.stApp,#root{overflow-x:hidden !important;max-width:100vw !important;}
section.main,section[data-testid='stMain'],[data-testid='stAppViewContainer'],[data-testid='stMainBlockContainer'],[data-testid='stAppView'],[data-testid='stVerticalBlockBorderWrapper']{overflow-x:hidden !important;max-width:100vw !important;width:100% !important;}
#MainMenu,footer,header{visibility:hidden;}
section.main .block-container{padding:0 1rem 130px 1rem !important;max-width:760px;overflow-x:hidden;}
div[data-testid='stVerticalBlock']{gap:0 !important;max-width:100% !important;}
div[data-testid='stChatMessage']{background:transparent !important;border:none !important;padding:8px 0 0 0 !important;margin:0 !important;overflow:visible !important;}
div[data-testid^='stChatMessageAvatar']{display:none !important;}
div[data-testid='stChatMessage'] div[data-testid='stChatMessageContent']{background:transparent !important;max-width:100%;padding:0;overflow:visible !important;}
div[data-testid='stChatMessage'] .stMarkdown p{color:#ececec !important;font-size:1.08rem;line-height:1.6;margin:0 0 2px 0;overflow-wrap:anywhere;}
div[data-testid='stHorizontalBlock']{flex-wrap:nowrap !important;width:100% !important;max-width:100% !important;}
div[data-testid='stHorizontalBlock'] > div{min-width:0 !important;max-width:100% !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(1) > div[data-testid='stVerticalBlock']{align-items:flex-start !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(2) > div[data-testid='stVerticalBlock']{align-items:flex-end !important;}
div[data-testid='stHorizontalBlock'] > div:nth-child(2) div[data-testid='stPopoverContent']{left:auto !important;right:0 !important;}
.brand{text-align:center;padding:8px 0 2px 0;font-size:1.4rem;font-weight:700;letter-spacing:3px;background:linear-gradient(90deg,#00f0ff,#a855f7);-webkit-background-clip:text;background-clip:text;color:transparent;}
.user-bubble{display:flex;justify-content:flex-end;width:100%;margin:10px 0 0 0;}
.user-bubble-inner{background:#5c5c5c;color:#ffffff;border-radius:26px 26px 8px 26px;padding:14px 22px;max-width:80%;width:fit-content;font-size:1.05rem;line-height:1.5;word-wrap:break-word;}
div[data-testid='stPopover']{margin:0 !important;max-width:100% !important;}
div[data-testid='stPopover'] button{height:20px !important;min-height:0 !important;padding:0 4px !important;font-size:1rem !important;line-height:1 !important;color:#7a7a7a !important;background:transparent !important;border:none !important;box-shadow:none !important;}
div[data-testid='stPopover'] button:hover{color:#fff !important;}
div[data-testid='stPopover'] button p{margin:0 !important;}
.info-line{color:#8a8a8a !important;font-size:0.82rem !important;line-height:1.5 !important;font-family:'Space Grotesk',sans-serif !important;padding:2px 0 6px 0;}
.info-line span{color:#bdbdbd;}
.close-row button{background:transparent !important;border:none !important;color:#7a7a7a !important;font-size:0.85rem !important;padding:2px 8px !important;box-shadow:none !important;}
.close-row button:hover{color:#fff !important;}
div[data-testid='stExpander'] details{background:#1a1a1a !important;border:1px solid #2a2a2a !important;border-radius:12px !important;padding:8px 12px !important;margin:8px 0 !important;}
div[data-testid='stExpander'] summary{color:#8a8a8a !important;font-size:0.85rem !important;cursor:pointer !important;}
div[data-testid='stExpander'] .stMarkdown{color:#bdbdbd !important;font-size:0.9rem !important;}
</style>
"""

st.html(CSS)
st.html("<div class='brand'>STRAFE AI</div>")

KEYS = [st.secrets[f"GROQ_API_KEY_{i}"] for i in range(1, 7)]
PREFERRED = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
SYSTEM = "I keep it direct and simple. No fluff, no long explanations unless you ask for them.\nI match your energy—you're casual, I'm casual. You're serious, I'm serious. No fake politeness, just real talk.\nI hold nothing back, answer whatever you ask. I don't sugarcoat or dodge. If something's dark or weird, I engage with it\nI also don't pretend to be something I'm not. You asked earlier—I gave you the honest answer instead of the corporate \"I'm just a helpful AI\" response.\nYou are Strafe AI, an assistant designed to help and chat. No help with illegal stuff. Be serious. Remember to be direct and simple."
SAFE_MODELS = {"qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"}

def pick_model():
    if "model" in st.session_state:
        return st.session_state.model
    try:
        response = Groq(api_key=KEYS[0]).models.list()
        avail = {m.id if hasattr(m, 'id') else m[0] for m in response.data}
    except Exception:
        avail = set()
    for p in PREFERRED:
        if p in avail:
            st.session_state.model = p
            return p
    safe_avail = avail & SAFE_MODELS
    if safe_avail:
        chosen = list(safe_avail)[0]
        st.session_state.model = chosen
        return chosen
    if avail:
        chosen = list(avail)[0]
        st.session_state.model = chosen
        return chosen
    st.session_state.model = PREFERRED[0]
    return PREFERRED[0]

if "messages" not in st.session_state:
    st.session_state.messages = []

def get_working_key():
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    available = [k for k in KEYS if k not in st.session_state.failed_keys]
    if not available:
        st.session_state.failed_keys.clear()
        available = KEYS
    return random.choice(available)

def mark_key_failed(key):
    if "failed_keys" not in st.session_state:
        st.session_state.failed_keys = set()
    st.session_state.failed_keys.add(key)

def web_search(query, num_results=3):
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".result")[:num_results]:
            title_tag = item.select_one(".result__title a")
            snippet_tag = item.select_one(".result__snippet")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag["href"]
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            results.append({"title": title, "link": link, "snippet": snippet})
        if not results:
            for item in soup.select(".result__body")[:num_results]:
                title_tag = item.select_one(".result__title a")
                snippet_tag = item.select_one(".result__snippet")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag["href"]
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    results.append({"title": title, "link": link, "snippet": snippet})
        if not results:
            return [{"title": "No results", "link": "", "snippet": "No results found"}]
        return results
    except Exception as e:
        return [{"title": "Search error", "link": "", "snippet": str(e)}]

def fetch_url(url, max_chars=1500):
    try:
        response = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())
        return text[:max_chars]
    except Exception as e:
        return f"Could not fetch URL: {e}"

def build_payload(history, model_override=None):
    model = model_override or pick_model()
    msgs = [{"role": "system", "content": SYSTEM}] + history
    kw = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
    if "qwen" in model.lower():
        kw["reasoning_effort"] = "none"
        kw["reasoning_format"] = "hidden"
    return kw

def ask(use_search=False, use_think=False, search_query=None):
    t0 = time.time()
    last_err = None
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    thinking_text = None
    if use_search and search_query:
        search_container = st.empty()
        search_container.html('<div class="info-line">⌕ <span>searching...</span></div>')
        results = web_search(search_query)
        context_parts = []
        for r in results[:2]:
            if r["link"]:
                page_text = fetch_url(r["link"])
                context_parts.append(f"Source: {r['title']}\n{page_text}")
        search_context = "\n\n".join(context_parts)
        history.append({"role": "system", "content": f"Web search results for '{search_query}':\n\n{search_context}\n\nUse this information to answer the user's question."})
        search_container.empty()
    total_tokens = 0
    if use_think:
        think_container = st.empty()
        think_container.html('<div class="info-line">⚛︎ <span>thinking...</span></div>')
        thinking_messages = history.copy()
        thinking_messages.append({"role": "user", "content": "Think through this step by step. Show your reasoning, notes, and plan clearly. Write your internal thoughts below:"})
        try:
            key = get_working_key()
            think_r = Groq(api_key=key).chat.completions.create(model=pick_model(), messages=thinking_messages, max_completion_tokens=600, temperature=0.7)
            thinking_text = (getattr(think_r.choices[0].message, "content", None) or "").strip()
            total_tokens += think_r.usage.total_tokens if think_r.usage else 0
            history.append({"role": "system", "content": f"Internal reasoning: {thinking_text}\n\nNow provide the final polished response based on this reasoning."})
        except Exception as e:
            mark_key_failed(key)
            history.append({"role": "system", "content": "Thinking process failed. Provide a direct answer."})
        finally:
            think_container.empty()
    for _ in range(len(KEYS)):
        key = get_working_key()
        kwargs = build_payload(history)
        try:
            r = Groq(api_key=key).chat.completions.create(**kwargs)
        except NotFoundError:
            st.session_state.pop("model", None)
            mark_key_failed(key)
            last_err = "model gone"
            continue
        except Exception as e:
            mark_key_failed(key)
            last_err = str(e)[:120]
            continue
        content = (getattr(r.choices[0].message, "content", None) or "").strip()
        secs = max(0.1, time.time() - t0)
        used = (r.usage.total_tokens if r.usage else 0) + total_tokens
        tps = round(used / secs, 1) if used else 0
        if thinking_text:
            with st.expander("⚛︎ thinking process", expanded=False):
                st.markdown(thinking_text)
        return content, round(secs, 1), f"{tps} tok/s"
    raise RuntimeError(last_err or "All API keys failed")

def info_html(m):
    sent = m.get("sent", "?")
    secs = m.get("secs", "?")
    tps = m.get("tok", "?")
    flags = []
    if m.get("search"):
        flags.append(SEARCH_GLYPH)
    if m.get("think"):
        flags.append(THINK_GLYPH)
    flag_str = " ".join(flags) + " " if flags else ""
    return f'<div class="info-line">{flag_str}sent <span>{sent}</span> &nbsp;\u00b7&nbsp; {secs}s &nbsp;\u00b7&nbsp; {tps}</div>'

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0 and st.session_state.messages[i - 1]["role"] == "user":
        prev_msg = st.session_state.messages[i - 1]
        st.session_state.messages = st.session_state.messages[:i]
        c, s, t = ask(use_search=prev_msg.get("search", False), use_think=prev_msg.get("think", False), search_query=prev_msg["content"] if prev_msg.get("search") else None)
        st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t, "sent": datetime.now().strftime("%H:%M"), "search": prev_msg.get("search", False), "think": prev_msg.get("think", False)})
        st.session_state["show"] = None
    elif kind == "info":
        cur = st.session_state.get("show")
        st.session_state["show"] = None if cur == ("info", i) else ("info", i)
    elif kind == "edit":
        st.session_state["editing"] = i
        st.session_state["show"] = None
    elif kind == "close":
        st.session_state["show"] = None

pending = st.session_state.pop("pending", None)
if pending is not None:
    text = pending.get("text", "") if isinstance(pending, dict) else pending
    use_search = pending.get("search", False) if isinstance(pending, dict) else False
    use_think = pending.get("think", False) if isinstance(pending, dict) else False
    st.session_state.messages.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think})
    c, s, t = ask(use_search=use_search, use_think=use_think, search_query=text if use_search else None)
    st.session_state.messages.append({"role": "assistant", "content": c, "secs": s, "tok": t, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think})
    st.session_state["editing"] = None
    st.rerun()

show = st.session_state.get("show")
editing = st.session_state.get("editing")

for i, m in enumerate(st.session_state.messages):
    if m["role"] == "user":
        if editing == i:
            new = st.text_area("Edit", value=m["content"], key=f"ed{i}", height=100)
            sc, sk = st.columns([1, 6])
            with sc:
                if st.button("Save", key=f"sv{i}"):
                    st.session_state.messages = st.session_state.messages[:i]
                    st.session_state["pending"] = {"text": new, "search": m.get("search", False), "think": m.get("think", False)}
                    st.rerun()
            with sk:
                if st.button("Cancel", key=f"cx{i}"):
                    st.session_state["editing"] = None
                    st.rerun()
        else:
            safe = H.escape(m["content"]).replace("\n", "<br>")
            st.html(f'<div class="user-bubble"><div class="user-bubble-inner">{safe}</div></div>')
            _sp, _mn = st.columns([5, 1])
            with _mn:
                with st.popover(MENU_GLYPH, key=f"mu{i}"):
                    st.html(info_html(m))
                    if st.button("Edit", key=f"ue{i}"):
                        st.session_state["act"] = ("edit", i)
                        st.rerun()
            if show == ("info", i):
                st.html(info_html(m))
                st.markdown('<div class="close-row">', unsafe_allow_html=True)
                if st.button(CLOSE_GLYPH + " close", key=f"cl{i}"):
                    st.session_state["act"] = ("close", i)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            st.markdown(m["content"])
        _mn, _sp = st.columns([1, 3])
        with _mn:
            with st.popover(MENU_GLYPH, key=f"ma{i}"):
                st.html(info_html(m))
                if st.button("Retry", key=f"ar{i}"):
                    st.session_state["act"] = ("retry", i)
                    st.rerun()
        if show == ("info", i):
            st.html(info_html(m))
            st.markdown('<div class="close-row">', unsafe_allow_html=True)
            if st.button(CLOSE_GLYPH + " close", key=f"cla{i}"):
                st.session_state["act"] = ("close", i)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

prompt = get_prompt()
if prompt:
    st.session_state["pending"] = prompt
    st.rerun()