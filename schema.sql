CREATE DATABASE IF NOT EXISTS observability;
USE observability;

CREATE TABLE IF NOT EXISTS api_events (
    id BIGINT NOT NULL AUTO_INCREMENT,
    tenant_id VARCHAR(64) NOT NULL,
    event_time DATETIME(6) NOT NULL,
    status_code SMALLINT NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_events_tenant_time_status (tenant_id, event_time, status_code),
    KEY ix_events_time_tenant_status (event_time, tenant_id, status_code)
) ENGINE=InnoDB;

-- Example read-only account (adjust host and password for your environment):
-- CREATE USER 'analytics_reader'@'localhost' IDENTIFIED BY 'CHANGE_ME';
-- GRANT SELECT ON observability.api_events TO 'analytics_reader'@'localhost';
