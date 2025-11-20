# -----------------------------------------------------------
# FILENAME: frontend/app.py (FINAL - READY FOR GIT PUSH)
# -----------------------------------------------------------
import streamlit as st
import requests
import base64
import uuid
import json
from datetime import datetime, timedelta 
from st_copy_button import st_copy_button 
from streamlit_local_storage import LocalStorage

# ==========================================
# ⚙️ CONFIGURATION: CONNECTION SETTINGS
# ==========================================

# 🔴 IMPORTANT: Set to FALSE for the Live Website
USE_LOCAL_BACKEND = False

if USE_LOCAL_BACKEND:
    API_BASE_URL = "http://127.0.0.1:8000"
else:
    API_BASE_URL = "https://clarityai-tnq0.onrender.com"

# Headers to mimic a real browser and avoid 403 errors
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================

# --- Page Configuration ---
st.set_page_config(
    page_title="ClarityAI",
    page_icon="💡",
    layout="wide"
)

# --- Initialize Storage ---
storage = LocalStorage(key="clarity_ai_storage_v3")

# --- Main App Title ---
st.title("ClarityAI 💡")

# --- Unified State Management Functions ---
def get_app_data():
    """Retrieves the entire app data object from storage."""
    data = storage.getItem("app_data")
    if not data:
        return {"chats": {}, "current_chat_id": None}
    return data

def save_app_data(data):
    """Saves the entire app data object to storage."""
    storage.setItem("app_data", data)

def generate_smart_title(prompt_text):
    """Generates a cleaner, shorter title from the prompt."""
    first_line = prompt_text.strip().split('\n')[0]
    words = first_line.split()
    if len(words) > 5:
        return " ".join(words[:5]) + "..."
    if len(first_line) > 35:
        return first_line[:35] + "..."
    return first_line

# --- Load State ---
if "app_data" not in st.session_state:
    st.session_state.app_data = get_app_data()

# --- Sidebar for Navigation AND File Uploads ---
with st.sidebar:
    st.title("Navigation")
    
    # Visual indicator for connection mode
    if USE_LOCAL_BACKEND:
        st.caption("🟢 Mode: Local Host")
    else:
        st.caption("☁️ Mode: Live Server")

    app_mode = st.selectbox("Choose your mode:", 
                            ["General Chatbot", "Documentation Generator"])
    
    # --- "New Chat" Button ---
    if st.button("New Chat", use_container_width=True, type="primary"):
        new_chat_id = str(uuid.uuid4())
        st.session_state.app_data["chats"][new_chat_id] = {
            "title": "New Chat",
            "file": None,
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
        st.session_state.app_data["current_chat_id"] = new_chat_id
        save_app_data(st.session_state.app_data)
        st.rerun() 

    st.divider()

    # --- SMART CHAT HISTORY ---
    st.title("Chat History")
    
    all_chats = []
    for c_id, chat_data in st.session_state.app_data["chats"].items():
        # Filter out empty new chats
        if chat_data["title"] == "New Chat" and not chat_data["messages"]:
            continue
            
        # Handle timestamp (fallback for old chats)
        ts_str = chat_data.get("created_at", datetime.now().isoformat())
        try:
            ts_dt = datetime.fromisoformat(ts_str)
        except ValueError:
            ts_dt = datetime.now()
            
        all_chats.append({
            "id": c_id,
            "title": chat_data["title"],
            "dt": ts_dt
        })

    # Sort newest first
    all_chats.sort(key=lambda x: x["dt"], reverse=True)

    # Group by date
    groups = {"Today": [], "Yesterday": [], "Previous 7 Days": [], "Older": []}
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    for chat in all_chats:
        chat_date = chat["dt"].date()
        if chat_date == today:
            groups["Today"].append(chat)
        elif chat_date == yesterday:
            groups["Yesterday"].append(chat)
        elif chat_date > last_week:
            groups["Previous 7 Days"].append(chat)
        else:
            groups["Older"].append(chat)

    # Render groups
    def draw_group(group_name, chats_list):
        if chats_list:
            st.markdown(f"**{group_name}**")
            for chat in chats_list:
                is_active = chat["id"] == st.session_state.app_data["current_chat_id"]
                button_type = "secondary" if not is_active else "primary"
                if st.button(chat["title"], key=chat["id"], use_container_width=True, type=button_type):
                    st.session_state.app_data["current_chat_id"] = chat["id"]
                    save_app_data(st.session_state.app_data)
                    st.rerun()
    
    draw_group("Today", groups["Today"])
    draw_group("Yesterday", groups["Yesterday"])
    draw_group("Previous 7 Days", groups["Previous 7 Days"])
    draw_group("Older", groups["Older"])
    
    # --- DELETE HISTORY BUTTON ---
    st.divider()
    if st.button("🗑️ Delete All History", use_container_width=True):
        st.session_state.app_data["chats"] = {}
        st.session_state.app_data["current_chat_id"] = None
        save_app_data(st.session_state.app_data)
        st.rerun()

    st.divider() 
    st.title("File Context 📎")
    
    current_chat_id = st.session_state.app_data["current_chat_id"]
    current_chat = st.session_state.app_data["chats"].get(current_chat_id)

    uploaded_file = st.file_uploader(
        "Upload a file", 
        type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'md', 'py'],
        key="sidebar_file_uploader",
        disabled=(current_chat is None)
    )
    
    if st.button("Clear File", use_container_width=True, disabled=(current_chat is None)):
        if current_chat:
            current_chat["file"] = None
            save_app_data(st.session_state.app_data)
            st.rerun() 

    if uploaded_file is not None and current_chat:
        file_bytes = uploaded_file.getvalue()
        b64_string = base64.b64encode(file_bytes).decode('utf-8')
        new_file_data = {
            "name": uploaded_file.name,
            "type": uploaded_file.type,
            "b64_string": b64_string
        }
        if current_chat["file"] != new_file_data:
            current_chat["file"] = new_file_data
            save_app_data(st.session_state.app_data)
            st.rerun()

    if current_chat and current_chat["file"]:
        st.info(f"Context: **{current_chat['file']['name']}**")
    elif current_chat:
        st.caption("No file attached.")


# === MODE 1: DOCUMENTATION GENERATOR =========================
if app_mode == "Documentation Generator":
    st.header("Code Documentation Generator 📚")
    st.subheader("Upload a code file to generate complete documentation.")

    doc_file = st.file_uploader("Upload your code file", type=['py', 'js', 'java', 'txt', 'md'], key="doc_uploader")

    if doc_file:
        content = doc_file.read().decode()
        st.code(content, language='python') 

        if st.button("Generate Documentation"):
            with st.spinner("Analyzing code..."):
                try:
                    with requests.post(
                        f"{API_BASE_URL}/generate-docs",
                        json={"code": content},
                        stream=True,
                        headers=REQUEST_HEADERS
                    ) as response:
                        if response.status_code == 200:
                            st.success("Documentation generated!")
                            def stream_doc_chunks():
                                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                                    yield chunk
                            doc_text = st.write_stream(stream_doc_chunks())
                            st_copy_button(doc_text, "Copy documentation", "Copied!")
                        else:
                            st.error(f"Error from backend: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error(f"Failed to connect to backend at {API_BASE_URL}. Is it running?")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# === MODE 2: GENERAL CHATBOT =======================
elif app_mode == "General Chatbot":
    
    st.header("General Chatbot 🤖")
    
    current_chat_id = st.session_state.app_data["current_chat_id"]
    current_chat = st.session_state.app_data["chats"].get(current_chat_id)

    # Fallback for empty state
    if not current_chat:
        new_chat_id = str(uuid.uuid4())
        st.session_state.app_data["chats"][new_chat_id] = {
            "title": "New Chat",
            "file": None,
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
        st.session_state.app_data["current_chat_id"] = new_chat_id
        save_app_data(st.session_state.app_data)
        st.rerun()

    for message in current_chat["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    def get_chat_stream(_prompt_text, _file_info, _chat_history):
        try:
            data = {"message": _prompt_text, "history": json.dumps(_chat_history)}
            files = {}
            if _file_info:
                file_bytes = base64.b64decode(_file_info["b64_string"])
                files["file"] = (_file_info["name"], file_bytes, _file_info["type"])
            
            with requests.post(
                f"{API_BASE_URL}/chat", 
                data=data, 
                files=files, 
                stream=True,
                headers=REQUEST_HEADERS
            ) as response:
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                        yield chunk
                else:
                    yield f"Error from backend: {response.text}"
        except requests.exceptions.ConnectionError:
             yield f"Failed to connect to backend at {API_BASE_URL}. Is it running?"
        except Exception as e:
            yield f"An error occurred: {e}"

    if prompt := st.chat_input("What is up?"):
        
        is_first_message = len(current_chat["messages"]) == 0
        
        if is_first_message:
            current_chat["title"] = generate_smart_title(prompt)
            if "created_at" not in current_chat:
                current_chat["created_at"] = datetime.now().isoformat()
        
        current_chat["messages"].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_chunks = st.write_stream(
                get_chat_stream(prompt, current_chat["file"], current_chat["messages"])
            )
        
        current_chat["messages"].append({"role": "assistant", "content": response_chunks})
        
        save_app_data(st.session_state.app_data)
        
        if is_first_message:
            st.rerun()