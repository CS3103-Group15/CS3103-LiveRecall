#!/usr/bin/env python3
# Start point of python solution_server.py --port 8765
"""Required LiveRecall command-line entry point."""
import argparse
import asyncio

from server.application import run_server


def main() -> None:
    parser = argparse.ArgumentParser()
    # Choose connection port for server to listen for captions from and for clients to connect to
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--disable-backpressure", action="store_true",
                        help="Stage 5 delivery policy for before/after experiments")
    args = parser.parse_args()
    try:
        asyncio.run(run_server(args.port, not args.disable_backpressure))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
