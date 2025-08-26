#!/usr/bin/env python3
"""Basic test script that validates server functionality without requiring AWS credentials."""

import asyncio
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def test_server_basic():
    """Test basic server functionality without AWS credentials."""
    
    # Create server parameters pointing to our server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        cwd="/Users/admin/repos/local/aws_mcp"
    )
    
    try:
        print("🔄 Connecting to AWS Cost Explorer MCP Server...")
        
        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                print("✅ Initializing connection...")
                result = await session.initialize()
                print(f"   Server: {result.serverInfo.name} v{result.serverInfo.version}")
                print(f"   Protocol: {result.protocolVersion}")
                
                # List available tools
                print("✅ Listing tools...")
                tools = await session.list_tools()
                tool_names = [tool.name for tool in tools.tools]
                print(f"   Available tools: {tool_names}")
                
                # Validate expected tools are present
                expected_tools = ["get_cost_and_usage", "get_dimension_values"]
                missing_tools = set(expected_tools) - set(tool_names)
                if missing_tools:
                    print(f"❌ Missing expected tools: {missing_tools}")
                    return False
                
                print("✅ All expected tools found!")
                
                # Test tool schema validation (should work without credentials)
                print("✅ Testing tool parameter validation...")
                try:
                    # This should fail with parameter validation, not AWS credentials
                    await session.call_tool("get_cost_and_usage", {"invalid_param": "test"})
                except Exception as e:
                    error_msg = str(e)
                    if "invalid_param" in error_msg.lower() or "unexpected keyword" in error_msg.lower():
                        print("   Parameter validation working correctly")
                    else:
                        print(f"   Got different error: {error_msg}")
                
                print("\n🎉 Basic server functionality test PASSED!")
                print("💡 To test AWS functionality, configure credentials and run test_server.py")
                return True
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server_basic())
    sys.exit(0 if success else 1)
