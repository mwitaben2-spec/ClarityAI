# -----------------------------------------------------------
# FILENAME: backend/main.py (WITH CHAT HISTORY)
# -----------------------------------------------------------
import os
import asyncio
import io
import json  # <-- 1. IMPORT JSON
from fastapi import FastAPI, Form, File, UploadFile
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from pypdf import PdfReader
from PIL import Image

# Load .env file
load_dotenv(dotenv_path="../.env") 

# --- Configure the Google AI Client ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# Create the FastAPI app
app = FastAPI()

# --- CORS Middleware (Your existing code) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- Pydantic Models (Only for /generate-docs) ---
class DocCodeInput(BaseModel):
    code: str

# --- Helper Generator for Streaming (Unchanged, for /generate-docs) ---
async def stream_gemini_response(model, prompt):
    """
    A generator function that yields chunks of text from the Gemini API.
    Works for single-turn, non-chat requests.
    """
    try:
        response_stream = await model.generate_content_async(
            prompt,
            stream=True
        )
        
        async for chunk in response_stream:
            try:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01) 
            except ValueError:
                print("Skipped a chunk due to safety settings or empty response.")
                pass
                
    except Exception as e:
        print(f"Error during Google API stream: {e}")
        yield f"Error: {e}"

# --- Endpoint 1: Documentation (Unchanged and still streaming) ---
@app.post("/generate-docs")
async def generate_docs_streaming(code_input: DocCodeInput): # Changed to async
    print("Received request to generate docs (Google 2.5 Pro)...")
    if not GOOGLE_API_KEY:
        async def error_stream():
            yield "# Error: GOOGLE_API_KEY not set."
        return StreamingResponse(error_stream(), media_type="text/plain")
        
    try:
        system_prompt = "You are an expert software developer. Your task is to write high-quality, concise, and clear documentation for the given code snippet. Respond only with the documentation in Markdown format."
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro", 
            system_instruction=system_prompt
        )
        
        prompt = f"Here is the code:\n\n```\n{code_input.code}\n```"
        return StreamingResponse(
            stream_gemini_response(model, prompt),
            media_type="text/plain"
        )
        
    except Exception as e:
        print(f"Error during Google API call: {e}")
        async def error_stream():
            yield f"Error generating documentation: {e}"
        return StreamingResponse(error_stream(), media_type="text/plain")

# --- Endpoint 2: General Chatbot (STREAMING) (UPDATED FOR HISTORY) ---
@app.post("/chat")
async def handle_chat_stream(
    message: str = Form(...),
    history: str = Form("[]"),  # <-- 2. NEW HISTORY FIELD
    file: UploadFile = File(None)
):
    print(f"Received STREAMING chat message (Google 2.5 Flash)...")
    
    if not GOOGLE_API_KEY:
        async def error_stream():
            yield "Error: GOOGLE_API_KEY not set on server."
        return StreamingResponse(error_stream(), media_type="text/plain")

    # --- 3. PROCESS THE NEW MESSAGE + FILE (Unchanged) ---
    prompt_object = message
    if file:
        print(f"Processing uploaded file: {file.filename} ({file.content_type})")
        contents = await file.read()
        try:
            if file.content_type == "application/pdf":
                pdf_reader = PdfReader(io.BytesIO(contents))
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
                prompt_object = f"Based on this PDF named '{file.filename}':\n\n{pdf_text}\n\n...Answer this question: {message}"
                print("PDF processed.")
            
            elif file.content_type in ["image/jpeg", "image/png"]:
                img = Image.open(io.BytesIO(contents))
                prompt_object = [message, img]
                print("Image processed.")
                
            elif file.content_type.startswith("text/"):
                text_content = contents.decode('utf-8')
                prompt_object = f"Based on this file named '{file.filename}':\n\n{text_content}\n\n...Answer this question: {message}"
                print("Text file processed.")
            else:
                raise ValueError(f"Unsupported file type: {file.content_type}")

        except Exception as e:
            print(f"Error processing file: {e}")
            async def error_stream():
                yield f"Error processing file '{file.filename}': {e}"
            return StreamingResponse(error_stream(), media_type="text/plain")

    # --- 4. PROCESS THE CHAT HISTORY ---
    try:
        chat_history_raw = json.loads(history)
        # Convert our format (role: "assistant") to Gemini's format (role: "model")
        converted_history = []
        for msg in chat_history_raw:
            role = "model" if msg["role"] == "assistant" else "user"
            converted_history.append({"role": role, "parts": [msg["content"]]})
    except Exception as e:
        print(f"Error parsing history JSON: {e}")
        converted_history = [] # Start fresh if history is corrupt

    # --- 5. START CHAT SESSION WITH HISTORY ---
    system_prompt = "You are a helpful assistant. You can answer questions, calculate simple syntax, tell stories, and have a friendly conversation. If you are given an image, you can describe it. If you are given text context, you must base your answer on that context."
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        system_instruction=system_prompt
    )
    
    # Start the chat session *with* the converted history
    chat_session = model.start_chat(history=converted_history)
    
    # --- 6. CREATE A NEW STREAMING GENERATOR FOR THE SESSION ---
    async def chat_stream_generator():
        try:
            # Send the new prompt (with file) to the ongoing session
            response_stream = await chat_session.send_message_async(
                prompt_object,
                stream=True
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error during chat stream: {e}")
            yield f"Error: {e}"

    # --- 7. RETURN THE NEW GENERATOR ---
    # We no longer use stream_gemini_response here
    return StreamingResponse(chat_stream_generator(), media_type="text/plain")