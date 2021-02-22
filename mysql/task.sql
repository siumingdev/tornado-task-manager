DROP TABLE IF EXISTS task_man.task;

CREATE TABLE IF NOT EXISTS task_man.task (
    PRIMARY KEY (id),
    id           BIGINT      NOT NULL AUTO_INCREMENT,
    title        VARCHAR(50) NULL,
    description  TEXT        NULL,
    expiry_dt    DATETIME(6) NULL,
    create_dt    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    update_dt    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
);