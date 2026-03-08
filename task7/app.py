"""
Spotify Flask Backend
Uses Spotify Web API (Free) with OAuth2 PKCE & Client Credentials flows
"""

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
import requests
import os
import base64
import secrets
import hashlib
from urllib.parse import urlencode
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

# ── Spotify Config ────────────────────────────────────────────────────────────
CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5000/auth/callback")
SPOTIFY_AUTH_URL  = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE  = "https://api.spotify.com/v1"

SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-top-read",
    "user-read-recently-played",
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "streaming",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_client_credentials_token():
    """App-level token (no user login needed) for public data."""
    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def spotify_get(endpoint, token, params=None):
    """Authenticated GET to Spotify API."""
    resp = requests.get(
        f"{SPOTIFY_API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params=params or {},
    )
    resp.raise_for_status()
    return resp.json()


def spotify_post(endpoint, token, json_data=None):
    resp = requests.post(
        f"{SPOTIFY_API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json=json_data or {},
    )
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def spotify_put(endpoint, token, json_data=None):
    resp = requests.put(
        f"{SPOTIFY_API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json=json_data or {},
    )
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def spotify_delete(endpoint, token, json_data=None):
    resp = requests.delete(
        f"{SPOTIFY_API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json=json_data or {},
    )
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def require_user_token(f):
    """Decorator – requires user OAuth token in session or Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = session.get("access_token")
        if not token:
            return jsonify({"error": "User authentication required"}), 401
        request.user_token = token
        return f(*args, **kwargs)
    return decorated


def api_response(data, status=200):
    return jsonify({"status": "success", "data": data}), status


def api_error(message, status=400):
    return jsonify({"status": "error", "message": message}), status


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/auth/login")
def auth_login():
    """Redirect user to Spotify login page."""
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         " ".join(SCOPES),
        "state":         state,
        "show_dialog":   "false",
    }
    return redirect(f"{SPOTIFY_AUTH_URL}?{urlencode(params)}")


@app.route("/auth/callback")
def auth_callback():
    """Exchange authorization code for access + refresh tokens."""
    error = request.args.get("error")
    if error:
        return api_error(f"Spotify denied access: {error}", 403)

    code  = request.args.get("code")
    state = request.args.get("state")

    if state != session.pop("oauth_state", None):
        return api_error("State mismatch – possible CSRF attack", 403)

    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code",
              "code": code,
              "redirect_uri": REDIRECT_URI},
    )
    if resp.status_code != 200:
        return api_error("Token exchange failed", 500)

    tokens = resp.json()
    session["access_token"]  = tokens["access_token"]
    session["refresh_token"] = tokens["refresh_token"]

    return api_response({
        "access_token":  tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in":    tokens["expires_in"],
        "token_type":    tokens["token_type"],
    })


@app.route("/auth/refresh", methods=["POST"])
def auth_refresh():
    """Refresh an expired access token."""
    data          = request.get_json() or {}
    refresh_token = data.get("refresh_token") or session.get("refresh_token")
    if not refresh_token:
        return api_error("refresh_token required", 400)

    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    if resp.status_code != 200:
        return api_error("Token refresh failed", 500)

    tokens = resp.json()
    session["access_token"] = tokens["access_token"]
    return api_response({
        "access_token": tokens["access_token"],
        "expires_in":   tokens["expires_in"],
    })


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return api_response({"message": "Logged out"})


# ══════════════════════════════════════════════════════════════════════════════
#  USER ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/me")
@require_user_token
def get_me():
    """Get current user profile."""
    data = spotify_get("/me", request.user_token)
    return api_response(data)


@app.route("/me/top/<item_type>")
@require_user_token
def get_top_items(item_type):
    """
    Get user's top artists or tracks.
    item_type: 'artists' | 'tracks'
    Query params: time_range (short_term|medium_term|long_term), limit, offset
    """
    if item_type not in ("artists", "tracks"):
        return api_error("item_type must be 'artists' or 'tracks'")
    params = {
        "time_range": request.args.get("time_range", "medium_term"),
        "limit":      request.args.get("limit", 20),
        "offset":     request.args.get("offset", 0),
    }
    data = spotify_get(f"/me/top/{item_type}", request.user_token, params)
    return api_response(data)


@app.route("/me/recently-played")
@require_user_token
def recently_played():
    """Get recently played tracks."""
    params = {
        "limit": request.args.get("limit", 20),
    }
    if "after" in request.args:
        params["after"] = request.args["after"]
    data = spotify_get("/me/player/recently-played", request.user_token, params)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/search")
def search():
    """
    Search Spotify catalog.
    Query params: q (required), type (track,artist,album,playlist), limit, offset, market
    Uses client credentials – no user login required.
    """
    q = request.args.get("q")
    if not q:
        return api_error("Query parameter 'q' is required")

    params = {
        "q":      q,
        "type":   request.args.get("type", "track,artist,album"),
        "limit":  request.args.get("limit", 10),
        "offset": request.args.get("offset", 0),
        "market": request.args.get("market", "US"),
    }
    token = get_client_credentials_token()
    data  = spotify_get("/search", token, params)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  TRACKS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/tracks/<track_id>")
def get_track(track_id):
    token = get_client_credentials_token()
    data  = spotify_get(f"/tracks/{track_id}", token,
                        {"market": request.args.get("market", "US")})
    return api_response(data)


@app.route("/tracks/<track_id>/audio-features")
def get_audio_features(track_id):
    """Get audio features (tempo, key, danceability …)."""
    token = get_client_credentials_token()
    data  = spotify_get(f"/audio-features/{track_id}", token)
    return api_response(data)


@app.route("/tracks/<track_id>/recommendations")
def get_recommendations(track_id):
    """Get track recommendations seeded by a single track."""
    token  = get_client_credentials_token()
    params = {
        "seed_tracks": track_id,
        "limit":       request.args.get("limit", 10),
        "market":      request.args.get("market", "US"),
    }
    data = spotify_get("/recommendations", token, params)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  ARTISTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/artists/<artist_id>")
def get_artist(artist_id):
    token = get_client_credentials_token()
    data  = spotify_get(f"/artists/{artist_id}", token)
    return api_response(data)


@app.route("/artists/<artist_id>/top-tracks")
def get_artist_top_tracks(artist_id):
    token  = get_client_credentials_token()
    market = request.args.get("market", "US")
    data   = spotify_get(f"/artists/{artist_id}/top-tracks", token,
                         {"market": market})
    return api_response(data)


@app.route("/artists/<artist_id>/albums")
def get_artist_albums(artist_id):
    token  = get_client_credentials_token()
    params = {
        "include_groups": request.args.get("include_groups", "album,single"),
        "market":         request.args.get("market", "US"),
        "limit":          request.args.get("limit", 20),
    }
    data = spotify_get(f"/artists/{artist_id}/albums", token, params)
    return api_response(data)


@app.route("/artists/<artist_id>/related-artists")
def get_related_artists(artist_id):
    token = get_client_credentials_token()
    data  = spotify_get(f"/artists/{artist_id}/related-artists", token)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  ALBUMS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/albums/<album_id>")
def get_album(album_id):
    token  = get_client_credentials_token()
    market = request.args.get("market", "US")
    data   = spotify_get(f"/albums/{album_id}", token, {"market": market})
    return api_response(data)


@app.route("/albums/<album_id>/tracks")
def get_album_tracks(album_id):
    token  = get_client_credentials_token()
    params = {
        "market": request.args.get("market", "US"),
        "limit":  request.args.get("limit", 50),
        "offset": request.args.get("offset", 0),
    }
    data = spotify_get(f"/albums/{album_id}/tracks", token, params)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYLISTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/me/playlists")
@require_user_token
def get_my_playlists():
    params = {
        "limit":  request.args.get("limit", 20),
        "offset": request.args.get("offset", 0),
    }
    data = spotify_get("/me/playlists", request.user_token, params)
    return api_response(data)


@app.route("/playlists/<playlist_id>")
def get_playlist(playlist_id):
    token  = get_client_credentials_token()
    params = {"market": request.args.get("market", "US")}
    data   = spotify_get(f"/playlists/{playlist_id}", token, params)
    return api_response(data)


@app.route("/playlists/<playlist_id>/tracks")
def get_playlist_tracks(playlist_id):
    token  = get_client_credentials_token()
    params = {
        "market": request.args.get("market", "US"),
        "limit":  request.args.get("limit", 50),
        "offset": request.args.get("offset", 0),
    }
    data = spotify_get(f"/playlists/{playlist_id}/tracks", token, params)
    return api_response(data)


@app.route("/playlists", methods=["POST"])
@require_user_token
def create_playlist():
    """Create a new playlist for the current user."""
    body = request.get_json() or {}
    user_data = spotify_get("/me", request.user_token)
    user_id   = user_data["id"]
    payload   = {
        "name":        body.get("name", "My Flask Playlist"),
        "description": body.get("description", "Created via Spotify Flask API"),
        "public":      body.get("public", True),
    }
    data = spotify_post(f"/users/{user_id}/playlists",
                        request.user_token, payload)
    return api_response(data, 201)


@app.route("/playlists/<playlist_id>/tracks", methods=["POST"])
@require_user_token
def add_tracks_to_playlist(playlist_id):
    """Add tracks to a playlist. Body: { uris: ['spotify:track:...'] }"""
    body = request.get_json() or {}
    uris = body.get("uris", [])
    if not uris:
        return api_error("'uris' list is required")
    data = spotify_post(f"/playlists/{playlist_id}/tracks",
                        request.user_token, {"uris": uris})
    return api_response(data)


@app.route("/playlists/<playlist_id>/tracks", methods=["DELETE"])
@require_user_token
def remove_tracks_from_playlist(playlist_id):
    """Remove tracks. Body: { uris: ['spotify:track:...'] }"""
    body  = request.get_json() or {}
    uris  = body.get("uris", [])
    if not uris:
        return api_error("'uris' list is required")
    tracks = [{"uri": u} for u in uris]
    data   = spotify_delete(f"/playlists/{playlist_id}/tracks",
                            request.user_token, {"tracks": tracks})
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  LIBRARY (SAVED ITEMS)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/me/tracks")
@require_user_token
def get_saved_tracks():
    params = {
        "limit":  request.args.get("limit", 20),
        "offset": request.args.get("offset", 0),
        "market": request.args.get("market", "US"),
    }
    data = spotify_get("/me/tracks", request.user_token, params)
    return api_response(data)


@app.route("/me/tracks", methods=["PUT"])
@require_user_token
def save_tracks():
    """Body: { ids: ['trackId1', 'trackId2'] }"""
    body = request.get_json() or {}
    ids  = body.get("ids", [])
    if not ids:
        return api_error("'ids' list required")
    spotify_put("/me/tracks", request.user_token, {"ids": ids})
    return api_response({"message": f"Saved {len(ids)} track(s)"})


@app.route("/me/tracks", methods=["DELETE"])
@require_user_token
def remove_saved_tracks():
    body = request.get_json() or {}
    ids  = body.get("ids", [])
    if not ids:
        return api_error("'ids' list required")
    spotify_delete("/me/tracks", request.user_token, {"ids": ids})
    return api_response({"message": f"Removed {len(ids)} track(s)"})


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER (Premium required for full control; read endpoints work on free)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/me/player")
@require_user_token
def get_player_state():
    """Get current playback state."""
    data = spotify_get("/me/player", request.user_token,
                       {"market": request.args.get("market", "US")})
    return api_response(data)


@app.route("/me/player/currently-playing")
@require_user_token
def currently_playing():
    data = spotify_get("/me/player/currently-playing", request.user_token,
                       {"market": request.args.get("market", "US")})
    return api_response(data)


@app.route("/me/player/play", methods=["PUT"])
@require_user_token
def player_play():
    """
    Start/resume playback (Premium).
    Optional body: { context_uri, uris, offset, position_ms }
    """
    body = request.get_json() or {}
    spotify_put("/me/player/play", request.user_token, body)
    return api_response({"message": "Playback started"})


@app.route("/me/player/pause", methods=["PUT"])
@require_user_token
def player_pause():
    spotify_put("/me/player/pause", request.user_token)
    return api_response({"message": "Playback paused"})


@app.route("/me/player/next", methods=["POST"])
@require_user_token
def player_next():
    spotify_post("/me/player/next", request.user_token)
    return api_response({"message": "Skipped to next track"})


@app.route("/me/player/previous", methods=["POST"])
@require_user_token
def player_previous():
    spotify_post("/me/player/previous", request.user_token)
    return api_response({"message": "Went to previous track"})


@app.route("/me/player/volume", methods=["PUT"])
@require_user_token
def set_volume():
    vol = request.args.get("volume_percent")
    if vol is None:
        return api_error("'volume_percent' query param required (0-100)")
    spotify_put("/me/player/volume", request.user_token,
                {"volume_percent": int(vol)})
    return api_response({"message": f"Volume set to {vol}%"})


@app.route("/me/player/shuffle", methods=["PUT"])
@require_user_token
def set_shuffle():
    state = request.args.get("state", "false").lower() == "true"
    spotify_put(f"/me/player/shuffle?state={str(state).lower()}",
                request.user_token)
    return api_response({"message": f"Shuffle {'on' if state else 'off'}"})


# ══════════════════════════════════════════════════════════════════════════════
#  BROWSE / FEATURED
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/browse/new-releases")
def new_releases():
    token  = get_client_credentials_token()
    params = {
        "country": request.args.get("country", "US"),
        "limit":   request.args.get("limit", 20),
        "offset":  request.args.get("offset", 0),
    }
    data = spotify_get("/browse/new-releases", token, params)
    return api_response(data)


@app.route("/browse/featured-playlists")
def featured_playlists():
    token  = get_client_credentials_token()
    params = {
        "country": request.args.get("country", "US"),
        "limit":   request.args.get("limit", 10),
    }
    data = spotify_get("/browse/featured-playlists", token, params)
    return api_response(data)


@app.route("/browse/categories")
def browse_categories():
    token  = get_client_credentials_token()
    params = {
        "country": request.args.get("country", "US"),
        "limit":   request.args.get("limit", 20),
    }
    data = spotify_get("/browse/categories", token, params)
    return api_response(data)


@app.route("/browse/categories/<category_id>/playlists")
def category_playlists(category_id):
    token  = get_client_credentials_token()
    params = {
        "country": request.args.get("country", "US"),
        "limit":   request.args.get("limit", 20),
    }
    data = spotify_get(f"/browse/categories/{category_id}/playlists",
                       token, params)
    return api_response(data)


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    return api_response({
        "status":  "running",
        "service": "Spotify Flask Backend",
        "version": "1.0.0",
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return api_error("Endpoint not found", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return api_error("Method not allowed", 405)


@app.errorhandler(requests.exceptions.HTTPError)
def spotify_http_error(e):
    status = e.response.status_code if e.response else 500
    try:
        msg = e.response.json().get("error", {}).get("message", str(e))
    except Exception:
        msg = str(e)
    return api_error(f"Spotify API error: {msg}", status)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
