"""Utility functions for the Telegram Member Adder"""

import json
import os
from datetime import datetime
from typing import Dict, List

def save_progress(processed_users: set, failed_users: set, filename: str = "progress.json"):
    """Save progress to resume later"""
    progress_data = {
        "processed_users": list(processed_users),
        "failed_users": list(failed_users),
        "timestamp": datetime.now().isoformat()
    }
    
    with open(filename, 'w') as f:
        json.dump(progress_data, f, indent=2)

def load_progress(filename: str = "progress.json") -> Dict:
    """Load saved progress"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"processed_users": [], "failed_users": []}

def format_time(seconds: int) -> str:
    """Format seconds to human readable time"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def validate_phone_number(phone: str) -> bool:
    """Basic phone number validation"""
    phone = phone.replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        phone = phone[1:]
    return phone.isdigit() and len(phone) >= 7

def sanitize_username(username: str) -> str:
    """Sanitize username for Telegram"""
    if username.startswith('@'):
        return username[1:]
    return username