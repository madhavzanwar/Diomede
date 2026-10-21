"""
Fill an Orthanc config template with the account from ORTHANC_USER / ORTHANC_PASSWORD.

The templates under config/orthanc/ hold ``${orthanc_user}`` and ``${orthanc_password}``
placeholders inside JSON strings. The values are escaped as JSON string contents, so a
password containing ``"``, ``\\``, ``/`` or ``&`` ends up in the config exactly as typed.

Standard library only: the cloud Orthanc containers run this file without the rest of src/.

Usage: python3 render_orthanc_config.py TEMPLATE OUTPUT
"""

from __future__ import annotations

import json
import os
import re
import sys

_PLACEHOLDER = re.compile(r"\$\{orthanc_(user|password)\}")


def _json_escape(value: str) -> str:
    """Return value as it must be written between the quotes of a JSON string."""
    return json.dumps(value)[1:-1]


def render(template: str, user: str, password: str) -> str:
    """Replace the placeholders in one pass, so a value is never itself substituted again."""
    values = {"user": user, "password": password}
    return _PLACEHOLDER.sub(lambda match: _json_escape(values[match.group(1)]), template)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    template_path, output_path = argv[1], argv[2]
    try:
        user, password = os.environ["ORTHANC_USER"], os.environ["ORTHANC_PASSWORD"]
    except KeyError as missing:
        print(f"{missing.args[0]} environment variable must be set", file=sys.stderr)
        return 1
    if not user or not password:
        print("ORTHANC_USER and ORTHANC_PASSWORD must not be empty", file=sys.stderr)
        return 1

    with open(template_path, encoding="utf-8") as template:
        rendered = render(template.read(), user, password)
    with open(output_path, "w", encoding="utf-8") as output:
        output.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
