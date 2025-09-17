import psycopg

def new_infected_files(curr:psycopg.cursor.Cursor, params:list[tuple]):
    insert_query = """
        UPDATE file_status
        SET status = 'infected', scan_end = %s, scan_result = %s
        WHERE file_id = 'SELECT file_id FROM file WHERE name = %s'
    """
    curr.executemany(insert_query, params)
    