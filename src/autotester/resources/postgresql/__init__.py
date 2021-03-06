import os
import getpass
import psycopg2
import secrets
import string
from psycopg2.extensions import AsIs
from autotester.config import config

POSTGRES_PREFIX = config["resources", "postgresql", "_prefix"]
PGPASSFILE = os.path.join(
    config["workspace"], config["_workspace_contents", "_logs"], ".pgpass"
)


def setup_database(test_username):
    user = getpass.getuser()
    database = f"{POSTGRES_PREFIX}{test_username}"

    with open(PGPASSFILE) as f:
        password = f.read().strip()

    with psycopg2.connect(
        database=database, user=user, password=password, host="localhost"
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DROP OWNED BY CURRENT_USER;")
            if test_username != user:
                user = test_username
                password = "".join(
                    secrets.choice(string.ascii_letters + string.digits)
                    for _ in range(20)
                )
                cursor.execute(
                    "ALTER USER %s WITH PASSWORD %s;", (AsIs(user), password)
                )

    return {
        "PGDATABASE": database,
        "PGPASSWORD": password,
        "PGUSER": user,
        "AUTOTESTENV": "true",
    }
