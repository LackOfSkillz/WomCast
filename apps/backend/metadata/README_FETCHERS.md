# Metadata Fetchers - Configuration Guide

## Overview

WomCast uses only legal, publicly accessible APIs for fetching media metadata and artwork:

- **TMDB (The Movie Database)**: Movies and TV shows metadata, posters, backdrops
- **MusicBrainz**: Music metadata (artist, album, genre)

All fetchers respect:
- Rate limits (TMDB: 40 req/10s, MusicBrainz: 1 req/s)
- Opt-out configuration
- Cache TTL settings

## Configuration File

Location: `apps/backend/metadata_config.json`

```json
{
  "enabled": true,
  "tmdb_api_key": null,
  "use_tmdb": true,
  "use_musicbrainz": true,
  "cache_ttl_days": 90,
  "rate_limit_enabled": true
}
```

### Fields

- **enabled**: Global toggle for metadata fetching
- **tmdb_api_key**: API key from https://www.themoviedb.org/settings/api (free tier)
- **use_tmdb**: Enable/disable TMDB fetching
- **use_musicbrainz**: Enable/disable MusicBrainz fetching
- **cache_ttl_days**: How long to keep cached metadata (default: 90 days)
- **rate_limit_enabled**: Respect API rate limits (recommended: true)

## REST API Endpoints

### Get Configuration

```http
GET /v1/metadata/config
```

Response:
```json
{
  "enabled": true,
  "tmdb_api_key": "***",
  "use_tmdb": true,
  "use_musicbrainz": true,
  "cache_ttl_days": 90,
  "rate_limit_enabled": true
}
```

### Update Configuration

```http
PUT /v1/metadata/config
Content-Type: application/json

{
  "enabled": false,
  "tmdb_api_key": "your_api_key_here"
}
```

Response: Updated configuration

### Sanitize Cache

Removes metadata older than specified days:

```http
POST /v1/metadata/cache/sanitize?older_than_days=90
```

Response:
```json
{
  "videos_cleared": 42,
  "audio_cleared": 0,
  "older_than_days": 90
}
```

## TMDB API Setup

1. Sign up at https://www.themoviedb.org/
2. Go to Settings → API
3. Request an API key (free for non-commercial use)
4. Add key to `metadata_config.json` or update via REST API

## CLI Usage

### Search Movie

```bash
python -m metadata.fetchers search-movie "The Matrix" 1999
```

Output:
```
Title: The Matrix
Year: 1999
Genre: Science Fiction
Director: Lana Wachowski
Rating: 8.2
TMDB ID: 603
IMDb ID: tt0133093
Poster: https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg
```

### Search Music

```bash
python -m metadata.fetchers search-music "Bohemian Rhapsody" "Queen"
```

### Sanitize Cache

```bash
python -m metadata.fetchers sanitize womcast.db 90
```

## Legal Sources

### TMDB

- Free tier: 40 requests per 10 seconds
- Requires attribution in app
- Free for non-commercial use
- API: https://developers.themoviedb.org/

### MusicBrainz

- Free, open-source music encyclopedia
- Rate limit: 1 request per second (respectful crawling)
- No API key required
- API: https://musicbrainz.org/doc/MusicBrainz_API

## Privacy

- All fetching is opt-in (can be disabled globally)
- No user data sent to external services
- Only media titles/names used for searches
- Cached metadata stored locally in SQLite

## Cache Management

- Metadata cached in `videos` and `audio_tracks` database tables
- Default TTL: 90 days
- Automatic cleanup via sanitization endpoint
- Manual cleanup: `POST /v1/metadata/cache/sanitize`

## Rate Limiting

- TMDB: 4 requests/second (40/10s average)
- MusicBrainz: 1 request/second
- Rate limiting can be disabled for testing (not recommended for production)

## Troubleshooting

### TMDB searches return empty results

- Check API key is configured: `GET /v1/metadata/config`
- Verify API key is valid at https://www.themoviedb.org/settings/api
- Check rate limiting isn't blocking requests

### MusicBrainz searches fail

- Verify internet connectivity
- Check MusicBrainz service status: https://musicbrainz.org/
- Ensure User-Agent header is set correctly

### Opt-out completely

```bash
curl -X PUT http://localhost:3003/v1/metadata/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

Or update `metadata_config.json`:
```json
{
  "enabled": false
}
```
