from mysql.connector import Error
from mysql.connector import pooling

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'DAILY_DB',
    'user': 'sa.sec',
    'password': ''
}

# Connection Pool Configuration
POOL_CONFIG = {
    'pool_name': 'daily_db_pool',
    'pool_size': 5,  # Adjust pool size as needed
    'pool_reset_session': True,
}

db_pool = None

def create_db_pool():
    global db_pool
    try:
        db_pool = pooling.MySQLConnectionPool(**POOL_CONFIG, **DB_CONFIG)
        print(f"MySQL connection pool '{POOL_CONFIG['pool_name']}' created with size {POOL_CONFIG['pool_size']}.")
    except Error as e:
        print(f"Error creating MySQL connection pool: {e}")

def get_conn():
    try:
        if db_pool:
            conn = db_pool.get_connection()
            if conn.is_connected():
                print("Connection obtained from pool successfully!")
                return conn
        else:
            print("Database pool not initialized.")
            return None
    except Error as e:
        print(f"Error getting connection from pool: {e}")
        return None

def close_conn(conn):
    if conn:
        conn.close()
        print("Connection returned to pool.")
