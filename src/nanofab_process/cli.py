"""Command-line entry point."""

import argparse

from .config import load_config
from .gds import export_gds


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate a GDSII mask from one YAML file")
    parser.add_argument("config", nargs="?", default="mask.yaml")
    parser.add_argument("-o", "--output", default="output.gds")
    args = parser.parse_args(argv)
    try:
        output = export_gds(load_config(args.config), args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
