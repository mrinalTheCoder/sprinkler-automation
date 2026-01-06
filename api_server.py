#!/usr/bin/env python3
"""
FastAPI REST API for Sprinkler Controller
Provides endpoints to manage zones and schedules.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
from sprinkler_controller import SprinklerController, SprinklerSchedule, Zone
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sprinkler Controller API",
    description="Control and schedule your sprinkler system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Global controller instance
controller: Optional[SprinklerController] = None


class ScheduleModel(BaseModel):
    """Schedule data model."""
    days: List[int] = Field(..., description="List of weekdays (0=Monday, 6=Sunday)", min_items=1, max_items=7)
    start_time: str = Field(..., description="Start time in HH:MM format (24-hour)", pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    duration_minutes: int = Field(..., description="Duration in minutes", gt=0, le=180)
    enabled: bool = Field(default=True, description="Whether the schedule is enabled")


class ZoneModel(BaseModel):
    """Zone data model."""
    name: str = Field(..., description="Zone name", min_length=1, max_length=50)
    gpio_pin: int = Field(..., description="GPIO pin number (BCM)", ge=0, le=27)
    schedule: ScheduleModel


class ZoneUpdateModel(BaseModel):
    """Model for updating zone schedule."""
    schedule: ScheduleModel


class ManualRunModel(BaseModel):
    """Model for manually running a zone."""
    duration_minutes: int = Field(..., description="Duration in minutes", gt=0, le=180)


class ZoneStatusModel(BaseModel):
    """Zone status response model."""
    name: str
    gpio_pin: int
    active: bool
    schedule: dict


@app.on_event("startup")
async def startup_event():
    """Initialize the sprinkler controller on startup."""
    global controller
    try:
        controller = SprinklerController()
        logger.info("Sprinkler controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize controller: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global controller
    if controller:
        controller.cleanup()
        logger.info("Controller cleaned up")


@app.get("/", tags=["General"])
async def root():
    """API root endpoint."""
    return {
        "message": "Sprinkler Controller API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/zones", response_model=List[ZoneStatusModel], tags=["Zones"])
async def get_zones():
    """Get all zones and their current status."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    zones_data = []
    for zone in controller.zones:
        zones_data.append({
            "name": zone.name,
            "gpio_pin": zone.gpio_pin,
            "active": zone.active,
            "schedule": zone.schedule.to_dict()
        })
    
    return zones_data


@app.get("/zones/{zone_name}", response_model=ZoneStatusModel, tags=["Zones"])
async def get_zone(zone_name: str):
    """Get a specific zone's status."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    for zone in controller.zones:
        if zone.name == zone_name:
            return {
                "name": zone.name,
                "gpio_pin": zone.gpio_pin,
                "active": zone.active,
                "schedule": zone.schedule.to_dict()
            }
    
    raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")


@app.post("/zones", status_code=201, tags=["Zones"])
async def create_zone(zone: ZoneModel):
    """Create a new zone."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Check if zone already exists
    for existing_zone in controller.zones:
        if existing_zone.name == zone.name:
            raise HTTPException(status_code=409, detail=f"Zone '{zone.name}' already exists")
        if existing_zone.gpio_pin == zone.gpio_pin:
            raise HTTPException(status_code=409, detail=f"GPIO pin {zone.gpio_pin} already in use")
    
    try:
        controller.add_zone(
            name=zone.name,
            gpio_pin=zone.gpio_pin,
            days=zone.schedule.days,
            start_time=zone.schedule.start_time,
            duration_minutes=zone.schedule.duration_minutes,
            enabled=zone.schedule.enabled
        )
        return {"message": f"Zone '{zone.name}' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/zones/{zone_name}/schedule", tags=["Zones"])
async def update_zone_schedule(zone_name: str, zone_update: ZoneUpdateModel):
    """Update a zone's schedule."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Check if zone exists
    zone_exists = any(zone.name == zone_name for zone in controller.zones)
    if not zone_exists:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    
    try:
        controller.update_zone_schedule(
            zone_name=zone_name,
            days=zone_update.schedule.days,
            start_time=zone_update.schedule.start_time,
            duration_minutes=zone_update.schedule.duration_minutes,
            enabled=zone_update.schedule.enabled
        )
        return {"message": f"Schedule for zone '{zone_name}' updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/zones/{zone_name}", tags=["Zones"])
async def delete_zone(zone_name: str):
    """Delete a zone."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    try:
        success = controller.remove_zone(zone_name)
        if success:
            return {"message": f"Zone '{zone_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/zones/{zone_name}/run", tags=["Manual Control"])
async def run_zone_manually(zone_name: str, run_params: ManualRunModel, background_tasks: BackgroundTasks):
    """Manually run a zone for a specified duration."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Find the zone
    target_zone = None
    for zone in controller.zones:
        if zone.name == zone_name:
            target_zone = zone
            break
    
    if not target_zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    
    if target_zone.active:
        raise HTTPException(status_code=409, detail=f"Zone '{zone_name}' is already running")
    
    # Run zone in background
    background_tasks.add_task(controller.run_zone, target_zone, run_params.duration_minutes)
    
    return {
        "message": f"Zone '{zone_name}' started",
        "duration_minutes": run_params.duration_minutes
    }


@app.post("/zones/{zone_name}/stop", tags=["Manual Control"])
async def stop_zone_manually(zone_name: str):
    """Stop a running zone."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Find the zone
    target_zone = None
    for zone in controller.zones:
        if zone.name == zone_name:
            target_zone = zone
            break
    
    if not target_zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    
    if not target_zone.active:
        raise HTTPException(status_code=409, detail=f"Zone '{zone_name}' is not running")
    
    # Stop the zone
    controller.stop_events[zone_name].set()
    
    return {"message": f"Zone '{zone_name}' stopped"}


@app.get("/status", tags=["General"])
async def get_system_status():
    """Get overall system status."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    active_zones = [zone.name for zone in controller.zones if zone.active]
    enabled_zones = [zone.name for zone in controller.zones if zone.schedule.enabled]
    
    return {
        "controller_running": controller.is_running,
        "global_schedule_enabled": controller.global_schedule_enabled,
        "total_zones": len(controller.zones),
        "active_zones": active_zones,
        "zones": [zone.name for zone in controller.zones],
        "enabled_schedules": enabled_zones
    }


@app.post("/schedule/enable", tags=["Schedule Control"])
async def enable_global_schedule():
    """Enable all automatic scheduling globally."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    controller.enable_global_schedule()
    return {"message": "Global schedule enabled", "enabled": True}


@app.post("/schedule/disable", tags=["Schedule Control"])
async def disable_global_schedule():
    """Disable all automatic scheduling globally."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    controller.disable_global_schedule()
    return {"message": "Global schedule disabled", "enabled": False}


@app.post("/zones/{zone_name}/schedule/enable", tags=["Schedule Control"])
async def enable_zone_schedule(zone_name: str):
    """Enable automatic scheduling for a specific zone."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Check if zone exists
    zone_exists = any(zone.name == zone_name for zone in controller.zones)
    if not zone_exists:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    
    controller.enable_zone_schedule(zone_name)
    return {"message": f"Schedule enabled for zone '{zone_name}'", "enabled": True}


@app.post("/zones/{zone_name}/schedule/disable", tags=["Schedule Control"])
async def disable_zone_schedule(zone_name: str):
    """Disable automatic scheduling for a specific zone."""
    if not controller:
        raise HTTPException(status_code=500, detail="Controller not initialized")
    
    # Check if zone exists
    zone_exists = any(zone.name == zone_name for zone in controller.zones)
    if not zone_exists:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found")
    
    controller.disable_zone_schedule(zone_name)
    return {"message": f"Schedule disabled for zone '{zone_name}'", "enabled": False}


def main():
    """Run the API server."""
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
