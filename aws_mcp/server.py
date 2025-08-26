"""MCP server implementation for AWS Cost Explorer."""

import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from .constants import DIMENSIONS_ALLOWED, METRICS_ALLOWED
from .cost_explorer import AWSCostExplorerClient, CostExplorerService, AWSCostExplorerError


class AWSCostExplorerMCPServer:
    """MCP Server for AWS Cost Explorer."""
    
    def __init__(self, name: str = "aws-cost-explorer"):
        """Initialize the MCP server."""
        self.server = Server(name)
        self.setup_handlers()
    
    def setup_handlers(self) -> None:
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="get_cost_and_usage",
                    description="Get AWS costs for a time period, optionally grouped by dimensions. End date is exclusive (YYYY-MM-DD).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "Start date (YYYY-MM-DD, inclusive)"},
                            "end": {"type": "string", "description": "End date (YYYY-MM-DD, exclusive)"},
                            "granularity": {"type": "string", "enum": ["DAILY", "MONTHLY"], "default": "MONTHLY"},
                            "group_by": {
                                "type": "array",
                                "items": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                                "description": "Dimensions to group by (max 2 per CE API).",
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string", "enum": METRICS_ALLOWED},
                                "default": ["UnblendedCost"],
                            },
                            "filter_config": {
                                "type": "object",
                                "properties": {
                                    "dimension": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                                    "values": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["dimension", "values"],
                            },
                            "next_page_token": {"type": "string"},
                            "profile": {"type": "string", "description": "AWS profile name from ~/.aws/config"},
                        },
                    },
                ),
                Tool(
                    name="get_dimension_values",
                    description="Get available values for a specific Cost Explorer dimension.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string", "enum": DIMENSIONS_ALLOWED},
                            "time_period_start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "time_period_end": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "search_string": {"type": "string"},
                            "max_results": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50},
                            "next_page_token": {"type": "string"},
                            "profile": {"type": "string", "description": "AWS profile name from ~/.aws/config"},
                        },
                        "required": ["dimension"],
                    },
                ),
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                if name == "get_cost_and_usage":
                    result = await self._get_cost_and_usage(**arguments)
                elif name == "get_dimension_values":
                    result = await self._get_dimension_values(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=result)]
                
            except (AWSCostExplorerError, ValueError) as e:
                error_response = {"error": str(e)}
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def _get_cost_and_usage(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        granularity: str = "MONTHLY",
        group_by: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        next_page_token: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> str:
        """Get cost and usage data."""
        client = AWSCostExplorerClient(profile)
        service = CostExplorerService(client)
        
        result = await service.get_cost_and_usage(
            start=start,
            end=end,
            granularity=granularity,
            group_by=group_by,
            metrics=metrics,
            filter_config=filter_config,
            next_page_token=next_page_token,
        )
        
        return json.dumps(result, separators=(",", ":"), default=str, indent=2)
    
    async def _get_dimension_values(
        self,
        dimension: str,
        time_period_start: Optional[str] = None,
        time_period_end: Optional[str] = None,
        search_string: Optional[str] = None,
        max_results: int = 50,
        next_page_token: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> str:
        """Get dimension values."""
        client = AWSCostExplorerClient(profile)
        service = CostExplorerService(client)
        
        result = await service.get_dimension_values(
            dimension=dimension,
            time_period_start=time_period_start,
            time_period_end=time_period_end,
            search_string=search_string,
            max_results=max_results,
            next_page_token=next_page_token,
        )
        
        return json.dumps(result, separators=(",", ":"), default=str, indent=2)
