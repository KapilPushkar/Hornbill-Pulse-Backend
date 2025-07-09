# Land Mapping Backend

This is the backend service for the Pulse App. It provides RESTful APIs for managing land boundaries, storing user land data, and generating vegetation analysis reports using satellite imagery.

## Overview

- **Framework:** FastAPI
- **Database:** MongoDB
- **Satellite Data:** Copernicus Data Space Ecosystem (CDSE)
- **Worker:** Threaded resource-limited worker for background tasks

## API Endpoints

The backend exposes the following main endpoints (see [FrontendREADME.md](FrontendREADME.md) for usage):

| Endpoint Description                | HTTP Method | Example URL                                      | Notes                                 |
|-------------------------------------|-------------|--------------------------------------------------|---------------------------------------|
| Save Land Boundary                  | POST        | `/api/v1/lands`                                  | Body: `{ land_name, coordinates, user_id, user_email }` |
| Get Lands by User ID                | GET         | `/api/v1/lands/user/{userId}`                    | Replace `{userId}` with actual user id |
| Delete Land                         | DELETE      | `/api/v1/lands/{landId}`                         | Replace `{landId}` with actual land id |
| Generate Vegetation Report for Land | POST        | `/api/v1/reports/vegetation/{landId}`            | Replace `{landId}` with actual land id |

## Project Structure

```
backend/
├── app/
│   ├── api/                # FastAPI routers and endpoints
│   ├── core/               # Configuration
│   ├── db/                 # MongoDB connection
│   ├── models/             # Pydantic schemas
│   ├── repositories/       # Database access logic
│   ├── services/           # Business logic (land, vegetation, copernicus)
│   ├── templates/          # Jinja2 HTML templates
│   ├── utils/              # Utility functions
│   ├── worker.py           # Worker thread for background tasks
│   └── main.py             # FastAPI app entrypoint
├── main.py                 # Uvicorn entrypoint
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
└── ...
```

## Flow Description

### 1. Land Creation

- **POST `/api/v1/lands`**
    - Stores land boundary and metadata in MongoDB.
    - Triggers a background worker task to fetch and store raw satellite data for the land.

### 2. Land Listing

- **GET `/api/v1/lands/user/{userId}`**
    - Returns all lands for a user.

### 3. Land Deletion

- **DELETE `/api/v1/lands/{landId}`**
    - Deletes a land and its associated data.

### 4. Vegetation Analysis Report

- **POST `/api/v1/reports/vegetation/{landId}`**
    - Triggers a background task to generate a vegetation analysis report for the land using Copernicus satellite data.
    - The report is generated asynchronously and stored in the database.

### 5. Worker Thread

- Uses Python's built-in `queue` and a dedicated thread (`app/worker.py`) to run heavy background tasks (e.g., satellite data processing, report generation) one at a time, with resource limits.

## Useful Services

- [`app/services/land.py`](app/services/land.py): Land creation, update, retrieval, deletion.
- [`app/services/land_vegetation.py`](app/services/land_vegetation.py): Satellite data processing, vegetation stats, report generation.
- [`app/services/copernicus_api.py`](app/services/copernicus_api.py): Handles Copernicus API integration and satellite image download.
- [`app/worker.py`](app/worker.py): Background worker for heavy/long-running tasks.

## Not Useful / Deprecated Code

- `app/services/notification.py`: FCM notification logic is not integrated with the main flow.
- `app/models/land_request.py` and `app/models/coordinates.py`: Redundant with `app/models/schemas/land.py`.
- Any code or endpoints not referenced in the above API table can be considered deprecated or not in use.

## Setup & Running

### 1. Clone the Repository

```sh
git clone <your-repository-url>
cd backend
```

### 2. Install Dependencies

```sh
pip install -r requirements.txt
```

### 3. Configure Environment

- Copy `.env.example` to `.env` and fill in your MongoDB and Copernicus credentials.

### 4. Start MongoDB

Make sure MongoDB is running locally or update the URI in `.env` to point to your MongoDB instance.

### 5. Run the Backend

```sh
python main.py
```

- The API will be available at `http://localhost:80/api/v1`

### 6. (Optional) Development Mode

For hot-reloading, you can use:

```sh
uvicorn app.main:app --reload --host 0.0.0.0 --port 80
```

## Notes

- Satellite images and reports are stored in the `satellite_images/` directory.
- The backend uses a resource-limited worker to avoid overloading the server during heavy processing.
- The API is designed to be used by the Flutter frontend app.

---

**Happy Mapping!**