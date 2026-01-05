# Raspberry Pi Sprinkler Automation

Automated sprinkler control system using Raspberry Pi GPIO.

## Features

- **Configurable Schedule**: Set which days, start time, and duration
- **GPIO Control**: Asserts signal on GPIO pin to trigger relay
- **Persistent Storage**: Schedule saved in JSON file
- **Auto-start**: Can run as system service
- **Safe Shutdown**: Ensures sprinklers turn off on exit

## Hardware Setup

1. **GPIO Pin**: Default is GPIO 17 (BCM numbering)
2. **Relay Module**: Connect to GPIO pin
   - GPIO pin → Relay IN
   - Relay COM/NO → Sprinkler valve/controller
3. **Power**: Ensure proper power supply for relay and sprinklers

## Installation

```bash
# Install required packages
sudo apt-get update
sudo apt-get install python3-rpi.gpio

# Make script executable
chmod +x sprinkler_controller.py
```

## Configuration

Edit `sprinkler_schedule.json`:

```json
{
  "days": [0, 2, 4],
  "start_time": "06:00",
  "duration_minutes": 20
}
```

- **days**: Weekday numbers (0=Monday, 1=Tuesday, ..., 6=Sunday)
- **start_time**: 24-hour format "HH:MM"
- **duration_minutes**: How long sprinklers run

## Usage

### Run manually:
```bash
python3 sprinkler_controller.py
```

### Run as system service:

Create `/etc/systemd/system/sprinkler.service`:

```ini
[Unit]
Description=Sprinkler Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/mrinal/projects/sprinkler_automation
ExecStart=/usr/bin/python3 /home/mrinal/projects/sprinkler_automation/sprinkler_controller.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sprinkler.service
sudo systemctl start sprinkler.service
sudo systemctl status sprinkler.service
```

## Customization

To change GPIO pin, edit the script:
```python
controller = SprinklerController(gpio_pin=27)  # Use GPIO 27 instead
```

## Testing

Test sprinklers manually (runs for 1 minute):
```python
from sprinkler_controller import SprinklerController
controller = SprinklerController(gpio_pin=17)
controller.run_sprinklers(duration_minutes=1)
controller.cleanup()
```

## Safety Notes

- Ensure proper electrical isolation between Raspberry Pi and high-voltage circuits
- Use appropriate relay module rated for your sprinkler system
- Test thoroughly before leaving unattended
- Consider adding rain sensor integration for water conservation

## Logs

View logs when running as service:
```bash
sudo journalctl -u sprinkler.service -f
```
