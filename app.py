import os
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_TTS_ENTITY = os.getenv("HA_TTS_ENTITY", "tts.home_assistant_cloud")
SPEAKERS_FILE = Path(
    os.getenv("SPEAKERS_FILE", str(Path(__file__).with_name("speakers.yaml")))
)

app = FastAPI(
    title="Voice Proxy",
    description="Internt API för röstmeddelanden via Home Assistant och Nabu Casa TTS",
    version="1.1.0",
    root_path="/api/voice",
)


class VoiceMessage(BaseModel):
    text: str = Field(min_length=1)
    speaker: str | None = None


def load_speaker_config() -> tuple[str, dict[str, str]]:
    try:
        with SPEAKERS_FILE.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Högtalarkonfiguration saknas: {SPEAKERS_FILE}",
        ) from exc
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Felaktig YAML i högtalarkonfigurationen: {exc}",
        ) from exc

    default_alias = config.get("default")
    speakers = config.get("speakers")

    if not isinstance(default_alias, str) or not default_alias.strip():
        raise HTTPException(
            status_code=500,
            detail="speakers.yaml saknar ett giltigt 'default'-alias",
        )

    if not isinstance(speakers, dict) or not speakers:
        raise HTTPException(
            status_code=500,
            detail="speakers.yaml saknar en giltig 'speakers'-lista",
        )

    clean_speakers: dict[str, str] = {}
    for alias, entity_id in speakers.items():
        if not isinstance(alias, str) or not isinstance(entity_id, str):
            raise HTTPException(
                status_code=500,
                detail="Alla speaker-alias och entity_id i speakers.yaml måste vara strängar",
            )
        clean_speakers[alias.strip()] = entity_id.strip()

    if default_alias.casefold() not in {
        alias.casefold() for alias in clean_speakers
    }:
        raise HTTPException(
            status_code=500,
            detail=f"Default-alias '{default_alias}' finns inte i speakers.yaml",
        )

    return default_alias.strip(), clean_speakers


def resolve_speaker(alias: str, speakers: dict[str, str]) -> tuple[str, str]:
    requested = alias.strip().casefold()

    for configured_alias, entity_id in speakers.items():
        if configured_alias.casefold() == requested:
            return configured_alias, entity_id

    raise HTTPException(
        status_code=400,
        detail={
            "message": f"Okänt speaker-alias: {alias}",
            "available_speakers": list(speakers.keys()),
        },
    )


@app.get("/health")
def health():
    default_alias, speakers = load_speaker_config()

    return {
        "status": "ok",
        "home_assistant_configured": bool(HA_URL and HA_TOKEN),
        "tts_entity": HA_TTS_ENTITY,
        "default_speaker": default_alias,
        "speakers": list(speakers.keys()),
    }


@app.get("/speakers")
def get_speakers():
    default_alias, speakers = load_speaker_config()

    return {
        "default": default_alias,
        "speakers": list(speakers.keys()),
    }


@app.post("/say")
def say(message: VoiceMessage):
    if not HA_URL:
        raise HTTPException(status_code=500, detail="HA_URL saknas")

    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="HA_TOKEN saknas")

    default_alias, speakers = load_speaker_config()
    requested_alias = message.speaker or default_alias
    speaker_alias, speaker_entity_id = resolve_speaker(requested_alias, speakers)

    try:
        response = requests.post(
            f"{HA_URL.rstrip('/')}/api/services/tts/speak",
            headers={
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "entity_id": HA_TTS_ENTITY,
                "media_player_entity_id": speaker_entity_id,
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
        "speaker": speaker_alias,
        "text": message.text,
    }
