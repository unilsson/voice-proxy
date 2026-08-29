# Voice Proxy

Lättviktig intern FastAPI-tjänst för att spela upp röstmeddelanden via Home Assistant och Nabu Casa TTS.

Tjänsten är avsedd att ligga bakom den interna Nginx API-proxyn och nås som:

```text
http://api.ulnihnw.net/api/voice/
```

## API

### POST `/say`

Spelar upp ett meddelande på angiven Home Assistant media player. Om `speaker` utelämnas används `DEFAULT_SPEAKER` från `.env`.

Exempel:

```bash
curl -X POST "http://api.ulnihnw.net/api/voice/say" \
  -H "Content-Type: application/json" \
  -d '{"text":"Detta är ett test från Voice Proxy."}'
```

Med explicit högtalare:

```bash
curl -X POST "http://api.ulnihnw.net/api/voice/say" \
  -H "Content-Type: application/json" \
  -d '{
    "text":"Maten är klar.",
    "speaker":"media_player.vardagsrummet"
  }'
```

### GET `/health`

En enkel kontroll av tjänsten och om Home Assistant-konfigurationen är laddad.

```bash
curl http://api.ulnihnw.net/api/voice/health
```

Health-endpointen returnerar aldrig `HA_TOKEN`.

## Swagger / OpenAPI

När tjänsten går genom Nginx-proxyn:

```text
http://api.ulnihnw.net/api/voice/docs
http://api.ulnihnw.net/api/voice/openapi.json
```

## Konfiguration

Kopiera `.env.example` till `.env` och fyll i riktiga värden:

```env
HA_URL=http://homeassistant.local:8123
HA_TOKEN=replace-with-long-lived-access-token
HA_TTS_ENTITY=tts.home_assistant_cloud
DEFAULT_SPEAKER=media_player.vardagsrummet
```

`HA_TOKEN` ska vara en Home Assistant Long-Lived Access Token. `.env` är medvetet exkluderad från Git via `.gitignore`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

För lokal testkörning:

```bash
uvicorn app:app --host 127.0.0.1 --port 21965
```

Direkt lokalt API:

```text
http://127.0.0.1:21965
```

## Nginx API-proxy

Exempel på route i Ansible-konfigurationen:

```yaml
- name: voice
  path: /api/voice/
  upstream: http://127.0.0.1:21965/
```

Nginx tar bort `/api/voice/` innan anropet skickas vidare till FastAPI. FastAPI är därför konfigurerat med:

```python
root_path="/api/voice"
```

så att Swagger och OpenAPI genererar rätt externa URL:er.

## Flöde

```text
Klient i hemmanätet
        |
        v
http://api.ulnihnw.net/api/voice/say
        |
        v
Nginx
        |
        v
Voice Proxy :21965
        |
        v
Home Assistant REST API
        |
        v
tts.home_assistant_cloud
        |
        v
Google-/Cast-högtalare
```

Klienterna behöver därmed inte känna till Home Assistants adress, access-token eller interna service-anrop.
