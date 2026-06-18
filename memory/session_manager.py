from datetime import datetime, timedelta
from supabase import create_client
from core.config import get_settings


class SessionManager:
    def __init__(self):
        settings = get_settings()
        self.supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    async def create_session(self, session_id: str):
        self.supabase.table("sessions").upsert({
            "id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(hours=1)
            ).isoformat()
        }).execute()