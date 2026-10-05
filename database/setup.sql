-- Run once as a MySQL admin (e.g. root):  mysql -u root -p < database/setup.sql
-- Tip: keep your real-password copy as database/setup.local.sql (git-ignored).
-- Change the password below, and use the same value for DB_PASSWORD in backend/.env
-- Safe to re-run: ALTER USER resets the password if the user already existed.
CREATE DATABASE IF NOT EXISTS placegenie CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'placegenie'@'localhost' IDENTIFIED BY 'change_me';
ALTER USER 'placegenie'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON placegenie.* TO 'placegenie'@'localhost';

-- The backend connects over TCP to 127.0.0.1, which some MySQL setups do not treat as 'localhost'.
CREATE USER IF NOT EXISTS 'placegenie'@'127.0.0.1' IDENTIFIED BY 'change_me';
ALTER USER 'placegenie'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON placegenie.* TO 'placegenie'@'127.0.0.1';

FLUSH PRIVILEGES;
