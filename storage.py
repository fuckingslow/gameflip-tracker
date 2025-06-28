"""
Storage management for Gameflip Sales Monitor
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class SalesStorage:
    def __init__(self, storage_file='last_sale.json'):
        self.storage_file = storage_file
        self.data = self._load_data()
    
    def _load_data(self):
        """Load data from storage file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded storage data from {self.storage_file}")
                    return data
            else:
                logger.info(f"Storage file {self.storage_file} doesn't exist, creating new one")
                return {}
        except Exception as e:
            logger.error(f"Error loading storage file {self.storage_file}: {e}")
            return {}
    
    def _save_data(self):
        """Save data to storage file"""
        try:
            # Create backup of existing file
            if os.path.exists(self.storage_file):
                backup_file = f"{self.storage_file}.backup"
                os.rename(self.storage_file, backup_file)
            
            # Save new data
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            # Remove backup if save was successful
            backup_file = f"{self.storage_file}.backup"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            logger.debug(f"Saved storage data to {self.storage_file}")
            
        except Exception as e:
            logger.error(f"Error saving storage file {self.storage_file}: {e}")
            
            # Restore backup if it exists
            backup_file = f"{self.storage_file}.backup"
            if os.path.exists(backup_file):
                try:
                    os.rename(backup_file, self.storage_file)
                    logger.info("Restored backup storage file")
                except:
                    pass
    
    def get_last_sale_id(self):
        """Get the ID of the last processed sale"""
        return self.data.get('last_sale_id')
    
    def set_last_sale_id(self, sale_id):
        """Set the ID of the last processed sale"""
        if sale_id:
            self.data['last_sale_id'] = sale_id
            self.data['last_updated'] = datetime.utcnow().isoformat()
            self._save_data()
            logger.info(f"Updated last sale ID: {sale_id}")
    
    def get_last_updated(self):
        """Get the timestamp of the last update"""
        return self.data.get('last_updated')
    
    def reset(self):
        """Reset storage data"""
        self.data = {}
        self._save_data()
        logger.info("Storage data reset")
    
    def get_stats(self):
        """Get storage statistics"""
        return {
            'last_sale_id': self.get_last_sale_id(),
            'last_updated': self.get_last_updated(),
            'storage_file': self.storage_file,
            'file_exists': os.path.exists(self.storage_file)
        }
