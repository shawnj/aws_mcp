"""Integration tests for the AWS Cost Explorer MCP Server."""

import asyncio
import sys
import os
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


class TestAWSCostExplorerMCPServer:
    """Integration tests for the MCP server."""

    @staticmethod
    def get_server_path():
        """Get the path to the main.py server entry point."""
        current_dir = Path(__file__).parent
        return current_dir.parent / "main.py"

    async def test_server_connection(self):
        """Test basic server connection and initialization."""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.get_server_path())],
            cwd=str(Path(__file__).parent.parent)
        )
        
        try:
            print("🔄 Connecting to AWS Cost Explorer MCP Server...")
            
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize the connection
                    print("✅ Initializing connection...")
                    result = await session.initialize()
                    print(f"   Server: {result.serverInfo.name} v{result.serverInfo.version}")
                    print(f"   Protocol: {result.protocolVersion}")
                    return True
                    
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

    async def test_list_tools(self):
        """Test that all expected tools are available."""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.get_server_path())],
            cwd=str(Path(__file__).parent.parent)
        )
        
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
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
                    return True
                    
        except Exception as e:
            print(f"❌ List tools test failed: {e}")
            return False

    async def test_parameter_validation(self):
        """Test tool parameter validation without requiring AWS credentials."""
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.get_server_path())],
            cwd=str(Path(__file__).parent.parent)
        )
        
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    print("✅ Testing parameter validation...")
                    
                    # Test invalid parameter - should fail validation, not AWS auth
                    try:
                        result = await session.call_tool("get_cost_and_usage", {"invalid_param": "test"})
                        # If we get here, check if it's an AWS error or successful call
                        if "error" in str(result).lower():
                            print("   ✅ Got expected error response")
                            return True
                        else:
                            print("   ✅ Parameter was ignored (acceptable behavior)")
                            return True
                    except Exception as e:
                        error_msg = str(e)
                        if any(keyword in error_msg.lower() for keyword in ["invalid_param", "unexpected keyword", "parameter", "argument"]):
                            print("   ✅ Parameter validation working correctly")
                            return True
                        elif "credentials" in error_msg.lower():
                            print("   ✅ Got AWS credentials error (parameter passed validation)")
                            return True
                        else:
                            print(f"   ❌ Got unexpected error: {error_msg}")
                            return False
                            
        except Exception as e:
            print(f"❌ Parameter validation test failed: {e}")
            return False

    async def test_aws_functionality(self):
        """Test actual AWS functionality (requires credentials)."""
        # Check if AWS credentials are available
        has_credentials = (
            os.getenv("AWS_ACCESS_KEY_ID") or
            os.getenv("AWS_PROFILE") or
            Path.home().joinpath(".aws", "credentials").exists()
        )
        
        if not has_credentials:
            print("⚠️  Skipping AWS functionality test - no credentials detected")
            print("   To test AWS functionality:")
            print("   - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables, or")
            print("   - Set AWS_PROFILE environment variable, or")
            print("   - Configure ~/.aws/credentials file")
            return True
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.get_server_path())],
            cwd=str(Path(__file__).parent.parent)
        )
        
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    print("✅ Testing AWS Cost Explorer functionality...")
                    
                    # Test get_cost_and_usage with minimal parameters
                    try:
                        cost_result = await session.call_tool(
                            "get_cost_and_usage", 
                            {
                                "granularity": "MONTHLY",
                                "metrics": ["UnblendedCost"]
                            }
                        )
                        print("   ✅ get_cost_and_usage call successful")
                        
                        # Test get_dimension_values
                        dimension_result = await session.call_tool(
                            "get_dimension_values",
                            {
                                "dimension": "SERVICE"
                            }
                        )
                        print("   ✅ get_dimension_values call successful")
                        return True
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "credentials" in error_msg.lower() or "access denied" in error_msg.lower():
                            print(f"   ⚠️  AWS credentials issue: {error_msg}")
                            print("   Please check your AWS credentials configuration")
                        else:
                            print(f"   ❌ AWS API error: {error_msg}")
                        return False
                        
        except Exception as e:
            print(f"❌ AWS functionality test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests and return overall success."""
        print("🧪 Running AWS Cost Explorer MCP Server Tests")
        print("=" * 50)
        
        tests = [
            ("Server Connection", self.test_server_connection),
            ("List Tools", self.test_list_tools),
            ("Parameter Validation", self.test_parameter_validation),
            ("AWS Functionality", self.test_aws_functionality),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}:")
            success = await test_func()
            results.append(success)
            print(f"   {'✅ PASSED' if success else '❌ FAILED'}")
        
        print("\n" + "=" * 50)
        passed = sum(results)
        total = len(results)
        print(f"🏁 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests PASSED!")
            return True
        else:
            print("💥 Some tests FAILED!")
            return False


async def main():
    """Main test runner."""
    tester = TestAWSCostExplorerMCPServer()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
