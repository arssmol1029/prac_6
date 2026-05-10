import shlex

from mood.common.models import InvalidCommand


def parse_sayall(arg: str) -> str:
    s = arg.strip()
    if not s:
        raise InvalidCommand
    try:
        parts = shlex.split(s, posix=True)
    except ValueError:
        raise InvalidCommand
    if len(parts) != 1:
        raise InvalidCommand
    return parts[0]
