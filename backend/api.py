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
    
    @classmethod
    def add_log(cls, level: str, message: str, phone: Optional[str] = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "phone": phone
        }
        cls.logs.append(log_entry)
        if len(cls.logs) > 1000: # Keep last 1000 logs
            cls.logs.pop(0)

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

@app.on_event("startup")
async def startup_event():
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
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
async def verify_code(phone: str, code: str):
    if phone not in state.active_sessions:
        raise HTTPException(status_code=400, detail="Session not found")
    
    client = state.active_sessions[phone]
    try:
        await client.sign_in(phone, code)
        me = await client.get_me()
        await worker_pool.add_worker(phone, client)
        return {"status": "authenticated", "user": me.username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if state.logs:
                # Send all currently buffered logs
                while state.logs:
                    log_entry = state.logs.pop(0)
                    await websocket.send_json(log_entry)
            await asyncio.sleep(0.5) # Poll less frequently to save resources
    except WebSocketDisconnect:
        pass

@app.post("/scrape")
async def scrape_members(phone: str, group_link: str):
    if phone not in worker_pool.workers:
        raise HTTPException(status_code=400, detail="Worker not authenticated")
    
    client = worker_pool.workers[phone]
    try:
        if group_link.startswith('https://t.me/'):
            group_link = group_link.split('/')[-1]
            
        entity = await client.get_entity(group_link)
        members = []
        async for user in client.iter_participants(entity, limit=500):
            if user.username:
                members.append({
                    "id": user.id,
                    "username": user.username,
                    "name": f"{user.first_name or ''} {user.last_name or ''}".strip()
                })
        
        return {"status": "success", "count": len(members), "members": members[:100]} # Return first 100 for result preview
    except Exception as e:
        state.add_log("ERROR", f"Scrape failed: {str(e)}", phone)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add")
async def add_members(target_group: str, members: List[Dict]):
    if not worker_pool.workers:
        raise HTTPException(status_code=400, detail="No authenticated workers available")
    
    # Run in background
    asyncio.create_task(worker_pool.start_swifting(target_group, members))
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
