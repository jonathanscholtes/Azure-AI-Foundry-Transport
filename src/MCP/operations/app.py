from mcp.server.fastmcp import FastMCP
import logging
from typing import List, Dict
from os import environ
from dotenv import load_dotenv

from cosmos_store import TruckingOperationsStore

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastMCP(
    name="Trucking Operations MCP Server",
    host="0.0.0.0",
    port=int(environ.get("MCP_PORT", 80)),
)

store = TruckingOperationsStore()

# ------------------------------------------------------------------
# MCP Tools
# ------------------------------------------------------------------



@app.tool()
async def get_load_context(load_id: str) -> List[Dict]:
    """
    Retrieve all operational records associated with a load.

    Use this tool when you need the full operational context for a load,
    including assignment and event history.

    Returns:
    - Load record
    - Dispatch record(s)
    - Exception record(s)

    Does NOT return:
    - Documents
    - Contracts or SLAs
    - Free-text explanations or reasoning
    """
    
    logger.info(f"[get_load_context] Requested load_id={load_id}")

    try:
        results = await store.get_load_context(load_id)
        logger.info(
            f"[get_load_context] Returned {len(results)} record(s) "
            f"for load_id={load_id}"
        )
        return results

    except Exception as exc:
        logger.error(
            "[get_load_context] Error retrieving operational context | "
            f"load_id={load_id} | "
            f"error_type={type(exc).__name__} | "
            f"error_message={str(exc)}"
        )
        logger.exception(
            "[get_load_context] Stack trace follows"
        )
        return []


@app.tool()
async def get_load_exceptions(load_id: str) -> List[Dict]:
    """
    Retrieve exception records for a specific load.

    Use this tool when you need to understand what operational issues
    occurred for a load (e.g., delays, breakdowns, violations).

    Returns:
    - Exception record(s) only

    Does NOT return:
    - Load or dispatch records
    - Documents or narratives
    - Root-cause analysis or reasoning
    """
    logger.info(f"[get_load_exceptions] Requested load_id={load_id}")

    try:
        results = await store.get_exceptions(load_id)
        logger.info(
            f"[get_load_exceptions] Returned {len(results)} exception(s) "
            f"for load_id={load_id}"
        )
        return results

    except Exception as exc:
        logger.error(
            "[get_load_exceptions] Error retrieving exceptions | "
            f"load_id={load_id} | "
            f"error_type={type(exc).__name__} | "
            f"error_message={str(exc)}"
        )
        logger.exception(
            "[get_load_exceptions] Stack trace follows"
        )
        return []


@app.tool()
async def get_exceptions_by_type(
    exception_type: str,
) -> List[Dict]:
    """
    Retrieve operational exception records filtered by exception type.

    Use this tool when you need to identify exceptions of a specific category
    (e.g., Late Delivery, Breakdown, Weather Delay, HOS Violation).

    Parameters:
    - exception_type: The exception category to filter by.


    Returns:
    - Matching exception record(s)

    Does NOT return:
    - Load or dispatch records
    - Root-cause analysis
    - Aggregations or summaries
    """
    
    logger.info(
        f"[get_exceptions_by_type] Requested exception_type={exception_type}"
    )

    try:
        results = await store.get_exceptions_by_type(
            exception_type=exception_type
        )
        logger.info(
            f"[get_exceptions_by_type] Returned {len(results)} record(s) "
            f"for exception_type={exception_type}"
        )
        return results

    except Exception as exc:
        logger.error(
            "[get_exceptions_by_type] Error retrieving exceptions | "
            f"exception_type={exception_type} | "
            f"error_type={type(exc).__name__} | "
            f"error_message={str(exc)}"
        )
        logger.exception(
            "[get_exceptions_by_type] Stack trace follows"
        )
        return []

# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Trucking Operations MCP Server...")
    logger.info(f"Service name: {environ.get('SERVICE_NAME', 'unknown')}")
    app.run(transport="streamable-http")
