"""Environment loading and safe setup diagnostics without importing the server."""

import argparse
import json
from pathlib import Path
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(
        description="Google Ads AI Command Center: read-only advertising intelligence"
    )
    parser.add_argument(
        "command", nargs="?", choices=["serve", "doctor"], default="serve"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Local dotenv file; existing environment variables take precedence",
    )
    args = parser.parse_args()
    load_dotenv(Path(args.env_file), override=False)
    if args.command == "doctor":
        from ads_mcp.security import validate_configuration

        validate_configuration()
        from ads_mcp.tools.intelligence import onboarding_check

        print(json.dumps(onboarding_check(), indent=2))
    else:
        from ads_mcp.server import run_server

        run_server()


if __name__ == "__main__":
    main()
