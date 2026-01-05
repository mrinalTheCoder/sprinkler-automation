#!/usr/bin/env python3
"""
Raspberry Pi Sprinkler Controller
Automates sprinkler control based on a configurable schedule.
"""

import RPi.GPIO as GPIO
import time
import json
from datetime import datetime, time as dt_time
from typing import List, Dict
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SprinklerSchedule:
    """Represents a sprinkler schedule configuration."""
    
    def __init__(self, days: List[int], start_time: str, duration_minutes: int, enabled: bool = True):
        """
        Initialize a sprinkler schedule.
        
        Args:
            days: List of weekday numbers (0=Monday, 6=Sunday)
            start_time: Time to start in "HH:MM" format (24-hour)
            duration_minutes: How long to run sprinklers in minutes
            enabled: Whether the schedule is enabled
        """
        self.days = days
        self.start_time = datetime.strptime(start_time, "%H:%M").time()
        self.duration_minutes = duration_minutes
        self.enabled = enabled
    
    def should_run_today(self) -> bool:
        """Check if sprinklers should run today."""
        return datetime.now().weekday() in self.days
    
    def is_start_time(self) -> bool:
        """Check if current time matches start time (within 1 minute)."""
        now = datetime.now().time()
        now_minutes = now.hour * 60 + now.minute
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        return now_minutes == start_minutes
    
    def to_dict(self) -> Dict:
        """Convert schedule to dictionary."""
        return {
            'days': self.days,
            'start_time': self.start_time.strftime("%H:%M"),
            'duration_minutes': self.duration_minutes,
            'enabled': self.enabled
        }


class Zone:
    """Represents a sprinkler zone with its own GPIO pin and schedule."""
    
    def __init__(self, name: str, gpio_pin: int, schedule: SprinklerSchedule):
        """
        Initialize a zone.
        
        Args:
            name: Descriptive name for the zone
            gpio_pin: GPIO pin number (BCM numbering) to control relay
            schedule: SprinklerSchedule object for this zone
        """
        self.name = name
        self.gpio_pin = gpio_pin
        self.schedule = schedule
        self.active = False
        
        # Setup GPIO for this zone
        GPIO.setup(self.gpio_pin, GPIO.OUT)
        GPIO.output(self.gpio_pin, GPIO.LOW)
    
    def to_dict(self) -> Dict:
        """Convert zone to dictionary."""
        return {
            'name': self.name,
            'gpio_pin': self.gpio_pin,
            'schedule': self.schedule.to_dict()
        }


class SprinklerController:
    """Controls sprinkler system via Raspberry Pi GPIO."""
    
    def __init__(self, schedule_file: str = "sprinkler_schedule.json"):
        """
        Initialize the sprinkler controller.
        
        Args:
            schedule_file: Path to JSON file storing schedule configuration
        """
        self.schedule_file = schedule_file
        self.zones = []
        self.is_running = False
        self.stop_events = {}
        self.global_schedule_enabled = True
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Load zones and schedules
        self.load_schedule()
        
        logger.info(f"Sprinkler controller initialized with {len(self.zones)} zones")
    
    def load_schedule(self):
        """Load zones and schedules from JSON file."""
        try:
            with open(self.schedule_file, 'r') as f:
                data = json.load(f)
                self.global_schedule_enabled = data.get('global_schedule_enabled', True)
                self.zones = []
                for zone_data in data['zones']:
                    schedule = SprinklerSchedule(
                        days=zone_data['schedule']['days'],
                        start_time=zone_data['schedule']['start_time'],
                        duration_minutes=zone_data['schedule']['duration_minutes'],
                        enabled=zone_data['schedule'].get('enabled', True)
                    )
                    zone = Zone(
                        name=zone_data['name'],
                        gpio_pin=zone_data['gpio_pin'],
                        schedule=schedule
                    )
                    self.zones.append(zone)
                    self.stop_events[zone.name] = threading.Event()
                logger.info(f"Loaded {len(self.zones)} zones")
        except FileNotFoundError:
            logger.warning(f"Schedule file not found. Creating default schedule.")
            self.create_default_schedule()
        except Exception as e:
            logger.error(f"Error loading schedule: {e}")
            self.create_default_schedule()
    
    def create_default_schedule(self):
        """Create default zones with schedules."""
        schedule1 = SprinklerSchedule(
            days=[0, 2, 4],  # Monday, Wednesday, Friday
            start_time="06:00",
            duration_minutes=20
        )
        schedule2 = SprinklerSchedule(
            days=[1, 3, 5],  # Tuesday, Thursday, Saturday
            start_time="06:30",
            duration_minutes=15
        )
        
        self.zones = [
            Zone(name="Front Yard", gpio_pin=17, schedule=schedule1),
            Zone(name="Back Yard", gpio_pin=27, schedule=schedule2)
        ]
        
        for zone in self.zones:
            self.stop_events[zone.name] = threading.Event()
        
        self.save_schedule()
        logger.info("Default zones created")
    
    def save_schedule(self):
        """Save current zones and schedules to JSON file."""
        try:
            with open(self.schedule_file, 'w') as f:
                data = {
                    'global_schedule_enabled': self.global_schedule_enabled,
                    'zones': [zone.to_dict() for zone in self.zones]
                }
                json.dump(data, f, indent=2)
            logger.info("Schedule saved")
        except Exception as e:
            logger.error(f"Error saving schedule: {e}")
    
    def update_zone_schedule(self, zone_name: str, days: List[int], start_time: str, duration_minutes: int, enabled: bool = True):
        """
        Update the schedule for a specific zone.
        
        Args:
            zone_name: Name of the zone to update
            days: List of weekday numbers (0=Monday, 6=Sunday)
            start_time: Time to start in "HH:MM" format (24-hour)
            duration_minutes: How long to run sprinklers in minutes
            enabled: Whether the schedule is enabled
        """
        for zone in self.zones:
            if zone.name == zone_name:
                zone.schedule = SprinklerSchedule(days, start_time, duration_minutes, enabled)
                self.save_schedule()
                logger.info(f"Schedule updated for zone '{zone_name}': {zone.schedule.to_dict()}")
                return
        logger.warning(f"Zone '{zone_name}' not found")
    
    def add_zone(self, name: str, gpio_pin: int, days: List[int], start_time: str, duration_minutes: int, enabled: bool = True):
        """
        Add a new zone.
        
        Args:
            name: Descriptive name for the zone
            gpio_pin: GPIO pin number (BCM numbering) to control relay
            days: List of weekday numbers (0=Monday, 6=Sunday)
            start_time: Time to start in "HH:MM" format (24-hour)
            duration_minutes: How long to run sprinklers in minutes
            enabled: Whether the schedule is enabled
        """
        schedule = SprinklerSchedule(days, start_time, duration_minutes, enabled)
        zone = Zone(name, gpio_pin, schedule)
        self.zones.append(zone)
        self.stop_events[zone.name] = threading.Event()
        self.save_schedule()
        logger.info(f"Zone '{name}' added on GPIO pin {gpio_pin}")
    
    def enable_zone_schedule(self, zone_name: str):
        """
        Enable the schedule for a specific zone.
        
        Args:
            zone_name: Name of the zone
        """
        for zone in self.zones:
            if zone.name == zone_name:
                zone.schedule.enabled = True
                self.save_schedule()
                logger.info(f"Schedule enabled for zone '{zone_name}'")
                return
        logger.warning(f"Zone '{zone_name}' not found")
    
    def disable_zone_schedule(self, zone_name: str):
        """
        Disable the schedule for a specific zone.
        
        Args:
            zone_name: Name of the zone
        """
        for zone in self.zones:
            if zone.name == zone_name:
                zone.schedule.enabled = False
                self.save_schedule()
                logger.info(f"Schedule disabled for zone '{zone_name}'")
                return
        logger.warning(f"Zone '{zone_name}' not found")
    
    def enable_global_schedule(self):
        """Enable all automatic scheduling."""
        self.global_schedule_enabled = True
        self.save_schedule()
        logger.info("Global schedule enabled")
    
    def disable_global_schedule(self):
        """Disable all automatic scheduling."""
        self.global_schedule_enabled = False
        self.save_schedule()
        logger.info("Global schedule disabled")
    
    def remove_zone(self, zone_name: str) -> bool:
        """
        Remove a zone.
        
        Args:
            zone_name: Name of the zone to remove
            
        Returns:
            True if zone was removed, False if not found
        """
        for i, zone in enumerate(self.zones):
            if zone.name == zone_name:
                # Stop zone if active
                if zone.active:
                    self.stop_events[zone_name].set()
                    self.stop_zone(zone)
                
                # Remove from lists
                del self.zones[i]
                del self.stop_events[zone_name]
                
                self.save_schedule()
                logger.info(f"Zone '{zone_name}' removed")
                return True
        
        logger.warning(f"Zone '{zone_name}' not found")
        return False
    
    def start_zone(self, zone: Zone):
        """Turn on sprinklers for a specific zone."""
        GPIO.output(zone.gpio_pin, GPIO.HIGH)
        zone.active = True
        logger.info(f"Zone '{zone.name}' turned ON")
    
    def stop_zone(self, zone: Zone):
        """Turn off sprinklers for a specific zone."""
        GPIO.output(zone.gpio_pin, GPIO.LOW)
        zone.active = False
        logger.info(f"Zone '{zone.name}' turned OFF")
    
    def run_zone(self, zone: Zone, duration_minutes: int):
        """
        Run sprinklers for a specific zone.
        
        Args:
            zone: Zone object to run
            duration_minutes: How long to run sprinklers in minutes
        """
        logger.info(f"Running zone '{zone.name}' for {duration_minutes} minutes")
        self.start_zone(zone)
        
        # Wait for duration or stop event
        self.stop_events[zone.name].wait(timeout=duration_minutes * 60)
        
        self.stop_zone(zone)
        self.stop_events[zone.name].clear()
    
    def check_and_run(self):
        """Check if it's time to run sprinklers for any zone and execute if needed."""
        if not self.global_schedule_enabled:
            return
        
        for zone in self.zones:
            if not zone.schedule.enabled:
                continue
                
            if zone.schedule.should_run_today() and zone.schedule.is_start_time():
                if not zone.active:
                    logger.info(f"Schedule triggered for zone '{zone.name}' - starting sprinklers")
                    # Run in separate thread to avoid blocking
                    thread = threading.Thread(
                        target=self.run_zone,
                        args=(zone, zone.schedule.duration_minutes)
                    )
                    thread.daemon = True
                    thread.start()
    
    def run_controller(self):
        """Main control loop - checks schedule every minute."""
        self.is_running = True
        logger.info("Sprinkler controller started")
        
        try:
            while self.is_running:
                self.check_and_run()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Controller stopped by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO and stop all zones."""
        self.is_running = False
        for zone in self.zones:
            self.stop_events[zone.name].set()
            if zone.active:
                self.stop_zone(zone)
        GPIO.cleanup()
        logger.info("Controller cleaned up")


def main():
    """Main entry point."""
    # Initialize controller
    controller = SprinklerController()
    
    # Example: Update schedule for a specific zone (optional)
    # controller.update_zone_schedule(
    #     zone_name="Front Yard",
    #     days=[0, 2, 4],  # Monday, Wednesday, Friday
    #     start_time="06:00",
    #     duration_minutes=20
    # )
    
    # Example: Add a new zone (optional)
    # controller.add_zone(
    #     name="Side Garden",
    #     gpio_pin=22,
    #     days=[0, 3, 6],  # Monday, Thursday, Sunday
    #     start_time="07:00",
    #     duration_minutes=10
    # )
    
    # Run the controller
    controller.run_controller()


if __name__ == "__main__":
    main()
