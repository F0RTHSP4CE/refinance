from os import environ

from uvicorn import run

from refinance.log import configure_logging


def main() -> None:
    configure_logging()
    run(
        "refinance.app:app_factory",
        host=environ.get("HOST", "0.0.0.0"),
        port=int(environ.get("PORT", 8000)),
        workers=int(environ.get("WORKERS", 1)),
        factory=True,
    )


if __name__ == "__main__":
    main()
