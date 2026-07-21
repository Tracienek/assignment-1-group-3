from datetime import datetime, timezone

from google.cloud import datastore


PROJECT_ID = "assignment-1-ug-g3"
BUCKET_NAME = "assignment-1-ug-g3-forum-images"

STUDENT_ID = "s3975175"
FULL_NAME = "Pham Tran Bao Tran"


def create_initial_users() -> None:
    client = datastore.Client(project=PROJECT_ID)

    passwords = [
        "012345",
        "123456",
        "234567",
        "345678",
        "456789",
        "567890",
        "678901",
        "789012",
        "890123",
        "901234",
    ]

    for number in range(10):
        user_id = f"{STUDENT_ID}{number}"

        query = client.query(kind="user")
        query.add_filter("id", "=", user_id)

        if list(query.fetch(limit=1)):
            print(f"Skipped: {user_id} already exists")
            continue

        key = client.key("user")
        user = datastore.Entity(key=key)

        user.update(
            {
                "id": user_id,
                "user_name": f"{FULL_NAME}{number}",
                "password": passwords[number],
                "image_url": (
                    f"https://storage.googleapis.com/"
                    f"{BUCKET_NAME}/digits/{number}.png"
                ),
                "created_at": datetime.now(timezone.utc),
            }
        )

        client.put(user)
        print(f"Created: {user_id}")


if __name__ == "__main__":
    create_initial_users()