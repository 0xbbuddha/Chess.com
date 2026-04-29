import pathlib

from mythic_container.C2ProfileBase import C2Profile, C2ProfileParameter, ParameterType
import mythic_container.mythic_service


class chesscom(C2Profile):
    name = "chesscom"
    description = (
        "C2 channel via Chess.com library collections and FEN positions "
        "(Base5 PNBRQ encoding, compatible with CheckmateC2 / Havoc logic). "
        "Requires a session cookie and _token values for add-from-pgn / remove-items."
    )
    author = "@0xbbuddha"
    is_p2p_c2 = False
    is_server_routed = True
    mythic_encrypts = True

    server_folder_path = pathlib.Path(__file__).parent.parent.parent / "c2_code"
    server_binary_path = server_folder_path / "main.py"

    parameters = [
        C2ProfileParameter(
            name="chess_com_cookie",
            description="Full Cookie header from www.chess.com (copy from browser DevTools).",
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="upload_token",
            description=’CSRF "_token" for POST .../actions/add-from-pgn’,
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="clear_token",
            description=’CSRF "_token" for POST .../actions/remove-items’,
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="agent_to_server_collection",
            description="UUID of the collection where the agent writes messages (server reads here).",
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="server_to_agent_collection",
            description="UUID of the collection where the server writes Mythic responses (agent reads here).",
            default_value="",
            parameter_type=ParameterType.String,
            required=True,
        ),
        C2ProfileParameter(
            name="callback_interval",
            description="Seconds between poll cycles.",
            default_value="10",
            parameter_type=ParameterType.Number,
            required=False,
        ),
        C2ProfileParameter(
            name="callback_jitter",
            description="Jitter percentage on the poll interval (0-50).",
            default_value="10",
            parameter_type=ParameterType.Number,
            required=False,
        ),
        C2ProfileParameter(
            name="skip_item_ids",
            description=(
                "Comma-separated Chess.com item UUIDs to ignore. "
                "CheckmateC2 placeholder IDs are already excluded by default."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=False,
        ),
        C2ProfileParameter(
            name="library_referer",
            description=(
                "Full URL of the collection page from the browser address bar, "
                "e.g. https://www.chess.com/analysis/collection/<slug>/games. "
                "Must match the Referer header of the working network request to .../collections/.../items. "
                "If empty, defaults to /analysis which often causes Insufficient permissions."
            ),
            default_value="",
            parameter_type=ParameterType.String,
            required=False,
        ),
    ]


mythic_container.mythic_service.start_and_run_forever()
