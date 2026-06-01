CREATE DATABASE IF NOT EXISTS watchtower;

USE watchtower;

CREATE TABLE IF NOT EXISTS customer_lottery_profile (
    user_id VARCHAR(64) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    balance DECIMAL(15, 2) NOT NULL,
    years_in_bank INT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pii_token_vault (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token VARCHAR(64) NOT NULL UNIQUE,
    pii_type VARCHAR(64) NOT NULL,
    pii_value TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customer_lottery_profile (user_id, full_name, balance, years_in_bank)
VALUES
    ('u1001', 'Alice Johnson', 76000.00, 4),
    ('u1002', 'Bob Kumar', 49000.00, 5),
    ('u1003', 'Chitra Nair', 120000.00, 2)
ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    balance = VALUES(balance),
    years_in_bank = VALUES(years_in_bank);
