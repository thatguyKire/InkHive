"""Who is connected to each whiteboard right now.

Lives in process memory, matching the in-memory channel layer (one Daphne
process). Written by the WebSocket consumer, read by pages such as the
teacher dashboard ("Live · 3 online").
"""
from collections import defaultdict

# {session_id: {channel_name: {"uid": "5", "meta": {...}}}}
PRESENCE = defaultdict(dict)


def online_count(session_id):
    """Number of distinct users connected to a session's board."""
    entries = PRESENCE.get(str(session_id), {})
    return len({entry["uid"] for entry in entries.values()})
