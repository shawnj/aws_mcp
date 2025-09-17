#!/usr/bin/env python3
"""Entry point for the AWS Cost Explorer MCP Server."""

import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server

from aws_mcp.server import AWSCostExplorerMCPServer
from aws_mcp.cost_explorer import AWSCostExplorerError

# Load environment variables from .env file
load_dotenv()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AWS Cost Explorer MCP Server")
    parser.add_argument(
        "--profile", 
        type=str, 
        help="AWS profile name to use (overrides AWS_PROFILE environment variable)"
    )
    return parser.parse_args()


async def async_main():
    """Async main entry point for the server."""
    args = parse_args()
    
    # Determine which profile to use
    profile = args.profile or os.getenv("AWS_PROFILE")
    
    try:
        mcp_server = AWSCostExplorerMCPServer(profile=profile)
        
        async with stdio_server() as (read, write):
            await mcp_server.server.run(read, write, mcp_server.server.create_initialization_options())
    except AWSCostExplorerError as e:
        print(f"Failed to start AWS Cost Explorer MCP Server: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Synchronous entry point for console script."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
