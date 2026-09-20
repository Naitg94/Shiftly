# Shiftly” "Find what matters."

Shiftly is an AI-powered communication intelligence layer. Its purpose is to process long, unstructured project communication and extract only the critical information so users do not have to read the entire conversation.

## Project Structure

```
Shiftly/
â”œâ”€â”€ frontend/        # Next.js (App Router, TypeScript, Tailwind CSS)
â”œâ”€â”€ backend/         # FastAPI (Python, Uvicorn, Pydantic)
â”œâ”€â”€ README.md
â”œâ”€â”€ .gitignore
â””â”€â”€ .env.example
```

## Getting Started

Frontend and backend run completely independently.

### Backend Setup

1. Open a terminal in `./backend`:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Backend health check endpoint: `http://localhost:8000/api/health`

### Frontend Setup

1. Open a terminal in `./frontend`:
   ```bash
   cd frontend
   ```
2. Copy the environment file:
   ```bash
   cp .env.example .env.local
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run the Next.js development server:
   ```bash
   npm run dev
   ```
   Frontend app: `http://localhost:3000`

---

## Core Features (Locked Roadmap)

1. Accept pasted conversations
2. Accept uploaded communication files
3. Process very long text through backend chunking
4. Extract:
   - Key points
   - Summary
   - Actions
   - Responsible person
   - Dates/deadlines
   - Decisions/approvals
5. Present extracted information in:
   - Key Points view
   - Summary view
   - Table view
   - Structured view
6. Source/info drill-down without displaying the entire raw conversation on the main results page
7. Phase 2: Project memory/history and search
8. Phase 3: Reliability, accuracy, UX, and polish
