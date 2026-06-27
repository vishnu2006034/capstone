# Meeting2Execution AI

An enterprise-grade system that converts meeting discussions into executable tasks, validates them against SOP documents, monitors progress, and provides AI-powered manager insights.

## Project Structure

This project is split into:
- `/backend`: FastAPI service with Google ADK orchestrating specialized agents.
- `/frontend`: React client compiled with Vite.
- `/docker`: Dockerfiles for local containerization.

## Setup Instructions

### Backend
1. Navigate to `/backend`.
2. Create a virtual environment: `python -m venv venv`.
3. Activate it:
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env` and fill in the values.
6. Run the FastAPI development server: `uvicorn app.main:app --reload`.

### Frontend
1. Navigate to `/frontend`.
2. Install dependencies: `npm install`.
3. Run the development server: `npm run dev`.

### Docker Compose
To run the entire stack locally using Docker:
```bash
docker-compose up --build
```
