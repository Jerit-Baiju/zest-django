# ZEST Django Backend

This is the Django backend for the ZEST video calling application. It provides UUID-based device tracking without traditional user authentication.

## Features

- **Device Tracking**: Each device/user is tracked by a unique UUID
- **No Login Required**: Devices are automatically registered and tracked
- **CORS Enabled**: Supports cross-origin requests from the Next.js frontend
- **Admin Interface**: Django admin for monitoring devices

## API Endpoints

### Authentication
- `POST /api/auth/get-device-uuid/` - Get a new device UUID
- `POST /api/auth/update-activity/` - Update device last seen timestamp
- `GET /api/status/` - API status check

## Setup

1. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

4. **Create Superuser (Optional)**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

## Admin Access

- URL: http://localhost:8000/admin/
- Default credentials: admin / admin123

## Frontend Integration

The Next.js frontend automatically fetches device UUIDs from this backend. Make sure both servers are running:

- Django: http://localhost:8000
- Next.js: http://localhost:3000

## Architecture

```
Device Model:
- uuid (Primary Key, Auto-generated)
- created_at (Auto timestamp)
- last_seen (Auto-updated timestamp)
- user_agent (Client info)
- ip_address (Client IP)
```

## CORS Configuration

CORS is configured to allow requests from:
- http://localhost:3000
- http://127.0.0.1:3000

## Environment Variables

Copy `.env.example` to `.env` and modify as needed for production deployment.
