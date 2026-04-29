import pathlib

from mythic_container.C2ProfileBase import C2Profile, C2ProfileParameter, ParameterType
import mythic_container.mythic_service


class chesscom(C2Profile):
    name = "chesscom"
    description = (
        "Canal C2 via Chess.com : collections de la bibliothèque et positions FEN "
        "(encodage Base5 PNBRQ, compatible avec la logique CheckmateC2 / Havoc). "
        "Nécessite cookie de session et jetons _token pour add-from-pgn / remove-items."
    )
    author = "@bbuddha"
    is_p2p_c2 = False
    is_server_routed = True
    mythic_encrypts = True

    server_folder_path = pathlib.Path(__file__).parent.parent.parent / "c2_code"
    server_binary_path = server_folder_path / "main.py"

    parameters = [
        C2ProfileParameter(
            name="chess_com_cookie",
            description=(
                "Cookie de session www.chess.com (copié depuis le navigateur), "
                "pour les requêtes authentifiées vers callback/library."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="upload_token",
            description='Jeton CSRF "_token" pour POST .../actions/add-from-pgn',
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="clear_token",
            description='Jeton CSRF "_token" pour POST .../actions/remove-items',
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="agent_to_server_collection",
            description=(
                "UUID de la collection où l’agent dépose les messages (le serveur lit ici). "
                "Doit correspondre à « partner » / collection distante selon votre schéma CheckmateC2."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="server_to_agent_collection",
            description=(
                "UUID de la collection où le serveur dépose les réponses Mythic "
                "(l’agent lit ici)."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="callback_interval",
            description="Pause entre cycles de traitement (secondes)",
            default_value="10",
            parameter_type=ParameterType.Number,
            required=False,
        ),
        C2ProfileParameter(
            name="callback_jitter",
            description="Jitter en pourcentage sur l’intervalle de pause (0–50)",
            default_value="10",
            parameter_type=ParameterType.Number,
            required=False,
        ),
        C2ProfileParameter(
            name="skip_item_ids",
            description=(
                "IDs d’items Chess.com à ignorer (UUIDs séparés par des virgules). "
                "Par défaut, les placeholders CheckmateC2 sont déjà exclus."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=False,
        ),
        C2ProfileParameter(
            name="library_referer",
            description=(
                "URL complète de la page « collection » dans le navigateur (barre d’adresse), "
                "ex. https://www.chess.com/analysis/collection/nom-slug/games — doit être la même "
                "que le Referer de la requête réseau vers …/collections/…/items qui répond 200. "
                "Si vide, Referer par défaut = /analysis (souvent Insufficient permissions)."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=False,
        ),
    ]


mythic_container.mythic_service.start_and_run_forever()
