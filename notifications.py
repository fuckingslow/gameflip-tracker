"""
Discord notification handler for Gameflip Sales Monitor
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.session = requests.Session()
    
    def send_webhook(self, payload):
        """Send a webhook to Discord"""
        response = None
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return True
            
        except requests.exceptions.HTTPError as e:
            if response and response.status_code == 429:
                # Check if this is Cloudflare blocking (HTML response) or actual Discord rate limit
                if 'cloudflare' in response.text.lower() or 'html' in response.text.lower():
                    logger.error("Cloudflare is blocking Discord webhook requests from this IP")
                    logger.error("This is a network-level restriction, not an application error")
                    return False
                else:
                    # Actual Discord rate limit
                    retry_after = response.headers.get('Retry-After', '5')
                    wait_time = min(int(retry_after), 10)
                    logger.warning(f"Discord rate limited, waiting {wait_time} seconds")
                    import time
                    time.sleep(wait_time)
                    try:
                        response = self.session.post(
                            self.webhook_url,
                            json=payload,
                            timeout=30
                        )
                        response.raise_for_status()
                        return True
                    except:
                        logger.warning("Still rate limited after retry, skipping this notification")
                        return False
            else:
                logger.error(f"Failed to send Discord webhook: {e}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False
    
    def send_sale_notification(self, sale_data):
        """Send a sale notification to Discord"""
        try:
            # Format the sale data
            sale_id = sale_data.get('sale_id', 'Unknown')
            item_name = sale_data.get('item_name', 'Unknown Item')
            price = sale_data.get('price', 0)
            buyer_id = sale_data.get('buyer_id', 'Unknown')
            created_date = sale_data.get('created_date', '')
            
            # Format date
            try:
                if created_date:
                    date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S UTC')
                else:
                    formatted_date = 'Unknown'
            except:
                formatted_date = created_date
            
            # Create Discord embed
            embed = {
                "title": "🎉 New Gameflip Sale!",
                "color": 0x00FF00,  # Green color
                "fields": [
                    {
                        "name": "📦 Item",
                        "value": item_name,
                        "inline": True
                    },
                    {
                        "name": "💰 Price",
                        "value": f"${price:.2f}",
                        "inline": True
                    },
                    {
                        "name": "👤 Buyer ID",
                        "value": buyer_id,
                        "inline": True
                    },
                    {
                        "name": "📅 Sale Date",
                        "value": formatted_date,
                        "inline": False
                    },
                    {
                        "name": "🔗 Sale ID",
                        "value": sale_id,
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {
                    "text": "Gameflip Sales Monitor"
                }
            }
            
            # Add description if available
            description = sale_data.get('item_description', '').strip()
            if description and len(description) <= 200:
                embed["description"] = description
            
            payload = {
                "embeds": [embed]
            }
            
            return self.send_webhook(payload)
            
        except Exception as e:
            logger.error(f"Error creating sale notification: {e}")
            return False
    
    def send_startup_notification(self):
        """Send a notification when the monitor starts"""
        try:
            embed = {
                "title": "🤖 Gameflip Monitor Started",
                "description": "Sales monitoring is now active!",
                "color": 0x0099FF,  # Blue color
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {
                    "text": "Gameflip Sales Monitor"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            success = self.send_webhook(payload)
            if success:
                logger.info("Startup notification sent to Discord")
            else:
                logger.warning("Failed to send startup notification")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False
    
    def send_error_notification(self, error_message):
        """Send an error notification to Discord"""
        try:
            embed = {
                "title": "⚠️ Gameflip Monitor Error",
                "description": f"An error occurred: {error_message}",
                "color": 0xFF0000,  # Red color
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {
                    "text": "Gameflip Sales Monitor"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            return self.send_webhook(payload)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
