#!/usr/bin/env python3
"""
Telegram Member Scraper & Adder v2.0
Modern async implementation with enhanced features
"""

import asyncio
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, PeerFloodError, UserPrivacyRestrictedError,
    UserBotError, UsernameNotOccupiedError, ChatAdminRequiredError
)
from telethon.tl.functions.channels import InviteToChannelRequest, GetFullChannelRequest
from telethon.tl.types import User, ChannelParticipant
from tqdm import tqdm
from colorama import init, Fore, Style

from config import Config

# Initialize colorama
init(autoreset=True)

class TelegramMemberManager:
    def __init__(self):
        self.setup_directories()
        self.setup_logging()
        self.clients: Dict[str, TelegramClient] = {}
        self.processed_users: Set[int] = set()
        self.failed_users: Set[int] = set()
        
    def setup_directories(self):
        """Create necessary directories"""
        Path(Config.SESSIONS_DIR).mkdir(exist_ok=True)
        Path(Config.OUTPUT_DIR).mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def print_header(self):
        """Print application header"""
        print(Fore.CYAN + "=" * 60)
        print(Fore.GREEN + "  Telegram Member Scraper & Adder v2.0")
        print(Fore.CYAN + "=" * 60)
        print(Fore.YELLOW + "  Updated for modern Telegram API")
        print(Fore.CYAN + "=" * 60 + "\n")
        
    def get_credentials(self) -> tuple:
        """Get API credentials from user or config"""
        if Config.API_ID and Config.API_HASH:
            api_id = Config.API_ID
            api_hash = Config.API_HASH
        else:
            print(Fore.YELLOW + "Please enter your Telegram API credentials")
            print(Fore.WHITE + "Get them from https://my.telegram.org\n")
            api_id = input(Fore.GREEN + "Enter API ID: ").strip()
            api_hash = input(Fore.GREEN + "Enter API Hash: ").strip()
            
        return api_id, api_hash
        
    def get_phone_numbers(self) -> List[str]:
        """Get phone numbers from user"""
        print(Fore.CYAN + "\nAccount Setup")
        print("-" * 30)
        phones = []
        while True:
            phone = input(Fore.GREEN + f"Enter phone number #{len(phones) + 1} (or press Enter to finish): ").strip()
            if not phone:
                break
            phones.append(phone)
        return phones if phones else [input(Fore.GREEN + "Enter your phone number: ").strip()]
        
    def get_group_info(self) -> tuple:
        """Get group information from user"""
        print(Fore.CYAN + "\nGroup Information")
        print("-" * 30)
        source_group = input(Fore.GREEN + "Source group (username/link): ").strip()
        target_group = input(Fore.GREEN + "Target group (username): ").strip()
        return source_group, target_group
        
    async def create_client(self, phone: str, api_id: str, api_hash: str) -> TelegramClient:
        """Create and configure Telegram client"""
        session_file = os.path.join(Config.SESSIONS_DIR, f"session_{phone.replace('+', '')}")
        proxy = Config.get_proxy()
        
        client = TelegramClient(
            session_file,
            api_id,
            api_hash,
            proxy=proxy,
            connection_retries=5
        )
        
        await client.start(phone)
        self.clients[phone] = client
        return client
        
    async def authenticate_clients(self, phones: List[str], api_id: str, api_hash: str):
        """Authenticate all clients"""
        print(Fore.CYAN + f"\nAuthenticating {len(phones)} account(s)...")
        
        for i, phone in enumerate(phones, 1):
            try:
                print(Fore.YELLOW + f"[{i}/{len(phones)}] Authenticating {phone}...")
                client = await self.create_client(phone, api_id, api_hash)
                
                # Test authentication
                me = await client.get_me()
                print(Fore.GREEN + f"✓ Authenticated as {me.first_name} (@{me.username or 'N/A'})")
                
            except Exception as e:
                print(Fore.RED + f"✗ Failed to authenticate {phone}: {e}")
                raise
                
    async def scrape_members(self, source_group: str, max_count: int = Config.MAX_PARTICIPANTS) -> List[Dict]:
        """Scrape members from source group"""
        print(Fore.CYAN + f"\nScraping members from {source_group}...")
        members = []
        
        # Use first available client
        client = next(iter(self.clients.values()))
        
        try:
            # Resolve the group
            if source_group.startswith('https://t.me/'):
                source_group = source_group.split('/')[-1]
                
            chat = await client.get_entity(source_group)
            print(Fore.YELLOW + f"Found group: {chat.title}")
            
            # Get participants
            progress_bar = tqdm(
                desc="Scraping members",
                unit="users",
                total=max_count,
                colour="green"
            )
            
            async for participant in client.iter_participants(chat, limit=max_count):
                if isinstance(participant, User) and self.filter_user(participant):
                    member_data = {
                        'id': participant.id,
                        'username': participant.username or '',
                        'first_name': participant.first_name or '',
                        'last_name': participant.last_name or '',
                        'access_hash': getattr(participant, 'access_hash', ''),
                        'date': datetime.now().isoformat()
                    }
                    members.append(member_data)
                    
                progress_bar.update(1)
                await asyncio.sleep(Config.SCRAPE_DELAY)
                
                if len(members) >= max_count:
                    break
                    
            progress_bar.close()
            
            print(Fore.GREEN + f"✓ Successfully scraped {len(members)} members")
            
            # Save to CSV
            csv_file = os.path.join(Config.OUTPUT_DIR, f"members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            self.save_members_to_csv(members, csv_file)
            print(Fore.GREEN + f"✓ Saved to {csv_file}")
            
            return members
            
        except Exception as e:
            print(Fore.RED + f"✗ Error scraping members: {e}")
            self.logger.error(f"Scraping error: {e}")
            raise
            
    def filter_user(self, user: User) -> bool:
        """Apply filters to determine if user should be included"""
        # Exclude bots
        if Config.EXCLUDE_BOTS and user.bot:
            return False
            
        # Exclude deleted accounts
        if Config.EXCLUDE_DELETED and user.deleted:
            return False
            
        # Check account age (approximate)
        if hasattr(user, 'date') and user.date:
            account_age = datetime.now().replace(tzinfo=None) - user.date.replace(tzinfo=None)
            if account_age.days < Config.MIN_ACCOUNT_AGE_DAYS:
                return False
                
        return True
        
    def save_members_to_csv(self, members: List[Dict], filename: str):
        """Save members to CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if members:
                writer = csv.DictWriter(f, fieldnames=members[0].keys())
                writer.writeheader()
                writer.writerows(members)
                
    def load_members_from_csv(self, filename: str) -> List[Dict]:
        """Load members from CSV file"""
        members = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                members = list(reader)
            print(Fore.GREEN + f"✓ Loaded {len(members)} members from {filename}")
        except FileNotFoundError:
            print(Fore.RED + f"✗ File not found: {filename}")
        except Exception as e:
            print(Fore.RED + f"✗ Error loading CSV: {e}")
            
        return members
        
    async def add_members_to_group(self, members: List[Dict], target_group: str):
        """Add members to target group"""
        print(Fore.CYAN + f"\nAdding members to {target_group}...")
        
        # Use all available clients for distribution
        clients_list = list(self.clients.values())
        client_count = len(clients_list)
        
        # Filter out already processed members
        pending_members = [m for m in members if int(m['id']) not in self.processed_users]
        
        if not pending_members:
            print(Fore.YELLOW + "No new members to add")
            return
            
        print(Fore.YELLOW + f"Processing {len(pending_members)} members using {client_count} account(s)")
        
        # Distribute members among clients
        for i, member in enumerate(tqdm(pending_members, desc="Adding members", unit="user")):
            client_idx = i % client_count
            client = clients_list[client_idx]
            
            try:
                await self.add_single_member(client, member, target_group)
                self.processed_users.add(int(member['id']))
                
                # Delay between adds
                await asyncio.sleep(Config.ADD_DELAY)
                
                # Batch delay
                if (i + 1) % Config.BATCH_SIZE == 0 and i > 0:
                    print(Fore.YELLOW + f"Batch limit reached. Waiting {Config.BATCH_DELAY} seconds...")
                    await asyncio.sleep(Config.BATCH_DELAY)
                    
            except Exception as e:
                self.failed_users.add(int(member['id']))
                self.logger.error(f"Failed to add {member['username']} ({member['id']}): {e}")
                
    async def add_single_member(self, client: TelegramClient, member: Dict, target_group: str):
        """Add a single member to the group"""
        retries = 0
        while retries < Config.MAX_RETRIES:
            try:
                # Get target group entity
                target_entity = await client.get_entity(target_group)
                
                # Get user entity
                if member['username']:
                    user_entity = await client.get_entity(f"@{member['username']}")
                else:
                    user_entity = await client.get_entity(int(member['id']))
                
                # Add user to group
                await client(InviteToChannelRequest(target_entity, [user_entity]))
                
                print(Fore.GREEN + f"✓ Added {member['username'] or member['first_name']} ({member['id']})")
                return
                
            except FloodWaitError as e:
                wait_time = e.seconds
                print(Fore.YELLOW + f"Flood wait: sleeping for {wait_time} seconds")
                await asyncio.sleep(wait_time)
                retries += 1
                
            except PeerFloodError:
                print(Fore.RED + f"Peer flood error for {member['username']}")
                raise
                
            except UserPrivacyRestrictedError:
                print(Fore.YELLOW + f"Privacy restricted: {member['username']}")
                return
                
            except UsernameNotOccupiedError:
                print(Fore.YELLOW + f"Username not found: {member['username']}")
                return
                
            except Exception as e:
                if retries < Config.MAX_RETRIES - 1:
                    print(Fore.YELLOW + f"Retry {retries + 1}/{Config.MAX_RETRIES} for {member['username']}: {e}")
                    await asyncio.sleep(5)
                    retries += 1
                else:
                    print(Fore.RED + f"Failed after {Config.MAX_RETRIES} retries: {member['username']}")
                    raise
                    
    def show_summary(self):
        """Show operation summary"""
        print(Fore.CYAN + "\n" + "=" * 50)
        print(Fore.GREEN + "OPERATION SUMMARY")
        print(Fore.CYAN + "=" * 50)
        print(Fore.WHITE + f"Processed users: {len(self.processed_users)}")
        print(Fore.WHITE + f"Failed users: {len(self.failed_users)}")
        print(Fore.WHITE + f"Success rate: {len(self.processed_users)/(len(self.processed_users)+len(self.failed_users))*100:.1f}%" if self.processed_users or self.failed_users else "0%")
        print(Fore.CYAN + "=" * 50)
        
    async def cleanup(self):
        """Cleanup resources"""
        for client in self.clients.values():
            try:
                await client.disconnect()
            except:
                pass
        self.clients.clear()

async def main():
    manager = TelegramMemberManager()
    manager.print_header()
    
    try:
        # Get credentials
        api_id, api_hash = manager.get_credentials()
        
        # Get phone numbers
        phones = manager.get_phone_numbers()
        
        # Get group information
        source_group, target_group = manager.get_group_info()
        
        # Authenticate clients
        await manager.authenticate_clients(phones, api_id, api_hash)
        
        # Menu
        while True:
            print(Fore.CYAN + "\nChoose operation:")
            print("1. Scrape members from source group")
            print("2. Add members to target group")
            print("3. Both (scrape then add)")
            print("4. Exit")
            
            choice = input(Fore.GREEN + "\nEnter choice (1-4): ").strip()
            
            if choice == '1':
                members = await manager.scrape_members(source_group)
                print(Fore.GREEN + f"\nScraping complete! Found {len(members)} members.")
                
            elif choice == '2':
                csv_files = list(Path(Config.OUTPUT_DIR).glob("members_*.csv"))
                if not csv_files:
                    print(Fore.RED + "No member files found. Please scrape members first.")
                    continue
                    
                print(Fore.CYAN + "\nAvailable member files:")
                for i, file in enumerate(csv_files, 1):
                    print(f"{i}. {file.name}")
                    
                try:
                    file_choice = int(input(Fore.GREEN + "Select file number: ")) - 1
                    selected_file = csv_files[file_choice]
                    members = manager.load_members_from_csv(str(selected_file))
                    await manager.add_members_to_group(members, target_group)
                except (ValueError, IndexError):
                    print(Fore.RED + "Invalid selection")
                    
            elif choice == '3':
                members = await manager.scrape_members(source_group)
                if members:
                    await manager.add_members_to_group(members, target_group)
                    
            elif choice == '4':
                break
                
            else:
                print(Fore.RED + "Invalid choice")
                
        manager.show_summary()
        
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nOperation cancelled by user")
    except Exception as e:
        print(Fore.RED + f"\nError: {e}")
        logging.error(f"Application error: {e}", exc_info=True)
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nGoodbye!")
    except Exception as e:
        print(Fore.RED + f"Fatal error: {e}")