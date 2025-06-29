#!/usr/bin/env python3
"""
Alternative notification methods when Discord webhooks are blocked
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AlternativeNotifier:
    def __init__(self):
        self.log_file = 'sales_notifications.log'
        self.json_file = 'sales_notifications.json'
        
    def log_sale_notification(self, sale_data):
        """Log sale notification to file when Discord is blocked"""
        try:
            # Create readable log entry
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            item_name = sale_data.get('item_name', 'Unknown Item')
            price = sale_data.get('price', 0)
            sale_id = sale_data.get('sale_id', 'Unknown')
            
            log_entry = f"""
{timestamp} - NEW GAMEFLIP SALE
Item: {item_name}
Price: ${price:.2f}
Sale ID: {sale_id}
{'='*50}
"""
            
            # Append to log file
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
            
            # Also save as JSON for programmatic access
            self.save_json_notification(sale_data)
            
            logger.info(f"Sale notification logged to {self.log_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log sale notification: {e}")
            return False
    
    def save_json_notification(self, sale_data):
        """Save notification as JSON for external processing"""
        try:
            # Load existing notifications
            notifications = []
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r') as f:
                    notifications = json.load(f)
            
            # Add timestamp and new notification
            notification = sale_data.copy()
            notification['notification_time'] = datetime.utcnow().isoformat()
            notification['status'] = 'logged_due_to_cloudflare_block'
            
            notifications.append(notification)
            
            # Keep only last 50 notifications
            notifications = notifications[-50:]
            
            # Save updated notifications
            with open(self.json_file, 'w') as f:
                json.dump(notifications, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save JSON notification: {e}")
    
    def get_pending_notifications(self):
        """Get all logged notifications for manual review"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to read notifications: {e}")
            return []
    
    def clear_notifications(self):
        """Clear logged notifications after they've been processed"""
        try:
            if os.path.exists(self.json_file):
                os.remove(self.json_file)
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            logger.info("Cleared notification logs")
        except Exception as e:
            logger.error(f"Failed to clear notifications: {e}")
    
    def clear_logs_daily(self):
        """Clear log and JSON files if the date has changed since last write."""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        marker_file = 'sales_notifications.last_cleared'
        last_cleared = None
        if os.path.exists(marker_file):
            with open(marker_file, 'r') as f:
                last_cleared = f.read().strip()
        if last_cleared != today:
            # Clear log and JSON files
            if os.path.exists(self.log_file):
                open(self.log_file, 'w').close()
            if os.path.exists(self.json_file):
                open(self.json_file, 'w').close()
            with open(marker_file, 'w') as f:
                f.write(today)
            logger.info("Cleared fallback notification logs for new day")