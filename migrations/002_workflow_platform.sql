-- WorkflowSpec v2 persistence for compiled plans, node attempts, checkpoints and evaluations.
CREATE TABLE IF NOT EXISTS workflow_versions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    template_id VARCHAR(100) NOT NULL,
    version INT NOT NULL,
    spec_json LONGTEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    UNIQUE KEY uq_workflow_version (template_id, version),
    INDEX idx_workflow_versions_template (template_id, created_at)
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) DEFAULT NULL,
    session_id VARCHAR(64) DEFAULT NULL,
    template_id VARCHAR(100) DEFAULT NULL,
    workflow_version INT DEFAULT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    spec_json LONGTEXT NOT NULL,
    input_json LONGTEXT,
    workspace VARCHAR(2048) DEFAULT NULL,
    current_node_id VARCHAR(100) DEFAULT NULL,
    plan_revision INT NOT NULL DEFAULT 1,
    replan_count INT NOT NULL DEFAULT 0,
    max_replans INT NOT NULL DEFAULT 3,
    max_parallelism INT NOT NULL DEFAULT 4,
    model_calls INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    approved TINYINT(1) NOT NULL DEFAULT 0,
    result_json LONGTEXT,
    error_text TEXT,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    started_at DATETIME(3) DEFAULT NULL,
    finished_at DATETIME(3) DEFAULT NULL,
    updated_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    INDEX idx_workflow_runs_status (status, updated_at),
    INDEX idx_workflow_runs_session (session_id, created_at),
    INDEX idx_workflow_runs_template (template_id, created_at)
);

CREATE TABLE IF NOT EXISTS workflow_node_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    attempt INT NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    input_json LONGTEXT,
    output_json LONGTEXT,
    error_text TEXT,
    evidence_json LONGTEXT,
    provider VARCHAR(80) DEFAULT NULL,
    model_profile VARCHAR(32) DEFAULT NULL,
    started_at DATETIME(3) DEFAULT NULL,
    finished_at DATETIME(3) DEFAULT NULL,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_workflow_node_runs (run_id, node_id, attempt),
    INDEX idx_workflow_node_status (run_id, status)
);

CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    label VARCHAR(255) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    path VARCHAR(2048) DEFAULT NULL,
    metadata_json LONGTEXT,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_workflow_checkpoints (run_id, created_at)
);

CREATE TABLE IF NOT EXISTS workflow_evaluations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    evaluator VARCHAR(100) NOT NULL,
    score DECIMAL(5,2) DEFAULT NULL,
    passed TINYINT(1) NOT NULL DEFAULT 0,
    result_json LONGTEXT,
    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_workflow_evaluations (run_id, created_at)
);

INSERT IGNORE INTO schema_migrations (version) VALUES (2);
