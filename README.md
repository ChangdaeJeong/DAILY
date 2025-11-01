# DAILY(Dev AI Loop for Your code)

## MySQL Database Setup

To set up the MySQL database and user, follow these steps:

1.  **Install MariaDB (if not already installed):**
    Download and install MariaDB from [https://mariadb.org/download/](https://mariadb.org/download/).
    During installation, set the root password to `ckdeo12!!` (or your preferred password).

2.  **Create User and Database:**
    Open your command prompt or PowerShell and navigate to your MariaDB `bin` directory (e.g., `cd "C:\Program Files\MariaDB 12.0\bin"`).
    Then, log in as the root user and execute the following SQL commands. When prompted for the password, enter `ckdeo12!!`.

    ```bash
    mysql -u root -p
    ```

    Once logged in, execute these SQL commands:

    ```sql
    CREATE USER 'sa.sec'@'localhost' IDENTIFIED BY '';
    CREATE DATABASE DAILY_DB;
    GRANT ALL PRIVILEGES ON DAILY_DB.* TO 'sa.sec'@'localhost';
    FLUSH PRIVILEGES;
    EXIT;
    ```
