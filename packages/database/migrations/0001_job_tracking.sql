-- Job result storage and dead-letter queue
-- Used by workers/base.py @job decorator

CREATE TABLE IF NOT EXISTS job_results (
    job_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    result TEXT,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS failed_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT NOT NULL,
    job_name TEXT NOT NULL,
    args TEXT,
    kwargs TEXT,
    error TEXT,
    traceback TEXT,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    replayed BOOLEAN NOT NULL DEFAULT false,
    replayed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS failed_jobs_replayed_idx ON failed_jobs (replayed) WHERE NOT replayed;
CREATE INDEX IF NOT EXISTS job_results_job_name_idx ON job_results (job_name);

-- RLS: service role only (workers use service role key)
ALTER TABLE job_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE failed_jobs ENABLE ROW LEVEL SECURITY;
