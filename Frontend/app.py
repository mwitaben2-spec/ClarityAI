# -----------------------------------------------------------
# FILENAME: frontend/app.py (With Copy Button)
# -----------------------------------------------------------
import streamlit as st
import requests
from st_copy import copy_button # <-- 1. IMPORT THE NEW COMPONENT

# --- Page Configuration ---
st.set_page_config(
    page_title="ClarityAI",
    page_icon="💡",
    layout="wide"
)

# --- Main App Title ---
st.title("ClarityAI 💡")

# --- Sidebar for Navigation ---
with st.sidebar:
    st.title("Navigation")
    app_mode = st.selectbox("Choose your mode:", 
                            ["Documentation Generator", "General Chatbot"])

# === MODE 1: DOCUMENTATION GENERATOR =======================================
if app_mode == "Documentation Generator":
    
    st.header("Code Documentation Generator 📚")
    st.subheader("Upload a code file to generate complete documentation.")

    uploaded_file = st.file_uploader("Upload your code file", type=['py', 'js', 'java'])

    if uploaded_file:
        content = uploaded_file.read().decode()
        st.code(content, language='python') 

        if st.button("Generate Documentation"):
            with st.spinner("Analyzing code..."):
                try:
                    response = requests.post(
                        "https://clarityai-tnq0.onrender.com/generate-docs", # <-- CHANGED: Replaced localhost with your Render URL
                        json={"code": content}
                    )
                    if response.status_code == 200:
                        
                        # --- THIS IS THE UPDATED SECTION ---
                        doc_text = response.json()["documentation"] # Get text
                        st.success("Documentation generated!")
                        
                        # 2. ADD THE COPY BUTTON
                        copy_button(doc_text, tooltip="Copy documentation", copied_label="Copied!")
                        
                        # 3. DISPLAY THE DOCUMENTATION
                        st.markdown(doc_text)
                        # --- END OF UPDATE ---
                        
                    else:
                        st.error(f"Error from backend: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Failed to connect to the backend. Is it running?")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# === MODE 2: GENERAL CHATBOT (STREAMING) ===============================
elif app_mode == "General Chatbot":
    
    st.header("General Chatbot 🤖")
    st.subheader("Ask me anything! (e.g., 'Tell me a story' or 'What is 12 * 5?').")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    def get_chat_stream(prompt):
        try:
            with requests.post(
                "https://clarityai-tnq0.onrender.com/chat", # <-- CHANGED: Replaced localhost with your Render URL
                json={"message": prompt},
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

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_chunks = st.write_stream(get_chat_stream(prompt))
        
        st.session_state.messages.append({"role": "assistant", "content": response_chunks})