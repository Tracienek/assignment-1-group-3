import os, uuid
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from google.cloud import datastore, storage

# Initialize Flask application
app = Flask(__name__)
# Secure cookies/sessions using environment variable or local dev fallback string
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
# Limit file upload to a maximum of 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

VIETNAM_TIMEZONE = timezone(timedelta(hours=7))

@app.template_filter("vn_datetime")
def vn_datetime(value):
    if value is None:
        return ""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    vietnam_time = value.astimezone(VIETNAM_TIMEZONE)

    return vietnam_time.strftime("%b %d, %Y %I:%M %p")

# Google Cloud infrastructure configurations
PROJECT_ID = "assignment-1-ug-g3"
BUCKET_NAME = "assignment-1-ug-g3-forum-images"

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
}

# Initialize Google Cloud Client Libraries
ds_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client()


def get_user_by_id(user_id):
    """Query a specific user from Datastore by their matching 'id' property string."""
    query = ds_client.query(kind="user")
    query.add_filter("id", "=", user_id)
    results = list(query.fetch(limit=1))
    return results[0] if results else None


def update_user_password(user_entity, new_password):
    """Update a user entity's password property string and save to Datastore"""
    user_entity["password"] = new_password
    ds_client.put(user_entity)


def upload_image(file_storage, folder="posts"):
    if not file_storage or not file_storage.filename:
        return None

    if file_storage.mimetype not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Unsupported image type")

    extension_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/avif": "avif",
    }

    extension = extension_map[file_storage.mimetype]
    blob_name = f"{folder}/{uuid.uuid4().hex}.{extension}"

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    blob.upload_from_file(
        file_storage,
        content_type=file_storage.mimetype,
    )

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    

def delete_storage_image(image_url):
    if not image_url:
        return

    expected_prefix = f"https://storage.googleapis.com/{BUCKET_NAME}/"

    if not image_url.startswith(expected_prefix):
        return

    blob_name = image_url[len(expected_prefix):]
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    try:
        blob.delete()
    except Exception:
        app.logger.exception(
            "Could not delete old image: %s",
            blob_name
        )


def create_post(subject, message_text, image_url, user_id, user_name):
    """Instantiate a new post entry in Datastore tracking metadata and timestamps"""
    key = ds_client.key("post")
    post = datastore.Entity(key=key)
    post.update(
        {
            "subject": subject,
            "message_text": message_text,
            "image_url": image_url,
            "user_id": user_id,
            "user_name": user_name,
            "created_at": datetime.now(timezone.utc),
        }
    )
    ds_client.put(post)
    return post


def get_latest_posts(limit=10):
    """Fetch recent global community posts ordered chronologically"""
    query = ds_client.query(kind="post")
    query.order = ["-created_at"]
    return list(query.fetch(limit=limit))


def get_posts_by_user(user_id):
    """Fetch individual author history posts using isolated property filtering"""
    query = ds_client.query(kind="post")
    query.add_filter("user_id", "=", user_id)
    query.order = ["-created_at"]
    return list(query.fetch())


def get_post_by_id(post_id):
    """Perform a direct primary key entity lookup using numeric post IDs"""
    return ds_client.get(ds_client.key("post", int(post_id)))


def update_post(post_entity, subject, message_text, image_url):
    now = datetime.now(timezone.utc)

    post_entity["subject"] = subject
    post_entity["message_text"] = message_text
    post_entity["image_url"] = image_url
    post_entity["updated_at"] = datetime.now(timezone.utc)

    post_entity["created_at"] = now
    post_entity["updated_at"] = now

    ds_client.put(post_entity)


def login_required(view):
    """Custom decorator route guard ensuring requests contain authenticated cookie session flags"""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        entered_id = request.form.get("id", "").strip()
        entered_password = request.form.get("password", "")

        user = get_user_by_id(entered_id)

        if user is None or user.get("password") != entered_password:
            error = "ID or password is invalid"
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("forum"))

    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        entered_id = request.form.get("id", "").strip()
        entered_name = request.form.get("user_name", "").strip()
        entered_password = request.form.get("password", "")
        entered_confirm_password = request.form.get("confirm_password", "")
        image_file = request.files.get("image")

        if not image_file or not image_file.filename:
            error = "User image is required"

        elif entered_password != entered_confirm_password:
            error = "Passwords do not match"

        elif get_user_by_id(entered_id):
            error = "The ID already exists"

        else:
            username_query = ds_client.query(kind="user")
            username_query.add_filter("user_name", "=", entered_name)

            if list(username_query.fetch(limit=1)):
                error = "The username already exists"   
            else:
                try:
                    image_url = upload_image(image_file, folder="profiles")

                    key = ds_client.key("user")
                    user_entity = datastore.Entity(key=key)
                    user_entity.update(
                        {
                            "id": entered_id,
                            "user_name": entered_name,
                            "password": entered_password,
                            "image_url": image_url,
                            "created_at": datetime.now(timezone.utc),
                        }
                    )

                    ds_client.put(user_entity)
                    return redirect(url_for("login"))

                except Exception:
                    app.logger.exception("Registration failed")
                    error = "Registration failed. Please try again."

    return render_template("register.html", error=error)

@app.route("/forum", methods=["GET", "POST"])
@login_required
def forum():
    """Render forum posts using optimized batch data query handling"""
    current_user = get_user_by_id(session["user_id"])

    if current_user is None:
        session.clear()
        return redirect(url_for("login"))

    error = None

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message_text = request.form.get("message_text", "")
        if not subject:
            error = "Subject is required"
        else:
            try:
                image_url = upload_image(request.files.get("image"), folder="posts")
                create_post(
                    subject,
                    message_text,
                    image_url,
                    current_user["id"],
                    current_user["user_name"],
                )
                return redirect(url_for("forum"))
            except Exception:
                app.logger.exception("Post creation failed")
                error = "Post creation failed. Please try again."

    raw_posts = get_latest_posts(limit=10)

    # Extract distinct authors from recent feed payload
    unique_user_ids = list({p["user_id"] for p in raw_posts if p.get("user_id")})

    # Resolve author details using one dynamic IN query
    authors_by_id = {}
    if unique_user_ids:
        query = ds_client.query(kind="user")
        query.add_filter("id", "IN", unique_user_ids)
        for author in query.fetch():
            authors_by_id[author["id"]] = author

    posts = []
    for p_entity in raw_posts:
        post_data = dict(p_entity)
        post_data["id"] = p_entity.key.id
        author = authors_by_id.get(post_data.get("user_id"))
        post_data["author_avatar"] = author["image_url"] if author else None
        post_data["user_name"] = (
            author["user_name"] if author else post_data.get("user_name")
        )
        post_data["user_id"] = author["id"] if author else post_data.get("user_id")
        posts.append(post_data)

    return render_template("forum.html", user=current_user, posts=posts, error=error)


@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Handles updating a post, including changing or removing its image"""
    post = get_post_by_id(post_id)
    if post is None or post["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    error = None
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message_text = request.form.get("message_text", "")
        delete_image_flag = request.form.get("delete_image") == "true"

        if not subject:
            error = "Subject is required"
        else:
            image_file = request.files.get("image")
            image_url = None

            if image_file and image_file.filename:
                old_image_url = post.get("image_url")

                try:
                    image_url = upload_image(image_file, folder="posts")
                except ValueError:
                    error = "Unsupported image type"
                    return render_template(
                        "edit_post.html",
                        post=post,
                        error=error,
                    )
                except Exception:
                    app.logger.exception("Post image upload failed")
                    error = "Image upload failed. Please try again."
                    return render_template(
                        "edit_post.html",
                        post=post,
                        error=error,
                    )

                if old_image_url:
                    delete_storage_image(old_image_url)
            elif delete_image_flag:
                old_image_url = post.get("image_url")

                if old_image_url:
                    delete_storage_image(old_image_url)

                image_url = None
            else:
                image_url = post.get("image_url")

            update_post(post, subject, message_text, image_url)
            return redirect(url_for("forum"))

    return render_template("edit_post.html", post=post, error=error)


@app.route("/user", methods=["GET", "POST"])
@login_required
def user_page():
    current_user = get_user_by_id(session["user_id"])

    if current_user is None:
        session.clear()
        return redirect(url_for("login"))

    error = None
    username_error = None

    if request.method == "POST":
        form_type = request.form.get("form_type")

        # Update username
        if form_type == "update_username":
            new_username = request.form.get(
                "new_username",
                ""
            ).strip()

            if not new_username:
                username_error = "Username cannot be empty"

            elif len(new_username) < 2 or len(new_username) > 40:
                username_error = (
                    "Username must be between 2 and 40 characters"
                )

            else:
                query = ds_client.query(kind="user")
                query.add_filter(
                    "user_name",
                    "=",
                    new_username
                )
                existing_users = list(query.fetch(limit=1))

                if (
                    existing_users
                    and existing_users[0]["id"]
                    != current_user["id"]
                ):
                    username_error = "The username already exists"

                else:
                    current_user["user_name"] = new_username
                    ds_client.put(current_user)

                    user_posts = get_posts_by_user(
                        current_user["id"]
                    )

                    for post in user_posts:
                        post["user_name"] = new_username

                    if user_posts:
                        ds_client.put_multi(user_posts)

                    return redirect(url_for("forum"))

        # Change password
        elif form_type == "change_password":
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")

            if current_user["password"] != old_password:
                error = "The old password is incorrect"

            else:
                update_user_password(
                    current_user,
                    new_password
                )
                session.clear()
                return redirect(url_for("login"))

    raw_my_posts = get_posts_by_user(session["user_id"])
    my_posts = []

    for post_entity in raw_my_posts:
        post_data = dict(post_entity)
        post_data["id"] = post_entity.key.id
        my_posts.append(post_data)

    return render_template(
        "user.html",
        user=current_user,
        posts=my_posts,
        error=error,
        username_error=username_error,
    )

@app.route("/<user_id>", methods=["GET"])
@login_required
def user_page(user_id):
    user = get_user_by_id(user_id)

    current_user = get_user_by_id(session["user_id"])
    
    if current_user == user:
        return redirect(url_for("user_page"))

    error = None
    username_error = None


    raw_posts = get_posts_by_user(user_id)
    posts = []

    for post_entity in raw_posts:
        post_data = dict(post_entity)
        post_data["id"] = post_entity.key.id
        posts.append(post_data)

    return render_template(
        "other_user.html",
        user=user,
        posts=posts,
        error=error,
        username_error=username_error,
    )


@app.route("/logout")
def logout():
    """Destroy context sessions and drop memory authorization variables"""
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
