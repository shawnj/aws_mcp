#!/usr/bin/env python3
"""Entry point for the AWS Cost Explorer MCP Server."""

import asyncio
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server

from aws_mcp.server import AWSCostExplorerMCPServer

# Load environment variables from .env file
load_dotenv()


async def main():
    """Main entry point for the server."""
    mcp_server = AWSCostExplorerMCPServer()
    
    async with stdio_server() as (read, write):
        await mcp_server.server.run(read, write, mcp_server.server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
