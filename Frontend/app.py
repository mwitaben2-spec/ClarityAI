# -----------------------------------------------------------
# FILENAME: frontend/app.py (FINAL, WITH CHAT HISTORY)
# -----------------------------------------------------------
import streamlit as st
import requests
import base64
import uuid
import json  # <-- 1. IMPORT JSON
from st_copy_button import st_copy_button 
from streamlit_local_storage import LocalStorage

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
        # Return the default structure if no data is found
        return {"chats": {}, "current_chat_id": None}
    return data

def save_app_data(data):
    """Saves the entire app data object to storage."""
    storage.setItem("app_data", data)

# --- Load State ---
# Load the entire data object into session state once
if "app_data" not in st.session_state:
    st.session_state.app_data = get_app_data()


# --- Sidebar for Navigation AND File Uploads ---
with st.sidebar:
    st.title("Navigation")
    app_mode = st.selectbox("Choose your mode:", 
                            ["General Chatbot", "Documentation Generator"])
    
    # --- "New Chat" Button ---
    if st.button("New Chat", use_container_width=True, type="primary"):
        # Create a new, blank chat
        new_chat_id = str(uuid.uuid4())
        st.session_state.app_data["chats"][new_chat_id] = {
            "title": "New Chat",
            "file": None,
            "messages": []
        }
        # Set this new chat as the active one
        st.session_state.app_data["current_chat_id"] = new_chat_id
        
        # Save the *entire* app_data object at once
        save_app_data(st.session_state.app_data)
        st.rerun() 

    st.divider()

    # --- Chat History List ---
    st.title("Chat History")
    
    # Iterate in reverse to show newest chats first
    chat_ids = list(st.session_state.app_data["chats"].keys())
    for chat_id in reversed(chat_ids):
        chat = st.session_state.app_data["chats"][chat_id]
        
        # --- FIX: Don't show the "New Chat" placeholder if it's empty ---
        if chat["title"] == "New Chat" and not chat["messages"]:
            continue
        
        # Button to load this chat
        if st.button(chat["title"], key=chat_id, use_container_width=True):
            st.session_state.app_data["current_chat_id"] = chat_id
            # Save the single data object
            save_app_data(st.session_state.app_data)
            st.rerun()
    
    st.divider() 
    st.title("File Context 📎")
    
    # --- File Uploader (Works on the *current* chat) ---
    
    # Get the current chat data
    current_chat_id = st.session_state.app_data["current_chat_id"]
    current_chat = st.session_state.app_data["chats"].get(current_chat_id)

    uploaded_file = st.file_uploader(
        "Upload a PDF, JPG, PNG, or Text file", 
        type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'md', 'py'],
        key="sidebar_file_uploader",
        disabled=(current_chat is None) # Disable if no chat is active
    )
    
    if st.button("Clear File Context", use_container_width=True, disabled=(current_chat is None)):
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
        
        # Check if it's a new file before saving
        if current_chat["file"] != new_file_data:
            current_chat["file"] = new_file_data
            save_app_data(st.session_state.app_data)
            st.rerun()

    # Display a message if a file is loaded
    if current_chat and current_chat["file"]:
        st.info(f"Context: **{current_chat['file']['name']}**")
    elif current_chat:
        st.info("No file uploaded. Chatting normally.")


# === MODE 1: DOCUMENTATION GENERATOR (UPDATED TO STREAM) =========================
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
                    # --- URL UPDATED FOR DEPLOYMENT ---
                    with requests.post(
                        "https://clarityai-tnq0.onrender.com/generate-docs",
                        json={"code": content},
                        stream=True
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
                    st.error("Failed to connect to the backend. Is it running?")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# === MODE 2: GENERAL CHATBOT (STREAMING) (UPDATED) =======================
elif app_mode == "General Chatbot":
    
    st.header("General Chatbot 🤖")
    
    current_chat_id = st.session_state.app_data["current_chat_id"]
    current_chat = st.session_state.app_data["chats"].get(current_chat_id)

    if not current_chat:
        new_chat_id = str(uuid.uuid4())
        st.session_state.app_data["chats"][new_chat_id] = {
            "title": "New Chat",
            "file": None,
            "messages": []
        }
        st.session_state.app_data["current_chat_id"] = new_chat_id
        save_app_data(st.session_state.app_data)
        st.rerun()

    for message in current_chat["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 2. UPDATED get_chat_stream function ---
    def get_chat_stream(_prompt_text, _file_info, _chat_history):
        try:
            data = {
                "message": _prompt_text,
                "history": json.dumps(_chat_history)
            }
            files = {}
            if _file_info:
                file_bytes = base64.b64decode(_file_info["b64_string"])
                files["file"] = (
                    _file_info["name"], 
                    file_bytes,
                    _file_info["type"]
                )
            
            # --- URL UPDATED FOR DEPLOYMENT ---
            with requests.post(
                "https://clarityai-tnq0.onrender.com/chat", 
                data=data,
                files=files,
                stream=True
            ) as response:
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                        yield chunk
                else:
                    yield f"Error from backend: {response.text}"
        except requests.exceptions.ConnectionError:
            yield "Failed to connect to the backend. Is it running?"
        except Exception as e:
            yield f"An error occurred: {e}"
    # --- END OF FUNCTION ---

    if prompt := st.chat_input("What is up?"):
        
        is_first_message = len(current_chat["messages"]) == 0
        if is_first_message:
            current_chat["title"] = prompt[:40] + "..."
        
        current_chat["messages"].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_chunks = st.write_stream(
                get_chat_stream(
                    prompt, 
                    current_chat["file"],
                    current_chat["messages"]
                )
            )
        
        current_chat["messages"].append({"role": "assistant", "content": response_chunks})
        
        save_app_data(st.session_state.app_data)
        if is_first_message:
            st.rerun()