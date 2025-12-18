#!/usr/bin/env python3

import random
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv

from cosmos_store import CosmosStore
from search_index import TruckingSearchIndex

# -------------------------------------------------------------------
# ENV / SEED
# -------------------------------------------------------------------

load_dotenv()
random.seed(42)

# -------------------------------------------------------------------
# LOAD CONFIRMATION TEMPLATE (RAG DOCUMENT)
# -------------------------------------------------------------------

LOAD_CONFIRM_TEMPLATE = """\
Load {load_id}
Origin: {origin}
Destination: {destination}
Delivery Deadline: {deadline}
Priority: {priority}
Weight: {weight_lbs} lbs
"""

def generate_load_doc(load: dict) -> dict:
    """
    Convert a structured load into a RAG-ready document
    """
    return {
        "id": f"doc-load-{load['load_id']}",
        "doc_type": "load_confirmation",
        "load_id": load["load_id"],
        "content": LOAD_CONFIRM_TEMPLATE.format(
            load_id=load["load_id"],
            origin=load["origin"],
            destination=load["destination"],
            deadline=load["delivery_deadline"],
            priority=load.get("priority", "Normal"),
            weight_lbs=load.get("weight_lbs", "N/A"),
        ),
    }

# -------------------------------------------------------------------
# STRUCTURED DATA GENERATORS (COSMOS)
# -------------------------------------------------------------------

def generate_trucks(n: int) -> List[dict]:
    return [
        {
            "id": f"T-{1000+i}",
            "truck_id": f"T-{1000+i}",
            "type": "truck",
            "make": random.choice(["Peterbilt", "Kenworth", "Freightliner"]),
            "model": random.choice(["579", "T680", "Cascadia"]),
            "year": random.randint(2019, 2024),
            "odometer_miles": random.randint(150_000, 650_000),
            "home_terminal": random.choice(["DAL", "PHX", "DEN", "ATL"]),
            "status": "Available",
        }
        for i in range(n)
    ]


def generate_drivers(n: int) -> List[dict]:
    return [
        {
            "id": f"D-{2000+i}",
            "driver_id": f"D-{2000+i}",
            "type": "driver",
            "cdl_class": "A",
            "hazmat_cert": random.random() < 0.2,
            "safety_score": random.randint(70, 99),
            "home_base": random.choice(
                ["Dallas, TX", "Phoenix, AZ", "Denver, CO", "Atlanta, GA"]
            ),
        }
        for i in range(n)
    ]


def generate_loads(n: int, start_date: datetime) -> List[dict]:
    loads = []
    for i in range(n):
        pickup = start_date + timedelta(hours=random.randint(0, 24 * 365))
        deadline = pickup + timedelta(hours=random.randint(24, 96))

        loads.append(
            {
                "id": f"L-{7000+i}",
                "load_id": f"L-{7000+i}",
                "type": "load",
                "customer_id": f"C-{random.randint(100,199)}",
                "origin": random.choice(
                    ["Dallas, TX", "Phoenix, AZ", "Denver, CO", "Atlanta, GA"]
                ),
                "destination": random.choice(
                    ["Chicago, IL", "Los Angeles, CA", "Houston, TX"]
                ),
                "pickup_time": pickup.isoformat(),
                "delivery_deadline": deadline.isoformat(),
                "priority": random.choice(["Low", "Normal", "High"]),
                "weight_lbs": random.randint(5_000, 45_000),
                "rate_usd": random.randint(1_500, 6_000),
            }
        )
    return loads


def generate_dispatch(loads, trucks, drivers) -> List[dict]:
    return [
        {
            "id": f"DP-{load['load_id']}",
            "load_id": load["load_id"],
            "type": "dispatch",
            "truck_id": random.choice(trucks)["truck_id"],
            "driver_id": random.choice(drivers)["driver_id"],
            "dispatch_time": load["pickup_time"],
        }
        for load in loads
    ]


def generate_exceptions(loads, exception_rate: float) -> List[dict]:
    return [
        {
            "id": f"EX-{load['load_id']}",
            "load_id": load["load_id"],
            "type": "exception",
            "exception_type": random.choice(
                ["Late Delivery", "Breakdown", "Weather Delay", "HOS Violation"]
            ),
            "detected_at": load["delivery_deadline"],
        }
        for load in loads
        if random.random() < exception_rate
    ]

# -------------------------------------------------------------------
# ANCHOR EXCEPTION (DEMO GUARANTEE)
# -------------------------------------------------------------------

def inject_anchor_exception(loads, exceptions):
    anchor_load = {
        "id": "L-7712",
        "load_id": "L-7712",
        "type": "load",
        "customer_id": "C-104",
        "origin": "Dallas, TX",
        "destination": "Phoenix, AZ",
        "pickup_time": "2025-02-14T06:00:00Z",
        "delivery_deadline": "2025-02-15T20:00:00Z",
        "priority": "High",
        "weight_lbs": 38500,
        "rate_usd": 4200,
    }

    anchor_exception = {
        "id": "EX-7712",
        "load_id": "L-7712",
        "type": "exception",
        "exception_type": "Late Delivery",
        "delay_minutes": 258,
        "detected_at": "2025-02-15T21:10:00Z",
    }

    loads.insert(0, anchor_load)
    exceptions.append(anchor_exception)

# -------------------------------------------------------------------
# NARRATIVE / NON-TEMPLATED RAG DOCS
# -------------------------------------------------------------------

def generate_anchor_documents() -> List[dict]:
    return [
        {
            "id": "doc-sla-C-104",
            "doc_type": "sla",
            "load_id": "L-7712",
            "content": (
                "Section 4.2 – Force Majeure. Carrier shall not be liable for "
                "delays caused by equipment failure, severe weather, or road "
                "closures beyond reasonable control."
            ),
        },
        {
            "id": "doc-driver-D-332",
            "doc_type": "driver_note",
            "load_id": "L-7712",
            "content": (
                "01:17 CST – Sudden vibration in steering wheel. "
                "Pulled over immediately for safety. Roadside assistance contacted."
            ),
        },
        {
            "id": "doc-customer-L-7712",
            "doc_type": "customer_email",
            "load_id": "L-7712",
            "content": (
                "We are extremely concerned about the late arrival of Load L-7712. "
                "This delay impacted our distribution center labor scheduling."
            ),
        },
    ]

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main():
    cosmos = CosmosStore()
    search = TruckingSearchIndex()

    print("🔧 Ensuring Azure AI Search index exists...")
    search.create_index_if_not_exists()

    print("📦 Generating structured data...")
    start_date = datetime.utcnow() - timedelta(days=365)

    trucks = generate_trucks(25)
    drivers = generate_drivers(50)
    loads = generate_loads(500, start_date)
    dispatch = generate_dispatch(loads, trucks, drivers)
    exceptions = generate_exceptions(loads, exception_rate=0.03)

    inject_anchor_exception(loads, exceptions)

    print("⬆️ Writing structured data to Cosmos DB...")
    cosmos.upsert_items(trucks)
    cosmos.upsert_items(drivers)
    cosmos.upsert_items(loads)
    cosmos.upsert_items(dispatch)
    cosmos.upsert_items(exceptions)

    print("📚 Generating RAG documents...")
    rag_docs = []

    # Bulk load confirmations (templated, scalable)
    rag_docs.extend(generate_load_doc(load) for load in loads[:250])

    # Anchor narrative documents
    rag_docs.extend(generate_anchor_documents())

    print(f"⬆️ Indexing {len(rag_docs)} documents into Azure AI Search...")
    search.upload_documents(rag_docs)

    print("✅ Generation complete")
    print(f"Trucks: {len(trucks)}")
    print(f"Drivers: {len(drivers)}")
    print(f"Loads: {len(loads)}")
    print(f"Exceptions: {len(exceptions)}")
    print(f"RAG Docs Indexed: {len(rag_docs)}")


if __name__ == "__main__":
    main()
