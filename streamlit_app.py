import streamlit as st
import streamlit.components.v2 as components
from groq import Groq, NotFoundError
import random, time, html as H, json
from datetime import datetime
from duckduckgo_search import DDGS

st.set_page_config(page_title="Strafe AI", page_icon="https://raw.githubusercontent.com/let7829/Strafe-ai/refs/heads/main/logo.png", layout="centered")

SEND_GLYPH = "\u2794"
MENU_GLYPH = "\u22ef"
CLOSE_GLYPH = "\u2715"

INPUT_HTML = '<div id="bar"><div id="cb"><input id="ci" type="text" placeholder="Ask something" autocomplete="off"/><button id="sb" type="button">' + SEND_GLYPH + '</button></div><div id="tools"><button id="btn-search" type="button" class="tool-btn"><span class="icon">\u2315</span><span class="label">Search</span></button><button id="btn-think" type="button" class="tool-btn"><span class="icon">\u269b</span><span class="label">Think</span></button></div></div>'
INPUT_CSS = """
#bar{position:fixed;bottom:16px;left:0;right:0;padding:0 14px;background:transparent;z-index:999999;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:8px;}
#tools{display:flex;gap:8px;width:100%;max-width:760px;justify-content:flex-start;padding-left:4px;}
.tool-btn{height:32px;border-radius:16px;border:1px solid #2a2a2a;background:#1a1a1a;color:#7a7a7a;font-size:0.85rem;cursor:pointer;display:flex;align-items:center;gap:6px;padding:0 12px;transition:all 0.2s;font-family:'Space Grotesk',sans-serif;}
.tool-btn .icon{font-size:1rem;line-height:1;}
.tool-btn .label{white-space:nowrap;}
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
    function updateLabels(){
        btnSearch.querySelector('.label').textContent=searchActive?'Searching':'Search';
        btnThink.querySelector('.label').textContent=thinkActive?'Thinking':'Think';
    }
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
        updateLabels();
    };
    btnThink.onclick=function(){
        thinkActive=!thinkActive;
        this.classList.toggle('active',thinkActive);
        updateLabels();
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
section.main .block-container{padding:0 1rem 160px 1rem !important;max-width:760px;overflow-x:hidden;}
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
SYSTEM = (
    "I keep it direct and simple. No fluff, no long explanations unless you ask for them.\n"
    "I match your energy\u2014you're casual, I'm casual. You're serious, I'm serious. No fake politeness, just real talk.\n"
    "I hold nothing back, answer whatever you ask. I don't sugarcoat or dodge. If something's dark or weird, I engage with it\n"
    "You are Strafe AI, an assistant designed to help and chat. No help with illegal stuff. Be serious. Remember to be direct and simple.\n\n"
    "CRITICAL INSTRUCTION: Your internal training data ends at early 2025. If the user asks a question answer it with web search (like current events, new technology, or recent financial news), YOU MUST USE THE web_search TOOL."
)
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
        results = []
        headers = {"Accept-Encoding": "gzip, deflate, br"}
        with DDGS(headers=headers) as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        if not results:
            return [{"title": "No results", "link": "", "snippet": "Search returned empty. Rely on training data."}]
        return results
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}. Tell the user."}]

def build_payload(history, model_override=None):
    model = model_override or pick_model()
    msgs = [{"role": "system", "content": SYSTEM}] + history
    kw = dict(model=model, messages=msgs, max_completion_tokens=1024, temperature=0.7)
    if "qwen" in model.lower():
        kw["reasoning_effort"] = "medium"
        kw["reasoning_format"] = "parsed"
    elif "gpt-oss" in model.lower():
        kw["reasoning_effort"] = "medium"
        kw["reasoning_format"] = "parsed"
    return kw

def ask(use_search=False, use_think=False, search_query=None, look_back=False):
    t0 = time.time()
    last_err = None
    if look_back:
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    else:
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-15:]]

    tools = None
    if use_search:
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for current info, news, or facts. If the user asks about recent events (like 2026 news), YOU MUST USE THIS TOOL. DO NOT fake the search. If the search returns 'No results' or 'Error', tell the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query. ALWAYS fix spelling mistakes and use clean keywords. (e.g., 'first trillionaire Elon Musk 2026', NOT 'for who first trillionare')."
                        }
                    },
                    "required": ["query"]
                }
            }
        }]

    max_rounds = 5 if use_search else 1
    tool_calls_made = 0

    for _ in range(max_rounds):
        key = get_working_key()
        kwargs = build_payload(history)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        try:
            r = Groq(api_key=key).chat.completions.create(**kwargs)
        except NotFoundError:
            st.session_state.pop("model", None)
            mark_key_failed(key)
            last_err = "model gone"
            continue
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "401" in err_str:
                mark_key_failed(key)
            last_err = err_str[:120]
            continue

        msg = r.choices[0].message
        if tools and getattr(msg, "tool_calls", None):
            tool_calls_made += len(msg.tool_calls)
            if tool_calls_made > 5:
                raise RuntimeError("Tool call limit reached")
            assistant_msg = {"role": "assistant", "content": msg.content or "", "tool_calls": []}
            for tc in msg.tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                })
            history.append(assistant_msg)
            for tc in msg.tool_calls:
                if tc.function.name == "web_search":
                    args = json.loads(tc.function.arguments)
                    results = web_search(args.get("query", ""))
                    context = "\n".join(f"{r['title']}: {r['snippet']} ({r['link']})" for r in results)
                    history.append({"role": "tool", "tool_call_id": tc.id, "content": context})
            continue
        else:
            content = (msg.content or "").strip()
            reasoning = getattr(msg, "reasoning_content", None)
            secs = max(0.1, time.time() - t0)
            used = (r.usage.total_tokens if r.usage else 0)
            tps = round(used / secs, 1) if used else 0
            return {
                "content": content,
                "secs": round(secs, 1),
                "tok": f"{tps} tok/s",
                "sent": datetime.now().strftime("%H:%M"),
                "search": use_search,
                "think": use_think,
                "reasoning": reasoning if use_think else None
            }

    raise RuntimeError(last_err or "All API keys failed")

def info_html(m):
    sent = m.get("sent", "?")
    secs = m.get("secs", "?")
    tps = m.get("tok", "?")
    flags = []
    if m.get("search"):
        flags.append("\u2315")
    if m.get("think"):
        flags.append("\u269b")
    flag_str = " ".join(flags) + " " if flags else ""
    return f'<div class="info-line">{flag_str}sent <span>{sent}</span> &nbsp;\u00b7&nbsp; {secs}s &nbsp;\u00b7&nbsp; {tps}</div>'

act = st.session_state.pop("act", None)
if act:
    kind, i = act
    if kind == "retry" and i > 0 and st.session_state.messages[i - 1]["role"] == "user":
        prev_msg = st.session_state.messages[i - 1]
        st.session_state.messages = st.session_state.messages[:i]
        result = ask(use_search=prev_msg.get("search", False), use_think=prev_msg.get("think", False), search_query=prev_msg["content"] if prev_msg.get("search") else None)
        st.session_state.messages.append({"role": "assistant", **result})
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
    is_look_back = text.strip().lower() == "look_back"
    st.session_state.messages.append({"role": "user", "content": text, "sent": datetime.now().strftime("%H:%M"), "search": use_search, "think": use_think})
    result = ask(use_search=use_search, use_think=use_think, search_query=text if use_search else None, look_back=is_look_back)
    st.session_state.messages.append({"role": "assistant", **result})
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
        reasoning = m.get("reasoning")
        if m.get("think"):
            think_secs = m.get("secs", "?")
            if reasoning:
                with st.expander(f"\u269b Thought for {think_secs}s", expanded=False):
                    st.markdown(reasoning)
            else:
                with st.expander(f"\u269b Thought for {think_secs}s", expanded=False):
                    st.markdown("_Model processed the request but didn't return visible thoughts._")
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