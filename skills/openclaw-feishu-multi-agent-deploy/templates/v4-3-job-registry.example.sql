CREATE TABLE IF NOT EXISTS jobs (
  job_ref TEXT PRIMARY KEY,
  group_peer_id TEXT NOT NULL,
  requested_by TEXT,
  source_message_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'queued', 'done', 'failed', 'cancelled')),
  queue_position INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_group_status ON jobs(group_peer_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_group_created ON jobs(group_peer_id, created_at);

CREATE TABLE IF NOT EXISTS job_participants (
  job_ref TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  role TEXT NOT NULL,
  -- 运行态建议：pending -> accepted -> running -> done/failed
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'running', 'done', 'failed')),
  -- dispatch_status 可记录 ping_ok / dispatch_sent / timeout / accepted / complete_received 等细粒度状态
  dispatch_run_id TEXT,
  dispatch_status TEXT,
  progress_message_id TEXT,
  final_message_id TEXT,
  summary TEXT,
  completed_at TEXT,
  PRIMARY KEY (job_ref, agent_id),
  FOREIGN KEY (job_ref) REFERENCES jobs(job_ref)
);

CREATE TABLE IF NOT EXISTS job_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_ref TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  -- 存放结构化事件 JSON，例如 job_started / worker_dispatched / worker_completed / job_closed
  payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_ref) REFERENCES jobs(job_ref)
);

-- 活跃任务唯一性约束：同一个团队群只允许一个 active 任务。
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_group_single_active
ON jobs(group_peer_id)
WHERE status = 'active';
