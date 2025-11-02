# -----------------------------------------------------------
# FILENAME: backend/main.py (THIS IS THE COMPLETE FILE)
# -----------------------------------------------------------
import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware # <-- 1. THIS IS THE NEW IMPORT

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

# --- 2. THIS IS THE NEW CODE BLOCK FOR DEPLOYMENT ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (e.g., your Streamlit app)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models (Your existing code) ---
class DocCodeInput(BaseModel):
    code: str

class DocOutput(BaseModel):
    documentation: str

class ChatInput(BaseModel):
    message: str

# --- Helper Generator for Streaming (Your existing code) ---
async def stream_gemini_response(model, prompt):
    """
    A generator function that yields chunks of text from the Gemini API.
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

# --- Endpoint 1: Documentation (Your existing code) ---
@app.post("/generate-docs", response_model=DocOutput)
def generate_docs(code_input: DocCodeInput):
    print("Received request to generate docs (Google 2.5 Pro)...")
    if not GOOGLE_API_KEY:
        return DocOutput(documentation="# Error: GOOGLE_API_KEY not set.")
    try:
        system_prompt = "You are an expert software developer. Your task is to write high-quality, concise, and clear documentation for the given code snippet. Respond only with the documentation in Markdown format."
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro", 
            system_instruction=system_prompt
        )
        response = model.generate_content(f"Here is the code:\n\n```\n{code_input.code}\n```")
        print("Documentation generated successfully (Google).")
        return DocOutput(documentation=response.text)
    except Exception as e:
        print(f"Error during Google API call: {e}")
        return DocOutput(documentation=f"Error generating documentation: {e}")

# --- Endpoint 2: General Chatbot (STREAMING) (Your existing code) ---
@app.post("/chat")
async def handle_chat_stream(chat_input: ChatInput):
    print(f"Received STREAMING chat message (Google 2.5 Flash)...")
    
    if not GOOGLE_API_KEY:
        return StreamingResponse("Error: GOOGLE_API_KEY not set.", media_type="text/plain")

    system_prompt = "You are a helpful assistant. You can answer questions, calculate simple syntax, tell stories, and have a friendly conversation."
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        system_instruction=system_prompt
    )
    
    return StreamingResponse(
        stream_gemini_response(model, chat_input.message),
        media_type="text/plain"
    )