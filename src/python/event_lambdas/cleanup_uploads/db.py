from asyncpg import Connection
from typing import List, Any, Dict

async def get_upload_files(conn:Connection, filters: Dict[str, Any]):
    query_base = """SELECT f.id
                FROM file f 
                JOIN file_status fs ON f.id = fs.id
                JOIN collection c ON f.collection_id = c.id
    """

    params = []
    where_clauses = ["fs.status = 'uploading'"]

    filter_map = {
        "start_date": "fs.upload_time >= ${index}::date",
        "end_date": "fs.upload_time < (${index}::date + interval '1 day')",
        "user_id": "f.cueuser_uploaded = ${index}",
        "collection_id": "f.collection_id = ${index}",
        "provider_id": "c.provider_id = ${index}"
    }

    for key, value in filters.items():
        if key in filter_map and value is not None:
            params.append(value)
            where_clauses.append(filter_map[key].format(index=len(params)))

    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = query_base + where_clause

    return await conn.fetch(query, *params)

async def delete_upload_files(conn:Connection, files:List):
    query = """DELETE FROM file f
               USING file_status fs 
               WHERE f.id = fs.id
                 AND f.id = ANY($1::uuid[])
                 AND fs.status = 'uploading'
    """ 

    result = await conn.execute(query, files)

    return f"DELETE {len(files)}" == result
