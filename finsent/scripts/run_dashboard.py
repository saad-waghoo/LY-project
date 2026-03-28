from __future__ import annotations

from finsent.app.dashboard.app import create_app


def main() -> None:
    app = create_app()
    app.run(debug=False)


if __name__ == "__main__":
    main()
