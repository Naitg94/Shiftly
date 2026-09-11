-- Shiftly Project Memory Database Schema (Supabase PostgreSQL)
-- Run this in your Supabase SQL Editor to initialize Project Memory tables

-- 1. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Analyses Table
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_type TEXT DEFAULT 'Chat Export',
    source_name TEXT,
    summary TEXT NOT NULL,
    stats JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Key Points Table
CREATE TABLE IF NOT EXISTS key_points (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    topic TEXT,
    source_reference JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Action Items Table
CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    responsible_person TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'Pending',
    priority TEXT DEFAULT 'Normal',
    source_reference JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Decisions Table
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    decision_type TEXT DEFAULT 'Approval',
    approved_by TEXT,
    date TEXT,
    source_reference JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Important Dates Table
CREATE TABLE IF NOT EXISTS important_dates (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    source_reference JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast deterministic project retrieval and foreign keys
CREATE INDEX IF NOT EXISTS idx_analyses_project_id ON analyses(project_id);
CREATE INDEX IF NOT EXISTS idx_key_points_analysis_id ON key_points(analysis_id);
CREATE INDEX IF NOT EXISTS idx_action_items_analysis_id ON action_items(analysis_id);
CREATE INDEX IF NOT EXISTS idx_decisions_analysis_id ON decisions(analysis_id);
CREATE INDEX IF NOT EXISTS idx_important_dates_analysis_id ON important_dates(analysis_id);

-- Row Level Security (RLS) Policies
-- Since all Shiftly traffic is mediated exclusively through the FastAPI backend:
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE key_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE important_dates ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'projects' AND policyname = 'Allow backend access to projects') THEN
        CREATE POLICY "Allow backend access to projects" ON projects FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'analyses' AND policyname = 'Allow backend access to analyses') THEN
        CREATE POLICY "Allow backend access to analyses" ON analyses FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'key_points' AND policyname = 'Allow backend access to key_points') THEN
        CREATE POLICY "Allow backend access to key_points" ON key_points FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'action_items' AND policyname = 'Allow backend access to action_items') THEN
        CREATE POLICY "Allow backend access to action_items" ON action_items FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'decisions' AND policyname = 'Allow backend access to decisions') THEN
        CREATE POLICY "Allow backend access to decisions" ON decisions FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'important_dates' AND policyname = 'Allow backend access to important_dates') THEN
        CREATE POLICY "Allow backend access to important_dates" ON important_dates FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
    END IF;
END $$;

