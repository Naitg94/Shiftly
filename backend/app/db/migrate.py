import os
import ssl
import logging
from dotenv import load_dotenv
import pg8000.native

logger = logging.getLogger("shiftly.migrate")

def parse_database_url(db_url: str):
    prefix = "postgresql://" if db_url.startswith("postgresql://") else "postgres://"
    rest = db_url[len(prefix):]
    at_idx = rest.rfind("@")
    user_pass = rest[:at_idx]
    host_part = rest[at_idx + 1:]

    colon_idx = user_pass.find(":")
    user = user_pass[:colon_idx]
    password = user_pass[colon_idx + 1:]
    if password.startswith("[") and password.endswith("]"):
        password = password[1:-1]

    slash_idx = host_part.find("/")
    host_port = host_part[:slash_idx]
    dbname = host_part[slash_idx + 1:].split("?")[0]

    if ":" in host_port:
        host, port_str = host_port.split(":")
        port = int(port_str)
    else:
        host = host_port
        port = 5432

    return user, password, host, port, dbname

def run_migration(database_url: str = None) -> bool:
    load_dotenv()
    db_url = database_url or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set. Please provide a direct PostgreSQL connection string in backend/.env.")

    user, password, host, port, dbname = parse_database_url(db_url)
    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"schema.sql not found at {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        sql_script = f.read()

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    logger.info("Connecting directly to Supabase PostgreSQL database...")
    conn = pg8000.native.Connection(
        user=user,
        password=password,
        host=host,
        port=port,
        database=dbname,
        ssl_context=ssl_ctx,
        timeout=20,
    )

    try:
        conn.run(sql_script)
        logger.info("schema.sql successfully executed on Supabase PostgreSQL!")
        return True
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        run_migration()
        print("MIGRATION_SUCCESS")
    except Exception as e:
        print(f"MIGRATION_ERROR: {e}")
