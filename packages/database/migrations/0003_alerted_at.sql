-- Track which breakouts have been alerted on so we don't re-alert on reruns.
-- Created: 2026-05-12

ALTER TABLE breakouts ADD COLUMN IF NOT EXISTS alerted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS breakouts_alerted_idx ON breakouts (alerted_at DESC)
    WHERE alerted_at IS NOT NULL;
