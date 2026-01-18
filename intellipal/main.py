from __future__ import annotations

try:
    from .app import create_app
except Exception:
    # When running as a script or from a frozen bundle the package
    # context may not be available; fall back to absolute import.
    from intellipal.app import create_app


def main() -> None:
    app = create_app()
    app.exec()


if __name__ == "__main__":
    main()
