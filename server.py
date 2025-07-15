import os
from dotenv import load_dotenv
from typing import Any
import logging

import httpx
from secedgar.core.rest import (
    get_submissions,
    get_company_concepts,
    get_company_facts,
    get_xbrl_frames,
)
from fastmcp import FastMCP

load_dotenv()

sec_edgar_user_agent = os.getenv("SEC_EDGAR_USER_AGENT")
if not sec_edgar_user_agent:
    sec_edgar_user_agent = "Manuel Mateo (manmat03@protiviti.com)"

# Initialize MCP
mcp = FastMCP("Multi-MCP", port=3000)


@mcp.tool("get_submissions")
def get_submissions_tool(
    lookups: str | list[str],
    user_agent: str = sec_edgar_user_agent,
    recent: bool = True,
) -> dict[str, dict] | str:
    """
    Retrieve submission records for specified companies using the SEC EDGAR REST API.

    Parameters:
        lookups (Union[str, List[str]]): Ticker(s) or CIK(s) of the companies.
        user_agent (str): User agent string required by the SEC.
        recent (bool): If True, retrieves at least one year of filings or the last 1000 filings. Defaults to True.

    Returns:
        Dict[str, dict]: A dictionary mapping each lookup to its submission data.
        str: If an error occurs, the function will return a string.
    """
    try:
        response = get_submissions(lookups=lookups, user_agent=user_agent, recent=recent)
        logger.info(response)
        return response
    except Exception as e:
        logger.error(e)
        return "unable to get submissions"


@mcp.tool("get_company_concepts")
def get_company_concepts_tool(
    lookups: str | list[str],
    concept_name: str,
    user_agent: str = sec_edgar_user_agent,
) -> dict[str, dict] | str:
    """
    Retrieve data for a specific financial concept for specified companies using the SEC EDGAR REST API.

    Parameters:
        lookups (Union[str, List[str]]): Ticker(s) or CIK(s) of the companies.
        concept_name (str): The financial concept to retrieve (e.g., "AccountsPayableCurrent").
        user_agent (str): User agent string required by the SEC.

    Returns:
        Dict[str, dict]: A dictionary mapping each lookup to its concept data.
        str: If an error occurs, the function will return a string.
    """
    try:
        response = get_company_concepts(
            lookups=lookups,
            concept_name=concept_name,
            user_agent=user_agent,
        )
        logger.info(response)
        return response
    except Exception as e:
        logger.error(e)
        return "unable to fetch concepts"


@mcp.tool("get_company_facts")
def get_company_facts_tool(lookups: str | list[str], user_agent: str = sec_edgar_user_agent) -> dict[str, dict] | str:
    """
    Retrieve all standardized financial facts for specified companies using the SEC EDGAR REST API.

    Parameters:
        lookups (Union[str, List[str]]): Ticker(s) or CIK(s) of the companies.
        user_agent (str): User agent string required by the SEC.

    Returns:
        Dict[str, dict]: A dictionary mapping each lookup to its company facts data.
        str: If an error occurs, the function will return a string.
    """
    try:
        response =  get_company_facts(lookups=lookups, user_agent=user_agent)
        logger.info(response)
        return response
    except Exception as e:
        logger.error(e)
        return "unable to get company facts"


@mcp.tool("get_xbrl_frames")
def get_xbrl_frames_tool(
    concept_name: str,
    year: int,
    quarter: int | None = None,
    currency: str = "USD",
    instantaneous: bool = False,
    user_agent: str = sec_edgar_user_agent,
) -> dict | str:
    """
    Retrieve XBRL 'frames' data for a concept across companies for a specified time frame using the SEC EDGAR REST API.

    Parameters:
        concept_name (str): The financial concept to query (e.g., "Assets").
        year (int): The year for which to retrieve the data.
        quarter (Union[int, None]): The fiscal quarter (1-4) within the year. If None, data for the entire year is returned.
        currency (str): The reporting currency filter (default is "USD").
        instantaneous (bool): Whether to retrieve instantaneous values (True) or duration values (False) for the concept.
        user_agent (str): User agent string required by the SEC.

    Returns:
        dict: A dictionary containing the frame data for the specified concept and period.
        str: If an error occurs, the function will return a string.
    """
    try:
        response = get_xbrl_frames(
            user_agent=user_agent,
            concept_name=concept_name,
            year=year,
            quarter=quarter,
            currency=currency,
            instantaneous=instantaneous,
        )
        logger.info(response)
        return response
    except Exception as e:
        logger.error(e)
        return "unable to fetch xbrl info"

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("Starting FastMCP server")
        mcp.run(transport="http", host="0.0.0.0")
    except KeyboardInterrupt:
        logger.info("Quitting...")
        quit()