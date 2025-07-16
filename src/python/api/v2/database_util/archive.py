from typing import Dict, Any
from uuid import UUID


async def query_archive_database(ngroup_id: UUID, filters: Dict[str, Any]) -> str:
    base_query = """
                    SELECT id, name, "type", cueuser_uploaded, size_bytes, collection_id, collection_path, edpub,
                           "checksum", upload_time, scan_start, scan_end, egress_start,
                           status, scan_results, provider_id, ngroup_id, "date"
                """
    where_clause = await build_where_clause(ngroup_id, filters)
    query = base_query + where_clause
    return query

async def build_where_clause(ngroup_id: UUID, filters: Dict[str, Any]) -> str:

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    user_id = filters.get("user_id")
    collection_id = filters.get("collection_id")
    provider_id = filters.get("provider_id")

    query_suffix = "FROM metrics "

    where_clauses = []
    where_clauses.append(f"ngroup_id = '{ngroup_id}'")

    if start_date:
        where_clauses.append(f"upload_time >= DATE '{start_date}'")
    if end_date:
        where_clauses.append(f"DATE(upload_time) <= DATE '{end_date}'")
    if user_id:
        where_clauses.append(f"cueuser_uploaded = '{user_id}'")
    if collection_id:
        where_clauses.append(f"collection_id = '{collection_id}'")
    if provider_id:
        where_clauses.append(f"provider_id = '{provider_id}'")

    if where_clauses:
        query_suffix += " WHERE " + " AND ".join(where_clauses)

    return query_suffix