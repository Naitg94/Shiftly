-- Shiftly Project Memory Database Schema (Supabase PostgreSQL)
-- Step 6.2 Multi-Tenant Authorization & Row Level Security

-- 1. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
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

-- Indexes for fast multi-tenant queries and foreign key lookups
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_project_id ON analyses(project_id);
CREATE INDEX IF NOT EXISTS idx_key_points_analysis_id ON key_points(analysis_id);
CREATE INDEX IF NOT EXISTS idx_action_items_analysis_id ON action_items(analysis_id);
CREATE INDEX IF NOT EXISTS idx_decisions_analysis_id ON decisions(analysis_id);
CREATE INDEX IF NOT EXISTS idx_important_dates_analysis_id ON important_dates(analysis_id);

-- Row Level Security (RLS) Enablement
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE key_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE important_dates ENABLE ROW LEVEL SECURITY;

-- Drop old broad policies if present
DROP POLICY IF EXISTS "Allow backend access to projects" ON projects;
DROP POLICY IF EXISTS "Allow backend access to analyses" ON analyses;
DROP POLICY IF EXISTS "Allow backend access to key_points" ON key_points;
DROP POLICY IF EXISTS "Allow backend access to action_items" ON action_items;
DROP POLICY IF EXISTS "Allow backend access to decisions" ON decisions;
DROP POLICY IF EXISTS "Allow backend access to important_dates" ON important_dates;

-- Drop existing user policies to allow idempotent recreation
DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can insert own projects" ON projects;
DROP POLICY IF EXISTS "Users can update own projects" ON projects;
DROP POLICY IF EXISTS "Users can delete own projects" ON projects;

DROP POLICY IF EXISTS "Users can view own project analyses" ON analyses;
DROP POLICY IF EXISTS "Users can insert own project analyses" ON analyses;
DROP POLICY IF EXISTS "Users can update own project analyses" ON analyses;
DROP POLICY IF EXISTS "Users can delete own project analyses" ON analyses;

DROP POLICY IF EXISTS "Users can view own project key_points" ON key_points;
DROP POLICY IF EXISTS "Users can insert own project key_points" ON key_points;
DROP POLICY IF EXISTS "Users can delete own project key_points" ON key_points;

DROP POLICY IF EXISTS "Users can view own project action_items" ON action_items;
DROP POLICY IF EXISTS "Users can insert own project action_items" ON action_items;
DROP POLICY IF EXISTS "Users can delete own project action_items" ON action_items;

DROP POLICY IF EXISTS "Users can view own project decisions" ON decisions;
DROP POLICY IF EXISTS "Users can insert own project decisions" ON decisions;
DROP POLICY IF EXISTS "Users can delete own project decisions" ON decisions;

DROP POLICY IF EXISTS "Users can view own project important_dates" ON important_dates;
DROP POLICY IF EXISTS "Users can insert own project important_dates" ON important_dates;
DROP POLICY IF EXISTS "Users can delete own project important_dates" ON important_dates;

-- 1. Strict Policies for Projects
CREATE POLICY "Users can view own projects" ON projects
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own projects" ON projects
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own projects" ON projects
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own projects" ON projects
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

-- 2. Strict Policies for Analyses
CREATE POLICY "Users can view own project analyses" ON analyses
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analyses.project_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert own project analyses" ON analyses
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analyses.project_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can update own project analyses" ON analyses
    FOR UPDATE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analyses.project_id AND projects.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analyses.project_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own project analyses" ON analyses
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM projects WHERE projects.id = analyses.project_id AND projects.user_id = auth.uid()
    ));

-- 3. Strict Policies for Key Points
CREATE POLICY "Users can view own project key_points" ON key_points
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = key_points.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert own project key_points" ON key_points
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = key_points.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own project key_points" ON key_points
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = key_points.analysis_id AND projects.user_id = auth.uid()
    ));

-- 4. Strict Policies for Action Items
CREATE POLICY "Users can view own project action_items" ON action_items
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = action_items.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert own project action_items" ON action_items
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = action_items.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own project action_items" ON action_items
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = action_items.analysis_id AND projects.user_id = auth.uid()
    ));

-- 5. Strict Policies for Decisions
CREATE POLICY "Users can view own project decisions" ON decisions
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = decisions.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert own project decisions" ON decisions
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = decisions.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own project decisions" ON decisions
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = decisions.analysis_id AND projects.user_id = auth.uid()
    ));

-- 6. Strict Policies for Important Dates
CREATE POLICY "Users can view own project important_dates" ON important_dates
    FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = important_dates.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert own project important_dates" ON important_dates
    FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = important_dates.analysis_id AND projects.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete own project important_dates" ON important_dates
    FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM analyses 
        JOIN projects ON projects.id = analyses.project_id
        WHERE analyses.id = important_dates.analysis_id AND projects.user_id = auth.uid()
    ));
