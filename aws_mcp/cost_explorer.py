"""AWS Cost Explorer client and service layer."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from .constants import AWS_REGION, MAX_RETRIES, USER_AGENT, DIMENSIONS_ALLOWED, METRICS_ALLOWED
from .utils import get_default_date_range, get_default_lookback_range, validate_date


class AWSCostExplorerError(Exception):
    """Custom exception for AWS Cost Explorer errors."""
    pass


class AWSCostExplorerClient:
    """AWS Cost Explorer client wrapper."""
    
    def __init__(self, profile: Optional[str] = None):
        """Initialize the AWS Cost Explorer client.
        
        Args:
            profile: AWS profile name from ~/.aws/config
            
        Raises:
            AWSCostExplorerError: If AWS credentials are not found
        """
        self.profile = profile
        self._client = None
    
    @property
    def client(self) -> boto3.client:
        """Get or create the Cost Explorer client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> boto3.client:
        """Create AWS Cost Explorer client with optional profile."""
        try:
            session_kwargs = {}
            if self.profile:
                session_kwargs["profile_name"] = self.profile
            
            session = boto3.Session(**session_kwargs)
            
            # Cost Explorer is a global service; us-east-1 is canonical
            return session.client(
                "ce",
                region_name=AWS_REGION,
                config=Config(
                    retries={"max_attempts": MAX_RETRIES, "mode": "standard"},
                    user_agent_extra=USER_AGENT
                ),
            )
        except NoCredentialsError:
            raise AWSCostExplorerError(
                "AWS credentials not found. Please configure AWS credentials or specify a profile."
            )


class CostExplorerService:
    """Service layer for AWS Cost Explorer operations."""
    
    def __init__(self, client: AWSCostExplorerClient):
        """Initialize the service with a client."""
        self.client = client
    
    async def get_cost_and_usage(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        granularity: str = "MONTHLY",
        group_by: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        filter_config: Optional[Dict[str, Any]] = None,
        next_page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get AWS costs for a time period, optionally grouped by dimensions.
        
        Args:
            start: Start date (YYYY-MM-DD, inclusive)
            end: End date (YYYY-MM-DD, exclusive)
            granularity: Time granularity - DAILY or MONTHLY
            group_by: List of dimensions to group by (max 2 per AWS API)
            metrics: List of cost metrics to retrieve
            filter_config: Filter configuration with dimension and values
            next_page_token: Token for pagination
        
        Returns:
            Dictionary with cost data
            
        Raises:
            AWSCostExplorerError: If API call fails or parameters are invalid
        """
        # Validate and set defaults
        metrics = metrics or ["UnblendedCost"]
        
        self._validate_granularity(granularity)
        self._validate_group_by(group_by)
        self._validate_metrics(metrics)
        
        # Set dates
        if not start or not end:
            start, end = get_default_date_range(granularity)
        else:
            start = validate_date(start)
            end = validate_date(end)
        
        # Build request parameters
        request_params = self._build_cost_request(
            start, end, granularity, group_by, metrics, filter_config, next_page_token
        )
        
        # Execute API call
        def _api_call():
            try:
                response = self.client.client.get_cost_and_usage(**request_params)
                return self._format_cost_response(response, start, end, granularity, metrics, group_by)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                raise AWSCostExplorerError(f"Cost Explorer API error ({error_code}): {error_message}")
        
        return await asyncio.to_thread(_api_call)
    
    async def get_dimension_values(
        self,
        dimension: str,
        time_period_start: Optional[str] = None,
        time_period_end: Optional[str] = None,
        search_string: Optional[str] = None,
        max_results: int = 50,
        next_page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get available values for a specific Cost Explorer dimension.
        
        Args:
            dimension: The dimension to get values for
            time_period_start: Start date for dimension search (YYYY-MM-DD)
            time_period_end: End date for dimension search (YYYY-MM-DD)
            search_string: Search string to filter dimension values
            max_results: Maximum number of results (1-1000)
            next_page_token: Token for pagination
        
        Returns:
            Dictionary with dimension values
            
        Raises:
            AWSCostExplorerError: If API call fails or parameters are invalid
        """
        # Validate inputs
        self._validate_dimension(dimension)
        self._validate_max_results(max_results)
        
        # Set default time period
        if not time_period_start or not time_period_end:
            time_period_start, time_period_end = get_default_lookback_range(30)
        else:
            time_period_start = validate_date(time_period_start)
            time_period_end = validate_date(time_period_end)
        
        # Build request parameters
        request_params = self._build_dimension_request(
            dimension, time_period_start, time_period_end, search_string, max_results, next_page_token
        )
        
        # Execute API call
        def _api_call():
            try:
                response = self.client.client.get_dimension_values(**request_params)
                return self._format_dimension_response(response, dimension, time_period_start, time_period_end)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                raise AWSCostExplorerError(f"Cost Explorer API error ({error_code}): {error_message}")
        
        return await asyncio.to_thread(_api_call)
    
    def _validate_granularity(self, granularity: str) -> None:
        """Validate granularity parameter."""
        if granularity not in ["DAILY", "MONTHLY"]:
            raise AWSCostExplorerError("granularity must be 'DAILY' or 'MONTHLY'")
    
    def _validate_group_by(self, group_by: Optional[List[str]]) -> None:
        """Validate group_by parameter."""
        if not group_by:
            return
            
        invalid_dimensions = [d for d in group_by if d not in DIMENSIONS_ALLOWED]
        if invalid_dimensions:
            raise AWSCostExplorerError(f"Invalid group_by dimensions: {invalid_dimensions}")
        
        if len(group_by) > 2:
            raise AWSCostExplorerError("Maximum 2 group_by dimensions allowed")
    
    def _validate_metrics(self, metrics: List[str]) -> None:
        """Validate metrics parameter."""
        invalid_metrics = [m for m in metrics if m not in METRICS_ALLOWED]
        if invalid_metrics:
            raise AWSCostExplorerError(f"Invalid metrics: {invalid_metrics}")
    
    def _validate_dimension(self, dimension: str) -> None:
        """Validate dimension parameter."""
        if dimension not in DIMENSIONS_ALLOWED:
            raise AWSCostExplorerError(f"Invalid dimension: {dimension}. Allowed: {DIMENSIONS_ALLOWED}")
    
    def _validate_max_results(self, max_results: int) -> None:
        """Validate max_results parameter."""
        if not (1 <= max_results <= 1000):
            raise AWSCostExplorerError("max_results must be between 1 and 1000")
    
    def _build_cost_request(
        self,
        start: str,
        end: str,
        granularity: str,
        group_by: Optional[List[str]],
        metrics: List[str],
        filter_config: Optional[Dict[str, Any]],
        next_page_token: Optional[str],
    ) -> Dict[str, Any]:
        """Build request parameters for get_cost_and_usage API call."""
        request_params = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": granularity,
            "Metrics": metrics,
        }
        
        if group_by:
            request_params["GroupBy"] = [
                {"Type": "DIMENSION", "Key": dimension}
                for dimension in group_by[:2]  # AWS allows max 2
            ]
        
        if filter_config:
            request_params["Filter"] = {
                "Dimensions": {
                    "Key": filter_config["dimension"],
                    "Values": filter_config.get("values", []),
                    "MatchOptions": ["EQUALS"],
                }
            }
        
        if next_page_token:
            request_params["NextPageToken"] = next_page_token
        
        return request_params
    
    def _build_dimension_request(
        self,
        dimension: str,
        time_period_start: str,
        time_period_end: str,
        search_string: Optional[str],
        max_results: int,
        next_page_token: Optional[str],
    ) -> Dict[str, Any]:
        """Build request parameters for get_dimension_values API call."""
        request_params = {
            "Dimension": dimension,
            "TimePeriod": {
                "Start": time_period_start,
                "End": time_period_end
            },
            "MaxResults": max_results,
        }
        
        if search_string:
            request_params["SearchString"] = search_string
        
        if next_page_token:
            request_params["NextPageToken"] = next_page_token
        
        return request_params
    
    def _format_cost_response(
        self,
        response: Dict[str, Any],
        start: str,
        end: str,
        granularity: str,
        metrics: List[str],
        group_by: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Format the cost and usage API response."""
        return {
            "time_period": response.get("TimePeriod", {"start": start, "end": end}),
            "granularity": granularity,
            "metrics": metrics,
            "group_by": group_by or [],
            "results_by_time": response.get("ResultsByTime", []),
            "next_page_token": response.get("NextPageToken"),
            "total_results": len(response.get("ResultsByTime", [])),
        }
    
    def _format_dimension_response(
        self,
        response: Dict[str, Any],
        dimension: str,
        time_period_start: str,
        time_period_end: str,
    ) -> Dict[str, Any]:
        """Format the dimension values API response."""
        return {
            "dimension": dimension,
            "time_period": {
                "start": time_period_start,
                "end": time_period_end
            },
            "dimension_values": response.get("DimensionValues", []),
            "next_page_token": response.get("NextPageToken"),
            "total_size": response.get("TotalSize", 0),
            "return_size": response.get("ReturnSize", 0),
        }
