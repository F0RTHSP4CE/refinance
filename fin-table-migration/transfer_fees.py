#!/usr/bin/env python3
"""
Script to transfer resident monthly fees from CSV to Refinance financial management system.
"""

import argparse
import csv
import logging
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RefinanceAPI:
    """Client for interacting with the Refinance API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Token": token, "Content-Type": "application/json"}
        )

    def get_entities(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all entities from the API."""
        url = f"{self.base_url}/entities"
        params = {"limit": limit}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return data["items"]

    def create_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new transaction."""
        url = f"{self.base_url}/transactions"

        response = self.session.post(url, json=transaction_data)
        response.raise_for_status()

        return response.json()


class FeeTransferProcessor:
    """Processes and transfers fee data from CSV to Refinance API."""

    def __init__(self, api: RefinanceAPI):
        self.api = api
        self.entities_by_name: Dict[str, int] = {}
        self.month_names = [
            "2025-01",
            "2025-02",
            "2025-03",
            "2025-04",
            "2025-05",
            "2025-06",
            "2025-07",
            "2025-08",
            "2025-09",
            "2025-10",
            "2025-11",
            "2025-12",
        ]

    def load_entities(self):
        """Load entities from API and create name-to-ID mapping."""
        logger.info("Loading entities from API...")
        entities = self.api.get_entities()

        for entity in entities:
            self.entities_by_name[entity["name"]] = entity["id"]

        logger.info(f"Loaded {len(entities)} entities")

        # Log some example entities for debugging
        for name, entity_id in list(self.entities_by_name.items())[:5]:
            logger.debug(f"Entity: {name} -> ID: {entity_id}")

    def parse_csv_data(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """Parse the CSV file and extract fee transactions."""
        transactions = []

        logger.info(f"Parsing CSV file: {csv_file_path}")

        with open(csv_file_path, "r", encoding="utf-8") as file:
            # Read all lines to handle the format properly
            lines = file.readlines()

            # Skip empty lines and find the header line
            header_line_idx = None
            for i, line in enumerate(lines):
                line = line.strip()
                if line and "RESIDENT" in line:
                    header_line_idx = i
                    break

            if header_line_idx is None:
                raise ValueError(
                    "Could not find header line with 'RESIDENT' in CSV file"
                )

            # Parse headers
            header_line = lines[header_line_idx].strip()
            headers = [col.strip() for col in header_line.split(",")]

            # Parse each resident row (starting after header)
            for line_num, line in enumerate(
                lines[header_line_idx + 1 :], header_line_idx + 2
            ):
                line = line.strip()
                if not line:
                    continue

                # Split by comma and clean up spaces
                columns = [col.strip() for col in line.split(",")]

                if len(columns) < len(headers):
                    logger.warning(f"Line {line_num}: Insufficient columns, skipping")
                    continue

                resident_name = columns[0]

                # Skip if resident name indicates they're not a resident
                if resident_name in ["not resident", "not yet"]:
                    continue

                # Check if resident exists in our entities
                if resident_name not in self.entities_by_name:
                    logger.warning(
                        f"Line {line_num}: Resident '{resident_name}' not found in entities, skipping"
                    )
                    continue

                # Process each month's fee
                for month_idx, amount_str in enumerate(columns[1 : len(headers)]):
                    if month_idx >= len(self.month_names):
                        break

                    amount_str = amount_str.strip()

                    # Skip if no amount or invalid amount
                    if not amount_str or amount_str in [
                        "0.00",
                        "0",
                        "not resident",
                        "not yet",
                    ]:
                        continue

                    try:
                        amount = Decimal(amount_str)
                        if amount <= 0:
                            continue
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Line {line_num}: Invalid amount '{amount_str}' for {resident_name} in {self.month_names[month_idx]}"
                        )
                        continue

                    # Extract month and year
                    month_year = self.month_names[month_idx]
                    year, month = month_year.split("-")

                    # Convert month number to month name
                    month_names = {
                        "01": "january",
                        "02": "february",
                        "03": "march",
                        "04": "april",
                        "05": "may",
                        "06": "june",
                        "07": "july",
                        "08": "august",
                        "09": "september",
                        "10": "october",
                        "11": "november",
                        "12": "december",
                    }
                    month_name = month_names.get(month, month)

                    transaction = {
                        "resident_name": resident_name,
                        "from_entity_id": self.entities_by_name[resident_name],
                        "to_entity_id": 1,  # As specified in requirements
                        "amount": str(amount),
                        "currency": "GEL",  # Georgian Lari
                        "comment": f"fee {month_name} {year} (migration)",
                        "tag_ids": [3],  # Fee tag ID as specified
                        "status": "completed",
                        "month_year": month_year,
                    }

                    transactions.append(transaction)

        logger.info(f"Parsed {len(transactions)} fee transactions from CSV")
        return transactions

    def calculate_resident_totals(
        self, transactions: List[Dict[str, Any]]
    ) -> Dict[str, Decimal]:
        """Calculate total amount paid by each resident."""
        totals = {}

        for transaction in transactions:
            resident_name = transaction["resident_name"]
            amount = Decimal(transaction["amount"])

            if resident_name not in totals:
                totals[resident_name] = Decimal("0")

            totals[resident_name] += amount

        return totals

    def create_initial_credit_transactions(
        self,
        resident_totals: Dict[str, Decimal],
        currency: str = "GEL",
        dry_run: bool = False,
    ) -> int:
        """Create initial credit transactions from entity 1 to each resident."""
        success_count = 0

        logger.info(
            f"Creating initial credit transactions for {len(resident_totals)} residents..."
        )

        for i, (resident_name, total_amount) in enumerate(resident_totals.items(), 1):
            try:
                if dry_run:
                    logger.info(
                        f"[Credit {i}/{len(resident_totals)}] Would create credit: "
                        f"Entity 1 -> {resident_name} {total_amount} GEL (migration to refinance)"
                    )
                else:
                    api_transaction = {
                        "from_entity_id": 1,  # From entity 1
                        "to_entity_id": self.entities_by_name[
                            resident_name
                        ],  # To resident
                        "amount": str(total_amount),
                        "currency": currency,
                        "comment": f"migration to refinance",
                        "status": "completed",
                        "tag_ids": [3],  # Fee tag
                    }

                    result = self.api.create_transaction(api_transaction)
                    logger.info(
                        f"[Credit {i}/{len(resident_totals)}] Created credit transaction ID {result['id']}: "
                        f"Entity 1 -> {resident_name} {total_amount} GEL"
                    )

                success_count += 1

            except Exception as e:
                logger.error(
                    f"[Credit {i}/{len(resident_totals)}] Failed to create credit transaction for {resident_name}: {e}"
                )

        return success_count

    def transfer_transactions(
        self, transactions: List[Dict[str, Any]], dry_run: bool = False
    ) -> int:
        """Transfer transactions to the API."""
        success_count = 0

        if dry_run:
            logger.info("DRY RUN MODE - No transactions will be created")

        for i, transaction in enumerate(transactions, 1):
            try:
                if dry_run:
                    logger.info(
                        f"[Fee {i}/{len(transactions)}] Would create: {transaction['resident_name']} -> "
                        f"{transaction['amount']} GEL for {transaction['month_year']}"
                    )
                else:
                    # Remove fields not needed for API
                    api_transaction = {
                        "from_entity_id": transaction["from_entity_id"],
                        "to_entity_id": transaction["to_entity_id"],
                        "amount": transaction["amount"],
                        "currency": transaction["currency"],
                        "comment": transaction["comment"],
                        "status": transaction["status"],
                        "tag_ids": transaction["tag_ids"],
                    }

                    result = self.api.create_transaction(api_transaction)
                    logger.info(
                        f"[Fee {i}/{len(transactions)}] Created fee transaction ID {result['id']}: "
                        f"{transaction['resident_name']} -> {transaction['amount']} GEL for {transaction['month_year']}"
                    )

                success_count += 1

            except Exception as e:
                logger.error(
                    f"[Fee {i}/{len(transactions)}] Failed to create fee transaction for {transaction['resident_name']} "
                    f"in {transaction['month_year']}: {e}"
                )

        return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Transfer resident fees from CSV to Refinance API"
    )
    parser.add_argument(
        "csv_file",
        help="Path to the CSV file containing fee data. openssl dec -aes-256-cbc -salt -in fin.csv.enc -out fin.csv",
    )
    parser.add_argument(
        "--api-url",
        default="https://refinance-api.f0rth.space",
        help="Refinance API base URL",
    )
    parser.add_argument("--token", help="API token for authentication")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transferred without actually doing it",
    )
    parser.add_argument(
        "--currency", default="GEL", help="Currency for transactions (default: GEL)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get token from argument, environment variable, or prompt
    token = args.token
    if not token:
        token = os.getenv("REFINANCE_API_TOKEN")
    if not token:
        token = input("Enter API token: ").strip()

    if not token:
        logger.error("API token is required")
        sys.exit(1)

    # Verify CSV file exists
    if not os.path.exists(args.csv_file):
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)

    try:
        # Initialize API client
        api = RefinanceAPI(args.api_url, token)

        # Initialize processor
        processor = FeeTransferProcessor(api)

        # Load entities
        processor.load_entities()

        # Parse CSV data
        transactions = processor.parse_csv_data(args.csv_file)

        if not transactions:
            logger.warning("No valid transactions found in CSV file")
            return

        # Calculate totals for each resident
        resident_totals = processor.calculate_resident_totals(transactions)

        # Show summary
        logger.info(
            f"Found {len(transactions)} individual fee transactions for {len(resident_totals)} residents"
        )

        # Show resident totals
        logger.info("Resident totals:")
        for resident_name, total in resident_totals.items():
            logger.info(f"  {resident_name}: {total} GEL")

        total_migration_amount = sum(resident_totals.values())
        logger.info(f"Total migration amount: {total_migration_amount} GEL")

        if args.dry_run:
            logger.info("This is a dry run - showing what would be transferred:")

        # Step 1: Create initial credit transactions (entity 1 -> residents)
        logger.info("\n=== STEP 1: Creating initial credit transactions ===")
        credit_success_count = processor.create_initial_credit_transactions(
            resident_totals, currency=args.currency, dry_run=args.dry_run
        )

        # Step 2: Create individual fee transactions (residents -> entity 1)
        logger.info("\n=== STEP 2: Creating individual fee transactions ===")
        fee_success_count = processor.transfer_transactions(
            transactions, dry_run=args.dry_run
        )

        # Summary
        logger.info(f"\n=== MIGRATION SUMMARY ===")
        logger.info(
            f"Credit transactions: {credit_success_count}/{len(resident_totals)}"
        )
        logger.info(f"Fee transactions: {fee_success_count}/{len(transactions)}")
        logger.info(
            f"Net amount should be zero: {total_migration_amount} GEL in, {total_migration_amount} GEL out"
        )

    except KeyboardInterrupt:
        logger.info("Transfer interrupted by user")
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
