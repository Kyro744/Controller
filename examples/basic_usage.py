# Basic Usage of DeviceController and DeviceDiscovery Classes

"""
This script demonstrates how to use the DeviceController and DeviceDiscovery classes
from the Kyro744 Controller module.
"""

from Controller import DeviceController, DeviceDiscovery

# Example usage of DeviceDiscovery

def discover_devices():
    discovery = DeviceDiscovery()
    devices = discovery.scan()  # Assuming scan() returns a list of devices
    for device in devices:
        print(f'Discovered device: {device}')

# Example usage of DeviceController

def control_device(device_id):
    controller = DeviceController(device_id)
    controller.connect()  # Connect to the device
    controller.perform_action('turn_on')  # Example action
    controller.disconnect()  # Disconnect from the device

if __name__ == "__main__":
    discover_devices()
    control_device('device_id_example')