"""
Compatibility shim for user_db.
Redirects all database operations to the Database Department in `database/user_db.py`.
"""
from database.user_db import *
from database.user_db import (
    save_copilot_query_record,
    get_copilot_queries_for_review,
    update_copilot_query_review,
    get_user_own_copilot_queries,
    get_all_copilot_user_tables,
    get_user_copilot_display_history,
    soft_clear_user_copilot_history,
)
