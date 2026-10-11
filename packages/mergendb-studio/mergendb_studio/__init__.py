"""
Mergen Studio: Interactive Web Management Dashboard extension for MergenDB.
"""

__version__ = "1.0.0"

def get_studio_html() -> str:
    try:
        from mergendb_studio.studio_ui import STUDIO_HTML
        return STUDIO_HTML
    except ImportError:
        from mergendb.server.studio_ui import STUDIO_HTML
        return STUDIO_HTML
