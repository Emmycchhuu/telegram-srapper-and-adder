from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import json
import logging
from datetime import datetime
import os
from telethon import TelegramClient
from config import Config

from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerChannel, InputPeerUser
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError, UsernameNotOccupiedError

app = FastAPI(title="Telegram Swift Adder API")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WorkerPool:
    def __init__(self):
        self.workers: Dict[str, TelegramClient] = {}
        self.running = False
        self.member_queue = asyncio.Queue()
        self.target_group = None
        self.status = "idle"

    async def add_worker(self, phone: str, client: TelegramClient):
        self.workers[phone] = client
        state.add_log("INFO", f"Worker ready: {phone}")
        
    async def remove_worker(self, phone: str):
        if phone in self.workers:
            client = self.workers.pop(phone)
            await client.disconnect()
            state.add_log("INFO", f"Worker removed: {phone}")

    async def start_swifting(self, target_group: str, members: List[Dict]):
        if not self.workers:
            state.add_log("ERROR", "No workers authenticated!")
            return
            
        self.target_group = target_group
        self.running = True
        self.status = "processing"
        
        # Fill queue
        for m in members:
            await self.member_queue.put(m)
            
        state.add_log("INFO", f"Started Swifting {len(members)} members using {len(self.workers)} accounts")
        
        # Start a consumer for each worker
        tasks = [asyncio.create_task(self.worker_loop(phone, client)) 
                 for phone, client in self.workers.items()]
        
        await asyncio.gather(*tasks)
        self.running = False
        self.status = "completed"
        state.add_log("INFO", "All members processed.")

    async def worker_loop(self, phone: str, client: TelegramClient):
        from telethon.tl.functions.channels import InviteToChannelRequest
        from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
        
        try:
            target_entity = await client.get_entity(self.target_group)
            while self.running and not self.member_queue.empty():
                member = await self.member_queue.get()
                try:
                    user_entity = await client.get_entity(member['username'] if member.get('username') else int(member['id']))
                    await client(InviteToChannelRequest(target_entity, [user_entity]))
                    state.add_log("INFO", f"Successfully added {member.get('username', member['id'])}", phone)
                    # Swift delay: 2026 standard optimized for speed vs safety
                    await asyncio.sleep(15) 
                except PeerFloodError:
                    state.add_log("WARNING", "Account hit flood limit. Cooling down...", phone)
                    await asyncio.sleep(300) # 5 min cooling
                except FloodWaitError as e:
                    state.add_log("WARNING", f"Flood wait: {e.seconds}s", phone)
                    await asyncio.sleep(e.seconds)
                except UserPrivacyRestrictedError:
                    state.add_log("DEBUG", f"Privacy restricted: {member.get('username', member['id'])}", phone)
                except Exception as e:
                    state.add_log("ERROR", f"Error adding {member.get('username', member['id'])}: {str(e)}", phone)
                finally:
                    self.member_queue.task_done()
        except Exception as e:
            state.add_log("ERROR", f"Worker crash for {phone}: {str(e)}")

worker_pool = WorkerPool()

# Global state
class State:
    active_sessions: Dict[str, TelegramClient] = {}
    logs: List[Dict] = []
    websockets: List[WebSocket] = []
    log_queue: asyncio.Queue = asyncio.Queue()
    scraped_data: Dict[str, List[Dict]] = {} # phone -> members list
    scrape_status: Dict[str, str] = {} # phone -> "idle" | "scraping" | "completed" | "error"
    
    @classmethod
    async def log_processor(cls):
        """Background task to broadcast logs from the queue."""
        while True:
            log_entry = await cls.log_queue.get()
            cls.logs.append(log_entry)
            if len(cls.logs) > 500:
                cls.logs.pop(0)
            
            # Broadcast to all connected clients
            dead_ws = []
            for ws in cls.websockets:
                try:
                    await ws.send_json(log_entry)
                except:
                    dead_ws.append(ws)
            
            for ws in dead_ws:
                if ws in cls.websockets:
                    cls.websockets.remove(ws)
            cls.log_queue.task_done()

    @classmethod
    def add_log(cls, level: str, message: str, phone: Optional[str] = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "phone": phone
        }
        # Safely put into queue (even from sync code)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(cls.log_queue.put(log_entry))
            else:
                cls.logs.append(log_entry)
        except:
            cls.logs.append(log_entry)

state = State()

class LogHandler(logging.Handler):
    def emit(self, record):
        state.add_log(record.levelname, self.format(record))

# Setup logging
logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
root_logger.addHandler(LogHandler())

class AccountRequest(BaseModel):
    phone: str
    api_id: str
    api_hash: str

class VerifyRequest(BaseModel):
    phone: str
    code: str

class ScrapeRequest(BaseModel):
    phone: str
    group_link: str

@app.on_event("startup")
async def startup_event():
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    # Start log processor in background
    asyncio.create_task(state.log_processor())
    state.add_log("INFO", "Engine starting up in cloud environment...")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/auth/send-code")
async def send_code(req: AccountRequest):
    try:
        client = TelegramClient(f"sessions/{req.phone}", req.api_id, req.api_hash)
        await client.connect()
        await client.send_code_request(req.phone)
        state.active_sessions[req.phone] = client
        return {"status": "code_sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/verify")
async def verify_code(req: VerifyRequest):
    if req.phone not in state.active_sessions:
        raise HTTPException(status_code=400, detail="Session not found. Try sending the code again.")
    
    client = state.active_sessions[req.phone]
    try:
        await client.sign_in(req.phone, req.code)
        me = await client.get_me()
        await worker_pool.add_worker(req.phone, client)
        return {"status": "authenticated", "user": me.username}
    except Exception as e:
        state.add_log("ERROR", f"Verification failed: {str(e)}", req.phone)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/session")
async def check_session(req: AccountRequest):
    """Check if a session file exists and is valid."""
    session_path = f"sessions/{req.phone}.session"
    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        client = TelegramClient(f"sessions/{req.phone}", req.api_id, req.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise HTTPException(status_code=401, detail="Session expired")
            
        me = await client.get_me()
        await worker_pool.add_worker(req.phone, client)
        state.active_sessions[req.phone] = client
        return {"status": "authenticated", "user": me.username}
    except Exception as e:
        state.add_log("ERROR", f"Session check failed: {str(e)}", req.phone)
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.websockets.append(websocket)
    try:
        # Send recent history on connect
        for log in state.logs[-20:]:
            await websocket.send_json(log)
            
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        if websocket in state.websockets:
            state.websockets.remove(websocket)
    except Exception:
        if websocket in state.websockets:
            state.websockets.remove(websocket)

@app.post("/scrape")
async def scrape_members(req: ScrapeRequest):
    if req.phone not in worker_pool.workers:
        raise HTTPException(status_code=400, detail="Worker not authenticated")
    
    # Run in background
    asyncio.create_task(background_scrape(req.phone, req.group_link))
    return {"status": "started", "message": "Scraping started in background"}

async def background_scrape(phone: str, group_link: str):
    client = worker_pool.workers[phone]
    state.scrape_status[phone] = "scraping"
    state.scraped_data[phone] = []
    
    try:
        clean_link = group_link.replace('https://t.me/', '').replace('@', '').strip()
        state.add_log("INFO", f"Resolving entity for: {clean_link}...", phone)
        
        entity = await client.get_entity(clean_link)
        state.add_log("INFO", f"Entity resolved. Starting swift scrape of {entity.title if hasattr(entity, 'title') else clean_link}", phone)
        
        members = []
        count = 0
        async for user in client.iter_participants(entity, limit=2000): # Increased limit for background
            if user.username:
                member_data = {
                    "id": user.id,
                    "username": user.username,
                    "name": f"{user.first_name or ''} {user.last_name or ''}".strip()
                }
                members.append(member_data)
            count += 1
            if count % 100 == 0:
                state.add_log("DEBUG", f"Scraped {count} members so far...", phone)
        
        state.scraped_data[phone] = members
        state.scrape_status[phone] = "completed"
        state.add_log("INFO", f"Scrape completed! Total: {len(members)} qualified users found.", phone)
        
    except Exception as e:
        state.scrape_status[phone] = "error"
        state.add_log("ERROR", f"Scrape failed: {str(e)}", phone)

@app.get("/scrape/results")
async def get_scrape_results(phone: str):
    return {
        "status": state.scrape_status.get(phone, "idle"),
        "count": len(state.scraped_data.get(phone, [])),
        "members": state.scraped_data.get(phone, [])
    }

@app.post("/add")
async def add_members(target_group: str, members: List[Dict]):
    if not worker_pool.workers:
        raise HTTPException(status_code=400, detail="No authenticated workers available")
    
    clean_target = target_group.replace('https://t.me/', '').replace('@', '').strip()
    state.add_log("INFO", f"Initiating Swift Add process for target: {clean_target} with {len(members)} members", "SYSTEM")
    
    # Run in background
    asyncio.create_task(worker_pool.start_swifting(clean_target, members))
    return {"status": "swift_process_started", "workers_active": len(worker_pool.workers)}

@app.get("/status")
async def get_status():
    return {
        "status": worker_pool.status,
        "active_workers": len(worker_pool.workers),
        "queue_size": worker_pool.member_queue.qsize() if worker_pool.member_queue else 0,
        "running": worker_pool.running
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
