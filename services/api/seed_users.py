from pathlib import Path

from sqlalchemy import text

from app.auth.security import hash_password
from app.db.database import engine


CREDENTIALS_FILE = Path(__file__).parent / ".env.users"


def load_credentials() -> list[tuple[str, str]]:
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Create {CREDENTIALS_FILE} first, "
            "one 'username:password' pair per line."
        )

    credentials = []

    for line in CREDENTIALS_FILE.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        username, _, password = line.partition(":")

        if not username or not password:
            raise ValueError(
                f"Invalid line in {CREDENTIALS_FILE}: {line!r}"
            )

        credentials.append((username.strip(), password.strip()))

    return credentials


def main():
    credentials = load_credentials()

    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth.users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        )

        for username, password in credentials:
            connection.execute(
                text(
                    """
                    INSERT INTO auth.users (username, password_hash)
                    VALUES (:username, :password_hash)
                    ON CONFLICT (username)
                    DO UPDATE SET password_hash = EXCLUDED.password_hash
                    """
                ),
                {
                    "username": username,
                    "password_hash": hash_password(password),
                },
            )

    print(
        f"Seeded {len(credentials)} account(s): "
        f"{', '.join(u for u, _ in credentials)}"
    )


if __name__ == "__main__":
    main()
