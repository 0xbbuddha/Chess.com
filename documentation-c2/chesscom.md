# Profil C2 Chess.com (Mythic)

Ce profil repose sur les **collections** de la bibliothèque Chess.com et des imports **PGN/FEN**, comme le projet de référence Havoc [CheckmateC2](https://github.com/OfficialScragg/CheckmateC2).

## Flux

1. L’agent encode la charge utile (octets Mythic, typiquement une chaîne base64) en Base5 (`PNBRQ`), la découpe en FEN, préfixe avec une position marqueur, et envoie les jeux via `add-from-pgn` sur la collection **agent → serveur**.
2. Le conteneur C2 interroge cette collection jusqu’à voir le marqueur en tête, reconstitue les octets et les `POST` vers `http://mythic_server:17443/agent_message` avec l’en-tête `mythic: chesscom`.
3. Il vide la collection **serveur → agent**, encode la réponse Mythic de la même façon et la publie.
4. Il tente de vider la collection entrante pour éviter les rejeux.

## Paramètres

Identiques à l’interface Mythic : cookie, jetons d’upload/clear, deux UUID de collection. Les jetons expirent ; renouvelez-les si les requêtes chess.com commencent à échouer.
