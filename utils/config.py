import os
from dotenv import load_dotenv
load_dotenv()
GUILD_ID = int(os.getenv("GUILD_ID"))
MIDMAN_CHANNEL_ID = int(os.getenv("MIDMAN_CHANNEL_ID"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
STORE_NAME = os.getenv("STORE_NAME", "Cellyn Store")
