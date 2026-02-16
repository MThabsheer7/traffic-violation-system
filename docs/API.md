# API Reference

> Base URL: `http://localhost:8000`

All endpoints are prefixed with `/api`. The API is built with FastAPI — interactive docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running the server.

---

## Health Check

### `GET /health`

Returns server health status.

**Response:**

```json
{ "status": "ok" }
```

---

## Alerts

### `POST /api/alerts`

Create a new violation alert. Called by the vision engine when a violation is detected.

**Request Body:**

```json
{
  "violation_type": "ILLEGAL_PARKING",
  "confidence": 0.92,
  "object_id": 7,
  "snapshot_path": "snapshots/ILLEGAL_PARKING_7_20260215_143022.jpg",
  "zone_id": "zone_a",
  "metadata": { "class_name": "car" }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `violation_type` | `"ILLEGAL_PARKING"` \| `"WRONG_WAY"` | ✅ | Violation type |
| `confidence` | `float` (0.0–1.0) | ✅ | Detection confidence score |
| `object_id` | `int` (≥ 0) | ✅ | Tracked object ID from vision engine |
| `snapshot_path` | `string` \| `null` | ❌ | Path to snapshot image |
| `zone_id` | `string` \| `null` | ❌ | Zone where violation occurred |
| `metadata` | `object` \| `null` | ❌ | Additional metadata (e.g., vehicle class) |

**Response (200):**

```json
{
  "id": 1,
  "violation_type": "ILLEGAL_PARKING",
  "confidence": 0.92,
  "object_id": 7,
  "snapshot_path": "snapshots/ILLEGAL_PARKING_7_20260215_143022.jpg",
  "zone_id": "zone_a",
  "metadata": { "class_name": "car" },
  "timestamp": "2026-02-15T14:30:22.123456"
}
```

---

### `GET /api/alerts`

List violation alerts with pagination and optional filters.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | `int` (≥ 1) | `1` | Page number |
| `page_size` | `int` (1–100) | `20` | Items per page |
| `violation_type` | `string` | `null` | Filter by type (`ILLEGAL_PARKING`, `WRONG_WAY`) |
| `date_from` | `datetime` | `null` | Filter from date (ISO 8601) |
| `date_to` | `datetime` | `null` | Filter to date (ISO 8601) |

**Response (200):**

```json
{
  "alerts": [
    {
      "id": 1,
      "violation_type": "ILLEGAL_PARKING",
      "confidence": 0.92,
      "object_id": 7,
      "snapshot_path": "snapshots/ILLEGAL_PARKING_7_20260215_143022.jpg",
      "zone_id": "zone_a",
      "metadata": { "class_name": "car" },
      "timestamp": "2026-02-15T14:30:22.123456"
    }
  ],
  "total": 47,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

### `GET /api/alerts/{id}`

Get a single alert by ID.

**Response (200):**

```json
{
  "id": 1,
  "violation_type": "ILLEGAL_PARKING",
  "confidence": 0.92,
  "object_id": 7,
  "snapshot_path": "snapshots/ILLEGAL_PARKING_7_20260215_143022.jpg",
  "zone_id": "zone_a",
  "metadata": { "class_name": "car" },
  "timestamp": "2026-02-15T14:30:22.123456"
}
```

**Response (404):**

```json
{ "detail": "Alert not found" }
```

---

## Statistics

### `GET /api/stats`

Get aggregate statistics for the dashboard KPI cards.

**Response (200):**

```json
{
  "total_violations": 100,
  "violations_today": 34,
  "by_type": {
    "ILLEGAL_PARKING": 47,
    "WRONG_WAY": 53
  },
  "hourly_distribution": [
    {
      "hour": "00:00",
      "count": 3,
      "illegal_parking": 1,
      "wrong_way": 2
    },
    {
      "hour": "01:00",
      "count": 5,
      "illegal_parking": 3,
      "wrong_way": 2
    }
  ],
  "recent_trend": -12.5
}
```

| Field | Type | Description |
|---|---|---|
| `total_violations` | `int` | All-time total violations |
| `violations_today` | `int` | Violations since midnight UTC |
| `by_type` | `object` | Breakdown by violation type |
| `hourly_distribution` | `array` | Violations per hour (last 24h) |
| `recent_trend` | `float` | % change vs previous period |

---

## WebSocket

### `WS /api/ws/alerts`

Live alert feed. Connects the React dashboard to receive real-time violation alerts.

**Connection:**

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/alerts");

ws.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  console.log("New violation:", alert);
};
```

**Message Format (server → client):**

```json
{
  "id": 42,
  "violation_type": "WRONG_WAY",
  "confidence": 0.87,
  "object_id": 12,
  "snapshot_path": null,
  "zone_id": null,
  "metadata": { "class_name": "truck" },
  "timestamp": "2026-02-15T14:30:22.123456"
}
```

Each message is a JSON-serialized `AlertResponse`, pushed immediately when a new alert is created via `POST /api/alerts`.
