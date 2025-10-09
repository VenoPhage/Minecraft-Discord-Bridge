from typing import Literal


def sendMessage(
    message: str, method: Literal["pterodactyl", "rcon"] = "pterodactyl"
) -> bool:
    """
    Sends str to Minecraft
    """
    match method:
        case "pterodactyl":
            pass
        case "rcon":
            pass
    return True
