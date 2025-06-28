"""
Configuration management for Gameflip Sales Monitor
"""

import os
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        # Gameflip API configuration
        self.gameflip_api_key = os.getenv('GAMEFLIP_API_KEY', '')
        self.gameflip_totp_secret = os.getenv('GAMEFLIP_TOTP_SECRET', '')
        self.gameflip_api_base = os.getenv('GAMEFLIP_API_BASE', 'https://production-gameflip.fingershock.com/api/v1')
        
        # Discord configuration
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        
        # Monitor configuration
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))  # 1 minute default
        self.retry_delay = int(os.getenv('RETRY_DELAY', '60'))  # 1 minute default
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        # Storage configuration
        self.storage_file = os.getenv('STORAGE_FILE', 'last_sale.json')
    
    def validate(self):
        """Validate required configuration"""
        errors = []
        
        if not self.gameflip_api_key:
            errors.append("GAMEFLIP_API_KEY environment variable is required")
        
        if not self.gameflip_totp_secret:
            errors.append("GAMEFLIP_TOTP_SECRET environment variable is required")
        
        if not self.discord_webhook_url:
            errors.append("DISCORD_WEBHOOK_URL environment variable is required")
        
        if self.check_interval < 30:
            errors.append("CHECK_INTERVAL must be at least 30 seconds to avoid rate limiting")
        
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError("Configuration validation failed. Please check your environment variables.")
        
        logger.info("Configuration validated successfully")
    
    def __str__(self):
        """String representation (hiding sensitive data)"""
        return f"""
        Gameflip API Base: {self.gameflip_api_base}
        Check Interval: {self.check_interval} seconds
        Retry Delay: {self.retry_delay} seconds
        Max Retries: {self.max_retries}
        Storage File: {self.storage_file}
        """
