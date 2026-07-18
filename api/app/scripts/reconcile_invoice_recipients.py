"""Preview or apply rotated recipients to existing pending fee invoices.

Run inside the API container:
    python -m app.scripts.reconcile_invoice_recipients
    python -m app.scripts.reconcile_invoice_recipients --apply
"""

from __future__ import annotations

import argparse
import json

from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.uow import UnitOfWork


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile rotated recipients on pending fee invoices"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (the default is a dry run)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    connection = DatabaseConnection(config)
    with UnitOfWork(connection.get_session()) as uow:
        service = ServiceContainer(uow.db, config).invoice_service
        changes = service.reconcile_recipient_rotations(apply=args.apply)
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "dry-run",
                    "count": len(changes),
                    "changes": changes,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
