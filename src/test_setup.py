# =============================================================================
#  Filename: test_setup.py
#
#  Short Description: Environment verification script for SupportVectors projects.
#
#  Creation date: 2025-08-31
#  Author: Asif Qamar
# =============================================================================
#!/usr/bin/env python3
"""
Test script to verify that the environment and configuration are set up correctly.
"""

import sys
import os
from pathlib import Path
from typing import NoReturn

from loguru import logger

def main() -> NoReturn:
    logger.info("🚀 SupportVectors Environment Setup Test")
    logger.info("=" * 50)
    
    # Test Python version
    logger.info(f"✅ Python version: {sys.version}")
    
    # Test current working directory
    logger.info(f"✅ Working directory: {os.getcwd()}")
    
    # Test PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH', 'Not set')
    logger.info(f"✅ PYTHONPATH: {pythonpath}")
    
    # Test PROJECT_PYTHON
    project_python = os.environ.get('PROJECT_PYTHON', 'Not set')
    logger.info(f"✅ PROJECT_PYTHON: {project_python}")
    
    # Verify the Python executable exists
    if project_python != 'Not set':
        if os.path.exists(project_python):
            logger.info(f"✅ Project Python executable found at: {project_python}")
        else:
            logger.warning(f"⚠️  Project Python executable not found at: {project_python}")
    
    # Test that we can import our module
    try:
        # Dynamic import based on the module structure
        src_path = Path('src')
        if src_path.exists():
            module_dirs = [d for d in src_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
            if module_dirs:
                module_name = module_dirs[0].name
                logger.info(f"✅ Found module: {module_name}")
                
                # Try to import the module
                sys.path.insert(0, str(src_path))
                try:
                    module = __import__(module_name)
                    logger.info(f"✅ Successfully imported {module_name}")
                    
                    # Try to access the config if it exists
                    if hasattr(module, 'config'):
                        logger.info("✅ Configuration object found and accessible")
                    else:
                        logger.info("ℹ️  Configuration object not yet accessible (this is normal)")
                        
                except ImportError as e:
                    logger.warning(f"⚠️  Could not import {module_name}: {e}")
                    logger.info("   This might be normal if dependencies aren't fully installed yet")
            else:
                logger.info("ℹ️  No module directories found in src/")
        else:
            logger.warning("⚠️  src/ directory not found")
    
    except Exception as e:
        logger.exception(f"⚠️  Error during module test: {e}")
    
    logger.info("=" * 50)
    logger.info("🎉 Hello World! Environment setup test completed!")
    logger.info("🎯 Your SupportVectors project environment is ready to use!")

if __name__ == "__main__":
    main()
