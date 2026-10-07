"""
Mergen Studio: Interactive Web Management Dashboard extension for MergenDB.
"""

__version__ = "0.8.3"

def get_studio_html() -> str:
    try:
        from mergendb_studio.studio_ui import STUDIO_HTML
        return STUDIO_HTML
    except ImportError:
        from mergendb.server.studio_ui import STUDIO_HTML
        return STUDIO_HTML
