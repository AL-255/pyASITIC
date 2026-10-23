"""Small JSON CLI: python -m reasitic request.json [--gds output.gds]."""
import argparse
import json
from pathlib import Path
from .bridge import handle
import base64


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request",type=Path)
    parser.add_argument("--gds",type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    if args.gds:
        request["action"] = "gds"
    try:
        result = handle(request)
        if args.gds:
            args.gds.write_bytes(base64.b64decode(result["base64"]))
            print(args.gds)
        else:
            print(json.dumps(result,indent=2,allow_nan=False))
    except (ValueError,KeyError,TypeError) as error:
        parser.exit(1,f"{error}\n")


if __name__ == "__main__":
    main()
