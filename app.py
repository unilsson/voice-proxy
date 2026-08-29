import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_TTS_ENTITY = os.getenv("HA_TTS_ENTITY", "tts.home_assistant_cloud")
DEFAULT_SPEAKER = os.getenv("DEFAULT_SPEAKER", "media_player.vardagsrummet")

app = FastAPI(
    title="Voice Proxy",
    description="Internt API för röstmeddelanden via Home Assistant och Nabu Casa TTS",
    version="1.0.0",
    root_path="/api/voice",
)


class VoiceMessage(BaseModel):
    text: str = Field(min_length=1)
    speaker: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "home_assistant_configured": bool(HA_URL and HA_TOKEN),
        "tts_entity": HA_TTS_ENTITY,
        "default_speaker": DEFAULT_SPEAKER,
    }


@app.post("/say")
def say(message: VoiceMessage):
    if not HA_URL:
        raise HTTPException(status_code=500, detail="HA_URL saknas")

    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN saknas")

    speaker = message.speaker or DEFAULT_SPEAKER

    if not speaker:
        raise HTTPException(status_code=400, detail="Ingen speaker angiven")

    try:
        response = requests.post(
            f"{HA_URL.rstrip('/')}/api/services/tts/speak",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "entity_id": HA_TTS_ENTITY,
                "media_player_entity_id": speaker,
                "message": message.text,
                "cache": True,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Kunde inte kontakta Home Assistant: {exc}",
        ) from exc

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant svarade {response.status_code}: {response.text}",
        )

    return {
        "status": "spoken",
        "speaker": speaker,
        "text": message.text,
    }
