import os, uuid
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from google.cloud import datastore, storage

# Initialize Flask application
app = Flask(__name__)
# Secure cookies/sessions using environment variable or local dev fallback string
app.secret_key = os.environ.get("SECRET_KEY") or "dev-secret-change-me"

# Google Cloud infrastructure configurations
PROJECT_ID = "my-sandbox-testing-501304"
BUCKET_NAME = "forum-images-2026"

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
    """Upload multipart form images to Google Cloud Storage and return public URLs"""
    if not file_storage or file_storage.filename == "":
        return None
    bucket = storage_client.bucket(BUCKET_NAME)
    ext = file_storage.filename.rsplit(".", 1)[-1]
    # Use unique UUID hex strings as filenames to prevent file overwrite collisions
    blob_name = f"{folder}/{uuid.uuid4().hex}.{ext}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file_storage, content_type=file_storage.content_type)
    return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

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

def update_post(post_entity, subject, message_text, image_url=None):
    """Overwrite properties of an existing post entity and push revisions online"""
    post_entity["subject"] = subject
    post_entity["message_text"] = message_text
    if image_url:
        post_entity["image_url"] = image_url
    post_entity["created_at"] = datetime.now(timezone.utc)
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
    """Handle new user registration and credential storage in Datastore"""
    error = None
    if request.method == "POST":
        image_url = upload_image(request.files.get("image"), folder="profiles")
        entered_id = request.form.get("id", "").strip()
        entered_password = request.form.get("password", "")
        if entered_password != entered_confirm_password:
            error = "Passwords do not match"
        elif get_user_by_id(entered_id):
            error = "The ID already exists"
        else:
            key = ds_client.key("user")
            user_entity = datastore.Entity(key=key)
            user_entity.update(
                {
                    "id": entered_id,
                    "user_name": entered_name,
                    "password": entered_password,
                    "image_url": image_url,
                }
            )
            ds_client.put(user_entity)
            return redirect(url_for("login"))
    return render_template("register.html", error=error)

@app.route("/forum", methods=["GET", "POST"])
@login_required
def forum():
    """Render forum posts using optimized batch data query handling"""
    current_user = get_user_by_id(session["user_id"])
    error = None

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message_text = request.form.get("message_text", "")
        if not subject:
            error = "Subject is required"
        else:
            image_url = upload_image(request.files.get("image"), folder="posts")
            create_post(
                subject, message_text, image_url,
                current_user["id"], current_user["user_name"],
            )
            return redirect(url_for("forum"))

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
        post_data["user_name"] = author["user_name"] if author else post_data.get("user_name")
        posts.append(post_data)

    return render_template("forum.html", user=current_user, posts=posts, error=error)

@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Provide secure context routing adjustments to overwrite specific content posts"""
    post = get_post_by_id(post_id)
    if post is None or post["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    error = None
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message_text = request.form.get("message_text", "")
        if not subject:
            error = "Subject is required"
        else:
            image_file = request.files.get("image")
            image_url = None
            if image_file and image_file.filename:
                image_url = upload_image(image_file, folder="posts")
            
            update_post(post, subject, message_text, image_url)
            return redirect(url_for("forum"))

    return render_template("edit_post.html", post=post, error=error)

@app.route("/user", methods=["GET", "POST"])
@login_required
def user_page():
    """Handle credential revisions and compile isolated author post layouts"""
    current_user = get_user_by_id(session["user_id"])
    error = None

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        if current_user["password"] != old_password:
            error = "The old password is incorrect"
        else:
            update_user_password(current_user, new_password)
            session.clear()
            return redirect(url_for("login"))

    raw_my_posts = get_posts_by_user(session["user_id"])
    my_posts = []
    for p_entity in raw_my_posts:
        p_data = dict(p_entity)
        p_data['id'] = p_entity.key.id
        my_posts.append(p_data)

    return render_template("user.html", user=current_user, posts=my_posts, error=error)

@app.route("/logout")
def logout():
    """Destroy context sessions and drop memory authorization variables"""
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)