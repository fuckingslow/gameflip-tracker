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
        self.discord_queue_file = 'discord_failed_queue.json'
        
    # --- Discord failed queue management ---
    def queue_failed_discord_notification(self, notification_data):
        """Add a failed Discord notification to the persistent queue."""
        try:
            queue = []
            if os.path.exists(self.discord_queue_file):
                with open(self.discord_queue_file, 'r') as f:
                    queue = json.load(f)
            queue.append(notification_data)
            with open(self.discord_queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
            logger.info("Queued failed Discord notification for retry")
        except Exception as e:
            logger.error(f"Failed to queue Discord notification: {e}")

    def get_failed_discord_notifications(self):
        """Get all queued failed Discord notifications."""
        try:
            if os.path.exists(self.discord_queue_file):
                with open(self.discord_queue_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to read Discord queue: {e}")
            return []

    def clear_failed_discord_notifications(self, sent_ids=None):
        """Remove sent notifications from the queue. If sent_ids is None, clear all."""
        try:
            if not os.path.exists(self.discord_queue_file):
                return
            if sent_ids is None:
                os.remove(self.discord_queue_file)
                logger.info("Cleared all failed Discord notifications queue")
                return
            queue = self.get_failed_discord_notifications()
            queue = [n for n in queue if n.get('sale_id') not in sent_ids]
            with open(self.discord_queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
            logger.info(f"Cleared {len(sent_ids)} sent Discord notifications from queue")
        except Exception as e:
            logger.error(f"Failed to clear sent Discord notifications: {e}")
    
    def retry_failed_discord_notifications(self, discord_notifier):
        """Try to resend all failed Discord notifications. Returns list of sent sale_ids."""
        sent_ids = []
        queue = self.get_failed_discord_notifications()
        for notification in queue:
            try:
                success = discord_notifier.send_sale_notification(notification)
                if success:
                    sent_ids.append(notification.get('sale_id'))
            except Exception as e:
                logger.error(f"Retry failed for Discord notification: {e}")
        if sent_ids:
            self.clear_failed_discord_notifications(sent_ids)
        return sent_ids