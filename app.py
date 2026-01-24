from fastapi import FastAPI

from api.supabase.db_api import router as db_api_router
from api.voice_bot.voice_api import router as voice_api_router
from api.email_inbound import router as email_inbound_router

app = FastAPI()

app.include_router(db_api_router)
app.include_router(voice_api_router)
app.include_router(email_inbound_router)
