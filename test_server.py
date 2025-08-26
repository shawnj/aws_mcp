#!/usr/bin/env python3
"""Test script for the AWS Cost Explorer MCP server."""

import asyncio
import json
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def test_server():
    """Test the MCP server functionality."""
    
    # Create server parameters pointing to our server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        cwd="/Users/admin/repos/local/aws_mcp"
    )
    
    try:
        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                print("Initializing connection...")
                result = await session.initialize()
                print(f"Initialization result: {result}")
                
                # List available tools
                print("\nListing tools...")
                tools = await session.list_tools()
                print(f"Available tools: {[tool.name for tool in tools.tools]}")
                
                # Test get_cost_and_usage tool
                print("\nTesting get_cost_and_usage tool...")
                try:
                    cost_result = await session.call_tool(
                        "get_cost_and_usage", 
                        {
                            "start": "2024-01-01",
                            "end": "2024-01-02",
                            "granularity": "DAILY",
                            "metrics": ["BlendedCost"]
                        }
                    )
                    print(f"Cost result: {cost_result}")
                except Exception as e:
                    print(f"Error calling tool: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_server())
