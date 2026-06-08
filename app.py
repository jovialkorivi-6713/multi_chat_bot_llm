import streamlit as st
import json
import os
import uuid
import random
import urllib.parse
import requests
from utils.llm import get_response
from utils.prompts import PROMPTS

# 1. Page Configuration & Theme
st.set_page_config(
    page_title="Multi_chat_bot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# 2. Chat Persistence & History Logic
HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history_data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.sidebar.error(f"Error saving chat: {e}")

# Initialize Session State
if "sessions" not in st.session_state:
    st.session_state.sessions = load_history()
    if not st.session_state.sessions:
        default_id = str(uuid.uuid4())
        st.session_state.sessions[default_id] = {
            "title": "New Chat Thread",
            "messages": [],
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 2048,
            "system_prompt": "You are a helpful, advanced AI assistant."
        }
        save_history(st.session_state.sessions)

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]

active_id = st.session_state.active_session_id
# Ensure the active ID still exists, otherwise fallback
if active_id not in st.session_state.sessions:
    st.session_state.active_session_id = list(st.session_state.sessions.keys())[0]
    active_id = st.session_state.active_session_id

# Sync widgets values to/from session state to allow persistence across tabs
def sync_session_to_widgets(session_id):
    sess = st.session_state.sessions[session_id]
    st.session_state.model_name = sess.get("model", "llama-3.3-70b-versatile")
    st.session_state.temperature = sess.get("temperature", 0.7)
    st.session_state.top_p = sess.get("top_p", 1.0)
    st.session_state.max_tokens = sess.get("max_tokens", 2048)
    st.session_state.system_prompt = sess.get("system_prompt", "You are a helpful, advanced AI assistant.")

# Trigger sync if active_session_id has changed or on initial load
if "last_synced_session_id" not in st.session_state or st.session_state.last_synced_session_id != st.session_state.active_session_id:
    sync_session_to_widgets(st.session_state.active_session_id)
    st.session_state.last_synced_session_id = st.session_state.active_session_id

active_session = st.session_state.sessions[st.session_state.active_session_id]

# 3. Sidebar (ChatGPT Style UI)
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #1d1d1f; font-weight: 600; font-size: 1.4rem; letter-spacing: -0.02em;'>⚡ AI HUB</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # New Thread Button
    if st.button("➕ New Chat Thread", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.sessions[new_id] = {
            "title": f"New Chat {len(st.session_state.sessions) + 1}",
            "messages": [],
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 2048,
            "system_prompt": "You are a helpful, advanced AI assistant."
        }
        save_history(st.session_state.sessions)
        st.session_state.active_session_id = new_id
        st.rerun()

    # Active Tool / Mode Selection
    st.markdown("### 🛠️ Mode Selection")
    
    if "current_tool" not in st.session_state:
        st.session_state.current_tool = "AI Chat"

    active_tool = st.selectbox(
        "Select Mode:",
        [
            "AI Chat",
            "Text Summary",
            "Grammar Fixer",
            "Email Writer",
            "LinkedIn Post Generator",
            "Text Translator",
            "Story Writer",
            "Code Explainer",
            "Code Generator",
        ],
        index=0,
        key="tool_selector"
    )

    # Reset last tool outputs when swapping modes to avoid confusion
    if active_tool != st.session_state.current_tool:
        st.session_state.current_tool = active_tool
        if "last_tool_output" in st.session_state:
            del st.session_state.last_tool_output
        if "last_tool_input" in st.session_state:
            del st.session_state.last_tool_input
        st.rerun()

    st.markdown("---")

    # Saved Threads List
    st.markdown("### 💬 Saved Threads")
    
    # We display threads inside a container
    for sid, sess in list(st.session_state.sessions.items()):
        is_active = (sid == st.session_state.active_session_id)
        title_label = sess.get("title", "Untitled Chat")
        
        # UI layout for thread list
        col_btn, col_del = st.columns([0.85, 0.15])
        with col_btn:
            if st.button(
                f"💬 {title_label}", 
                key=f"sel_{sid}", 
                use_container_width=True, 
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_session_id = sid
                st.rerun()
        with col_del:
            if len(st.session_state.sessions) > 1:
                if st.button("🗑️", key=f"del_{sid}", help="Delete Thread"):
                    del st.session_state.sessions[sid]
                    save_history(st.session_state.sessions)
                    # If we deleted the active thread, switch to another
                    if st.session_state.active_session_id == sid:
                        fallback_id = list(st.session_state.sessions.keys())[0]
                        st.session_state.active_session_id = fallback_id
                    st.rerun()

    st.markdown("---")

    # Rename Current Thread
    st.markdown("### 📝 Rename Current Thread")
    new_title = st.text_input("Thread Title:", value=active_session.get("title", ""), key="rename_title_input")
    if new_title and new_title != active_session.get("title", ""):
        active_session["title"] = new_title
        save_history(st.session_state.sessions)
        st.rerun()

    st.markdown("---")

    # Advanced Settings Expander
    with st.expander("⚙️ Model Settings", expanded=False):
        model_name = st.selectbox(
            "Model",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ],
            key="model_name"
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            step=0.1,
            key="temperature"
        )
        
        top_p = st.slider(
            "Top-P",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key="top_p"
        )
        
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=256,
            max_value=8192,
            step=256,
            key="max_tokens"
        )
        
        system_prompt = st.text_area(
            "System Prompt",
            key="system_prompt"
        )

    # Sync any slider changes directly to the active session dictionary
    active_session["model"] = st.session_state.model_name
    active_session["temperature"] = st.session_state.temperature
    active_session["top_p"] = st.session_state.top_p
    active_session["max_tokens"] = st.session_state.max_tokens
    active_session["system_prompt"] = st.session_state.system_prompt
    save_history(st.session_state.sessions)

    st.markdown("---")

    # Export & Thread Management Buttons
    st.markdown("### 📁 Thread Actions")
    
    # Download thread logic
    chat_messages = active_session.get("messages", [])
    
    # JSON Download
    chat_json = json.dumps({
        "title": active_session.get("title"),
        "model": active_session.get("model"),
        "temperature": active_session.get("temperature"),
        "system_prompt": active_session.get("system_prompt"),
        "messages": chat_messages
    }, indent=2)
    
    st.download_button(
        label="📥 Download Chat (JSON)",
        data=chat_json,
        file_name=f"{active_session.get('title').lower().replace(' ', '_')}_chat.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Text format Download
    chat_txt = f"Chat Session: {active_session.get('title')}\nModel: {active_session.get('model')}\n"
    chat_txt += "="*40 + "\n\n"
    for msg in chat_messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        chat_txt += f"[{role}]:\n{msg['content']}\n\n"
    chat_txt += "="*40 + "\n"
    
    st.download_button(
        label="📄 Download Chat (TXT)",
        data=chat_txt,
        file_name=f"{active_session.get('title').lower().replace(' ', '_')}_chat.txt",
        mime="text/plain",
        use_container_width=True
    )

    if st.button("🧹 Clear Chat History", use_container_width=True, help="Clears messages in current thread"):
        active_session["messages"] = []
        save_history(st.session_state.sessions)
        st.toast("Chat history cleared!")
        st.rerun()

    if st.button("⚠️ Reset All Threads", use_container_width=True, help="Deletes all threads"):
        if os.path.exists(HISTORY_FILE):
            try:
                os.remove(HISTORY_FILE)
            except Exception:
                pass
        st.session_state.sessions = {}
        fallback_id = str(uuid.uuid4())
        st.session_state.sessions[fallback_id] = {
            "title": "New Chat Thread",
            "messages": [],
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 2048,
            "system_prompt": "You are a helpful, advanced AI assistant."
        }
        save_history(st.session_state.sessions)
        st.session_state.active_session_id = fallback_id
        st.toast("All sessions reset!")
        st.rerun()

# 4. Main UI Content Area
st.markdown(f"<div class='main-title'>KickStack IQ</div>", unsafe_allow_html=True)
st.markdown(f"<div class='badge'>✨ Mode: {active_tool}</div>", unsafe_allow_html=True)

# ----------------- MODE: AI Chat -----------------
if active_tool == "AI Chat":
    # Display Chat Messages
    for msg in active_session.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "image_base64" in msg and msg["image_base64"]:
                import base64
                try:
                    img_bytes = base64.b64decode(msg["image_base64"])
                    st.image(img_bytes, use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to display image: {e}")

    # User Input
    prompt = st.chat_input("Ask anything...")

    if prompt:
        # Append User Message
        active_session["messages"].append({
            "role": "user",
            "content": prompt
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        # Title auto-summarization on first message
        if len(active_session["messages"]) == 1 or active_session.get("title", "").startswith("New Chat"):
            short_title = prompt[:30] + ("..." if len(prompt) > 30 else "")
            active_session["title"] = short_title

        # Stream LLM Response
        with st.chat_message("assistant"):
            # Gather past messages (excluding system prompt as llm.py handles it separately)
            history = active_session["messages"][:-1]
            
            # Response stream generator
            response_generator = get_response(
                prompt=prompt,
                history=history,
                temperature=st.session_state.temperature,
                top_p=st.session_state.top_p,
                max_tokens=st.session_state.max_tokens,
                system_prompt=st.session_state.system_prompt,
                model_name=st.session_state.model_name,
                stream=True
            )
            
            # Write stream
            full_response = st.write_stream(response_generator)

        # Append Assistant Response
        active_session["messages"].append({
            "role": "assistant",
            "content": full_response
        })
        save_history(st.session_state.sessions)
        st.rerun()

# ----------------- MODE: Text Summary -----------------
elif active_tool == "Text Summary":
    st.markdown("### 📝 Text Summarizer")
    st.markdown("Paste long articles, documents, or notes to get a structured, key-point summary.")
    
    text_input = st.text_area("Paste text to summarize here:", height=250, placeholder="Enter text here...")
    
    if st.button("⚡ Summarize Text"):
        if not text_input.strip():
            st.warning("Please provide some text to summarize.")
        else:
            formatted_prompt = PROMPTS["Text Summary"].format(text_input[:8000])
            with st.spinner("Analyzing and summarizing..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Summarize text:\n\n{text_input[:200]}..."

# ----------------- MODE: Grammar Fixer -----------------
elif active_tool == "Grammar Fixer":
    st.markdown("### ✍️ Grammar Fixer & Editor")
    st.markdown("Submit text with typos, grammar bugs, or awkward phrasing to receive a polished, clean copy.")
    
    text_input = st.text_area("Paste text to fix here:", height=200, placeholder="Enter text here...")
    
    if st.button("⚡ Fix Grammar & Polish"):
        if not text_input.strip():
            st.warning("Please enter some text to correct.")
        else:
            formatted_prompt = PROMPTS["Grammar Fixer"].format(text_input[:8000])
            with st.spinner("Editing text..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Correct grammar in:\n\n{text_input[:200]}..."

# ----------------- MODE: Email Writer -----------------
elif active_tool == "Email Writer":
    st.markdown("### 📧 Professional Email Writer")
    st.markdown("Generate clean, well-tailored emails for any business or personal occasion.")
    
    col1, col2 = st.columns(2)
    with col1:
        email_topic = st.text_area("What is the email about? (Key Points)", height=120, placeholder="e.g., Requesting project update, following up on proposal...")
        email_recipient = st.text_input("Who is the recipient?", placeholder="e.g., Client, Manager, Marketing Team, Professor...")
    with col2:
        email_tone = st.selectbox("Tone of the email:", ["Professional", "Friendly & Warm", "Urgent/Direct", "Apologetic", "Persuasive"])
        email_context = st.text_area("Additional Context (Optional)", height=120, placeholder="e.g., We missed the deadline yesterday, mention the attachment, keep it under 150 words...")
        
    if st.button("⚡ Generate Email"):
        if not email_topic.strip():
            st.warning("Please describe what the email is about.")
        else:
            formatted_prompt = PROMPTS["Email Writer"].format(
                topic=email_topic,
                tone=email_tone,
                recipient=email_recipient,
                context=email_context if email_context.strip() else "None provided"
            )
            with st.spinner("Drafting email..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Write a {email_tone} email to {email_recipient} regarding: {email_topic}"

# ----------------- MODE: LinkedIn Post Generator -----------------
elif active_tool == "LinkedIn Post Generator":
    st.markdown("### 🚀 LinkedIn Post Creator")
    st.markdown("Craft highly engaging posts with formatting, tags, and hooks optimized for professional networks.")
    
    col1, col2 = st.columns(2)
    with col1:
        post_content = st.text_area("What is the post about?", height=120, placeholder="e.g., Lessons learned launch our SaaS, sharing tips on Python, celebrating a work promotion...")
        post_tone = st.selectbox("Post Tone:", ["Professional", "Casual & Relatable", "Inspirational/Storytelling", "Educational/Insights", "Promotional/Pitching"])
    with col2:
        post_keywords = st.text_input("Keywords to include (comma-separated):", placeholder="e.g., tech, AI, growth, coding, startup")
        col_em, col_hash = st.columns(2)
        with col_em:
            use_emojis = st.checkbox("Include Emojis", value=True)
        with col_hash:
            use_hashtags = st.checkbox("Include Hashtags", value=True)
            
    if st.button("⚡ Generate LinkedIn Post"):
        if not post_content.strip():
            st.warning("Please input some details about what the post should contain.")
        else:
            formatted_prompt = PROMPTS["LinkedIn Post Generator"].format(
                content=post_content,
                tone=post_tone,
                keywords=post_keywords if post_keywords.strip() else "None",
                use_emojis="Yes" if use_emojis else "No",
                use_hashtags="Yes" if use_hashtags else "No"
            )
            with st.spinner("Generating post..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"LinkedIn post on: {post_content[:50]}... in {post_tone} tone."

# ----------------- MODE: Text Translator -----------------
elif active_tool == "Text Translator":
    st.markdown("### 🌐 Universal Translator")
    st.markdown("Translate words, articles, or text snippets into multiple languages with high fidelity.")
    
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        text_to_translate = st.text_area("Enter text to translate:", height=150, placeholder="Type or paste text...")
    with col2:
        target_lang = st.selectbox(
            "Target Language:",
            ["Spanish", "French", "German", "Japanese", "Chinese", "Hindi", "Telugu", "Arabic", "Portuguese", "Italian", "Russian", "Korean", "Dutch"]
        )
        
    if st.button("⚡ Translate"):
        if not text_to_translate.strip():
            st.warning("Please enter some text to translate.")
        else:
            formatted_prompt = PROMPTS["Text Translator"].format(
                target_lang=target_lang,
                text=text_to_translate
            )
            with st.spinner(f"Translating to {target_lang}..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Translate text to {target_lang}:\n\n'{text_to_translate[:100]}...'"

# ----------------- MODE: Story Writer -----------------
elif active_tool == "Story Writer":
    st.markdown("### 📖 Creative Story Writer")
    st.markdown("Create compelling narratives, fan fiction, or story plots based on your custom prompt details.")
    
    col1, col2 = st.columns(2)
    with col1:
        story_concept = st.text_area("What is the story prompt/concept?", height=120, placeholder="e.g., An astronaut discovers an ancient temple on a remote moon...")
        story_genre = st.selectbox("Genre:", ["Sci-Fi", "Fantasy", "Mystery/Detective", "Romance", "Thriller/Horror", "Historical Fiction", "Comedy/Satire"])
    with col2:
        story_tone = st.selectbox("Tone:", ["Adventurous & Epic", "Dark & Atmospheric", "Whimsical & Magical", "Suspenseful", "Humorous", "Emotional & Melancholic"])
        story_length = st.selectbox("Length:", ["Short (~300 words)", "Medium (~700 words)", "Long (~1200 words)"])
        
    if st.button("⚡ Write Story"):
        if not story_concept.strip():
            st.warning("Please write a story concept/prompt.")
        else:
            formatted_prompt = PROMPTS["Story Writer"].format(
                concept=story_concept,
                genre=story_genre,
                tone=story_tone,
                length=story_length
            )
            with st.spinner("Writing story..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Write a {story_genre} story ({story_length}) in {story_tone} tone about: {story_concept[:50]}..."

# ----------------- MODE: Code Explainer -----------------
elif active_tool == "Code Explainer":
    st.markdown("### 💡 Code Explainer")
    st.markdown("Paste code snippets to receive high-level summaries, line-by-line analyses, and complexity annotations.")
    
    code_input = st.text_area("Paste code here:", height=200, placeholder="def example():\n    return 'Hello World'")
    
    if st.button("⚡ Explain Code"):
        if not code_input.strip():
            st.warning("Please provide code to explain.")
        else:
            formatted_prompt = PROMPTS["Code Explainer"].format(code_input[:8000])
            with st.spinner("Analyzing code..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Explain code snippet:\n```\n{code_input[:100]}...\n```"

# ----------------- MODE: Code Generator -----------------
elif active_tool == "Code Generator":
    st.markdown("### 💻 Code Generator")
    st.markdown("Generate clean, syntax-highlighted code files with library support and quick comments.")
    
    col1, col2 = st.columns(2)
    with col1:
        code_request = st.text_area("What do you want the code to do?", height=120, placeholder="e.g., Write a function to check if a string is palindrome...")
        code_lang = st.selectbox("Programming Language:", ["Python", "JavaScript", "TypeScript", "HTML & CSS", "C++", "Java", "Go", "Rust", "Bash"])
    with col2:
        code_constraints = st.text_area("Additional Constraints/Libraries (Optional):", height=120, placeholder="e.g., Use pandas, do not use built-in reverse functions, make it O(N)...")
        
    if st.button("⚡ Generate Code"):
        if not code_request.strip():
            st.warning("Please specify code requirements.")
        else:
            formatted_prompt = PROMPTS["Code Generator"].format(
                request=code_request,
                language=code_lang,
                constraints=code_constraints if code_constraints.strip() else "None specified"
            )
            with st.spinner("Generating code..."):
                resp_stream = get_response(
                    prompt=formatted_prompt,
                    temperature=st.session_state.temperature,
                    top_p=st.session_state.top_p,
                    max_tokens=st.session_state.max_tokens,
                    model_name=st.session_state.model_name,
                    stream=True
                )
                output = st.write_stream(resp_stream)
            st.session_state.last_tool_output = output
            st.session_state.last_tool_input = f"Generate {code_lang} code for request: {code_request[:50]}..."

# 5. Connect Playground Output to Chat Thread (If Output Exists)
if active_tool != "AI Chat":
    if "last_tool_output" in st.session_state and st.session_state.last_tool_output:
        st.markdown("---")
        st.markdown("<div class='output-card'><strong>📝 Latest Output Ready:</strong> You can copy it above, download it below, or export it directly into the active chat session history to talk about it.</div>", unsafe_allow_html=True)
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("💬 Send to Active Chat Thread", use_container_width=True):
                # Append to messages list
                active_session["messages"].append({
                    "role": "user",
                    "content": f"**[Tool Run: {active_tool}]**\n{st.session_state.last_tool_input}"
                })
                active_session["messages"].append({
                    "role": "assistant",
                    "content": st.session_state.last_tool_output
                })
                save_history(st.session_state.sessions)
                st.toast("Tool output sent to active chat thread!")
        with col_act2:
            st.download_button(
                label="💾 Download Output as TXT",
                data=st.session_state.last_tool_output,
                file_name=f"{active_tool.lower().replace(' ', '_')}_output.txt",
                mime="text/plain",
                use_container_width=True
            )