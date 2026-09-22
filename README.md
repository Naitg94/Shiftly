# Shiftly — Find what matters.

Shiftly is an intelligent communication layer that transforms unstructured project communication into structured project intelligence. Instead of reading through sprawling chat threads, email chains, and meeting transcripts, teams get clear, actionable insights in seconds.

---

## Core Workflow

```
Communication ──> Understand ──> Extract ──> Structure ──> Remember
```

1. **Communication**: Ingest long conversations via direct text paste or file uploads.
2. **Understand**: Normalize and intelligently chunk long transcripts without losing conversational context.
3. **Extract**: Leverage Google Gemini to isolate critical decisions, commitments, dates, and takeaways while filtering conversational noise.
4. **Structure**: Present insights cleanly across specialized views (Structured, Key Points, Summary, Table).
5. **Remember**: Save analyses to persistent Project Memory for long-term project intelligence and cross-analysis search.

---

## Core Intelligence

Shiftly extracts and categorizes:

- **Key Points**: Essential factual takeaways and project developments.
- **Action Items**: Explicit tasks and commitments with assignees and due dates.
- **Responsibility**: Commitments organized by responsible person or team member.
- **Important Dates**: Project milestones, deadlines, and delivery targets.
- **Decisions**: Final agreements, choices made, and sign-offs.
- **Pending Decisions**: Items awaiting resolution, open questions, and blocker status.
- **Approvals**: Formal authorizations and sign-offs with approver attribution.
- **Analysis Summary**: Executive context and high-level project briefing.

Every extracted item includes clickable **Source** citations pointing directly to the original excerpt and message reference.

---

## Project Memory

A persistent intelligence workspace powered by Supabase PostgreSQL:

- Organize analyses by project with inline renaming for projects and analysis titles.
- Scoped search across all key points, actions, decisions, and deadlines within a project.
- Real-time aggregated intelligence across all saved project documents.
- Fast, secure data ownership protected by PostgreSQL Row Level Security (RLS).

---

## Supported Inputs

- **Pasted Text**: Direct text input of conversations, transcripts, meeting notes, and logs.
- **Plain Text / Chat Logs**: `.txt`, `.log`, `.chat`, `.csv`
- **Documents**: `.pdf` (selectable text), `.docx` (Microsoft Word documents)
- **Email Archives**: `.eml`, `.mbox`
- **WhatsApp Chat Exports**: `.zip` archives containing WhatsApp chat transcripts (`_chat.txt`)

---

## Technology Stack

### Frontend
- **Framework**: Next.js 16 (App Router) & React 19
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4
- **Icons**: Lucide React
- **Client**: `@supabase/supabase-js`

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Server**: Uvicorn
- **Validation**: Pydantic v2
- **Database Driver**: `pg8000` & Supabase Python client
- **Document Parsing**: PyMuPDF (`fitz`), `python-docx`

### AI & Intelligence
- **Provider**: Google Gemini via `google-genai` SDK
- **Configured Model**: `gemini-3.5-flash-lite`

### Database & Authentication
- **Database**: PostgreSQL on Supabase
- **Authentication**: Supabase Auth (JWT & Row Level Security)

---

## Project Structure

```
Shiftly/
├── backend/                  # FastAPI application & services
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (/analyze, /projects, /health)
│   │   ├── core/            # Config, auth, rate limiting, plans
│   │   ├── db/              # Database models, Supabase/SQLite repository
│   │   ├── models/          # Pydantic request/response schemas
│   │   └── services/        # Gemini AI, chunking, file processing
│   ├── tests/               # Pytest test suite
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Backend environment template
├── frontend/                 # Next.js web application
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   ├── components/      # UI components (Dashboard, Views, Memory)
│   │   ├── context/         # Auth context & Supabase session
│   │   ├── lib/             # API client & Supabase client
│   │   └── types/           # TypeScript type definitions
│   ├── package.json         # Frontend dependencies & scripts
│   └── .env.example         # Frontend environment template
├── .gitignore               # Repository-wide ignore rules
└── README.md                # Project documentation
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Google Gemini API Key
- Supabase project (URL and publishable/anon key)

---

### Backend Setup

1. Open a terminal in `./backend`:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows PowerShell:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS/Linux:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Provide your `GEMINI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` in `./backend/.env`.

5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Backend health check endpoint: `http://localhost:8000/api/health`

---

### Frontend Setup

1. Open a terminal in `./frontend`:
   ```bash
   cd frontend
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000`, and set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

3. Install dependencies:
   ```bash
   npm install
   ```

4. Run the Next.js development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.

---

## Testing

Run the backend pytest test suite:
```bash
cd backend
pytest
```

---

## Production Build

To build the frontend for production:
```bash
cd frontend
npm run build
```

---

## Security & Architecture Principles

- **Zero Secret Leakage**: API keys (`GEMINI_API_KEY`) and administrative service-role keys are strictly server-side and never exposed to the client or version control.
- **PostgreSQL Row Level Security (RLS)**: User projects and analyses are strictly isolated by Supabase Auth user ID.
- **Upload Safety**: Strict validation against Zip Slip, Zip Bomb, and oversized files.
- **Rate Limiting**: In-memory rate limiting across analysis and recovery endpoints.
