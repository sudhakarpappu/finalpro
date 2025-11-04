from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from app import app  # Import AFTER app & mysql are defined (keep for compatibility)
from blog_data import blog_posts
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv, find_dotenv
import time
import base64
import requests
import pyodbc


# Azure SQL Server connection details
# (Set these in your .env file for safety)
# Example .env entries:
# AZURE_SQL_SERVER=yourservername.database.windows.net
# AZURE_SQL_DATABASE=data1
# AZURE_SQL_USERNAME=yourusername
# AZURE_SQL_PASSWORD=yourStrongPassword!
# AZURE_SQL_DRIVER=ODBC Driver 18 for SQL Server

load_dotenv(find_dotenv())

MCP_SERVER_URL = "http://135.235.162.57/"
adminlogin = "EducationalBlog"
password = "2nEqN@LsgwahS4s"

ulogin = Blueprint('ulogin', __name__, template_folder='../templates/ulogin')

@app.route('/')
def index():
    return render_template('index.html', posts=blog_posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = next((p for p in blog_posts if p['id'] == post_id), None)
    if post:
        return render_template('post.html', post=post)
    else:
        return "Post not found", 404

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


def get_connection():
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    username = os.getenv("AZURE_SQL_USERNAME")
    password = os.getenv("AZURE_SQL_PASSWORD")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},1433;"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']   # ⚠️ plain text for now (you should hash it!)
    created = datetime.now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password, created_at, rid) VALUES (?, ?, ?, ?, 2)",
        (name, email, password, created)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/login')

@app.route('/signin', methods=['POST'])
def signin():
    email = request.form['email']
    password = request.form['password']

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT u.username, u.email, u.password, r.rid, r.name
        FROM users u
        JOIN role r ON u.rid = r.rid
        WHERE u.email = ?
    """
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and user[2] == password:
        session['user'] = user[0]
        session['rid'] = user[3]

        if user[3] == 1:
            return render_template('/alogin/ahome.html', user=user, posts=blog_posts)
        elif user[3] == 2:
            return render_template('/ulogin/uhome.html', user=user, posts=blog_posts)
        elif user[3] == 3:
            return render_template('/mlogin/mhome.html', user=user, posts=blog_posts)
        else:
            flash('Unknown role. Contact admin.', 'warning')
            return redirect('/login')
    else:
        flash('Invalid email or password', 'danger')
        return redirect('/login')

@app.route('/features')
def features():
    return render_template('alogin/features.html')

# ✅ Google Gemini setup
genai.configure(api_key=os.getenv("API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro")

# Import additional project context
from controllers.chat import description as base_description, prompt as base_prompt, project_structure, code

def strip_code_fences(content: str) -> str:
    lines = []
    for line in content.splitlines():
        if line.strip().startswith("```"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
def split_files(ai_output, project_root="."):
    files = {}
    current_file = None
    buffer = []

    for line in ai_output.splitlines():
        # ✅ Detect file markers in Python, JS, or HTML
        if any(line.strip().startswith(x) for x in ("# file:", "<!-- file:", "// file:")):
            # Save the previous file content before switching
            if current_file and buffer:
                content = "\n".join(buffer).strip()
                content = strip_code_fences(content)
                files[current_file] = content

            # ✅ Extract and clean the filename from the marker
            current_file = (
                line.replace("# file:", "")
                    .replace("<!-- file:", "")
                    .replace("-->", "")
                    .replace("// file:", "")
                    .strip()
            )
            buffer = []
        else:
            buffer.append(line)

    # ✅ Add the last file if present
    if current_file and buffer:
        content = "\n".join(buffer).strip()
        content = strip_code_fences(content)
        files[current_file] = content

    # ✅ Merge or append new content into existing routes.py files
    for path, content in list(files.items()):
        if path.endswith("routes.py"):
            file_path = os.path.join(project_root, path)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    existing = f.read()
                updated = existing.strip() + "\n\n" + content.strip()
                files[path] = updated
            else:
                files[path] = content.strip()

    return files


@app.route("/generate_feature", methods=["POST"])
def generate_feature():
    feature_desc = request.form.get("featureDescription")

    full_description = f"{base_description} {feature_desc}"

    final_prompt = f"""
    You are an AI developer. The project has this structure:

    {project_structure}

    Task: {full_description}

    Instructions:
    - Don't change the file named app.py under any circumstances.
    - Indicate the file path in comments like # file: <path>.
    - Also add the path to the nav bar {code} and don't change the existing paths.
    - If creating new features, place HTML in templates/ulogin/.
    - Add Flask routes in controllers/routes.py inside the ulogin blueprint.
    - Do not include <html>, <head>, or <body> tags.
    - All new or modified templates must extend 'ulayout.html' and put page-specific content inside % block content %% endblock % .
    - Keep code semantic, modular, and responsive.
    """

    response = model.generate_content(final_prompt)
    ai_output = response.text

    files = split_files(ai_output)
    print(files)

    for path, content in files.items():
        payload = {
            "file_path": path,
            "content": content,
            "commit_message": f"Auto-added feature: {feature_desc}"
        }
        mcp_response = requests.post(f"{MCP_SERVER_URL}/commit", json=payload)
        if mcp_response.status_code != 200:
            return f"MCP Error on {path}: {mcp_response.text}"

    return redirect("/features")

from flask import Blueprint, render_template, request, redirect, url_for, session

# Assuming 'ulogin' blueprint is defined here.
# For context, a blueprint definition might look like this:
# ulogin = Blueprint('ulogin', __name__, template_folder='../templates/ulogin')

# The user asked to add a new endpoint to an existing file.
# We'll add the new route handler within the existing ulogin blueprint context.

# Existing routes for the ulogin blueprint would be here...

@ulogin.route('/create_post', methods=['GET', 'POST'])
def create_blog():
    """
    Renders the blog creation page and handles form submission.
    """
    if 'user' not in session:
        return redirect(url_for('ulogin.login')) # Protect route

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Here, you would typically save the blog post to a database.
        # For this task, we will just print it and redirect.
        print(f"New Blog Post Submitted by {session['user']}:")
        print(f"Title: {title}")
        print(f"Content: {content}")
        
        return redirect(url_for('ulogin.uhome')) # Redirect to user home after creation

    return render_template('create_blog.html')

# Other routes continue below...

/* file: static/css/feature-card.css */
.feature-card-container {
  display: flex;
  justify-content: center;
  padding: 2rem 1rem;
}

.feature-card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  text-decoration: none;
  color: #333;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  width: 100%;
  max-width: 380px;
  display: block;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
}

.feature-card .card-image {
  width: 100%;
  height: 220px;
  object-fit: cover;
  background-color: #e9e9e9; /* Placeholder if image is missing */
}

.feature-card .card-content {
  padding: 1.5rem;
}

.feature-card .card-title {
  font-size: 1.6rem;
  font-weight: 600;
  margin: 0 0 0.5rem;
}

.feature-card .card-description {
  font-size: 1rem;
  line-height: 1.6;
  color: #555;
}