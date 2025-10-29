import sys
from typing import List

try:
    from pymongo import MongoClient
except ImportError as exc:
    raise SystemExit(
        "pymongo is not installed. Install it with: pip install pymongo"
    ) from exc


def drop_all_collections(mongo_uri: str, database_name: str) -> List[str]:
    client = MongoClient(mongo_uri)
    db = client[database_name]
    collection_names = db.list_collection_names()
    for name in collection_names:
        db.drop_collection(name)
    client.close()
    return collection_names


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python backend/scripts/empty_mongo_db.py <MONGO_URI> [DATABASE_NAME]",
            file=sys.stderr,
        )
        sys.exit(1)

    mongo_uri = sys.argv[1]
    database_name = sys.argv[2] if len(sys.argv) > 2 else "bitgpt"

    dropped = drop_all_collections(mongo_uri, database_name)
    if dropped:
        print(f"Dropped collections from '{database_name}': {', '.join(dropped)}")
    else:
        print(f"No collections found in '{database_name}'. Nothing to drop.")


if __name__ == "__main__":
    main()


