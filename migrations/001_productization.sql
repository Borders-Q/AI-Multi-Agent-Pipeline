-- MySQL 8.0+ / migration version 1
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) DEFAULT NULL,
    run_id VARCHAR(64) DEFAULT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    attempt INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    payload_json LONGTEXT,
    result_json LONGTEXT,
    error_text TEXT,
    worker_id VARCHAR(100) DEFAULT NULL,
    lease_until DATETIME(3) DEFAULT NULL,
    next_attempt_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    heartbeat_at DATETIME(3) DEFAULT NULL,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX idx_tasks_claim (status, next_attempt_at, lease_until),
    INDEX idx_tasks_session (session_id, created_at),
    INDEX idx_tasks_run (run_id, created_at)
);

CREATE TABLE IF NOT EXISTS task_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    detail_json LONGTEXT,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_task_events (task_id, created_at, id)
);

INSERT IGNORE INTO schema_migrations (version) VALUES (1);
