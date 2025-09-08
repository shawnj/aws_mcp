"""MCP server implementation for AWS Cost Explorer."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from mcp.server import Server
from mcp.types import TextContent, Tool

from .constants import DIMENSIONS_ALLOWED, METRICS_ALLOWED
from .cost_explorer import AWSCostExplorerClient, CostExplorerService, AWSCostExplorerError

class AWSCostExplorerMCPServer:
    """MCP Server for AWS Cost Explorer."""

    def __init__(self, name: str = "aws-cost-explorer", profile: Optional[str] = None):
        """Initialize the MCP server."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.profile = profile or os.getenv("AWS_PROFILE")
        self.server = Server(name)
        self.logger.info(f"Initializing MCP server: {name}")
        
        # Validate AWS credentials before setting up handlers
        self._validate_aws_credentials()
        
        self.setup_handlers()

    def _validate_aws_credentials(self) -> None:
        """Validate AWS credentials and profile connectivity.
        
        Raises:
            AWSCostExplorerError: If AWS credentials or profile are invalid
        """
        try:
            self.logger.info("Validating AWS credentials and profile connectivity...")
            
            # Create a session with the specified profile
            session_kwargs = {}
            if self.profile:
                session_kwargs["profile_name"] = self.profile
                self.logger.info(f"Using AWS profile: {self.profile}")
            else:
                self.logger.info("Using default AWS credentials")
            
            session = boto3.Session(**session_kwargs)
            
            # Test if we can create a client and get credentials
            try:
                sts_client = session.client("sts")
                identity = sts_client.get_caller_identity()
                self.logger.info(f"AWS credentials validated. Account: {identity.get('Account')}, ARN: {identity.get('Arn')}")
            except ClientError as e:
                raise AWSCostExplorerError(f"Failed to validate AWS credentials: {e}")
            
            # Test if we can create Cost Explorer client
            try:
                ce_client = session.client("ce", region_name="us-east-1")
                # Test a simple API call to verify permissions
                ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': '2024-01-01',
                        'End': '2024-01-02'
                    },
                    Granularity='MONTHLY',
                    Metrics=['UnblendedCost']
                )
                self.logger.info("Cost Explorer API access validated successfully")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'AccessDenied':
                    raise AWSCostExplorerError(
                        f"Access denied to Cost Explorer API. Please ensure your AWS profile has the necessary permissions: {e}"
                    )
                elif error_code == 'UnauthorizedOperation':
                    raise AWSCostExplorerError(
                        f"Unauthorized to access Cost Explorer API. Check your AWS permissions: {e}"
                    )
                else:
                    self.logger.warning(f"Cost Explorer API test call failed (this may be normal): {e}")
                    
        except ProfileNotFound as e:
            raise AWSCostExplorerError(f"AWS profile '{self.profile}' not found: {e}")
        except NoCredentialsError as e:
            raise AWSCostExplorerError(f"AWS credentials not configured: {e}")
        except Exception as e:
            raise AWSCostExplorerError(f"Unexpected error validating AWS credentials: {e}")

    def setup_handlers(self) -> None:
        """Set up MCP server handlers."""
        self.logger.info("Setting up handlers for MCP server.")
        self.server.list_tools()(self.handle_list_tools)
        self.server.call_tool()(self.handle_call_tool)

    async def handle_list_tools(self) -> List[Tool]:
        """List available tools."""
        self.logger.info("Listing available tools.")
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

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls."""
        self.logger.info(f"Tool called: {name} with arguments: {arguments}")
        try:
            if name == "get_cost_and_usage":
                result = await self._get_cost_and_usage(**arguments)
            elif name == "get_dimension_values":
                result = await self._get_dimension_values(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            self.logger.info(f"Tool {name} executed successfully.")
            return [TextContent(type="text", text=result)]
        except (AWSCostExplorerError, ValueError) as e:
            self.logger.error(f"Error in tool {name}: {e}")
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
        self.logger.info(f"Getting cost and usage: start={start}, end={end}, granularity={granularity}, group_by={group_by}, metrics={metrics}, filter_config={filter_config}, next_page_token={next_page_token}, profile={profile}")
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
        self.logger.info("Cost and usage data retrieved successfully.")
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
        self.logger.info(f"Getting dimension values: dimension={dimension}, time_period_start={time_period_start}, time_period_end={time_period_end}, search_string={search_string}, max_results={max_results}, next_page_token={next_page_token}, profile={profile}")
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
        self.logger.info("Dimension values retrieved successfully.")
        return json.dumps(result, separators=(",", ":"), default=str, indent=2)
