import json
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collection.scraper_hr_ge import JobScraper
from inference.job_matcher import JobMatcher
from database.operations import ChatOperations, UserOperations
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch


class JobSearchRequest(BaseModel):
    message: str
    user_id: str
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None


class JobSearchResponse(BaseModel):
    response: str
    jobs: List[Dict[str, Any]]
    matched_jobs: List[Dict[str, Any]]
    requirements_extracted: Dict[str, Any]


class MCPJobServer:
    def __init__(self, trained_model_path: Optional[str] = None):
        self.app = FastAPI(title="MCP Job Search Server")
        self.setup_cors()
        self.setup_routes()

        # Initialize components
        self.scraper = JobScraper()
        self.matcher = JobMatcher()
        self.active_connections: List[WebSocket] = []

        # Initialize database operations
        self.chat_ops = ChatOperations()
        self.user_ops = UserOperations()

        # Store trained model path
        self.trained_model_path = trained_model_path
        self.is_trained_model = False

        # Initialize LLM for chat
        self.setup_llm()

    def setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_llm(self):
        """Initialize the language model for chat (trained or base model)"""
        try:
            # Try to load trained model first if path provided
            if self.trained_model_path and os.path.exists(self.trained_model_path):
                print(f"🎯 Loading trained model from: {self.trained_model_path}")
                try:
                    from model_manager.lora_trainer import JobSearchLoRATrainer
                    self.model, self.tokenizer = JobSearchLoRATrainer.load_trained_model(self.trained_model_path)
                    self.is_trained_model = True
                    print("✅ Trained model loaded successfully")
                    return
                except Exception as e:
                    print(f"⚠️ Failed to load trained model: {e}")
                    print("📱 Falling back to base model...")
            
            # Load base model if no trained model or loading failed
            model_id = "openchat/openchat-3.5-0106"
            print(f"📱 Loading base model: {model_id}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                load_in_4bit=True,
                device_map="auto",
                torch_dtype=torch.float16,
            )
            self.is_trained_model = False
            print("✅ Base LLM initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize any LLM: {e}")
            self.tokenizer = None
            self.model = None
            self.is_trained_model = False

    def setup_routes(self):
        """Setup API routes"""
        
        # Mount static files for CSS, JS, etc.
        self.app.mount("/static", StaticFiles(directory="static"), name="static")

        @self.app.get("/")
        async def root():
            return {"message": "MCP Job Search Server is running"}

        @self.app.get("/chatbox", response_class=HTMLResponse)
        async def get_chatbox():
            return FileResponse("templates/chatbox.html")

        @self.app.websocket("/ws/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str):
            await self.websocket_handler(websocket, user_id)

        @self.app.post("/search_jobs")
        async def search_jobs(request: JobSearchRequest):
            """REST API endpoint for job search"""
            return await self.process_job_search(request.message, request.user_id, request.chat_id)

        @self.app.get("/api/chat_history/{user_id}")
        async def get_chat_history(user_id: str, limit: int = 50):
            """Get user's chat history"""
            try:
                chats = await self.chat_ops.get_user_chats(user_id, limit)
                return {"chats": chats}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/chat_history/{user_id}")
        async def clear_chat_history(user_id: str):
            """Clear user's chat history"""
            try:
                deleted_count = await self.chat_ops.clear_user_chats(user_id)
                return {"deleted_count": deleted_count}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def websocket_handler(self, websocket: WebSocket, user_id: str):
        """Handle WebSocket connections for real-time chat"""
        await websocket.accept()
        self.active_connections.append(websocket)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                message_type = message_data.get("type", "job_search")

                if message_type == "job_search" or "message" in message_data:
                    # Handle job search request
                    response = await self.process_job_search(
                        message_data.get("message", ""), 
                        user_id, 
                        message_data.get("chat_id"),
                        message_data.get("message_id")
                    )

                    # Send response back to client
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "job_search_response",
                                "data": response,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )

                elif message_type == "save_chat":
                    # Handle chat history saving
                    try:
                        chat_data = message_data.get("chat_data", {})
                        await self.chat_ops.save_chat(chat_data)
                        await websocket.send_text(
                            json.dumps({
                                "type": "chat_saved",
                                "data": {"success": True},
                                "timestamp": datetime.now().isoformat()
                            })
                        )
                    except Exception as e:
                        await websocket.send_text(
                            json.dumps({
                                "type": "error",
                                "message": f"Failed to save chat: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            })
                        )

                elif message_type == "load_chat_history":
                    # Handle chat history loading
                    try:
                        chats = await self.chat_ops.get_user_chats(user_id, limit=50)
                        await websocket.send_text(
                            json.dumps({
                                "type": "chat_history",
                                "data": {"chats": chats},
                                "timestamp": datetime.now().isoformat()
                            })
                        )
                    except Exception as e:
                        await websocket.send_text(
                            json.dumps({
                                "type": "error",
                                "message": f"Failed to load chat history: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            })
                        )

                elif message_type == "clear_chat_history":
                    # Handle chat history clearing
                    try:
                        deleted_count = await self.chat_ops.clear_user_chats(user_id)
                        await websocket.send_text(
                            json.dumps({
                                "type": "chat_history_cleared",
                                "data": {"deleted_count": deleted_count},
                                "timestamp": datetime.now().isoformat()
                            })
                        )
                    except Exception as e:
                        await websocket.send_text(
                            json.dumps({
                                "type": "error",
                                "message": f"Failed to clear chat history: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            })
                        )

                elif message_type == "get_chat":
                    # Handle specific chat loading
                    try:
                        chat_id = message_data.get("chat_id")
                        chat = await self.chat_ops.get_chat_by_id(chat_id, user_id)
                        await websocket.send_text(
                            json.dumps({
                                "type": "chat_loaded",
                                "data": {"chat": chat},
                                "timestamp": datetime.now().isoformat()
                            })
                        )
                    except Exception as e:
                        await websocket.send_text(
                            json.dumps({
                                "type": "error",
                                "message": f"Failed to load chat: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            })
                        )

                else:
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat()
                        })
                    )

        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
        except Exception as e:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error processing request: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    async def process_job_search(self, message: str, user_id: str, chat_id: Optional[str] = None, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Process job search request and return results"""
        try:
            print(f"Processing job search for user {user_id}: {message}")
            start_time = datetime.now()

            # Log user interaction if needed
            try:
                from database.models import UserInteraction
                interaction = UserInteraction(
                    user_id=user_id,
                    session_id=chat_id or f"session_{user_id}",
                    message=message,
                    message_type="job_search_query",
                    language="english"  # Could be detected from message
                )
                await self.user_ops.log_interaction(interaction)
            except Exception as e:
                print(f"Failed to log interaction: {e}")

            requirements = await self.extract_requirements(message)
            print(f"Extracted requirements: {requirements}")

            jobs = []
            if requirements.get("keywords"):
                # Convert keywords list to string for scrapers
                keywords_str = " ".join(requirements["keywords"]) if isinstance(requirements["keywords"], list) else str(requirements["keywords"])
                
                jobs = self.scraper.scrape_all_sources(
                    keywords=keywords_str,
                    location=requirements.get("location", ""),
                    limit_per_source=10,
                )

            matched_jobs = self.matcher.match_jobs(jobs, requirements)

            response_text = await self.generate_response(
                message, requirements, matched_jobs
            )

            # Calculate response time
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Update interaction with response
            try:
                if chat_id:
                    interaction.response = response_text
                    interaction.matched_jobs = [str(job.get("id", "")) for job in matched_jobs if job.get("id")]
                    interaction.search_results_count = len(matched_jobs)
                    interaction.response_time_ms = response_time_ms
                    await self.user_ops.log_interaction(interaction)
            except Exception as e:
                print(f"Failed to update interaction: {e}")

            return {
                "response": response_text,
                "jobs": jobs,
                "matched_jobs": matched_jobs,
                "requirements_extracted": requirements,
                "total_jobs_found": len(jobs),
                "total_matched_jobs": len(matched_jobs),
                "response_time_ms": response_time_ms,
                "model_used": "trained" if self.is_trained_model else "base"
            }

        except Exception as e:
            print(f"Error in process_job_search: {e}")
            return {
                "response": f"Sorry, I encountered an error while searching for jobs: {str(e)}",
                "jobs": [],
                "matched_jobs": [],
                "requirements_extracted": {},
                "total_jobs_found": 0,
                "total_matched_jobs": 0,
                "response_time_ms": 0,
                "model_used": "trained" if self.is_trained_model else "base"
            }

    async def extract_requirements(self, message: str) -> Dict[str, Any]:
        """Extract job requirements from user message using LLM"""
        try:
            if not self.model or not self.tokenizer:
                return self.simple_requirement_extraction(message)

            prompt = f"""
            Extract job search requirements from the following message. When "Georgia" is mentioned, assume it refers to the country Georgia (საქართველო) unless explicitly stated as "Georgia USA" or "Atlanta". Return a JSON object with these fields:
            - keywords: main job titles or skills mentioned
            - location: any location preferences (if Georgia is mentioned, interpret as "Georgia (country)")
            - experience_level: entry, mid, senior, or any
            - job_type: full-time, part-time, contract, remote, or any
            - salary_min: minimum salary if mentioned
            - skills: list of required skills
            - company_type: startup, enterprise, any, etc.
            
            Context: Georgia (country) has major cities like Tbilisi, Batumi, Kutaisi. Georgian companies include TBC Bank, Bank of Georgia, and many tech startups.
            
            Message: "{message}"
            
            JSON:
            """

            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=inputs["input_ids"].shape[1] + 150,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                try:
                    requirements = json.loads(json_str)
                    return requirements
                except json.JSONDecodeError:
                    pass

            return self.simple_requirement_extraction(message)

        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return self.simple_requirement_extraction(message)

    def simple_requirement_extraction(self, message: str) -> Dict[str, Any]:
        """Simple keyword-based requirement extraction fallback with Georgian context"""
        message_lower = message.lower()
        
        # Extract location with Georgia-specific handling FIRST
        location = ""
        
        # Check for Georgian cities first
        georgian_cities = ["tbilisi", "batumi", "kutaisi", "rustavi", "gori", "zugdidi", "poti", "kobuleti"]
        for city in georgian_cities:
            if city in message_lower:
                location = f"{city.capitalize()}, Georgia (country)"
                break
        
        # Check for Georgia country references
        if not location:
            if "georgia" in message_lower:
                # Check if it's explicitly US Georgia
                if any(indicator in message_lower for indicator in ["atlanta", "savannah", "columbus", "augusta", "georgia usa", "georgia us", "us state"]):
                    location = "Georgia, USA"
                else:
                    # Default to Georgia country
                    location = "Georgia (country)"
            else:
                # General location extraction
                location_indicators = ["in ", "at ", "near ", "from "]
                for indicator in location_indicators:
                    if indicator in message_lower:
                        start = message_lower.find(indicator) + len(indicator)
                        location_part = message[start:start+50].split()[0:3]  # Take next few words
                        location = " ".join(location_part).strip(",.!?")
                        break
        
        # Extract job titles/keywords (exclude location words)
        job_keywords = []
        exclude_words = {"georgia", "tbilisi", "batumi", "kutaisi", "rustavi", "gori", "country", "in", "at", "near", "from"}
        
        # Job title keywords
        job_titles = ["developer", "engineer", "scientist", "analyst", "manager", "designer", "consultant", "programmer", "architect", "specialist"]
        for keyword in job_titles:
            if keyword in message_lower and keyword not in exclude_words:
                job_keywords.append(keyword)
        
        # Technology keywords
        tech_keywords = ["python", "javascript", "react", "node", "java", "sql", "aws", "docker", "kubernetes", "frontend", "backend", "fullstack", "devops"]
        for tech in tech_keywords:
            if tech in message_lower and tech not in exclude_words:
                job_keywords.append(tech)
        
        # If no specific job keywords found but location is specified, add general terms
        if not job_keywords and location:
            # Look for general job-related terms
            general_terms = ["job", "work", "position", "opportunity", "career", "employment"]
            for term in general_terms:
                if term in message_lower:
                    job_keywords.append("job opportunities")
                    break
        
        # Extract experience level
        experience_level = "any"
        if any(word in message_lower for word in ["senior", "sr", "lead"]):
            experience_level = "senior"
        elif any(word in message_lower for word in ["junior", "jr", "entry", "graduate"]):
            experience_level = "entry"
        elif any(word in message_lower for word in ["mid", "intermediate"]):
            experience_level = "mid"
        
        # Extract job type
        job_type = "any"
        if "remote" in message_lower:
            job_type = "remote"
        elif "contract" in message_lower:
            job_type = "contract"
        elif "part-time" in message_lower or "part time" in message_lower:
            job_type = "part-time"
        elif "full-time" in message_lower or "full time" in message_lower:
            job_type = "full-time"

        return {
            "keywords": job_keywords,
            "location": location,
            "experience_level": experience_level,
            "job_type": job_type,
            "skills": job_keywords,  # For now, same as keywords
            "company_type": "any"
        }

    async def generate_response(
        self, message: str, requirements: Dict, matched_jobs: List[Dict]
    ) -> str:
        """Generate a response to the user's job search query with Georgian context"""
        
        # Check if this is a Georgia-related search
        is_georgia_search = (
            requirements.get("location", "").lower().find("georgia") != -1 and 
            "usa" not in requirements.get("location", "").lower()
        )
        
        if not matched_jobs:
            if is_georgia_search:
                return (
                    f"I searched for jobs in Georgia (country) based on your criteria but didn't find any exact matches. "
                    f"Georgia's job market is growing, especially in Tbilisi's tech sector. "
                    f"You might want to try:\n"
                    f"• Checking major Georgian companies like TBC Bank, Bank of Georgia, or Wissol\n"
                    f"• Looking for remote opportunities with international companies\n"
                    f"• Broadening your search to include Batumi or other cities\n"
                    f"• Searching on hr.ge or jobs.ge directly"
                )
            else:
                return f"I searched for jobs based on your criteria but didn't find any exact matches. You might want to try broadening your search terms or checking different locations."

        job_count = len(matched_jobs)
        requirements_text = []
        
        if requirements.get("keywords"):
            requirements_text.append(f"skills: {', '.join(requirements['keywords'])}")
        if requirements.get("location"):
            requirements_text.append(f"location: {requirements['location']}")
        if requirements.get("experience_level") and requirements["experience_level"] != "any":
            requirements_text.append(f"experience: {requirements['experience_level']}")

        req_summary = " with " + " and ".join(requirements_text) if requirements_text else ""

        base_response = f"I found {job_count} job{'s' if job_count != 1 else ''} matching your search{req_summary}. Here are the best matches:"
        
        if is_georgia_search:
            georgian_context = (
                f"\n\n🇬🇪 About working in Georgia (country):\n"
                f"• Major tech hub: Tbilisi with growing startup ecosystem\n"
                f"• Key employers: TBC Bank, Bank of Georgia, international companies\n"
                f"• Languages: Georgian (ქართული) + English often required for tech roles\n"
                f"• Currency: Georgian Lari (GEL)\n"
                f"• Time zone: Georgia Standard Time (GET, UTC+4)"
            )
            return base_response + georgian_context
        
        return base_response


def run_server(host: str = "0.0.0.0", port: int = 8000, trained_model_path: Optional[str] = None):
    """Run the MCP Job Server (with optional trained model)"""
    model_info = "🎯 Trained Model" if trained_model_path else "📱 Base Model"
    print(f"🚀 Starting Job Search AI Server ({model_info}) on {host}:{port}")
    print(f"📱 Open your browser to: http://localhost:{port}/chatbox")
    print(f"🔄 WebSocket endpoint: ws://localhost:{port}/ws/{{user_id}}")
    print(f"📊 REST API docs: http://localhost:{port}/docs")
    if trained_model_path:
        print(f"🎯 Using trained model from: {trained_model_path}")
    
    server = MCPJobServer(trained_model_path=trained_model_path)
    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    run_server()
