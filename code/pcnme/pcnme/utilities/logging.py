"""
Centralized logging utilities for PCNME experiments.
All scripts use this module instead of duplicating setup code.
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logging(output_dir: Path, script_name: str, log_level: str = "INFO"):
    """
    Setup logging to console and file.
    
    Args:
        output_dir: directory to save logs
        script_name: name of script (used in log filename and logger name)
        log_level: logging level (DEBUG, INFO, WARNING)
        
    Returns:
        logger instance
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logger = logging.getLogger(f'PCNME.{script_name}')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler (INFO or higher)
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, log_level))
    
    # File handler (always DEBUG)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    
    logger.addHandler(ch)
    logger.addHandler(fh)
    
    return logger


def get_logger(name: str):
    """Get or create a logger by name."""
    return logging.getLogger(f'PCNME.{name}')
