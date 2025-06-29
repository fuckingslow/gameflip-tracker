#!/usr/bin/env python3
"""
Gameflip Sales Monitor with proper TOTP authentication
"""

import os
import json
import time
import logging
import requests
import pyotp
from datetime import datetime
from config import Config
from notifications import DiscordNotifier
from storage import SalesStorage
from alternative_notifications import AlternativeNotifier

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gameflip_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class GameflipMonitor:
    def __init__(self):
        self.config = Config()
        self.discord_notifier = DiscordNotifier(self.config.discord_webhook_url)
        self.alt_notifier = AlternativeNotifier()
        self.storage = SalesStorage()
        self.session = requests.Session()
        self.authenticated = self.authenticate()
        self.your_user_id = "us-east-1:36dd22da-79fb-461f-ad14-43679c44f78c"
        
    def authenticate(self):
        """Authenticate with Gameflip using GFAPI + TOTP format"""
        try:
            # Extract API key (client ID only)
            api_key = self.config.gameflip_api_key
            if ':' in api_key:
                api_key = api_key.split(':')[0]
            
            # Generate TOTP code
            totp = pyotp.TOTP(self.config.gameflip_totp_secret, digits=6, interval=30)
            totp_code = totp.now()
            
            # Set up GFAPI authentication with TOTP
            auth_header = f'GFAPI {api_key}:{totp_code}'
            self.session.headers.update({
                'Authorization': auth_header,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            # Test authentication with profile endpoint
            test_url = f"{self.config.gameflip_api_base}/account/me/profile"
            response = self.session.get(test_url, timeout=30)
            
            if response.status_code == 200:
                profile = response.json().get('data', {})
                display_name = profile.get('display_name', 'Unknown')
                user_id = profile.get('owner', 'Unknown')
                logger.info(f"Successfully authenticated as: {display_name} ({user_id})")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                if response.text:
                    error_data = response.json().get('error', {})
                    logger.error(f"Error: {error_data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def refresh_auth(self):
        """Refresh TOTP authentication"""
        try:
            api_key = self.config.gameflip_api_key
            if ':' in api_key:
                api_key = api_key.split(':')[0]
            
            totp = pyotp.TOTP(self.config.gameflip_totp_secret, digits=6, interval=30)
            totp_code = totp.now()
            
            auth_header = f'GFAPI {api_key}:{totp_code}'
            self.session.headers.update({'Authorization': auth_header})
            return True
        except Exception as e:
            logger.error(f"Error refreshing auth: {e}")
            return False

    def get_recent_sales(self):
        """Fetch recent sales from Gameflip API"""
        try:
            # Refresh TOTP authentication
            if not self.refresh_auth():
                logger.error("Failed to refresh authentication")
                return []
            
            # Use /listing endpoint with status=sold to get sales data
            url = f"{self.config.gameflip_api_base}/listing"
            params = {
                'status': 'sold',
                'limit': 20,
                'owner': self.your_user_id,  # Filter by your user ID
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                all_sales = data.get('data', [])
                # print(f"Fetched {len(all_sales)} sales from Gameflip API")
                # print(f"Sales data: {json.dumps(all_sales, indent=2)}")
                return all_sales
            else:
                logger.error(f"Failed to fetch sales: {response.status_code}")
                if response.text:
                    error_data = response.json().get('error', {})
                    logger.error(f"Error: {error_data.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching sales: {e}")
            return []

    def get_listing_details(self, listing_id):
        """Get detailed information about a listing"""
        try:
            # Refresh auth for this request
            if not self.refresh_auth():
                return {}
            
            url = f"{self.config.gameflip_api_base}/listing/{listing_id}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {})
            else:
                logger.warning(f"Failed to get listing details for {listing_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching listing details: {e}")
            return {}

    def process_new_sales(self, sales):
        """Process new sales and send notifications"""
        last_sale_ids = set(self.storage.get_last_sale_ids())
        new_sales = []
        sales_to_track = sales[:20] if sales else []
        current_sale_ids = [sale.get('id') for sale in sales_to_track if sale.get('id')]

        # If first run (no last_sale_ids), just store the current 20 and don't send notifications
        if not last_sale_ids and current_sale_ids:
            logger.info("First run detected - setting initial sale IDs without sending notifications for historical sales")
            self.storage.set_last_sale_ids(current_sale_ids)
            return 0

        # Find sales not in last tracked list
        for sale in sales_to_track:
            sale_id = sale.get('id')
            if sale_id and sale_id not in last_sale_ids:
                new_sales.append(sale)

        if new_sales:
            # Update tracked sale IDs with the latest 20
            self.storage.set_last_sale_ids(current_sale_ids)
            # Limit notifications to prevent spam (max 5 at once)
            if len(new_sales) > 5:
                logger.info(f"Found {len(new_sales)} new sales, sending notifications for the 5 most recent")
                new_sales = new_sales[:5]
            for sale in new_sales:
                self.send_sale_notification(sale)
                if len(new_sales) > 1:
                    time.sleep(0.5)
        return len(new_sales)

    def send_sale_notification(self, sale):
        """Send Discord notification for a sale"""
        try:
            sale_id = sale.get('id', 'Unknown')
            listing_id = sale.get('listing_id')
            price = sale.get('price', 0) / 100  # Convert from cents to dollars
            buyer_id = sale.get('buyer', {}).get('id', 'Unknown')
            created_date = sale.get('created', '')
            
            # Get listing details for item name
            listing_details = {}
            if listing_id:
                listing_details = self.get_listing_details(listing_id)
            
            item_name = listing_details.get('name', sale.get('name', 'Unknown Item'))
            item_description = listing_details.get('description', '')
            
            # Format the notification
            notification_data = {
                'sale_id': sale_id,
                'item_name': item_name,
                'item_description': item_description,
                'price': price,
                'buyer_id': buyer_id,
                'created_date': created_date,
                'listing_id': listing_id
            }
            
            # Try Discord first, fallback to file logging if blocked
            success = self.discord_notifier.send_sale_notification(notification_data)
            
            if success:
                logger.info(f"Discord notification sent for sale: {sale_id} - {item_name} - ${price:.2f}")
            else:
                # Fallback to file logging when Discord is blocked
                logger.warning(f"Discord blocked, logging sale to file: {sale_id} - {item_name} - ${price:.2f}")
                self.alt_notifier.log_sale_notification(notification_data)
                
        except Exception as e:
            logger.error(f"Error processing sale notification: {e}")

    def run_monitor_cycle(self):
        """Run a single monitoring cycle"""
        try:
            logger.info("Checking for new sales...")
            
            # Get recent sales
            sales = self.get_recent_sales()
            
            if not sales:
                logger.info("No sales found for your account")
                return 0
            
            # Process new sales
            new_sales_count = self.process_new_sales(sales)
            
            if new_sales_count > 0:
                logger.info(f"Found {new_sales_count} new sales")
            else:
                logger.info("No new sales found")
                
            return new_sales_count
            
        except Exception as e:
            logger.error(f"Error in monitor cycle: {e}")
            return 0

    def run(self):
        """Main monitoring loop"""
        if not self.authenticated:
            logger.error("Authentication failed. Cannot start monitoring.")
            return
        
        # Send startup notification
        try:
            self.discord_notifier.send_startup_notification()
        except Exception as e:
            logger.warning("Failed to send startup notification")
        
        logger.info("Starting Gameflip Sales Monitor...")
        logger.info(f"Check interval: {self.config.check_interval} seconds")
        
        while True:
            try:
                self.run_monitor_cycle()
                
                logger.info(f"Waiting {self.config.check_interval} seconds until next check...")
                time.sleep(self.config.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)

def main():
    """Main entry point"""
    try:
        config = Config()
        config.validate()
        
        monitor = GameflipMonitor()
        monitor.run()
        
    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())