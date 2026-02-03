import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram API credentials
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    
    # Proxy settings
    PROXY_TYPE = os.getenv('PROXY_TYPE')
    PROXY_HOST = os.getenv('PROXY_HOST')
    PROXY_PORT = os.getenv('PROXY_PORT')
    PROXY_USERNAME = os.getenv('PROXY_USERNAME')
    PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
    
    # Application settings
    SESSIONS_DIR = 'sessions'
    OUTPUT_DIR = 'output'
    LOG_FILE = 'telegram_member_adder.log'
    
    # Scraping settings
    MAX_PARTICIPANTS = 10000  # Maximum members to scrape
    SCRAPE_DELAY = 1  # Delay between requests in seconds
    
    # Adding settings
    BATCH_SIZE = 50  # Users per batch
    ADD_DELAY = 30   # Delay between adds in seconds
    BATCH_DELAY = 900  # Delay between batches in seconds
    MAX_RETRIES = 3    # Max retries for failed adds
    
    # Filters
    MIN_ACCOUNT_AGE_DAYS = 30  # Minimum account age
    EXCLUDE_BOTS = True
    EXCLUDE_DELETED = True
    
    @classmethod
    def get_proxy(cls):
        """Return proxy configuration if set"""
        if cls.PROXY_HOST and cls.PROXY_PORT:
            proxy = {
                'proxy_type': cls.PROXY_TYPE or 'socks5',
                'addr': cls.PROXY_HOST,
                'port': int(cls.PROXY_PORT),
            }
            if cls.PROXY_USERNAME:
                proxy['username'] = cls.PROXY_USERNAME
            if cls.PROXY_PASSWORD:
                proxy['password'] = cls.PROXY_PASSWORD
            return proxy
        return None