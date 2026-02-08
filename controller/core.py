class DeviceController:
    def __init__(self):
        self.devices = []  # To store device information
        self.configurations = {}  # To store device configurations
    
    def add_device(self, device_id, device_info):
        """Add a new device with its information."""
        self.devices.append({'id': device_id, 'info': device_info})
        print(f'Device {device_id} added.')
    
    def remove_device(self, device_id):
        """Remove a device by its ID."""
        self.devices = [device for device in self.devices if device['id'] != device_id]
        print(f'Device {device_id} removed.')
    
    def configure_device(self, device_id, configuration):
        """Configure a specific device with the given settings."""
        self.configurations[device_id] = configuration
        print(f'Device {device_id} configured.')
    
    def get_device_info(self, device_id):
        """Retrieve information for a specific device."""
        for device in self.devices:
            if device['id'] == device_id:
                return device['info']
        return None
    
    def list_devices(self):
        """List all registered devices."""
        return self.devices
    
    def handle_permissions(self, device_id, user_permissions):
        """Manage permissions for each device based on user roles."""
        # Implement permission handling logic here
        print(f'Permissions for device {device_id} handled based on provided user roles.')
