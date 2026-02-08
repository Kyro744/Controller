"""
Controller - Universal Device Control Tool
A powerful Python application for controlling TVs, smart devices, and IoT devices
with built-in internet connectivity and permission-based access control.
"""

__version__ = "0.1.0"
__author__ = "Kyro744"
__description__ = "Universal device control with internet connectivity and permissions"

from .core import DeviceController
from .discovery import DeviceDiscovery

__all__ = ['DeviceController', 'DeviceDiscovery']