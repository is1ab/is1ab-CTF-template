#!/usr/bin/env python3
"""
Challenge validation module for web server integration
"""

# Import the main class from the hyphenated file
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Load and re-export the class
exec(open(os.path.join(os.path.dirname(__file__), 'validate-challenge.py')).read())