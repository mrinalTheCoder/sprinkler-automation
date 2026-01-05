# Sprinkler Controller API Examples

## Quick Start

Start the API server:
```bash
python3 api_server.py
```

Access interactive docs at: `http://localhost:8000/docs`

---

## Manual Control APIs

### Turn ON Sprinklers (Run Zone)

**Endpoint:** `POST /zones/{zone_name}/run`

**Description:** Manually turn on sprinklers for a specific zone with a custom duration.

**Request Body:**
```json
{
  "duration_minutes": 15
}
```

**Examples:**

```bash
# Turn on Front Yard for 15 minutes
curl -X POST http://localhost:8000/zones/Front%20Yard/run \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 15}'

# Turn on Back Yard for 10 minutes
curl -X POST http://localhost:8000/zones/Back%20Yard/run \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 10}'
```

**Response:**
```json
{
  "message": "Zone 'Front Yard' started",
  "duration_minutes": 15
}
```

---

### Turn OFF Sprinklers (Stop Zone)

**Endpoint:** `POST /zones/{zone_name}/stop`

**Description:** Immediately stop a running zone.

**Examples:**

```bash
# Stop Front Yard
curl -X POST http://localhost:8000/zones/Front%20Yard/stop

# Stop Back Yard
curl -X POST http://localhost:8000/zones/Back%20Yard/stop
```

**Response:**
```json
{
  "message": "Zone 'Front Yard' stopped"
}
```

---

## Schedule Control APIs

### Enable Global Schedule

**Endpoint:** `POST /schedule/enable`

**Description:** Enable all automatic scheduling globally. All zones with enabled schedules will run.

**Example:**

```bash
curl -X POST http://localhost:8000/schedule/enable
```

**Response:**
```json
{
  "message": "Global schedule enabled",
  "enabled": true
}
```

---

### Disable Global Schedule

**Endpoint:** `POST /schedule/disable`

**Description:** Disable all automatic scheduling globally. No zones will run automatically (manual control still works).

**Example:**

```bash
curl -X POST http://localhost:8000/schedule/disable
```

**Response:**
```json
{
  "message": "Global schedule disabled",
  "enabled": false
}
```

---

### Enable Zone Schedule

**Endpoint:** `POST /zones/{zone_name}/schedule/enable`

**Description:** Enable automatic scheduling for a specific zone.

**Example:**

```bash
curl -X POST http://localhost:8000/zones/Front%20Yard/schedule/enable
```

**Response:**
```json
{
  "message": "Schedule enabled for zone 'Front Yard'",
  "enabled": true
}
```

---

### Disable Zone Schedule

**Endpoint:** `POST /zones/{zone_name}/schedule/disable`

**Description:** Disable automatic scheduling for a specific zone (manual control still works).

**Example:**

```bash
curl -X POST http://localhost:8000/zones/Front%20Yard/schedule/disable
```

**Response:**
```json
{
  "message": "Schedule disabled for zone 'Front Yard'",
  "enabled": false
}
```

---

## Zone Management APIs

### Get All Zones

```bash
curl http://localhost:8000/zones
```

**Response:**
```json
[
  {
    "name": "Front Yard",
    "gpio_pin": 17,
    "active": false,
    "schedule": {
      "days": [0, 2, 4],
      "start_time": "06:00",
      "duration_minutes": 20,
      "enabled": true
    }
  },
  {
    "name": "Back Yard",
    "gpio_pin": 27,
    "active": true,
    "schedule": {
      "days": [1, 3, 5],
      "start_time": "06:30",
      "duration_minutes": 15,
      "enabled": false
    }
  }
]
```

---

### Get Specific Zone

```bash
curl http://localhost:8000/zones/Front%20Yard
```

---

### Create New Zone

```bash
curl -X POST http://localhost:8000/zones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Side Garden",
    "gpio_pin": 22,
    "schedule": {
      "days": [0, 3, 6],
      "start_time": "07:00",
      "duration_minutes": 10
    }
  }'
```

---

### Update Zone Schedule

```bash
curl -X PUT http://localhost:8000/zones/Front%20Yard/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": {
      "days": [0, 2, 4, 6],
      "start_time": "05:30",
      "duration_minutes": 25
    }
  }'
```

---

### Delete Zone

```bash
curl -X DELETE http://localhost:8000/zones/Side%20Garden
```

---

## System Status

### Get Overall Status

```bash
curl http://localhost:8000/status
```

**Response:**
```json
{
  "controller_running": true,
  "global_schedule_enabled": true,
  "total_zones": 2,
  "active_zones": ["Back Yard"],
  "zones": ["Front Yard", "Back Yard"],
  "enabled_schedules": ["Front Yard", "Back Yard"]
}
```

---

## Error Responses

### Zone Not Found (404)
```json
{
  "detail": "Zone 'Invalid Zone' not found"
}
```

### Zone Already Running (409)
```json
{
  "detail": "Zone 'Front Yard' is already running"
}
```

### Zone Not Running (409)
```json
{
  "detail": "Zone 'Front Yard' is not running"
}
```

---

## Python Examples

### Using requests library

```python
import requests

BASE_URL = "http://localhost:8000"

# Turn on sprinklers
response = requests.post(
    f"{BASE_URL}/zones/Front Yard/run",
    json={"duration_minutes": 20}
)
print(response.json())

# Stop sprinklers
response = requests.post(f"{BASE_URL}/zones/Front Yard/stop")
print(response.json())

# Disable global schedule (vacation mode)
response = requests.post(f"{BASE_URL}/schedule/disable")
print(response.json())

# Enable global schedule
response = requests.post(f"{BASE_URL}/schedule/enable")
print(response.json())

# Disable schedule for specific zone
response = requests.post(f"{BASE_URL}/zones/Front Yard/schedule/disable")
print(response.json())

# Enable schedule for specific zone
response = requests.post(f"{BASE_URL}/zones/Front Yard/schedule/enable")
print(response.json())

# Get all zones
response = requests.get(f"{BASE_URL}/zones")
zones = response.json()
for zone in zones:
    status = 'ON' if zone['active'] else 'OFF'
    schedule_status = 'ENABLED' if zone['schedule']['enabled'] else 'DISABLED'
    print(f"{zone['name']}: {status} (Schedule: {schedule_status})")

# Update schedule
response = requests.put(
    f"{BASE_URL}/zones/Front Yard/schedule",
    json={
        "schedule": {
            "days": [0, 2, 4],
            "start_time": "06:00",
            "duration_minutes": 30,
            "enabled": true
        }
    }
)
print(response.json())
```

---

## JavaScript/Node.js Examples

```javascript
const BASE_URL = "http://localhost:8000";

// Turn on sprinklers
async function turnOnSprinklers(zoneName, minutes) {
  const response = await fetch(`${BASE_URL}/zones/${zoneName}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ duration_minutes: minutes })
  });
  return await response.json();
}

// Stop sprinklers
async function stopSprinklers(zoneName) {
  const response = await fetch(`${BASE_URL}/zones/${zoneName}/stop`, {
    method: 'POST'
  });
  return await response.json();
}

// Get status
async function getStatus() {
  const response = await fetch(`${BASE_URL}/zones`);
  return await response.json();
}

// Usage
turnOnSprinklers("Front Yard", 15)
  .then(result => console.log(result));

stopSprinklers("Front Yard")
  .then(result => console.log(result));

getStatus()
  .then(zones => zones.forEach(z => 
    console.log(`${z.name}: ${z.active ? 'ON' : 'OFF'}`)
  ));
```

---

## Testing with HTTPie

If you have HTTPie installed:

```bash
# Turn on sprinklers
http POST localhost:8000/zones/Front%20Yard/run duration_minutes:=15

# Stop sprinklers
http POST localhost:8000/zones/Front%20Yard/stop

# Get zones
http GET localhost:8000/zones

# Update schedule
http PUT localhost:8000/zones/Front%20Yard/schedule schedule:='{"days":[0,2,4],"start_time":"06:00","duration_minutes":30}'
```

---

## Notes

- Zone names with spaces must be URL-encoded (e.g., "Front Yard" → "Front%20Yard")
- Duration is limited to 180 minutes (3 hours) maximum
- Only one instance of a zone can run at a time
- Stopping a zone will interrupt its current run immediately
- The API runs on port 8000 by default
- **Global schedule disable**: Useful for vacation mode - disables all automatic scheduling
- **Zone schedule disable**: Disables scheduling for a specific zone while keeping others active
- Manual control works independently of schedule enable/disable settings
- Schedule configuration is preserved when disabled
