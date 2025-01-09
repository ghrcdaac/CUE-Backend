import psycopg
import os

def query(operation, params):
    conn = psycopg.connect(f'dbname={os.getenv("DB_DATABASE")} user={os.getenv("DB_USER")} password={os.getenv("DB_PASSWORD")} host={os.getenv("DB_HOST")}')
    try:
        with conn.cursor() as cur:
            operation(cur, params)
            return cur.fetchall()
    except Exception as e:
        print(e)
        conn.rollback()
    else:
        conn.commit()
    finally:
        conn.close()