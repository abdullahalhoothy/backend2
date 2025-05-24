import json
from typing import List, Any
# from asyncpg.pool import Pool # No longer needed as we'll use Database class directly
from backend_common.database import Database # Import Database class

async def seed_table(table_name: str, columns: List[str], data_rows: List[tuple], pk_column_name: str) -> List[Any]:
    """
    Seeds a table with data and returns the primary keys of inserted rows.

    Args:
        db_pool: The asyncpg connection pool.
        table_name: Name of the table to seed.
        columns: List of column names for insertion.
        data_rows: List of tuples, where each tuple represents a row to insert.
                   Values should be in the same order as `columns`.
        pk_column_name: The name of the primary key column to return.

    Returns:
        A list of primary keys of the inserted rows.
    """
    if not data_rows:
        return []

    cols_str = ", ".join(f'"{c}"' for c in columns) # Quote column names if they might be reserved keywords
    
    # Prepare value placeholders: ($1, $2, $3), ($4, $5, $6), ...
    num_cols = len(columns)
    value_placeholders = []
    current_param_index = 1
    for i in range(len(data_rows)):
        row_placeholders = []
        for j in range(num_cols):
            row_placeholders.append(f"${current_param_index}")
            current_param_index += 1
        value_placeholders.append(f"({', '.join(row_placeholders)})")
    
    values_str = ", ".join(value_placeholders)
    
    # Flatten data_rows for passing to fetch
    flat_data = [item for row in data_rows for item in row]

    # Ensure pk_column_name is quoted if it's a reserved keyword or contains special characters
    returning_pk_column = f'"{pk_column_name}"'

    query = f"INSERT INTO {table_name} ({cols_str}) VALUES {values_str} RETURNING {returning_pk_column};"
    
    # print(f"Executing seed query: {query} with data: {flat_data}") # For debugging
    
    # Database.fetch is suitable for INSERT ... RETURNING
    # It expects a flat list of parameters
    records = await Database.fetch(query, *flat_data)
    
    return [record[pk_column_name] for record in records]


async def cleanup_table_by_ids(table_name: str, pk_column_name: str, ids: List[Any]):
    """
    Deletes rows from a table based on a list of primary key IDs.

    Args:
        db_pool: The asyncpg connection pool.
        table_name: Name of the table to clean up.
        pk_column_name: Name of the primary key column.
        ids: List of primary key IDs to delete.
    """
    if not ids:
        return

    # Ensure pk_column_name is quoted
    pk_col = f'"{pk_column_name}"'
    
    # Using ANY($1) is efficient for a list of IDs.
    # The list of IDs should be passed as a single argument.
    query = f"DELETE FROM {table_name} WHERE {pk_col} = ANY($1);"
    
    # print(f"Executing cleanup query: {query} with IDs: {ids}") # For debugging
    await Database.execute(query, ids)


