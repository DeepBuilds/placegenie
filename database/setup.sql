-- Run once as a MySQL admin (e.g. root):  mysql -u root -p < database/setup.sql
-- Change the password below, and use the same value for DB_PASSWORD in backend/.env
CREATE DATABASE IF NOT EXISTS placegenie CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'placegenie'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON placegenie.* TO 'placegenie'@'localhost';
FLUSH PRIVILEGES;
