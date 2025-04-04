"""
File Watcher Module

This module provides functionality to monitor a directory for file changes
using the watchfiles library.
"""

import os
import time
import logging
from enum import Enum
from typing import Callable, Optional
from watchfiles import watch, Change

# Set up logging
logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Enum for file event types."""
    CREATED = 'created'
    MODIFIED = 'modified'
    DELETED = 'deleted'


def _map_event_type(change_type: Change) -> EventType:
    """
    Maps watchfiles Change enum to our EventType enum.
    
    Args:
        change_type: The Change enum value from watchfiles
        
    Returns:
        EventType: The corresponding EventType value
    """
    mapping = {
        Change.added: EventType.CREATED,
        Change.modified: EventType.MODIFIED,
        Change.deleted: EventType.DELETED
    }
    return mapping.get(change_type, EventType.MODIFIED)


def start_file_watcher(callback: Callable[[str, str], None], watch_dir: str = 'src') -> None:
    """
    Start watching a directory for file changes.
    
    Args:
        callback: A function that will be called when a file change is detected.
                 The callback should accept two parameters:
                 - event_type: A string, one of 'created', 'modified', 'deleted'
                 - file_path: The path to the file that changed
        watch_dir: The directory to watch for changes. Defaults to 'src'.
        
    Raises:
        FileNotFoundError: If the watch_dir does not exist
        PermissionError: If there are permission issues accessing the directory
    """
    if not os.path.exists(watch_dir):
        logger.error(f"Directory not found: {watch_dir}")
        raise FileNotFoundError(f"Directory not found: {watch_dir}")
    
    if not os.path.isdir(watch_dir):
        logger.error(f"Path is not a directory: {watch_dir}")
        raise NotADirectoryError(f"Path is not a directory: {watch_dir}")
    
    try:
        logger.info(f"Starting file watcher on directory: {watch_dir}")
        for changes in watch(watch_dir):
            for change_type, file_path in changes:
                event_type = _map_event_type(change_type)
                logger.debug(f"File change detected: {event_type.value} - {file_path}")
                
                try:
                    callback(event_type.value, file_path)
                except Exception as e:
                    logger.error(f"Error in callback function: {str(e)}")
    except KeyboardInterrupt:
        logger.info("File watcher stopped by user")
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in file watcher: {str(e)}")
        raise


def stop_file_watcher() -> None:
    """
    Stop the file watcher.
    
    Note: This is a placeholder function for future implementation.
    Currently, the watcher can be stopped by sending a KeyboardInterrupt.
    """
    # This is a placeholder for future implementation
    # Currently, the watcher can be stopped by KeyboardInterrupt
    logger.info("File watcher stopping method called (placeholder)") 