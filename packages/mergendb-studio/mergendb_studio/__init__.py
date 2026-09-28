"""
Mergen Studio: Interactive phpMyAdmin-style Web Management Dashboard extension for MergenDB.
"""

__version__ = "0.6.10"

def get_studio_html() -> str:
    try:
        from mergendb_studio.studio_ui import STUDIO_HTML
        return STUDIO_HTML
    except ImportError:
        from mergendb.server.studio_ui import STUDIO_HTML
        return STUDIO_HTML
