# Voice Proxy

Lättviktig intern FastAPI-tjänst för att spela upp röstmeddelanden via Home Assistant och Nabu Casa TTS.

Tjänsten är avsedd att ligga bakom den interna Nginx API-proxyn och nås som:

```text
http://api.ulnihnw.net/api/voice/
```

## Speaker-alias

Klienterna använder korta alias i stället för Home Assistant entity-id:n. Alias och default-högtalare definieras i `speakers.yaml`.

Exempel:

```yaml
default: Vardagsrum

speakers:
  Vardagsrum: media_player.vardagsrummet
  Kök: media_player.koket
```

Alias matchas utan hänsyn till stora/små bokstäver. `Kök`, `kök` och `KÖK` träffar alltså samma konfiguration.

Konfigurationsfilen läses vid varje API-anrop, så ändringar i `speakers.yaml` kräver normalt ingen restart av tjänsten.

## API

### POST `/say`

Spelar upp ett meddelande på angivet speaker-alias. Om `speaker` utelämnas används aliaset i `default` från `speakers.yaml`.

Använd default-högtalaren:

```bash
curl -X POST "http://api.ulnihnw.net/api/voice/say" \
  -H "Content-Type: application/json" \
  -d '{"text":"Detta är ett test från Voice Proxy."}'
```

Ange speaker-alias:

```bash
curl -X POST "http://api.ulnihnw.net/api/voice/say" \
  -H "Content-Type: application/json" \
  -d '{
    "text":"Maten är klar.",
    "speaker":"Kök"
  }'
```

Ett okänt alias ger HTTP 400 och svaret innehåller vilka alias som är tillgängliga.

### GET `/speakers`

Visar default-alias och vilka speaker-alias som är konfigurerade, utan att exponera Home Assistant entity-id:n.

```bash
curl http://api.ulnihnw.net/api/voice/speakers
```

### GET `/health`

En enkel kontroll av tjänsten, Home Assistant-konfigurationen och högtalarkonfigurationen.

```bash
curl http://api.ulnihnw.net/api/voice/health
```

Health-endpointen returnerar aldrig `HA_TOKEN`.

## Swagger / OpenAPI

```text
http://api.ulnihnw.net/api/voice/docs
http://api.ulnihnw.net/api/voice/openapi.json
```

## Miljökonfiguration

Kopiera `.env.example` till `.env` och fyll i riktiga värden:

```env
HA_URL=http://homeassistant.local:8123
HA_TOKEN=replace-with-long-lived-access-token
HA_TTS_ENTITY=tts.home_assistant_cloud
SPEAKERS_FILE=/opt/voice-proxy/speakers.yaml
```

`HA_TOKEN` ska vara en Home Assistant Long-Lived Access Token. `.env` är medvetet exkluderad från Git via `.gitignore`.

`SPEAKERS_FILE` är valfri. Om den inte anges används `speakers.yaml` i samma katalog som `app.py`.

## Installation

Installera beroenden i den Python-miljö som tjänsten använder:

```bash
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
speaker-alias -> Home Assistant media_player
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

Klienterna behöver därmed inte känna till Home Assistants adress, access-token eller interna entity-id:n.
