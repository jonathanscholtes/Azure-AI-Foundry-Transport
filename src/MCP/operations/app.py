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
    Retrieve the full operational context for a SINGLE, SPECIFIC load.

    IMPORTANT USAGE RULES:
    - Use this tool ONLY when the user provides a concrete load identifier
      (for example: "Load 12345").
    - The load_id parameter MUST be an exact, known load or shipment ID.
    - Do NOT use this tool to search, filter, list, or discover loads.
    - Do NOT pass descriptive terms such as "high_priority", "late",
      "delayed", or "with exceptions" as load_id values.

    This tool is for LOOKUP by ID, not for attribute-based queries.

    Returns:
    - Load record
    - Dispatch record(s)
    - Exception record(s)

    Does NOT return:
    - Search results or filtered lists
    - Documents, contracts, or SLAs
    - Aggregations, summaries, or reasoning
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
    Retrieve exception records for a SINGLE, SPECIFIC load.

    IMPORTANT USAGE RULES:
    - Use this tool ONLY when a valid load ID is known.
    - Do NOT use this tool to discover which loads have exceptions.
    - Do NOT pass descriptive or categorical values as load_id.

    Returns:
    - Exception record(s) only
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

    VALID EXCEPTION TYPES (case-insensitive):
    - Late Delivery
    - Breakdown
    - Weather Delay
    - HOS Violation

    IMPORTANT USAGE RULES:
    - Use this tool ONLY with one of the valid exception types listed above.
    - Do NOT invent new exception categories.
    - Do NOT pass free-form descriptions or combined values.
    - This tool identifies exceptions, NOT loads.
    - Load attributes such as priority must be retrieved separately.

    Returns:
    - Matching exception record(s) referencing load IDs

    Does NOT return:
    - Load or dispatch records
    - Aggregations or summaries
    - Root-cause analysis
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
