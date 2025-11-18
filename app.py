import os
import httpx
import json  # <-- 新增导入
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import traceback

# --- Configuration ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# --- FastAPI App Initialization ---
app = FastAPI()

# Create a reusable HTTP client
client = httpx.AsyncClient()

# --- Absolute Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- Helper Function for DeepSeek API Call ---
async def call_deepseek_api(messages: list, model: str = "deepseek-chat", temperature: float = 0.7):
    """
    A helper function to make calls to the DeepSeek API.
    """
    if not DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY is not set!")
        raise HTTPException(
            status_code=500, 
            detail="DEEPSEEK_API_KEY is not set on the server."
        )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    
    try:
        response = await client.post(
            DEEPSEEK_ENDPOINT,
            json=body,
            headers=headers,
            timeout=300.0
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except httpx.HTTPStatusError as e:
        error_msg = f"DeepSeek API Error: {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"Internal server error in API call: {type(e).__name__} - {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=error_msg
        )

# --- NEW: AI Agent Endpoint (Extractor + Expert Model) ---
@app.post("/generate")
async def generate_content(request: Request):
    """
    This endpoint uses a robust "Extractor + Template + Expert" pattern.
    
    1. (Optional) LLM 1 (Extractor): For tasks with messy user input (like 'resume'),
       this step cleans and structures the data into a reliable JSON.
    2. (Required) Human Template: We use a precise, human-written f-string template
       to build the perfect prompt for the expert.
    3. (Required) LLM 2 (Expert): This model receives the clean prompt and generates
       the final, high-quality content.
    """
    try:
        body = await request.json()
        task = body.get("task")
        data = body.get("data")

        if not task or not data:
            raise HTTPException(status_code=400, detail="Missing 'task' or 'data' in request body")

        structured_data = data  # Default to original data

        # --- Step 1: (Optional) LLM 1 (Extractor) ---
        # We only run this for tasks where user input might be "messy"
        if task == "resume":
            print(f"[INFO] Task '{task}' requires data extraction. Running LLM 1 (Extractor)...")
            
            extractor_system_prompt = """
            You are an expert data analyst. Your job is to extract and structure key information 
            from a user's raw data for a resume. Pay close attention to the 'skills' field, 
            which might be a messy, comma-separated list or natural language.
            Your output MUST be a valid JSON object.
            
            Keep all fields from the original data, but add a new key 'skills_list' 
            containing a clean Python-style list of skills extracted from the 'skills' field.
            
            Example Input Data:
            { "name": "Alex", "skills": "i use react, js, and a bit of python. also project management", ... }
            
            Example Output JSON:
            { "name": "Alex", "skills": "i use react, js, and a bit of python. also project management", "skills_list": ["React", "JavaScript", "Python (Beginner)", "Project Management"], ... }
            """
            
            extractor_user_prompt = f"""
            Please process the following raw user data and return ONLY a valid JSON object.
            
            Raw Data:
            ```json
            {json.dumps(data)}
            ```
            """
            
            try:
                # --- LLM 1 Call ---
                json_string_output = await call_deepseek_api(
                    messages=[
                        {"role": "system", "content": extractor_system_prompt},
                        {"role": "user", "content": extractor_user_prompt}
                    ],
                    model="deepseek-chat", # Use a fast model
                    temperature=0.1        # Low temp for high accuracy
                )
                
                # Clean up potential markdown ```json ... ```
                if "```json" in json_string_output:
                    json_string_output = json_string_output.split("```json\n", 1)[1].split("```")[0]
                
                structured_data = json.loads(json_string_output)
                print(f"[DEBUG] LLM 1 (Extractor) output: {structured_data}")
                
            except Exception as e:
                print(f"[ERROR] LLM 1 (Extractor) failed: {e}. Falling back to raw data.")
                # Fallback: If extraction fails, use the original data and do a simple split
                structured_data = data
                structured_data['skills_list'] = [skill.strip() for skill in data.get('skills', '').split(',')]

        else:
            print(f"[INFO] Task '{task}' does not require extraction. Using raw data.")
            structured_data = data

        # --- Step 2: Human-Written Templates ---
        
        final_system_prompts = {
            "resume": "You are a professional career consultant and resume expert. Your task is to generate a JSON object with two keys: 'resume' (HTML content) and 'analysis' (HTML content). Please strictly follow the JSON format, ensuring all HTML is well-formed and professional.",
            "interview": "You are an experienced interviewer and career mentor. Provide practical, professional interview preparation materials in well-formed HTML.",
            "learning_path": "You are an experienced career mentor and learning planner. Create a personalized, actionable learning path in well-formed HTML.",
            "cover_letter": "You are an expert cover letter writer. Write a professional, persuasive, and personalized cover letter in well-formed HTML.",
            "linkedin": "You are a LinkedIn optimization expert. Create a professional and attractive LinkedIn profile optimization plan in well-formed HTML.",
            "salary": "You are a salary negotiation expert and market analyst. Provide an accurate, practical salary analysis and negotiation advice in well-formed HTML."
        }
        final_system_prompt = final_system_prompts.get(task, "You are a helpful AI career assistant.")

        # --- Build Final User Prompt from Template ---
        final_user_prompt = ""
        
        if task == "resume":
            final_user_prompt = f"""
            Please act as a resume expert. Create an optimized resume and a matching analysis based on the following structured data.
            
            **User Profile:**
            - Name: {structured_data.get('name', 'N/A')}
            - Current Role: {structured_data.get('currentRole', 'N/A')}
            - Years of Experience: {structured_data.get('experience', 'N/A')}
            - Cleaned Skills List: {structured_data.get('skills_list', 'N/A')}
            
            **Target Opportunity:**
            - Job Title: {structured_data.get('jobTitle', 'N/A')}
            - Company: {structured_data.get('company', 'N/A')}
            - Job Description:
              ```
              {structured_data.get('jobDescription', 'N/A')}
              ```
            
            **Required Output Format:**
            You MUST return a single, valid JSON object with two keys: "resume" and "analysis".
            Both keys must contain well-formed HTML content.
            """
        
        elif task == "interview":
            final_user_prompt = f"""
            Please act as an interview coach. Generate interview questions based on this data.
            
            - Role: {structured_data.get('role', 'N/A')}
            - Level: {structured_data.get('level', 'N/A')}
            - Key Skills: {structured_data.get('skills', 'N/A')}
            
            **Required Output Format:**
            A single block of well-formed HTML content.
            """
            
        elif task == "learning_path":
             final_user_prompt = f"""
             Please act as a learning planner. Create a personalized learning path.
             
             - Current Skills: {structured_data.get('currentSkills', 'N/A')}
             - Target Role: {structured_data.get('targetRole', 'N/A')}
             - Timeline: {structured_data.get('timeline', 'N/A')} months
             
             **Required Output Format:**
             A single block of well-formed HTML content, detailing a roadmap.
             """

        elif task == "cover_letter":
            final_user_prompt = f"""
            Please act as a cover letter writer. Write a letter based on these details.
            
            - Company: {structured_data.get('company', 'N/A')}
            - Role: {structured_data.get('role', 'N/A')}
            - Key Achievement: {structured_data.get('achievement', 'N/A')}
            - Tone: {structured_data.get('tone', 'N/A')}
            
            **Required Output Format:**
            A single block of well-formed HTML content, formatted as a letter.
            """

        elif task == "linkedin":
            final_user_prompt = f"""
            Please act as a LinkedIn expert. Optimize a profile based on this data.
            
            - Current Headline: {structured_data.get('headline', 'N/A')}
            - Current About: {structured_data.get('about', 'N/A')}
            - Target Industry/Roles: {structured_data.get('target', 'N/A')}
            
            **Required Output Format:**
            A single block of well-formed HTML content with sections for "New Headline" and "New About Section".
            """

        elif task == "salary":
            final_user_prompt = f"""
            Please act as a salary analyst. Provide insights for the following role.
            
            - Role: {structured_data.get('role', 'N/A')}
            - Location: {structured_data.get('location', 'N/A')}
            - Experience: {structured_data.get('experience', 'N/A')} years
            - Company Size: {structured_data.get('companySize', 'N/A')}
            
            **Required Output Format:**
            A single block of well-formed HTML content, including an estimated range and negotiation tips.
            """
        else:
            final_user_prompt = f"Please perform the task '{task}' with the data: {json.dumps(structured_data)}"

        print(f"[DEBUG] Final User Prompt for LLM 2:\n{final_user_prompt[:500]}...") # Log first 500 chars

        # --- Step 3: LLM 2 (Expert) Call ---
        print(f"[INFO] Generating final content for task: {task} using LLM 2 (Expert)...")
        final_content = await call_deepseek_api(
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": final_user_prompt}
            ],
            temperature=0.7 # Standard temp for creative/expert output
        )

        return JSONResponse(content={"content": final_content})

    except Exception as e:
        error_msg = f"Error in /generate endpoint: {type(e).__name__} - {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=error_msg
        )


# --- Original API Endpoint (Proxy) ---
@app.post("/call-deepseek")
async def proxy_deepseek(request: Request):
    """
    This endpoint is kept for legacy purposes but is not used by the
    new /generate logic.
    """
    if not DEEPSEEK_API_KEY:
        print("[ERROR] DEEPSEEK_API_KEY is not set!")
        raise HTTPException(
            status_code=500, 
            detail="DEEPSEEK_API_KEY is not set on the server."
        )
        
    try:
        body = await request.json()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        response = await client.post(
            DEEPSEEK_ENDPOINT,
            json=body,
            headers=headers,
            timeout=300.0
        )
        
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as e:
        error_msg = f"DeepSeek API Error: {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_msg}")
        raise HTTPException(
            status_code=e.response.status_code, 
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"Internal server error: {type(e).__name__} - {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=error_msg
        )

# --- Static File Serving ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    """
    Serves the main index.html file from the 'static' directory.
    """
    try:
        with open(os.path.join(STATIC_DIR, "index.html")) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: index.html not found</h1><p>Ensure index.html is in a 'static' folder.", 
            status_code=404
        )
