"""Compatibility entry point for the decoded-audio health check."""
import os
from pathlib import Path
import sys

os.chdir(Path(__file__).resolve().parents[1])
os.execv(sys.executable, [sys.executable, "-m", "radio.watchdog", "--health"])
