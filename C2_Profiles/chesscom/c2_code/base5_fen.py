"""
Base5 encoding (chess piece alphabet PNBRQ) + FEN projection, compatible with
CheckmateC2 / Havoc (OfficialScragg/CheckmateC2).
"""

from __future__ import annotations


class Base5Chess:
    """Port of the CheckmateC2 encoding scheme for interoperability with agents using the same logic."""

    ALPHABET = "PNBRQ"

    @staticmethod
    def encode(data: bytes) -> str:
        if not data:
            return ""
        num = int.from_bytes(data, "big")
        if num == 0:
            return "P"
        encoded: list[str] = []
        while num > 0:
            encoded.append(Base5Chess.ALPHABET[num % 5])
            num //= 5
        return "".join(reversed(encoded))

    @staticmethod
    def decode(encoded: str) -> bytes:
        if not encoded:
            return b""
        num = 0
        for char in encoded:
            num = num * 5 + Base5Chess.ALPHABET.index(char)
        byte_len = (num.bit_length() + 7) // 8
        return num.to_bytes(byte_len, "big")

    @staticmethod
    def string_to_fen(encoded: str) -> list[str]:
        chunks = [encoded[i : i + 8] for i in range(0, len(encoded), 8)]
        games: list[str] = []
        fen_template = ["7k", "8", "8", "8", "8", "8", "8", "7K", " w - - 0 1"]
        fen_data: list[str] = []
        i = 0
        for c in chunks:
            if len(fen_data) < 6:
                if i <= 2:
                    fen_data.append(c.lower())
                else:
                    fen_data.append(c.upper())
            else:
                for idx, f in enumerate(fen_data):
                    if len(f) < 8:
                        fen_data[idx] = f + str(8 - len(f))
                games.append(
                    [fen_template[0]] + fen_data + [fen_template[7], fen_template[8]]
                )
                fen_data = []
                if c != "":
                    fen_data.append(c.lower())
                    i = 1
                    continue
                break
            i += 1

        if fen_data:
            for idx, f in enumerate(fen_data):
                if len(f) < 8:
                    fen_data[idx] = f + str(8 - len(f))
            games.append(
                [fen_template[0]]
                + fen_data
                + (6 - len(fen_data)) * ["8"]
                + [fen_template[7], fen_template[8]]
            )
        res: list[str] = []
        for g in games:
            res.append(str("/".join(g[0:8]) + str(g[8])))
        return res

    @staticmethod
    def fen_to_string(fen: str) -> str:
        data = fen.split("/")
        return "".join(data[1:7])


MARKER_FEN = "7k/8/8/8/8/8/8/7K w - - 0 1"
