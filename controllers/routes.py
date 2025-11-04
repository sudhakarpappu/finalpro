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
        if line.strip().startswith("# file:"):
            if current_file and buffer:
                content = "\n".join(buffer).strip()
                content = strip_code_fences(content)
                files[current_file] = content
            current_file = line.strip().replace("# file:", "").strip()
            buffer = []
        else:
            buffer.append(line)

    if current_file and buffer:
        content = "\n".join(buffer).strip()
        content = strip_code_fences(content)
        files[current_file] = content

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

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from blog_data import posts

# Blueprints
ulogin_blueprint = Blueprint('ulogin', __name__, template_folder='templates')
alogin_blueprint = Blueprint('alogin', __name__, template_folder='templates')

# --- User Routes ---
@ulogin_blueprint.route('/')
def index():
    return render_template('ulogin/index.html', posts=posts)

@ulogin_blueprint.route('/post/<int:post_id>')
def post(post_id):
    post = next((post for post in posts if post['id'] == post_id), None)
    if post:
        return render_template('ulogin/post.html', post=post)
    return "Post not found", 404

@ulogin_blueprint.route('/create')
def create_content():
    """Renders the page for users to create content."""
    if 'user' not in session:
        flash('You need to be logged in to create content.')
        return redirect(url_for('login'))
    return render_template('ulogin/create_content.html')


# --- Admin Routes ---
@alogin_blueprint.route('/admin_home')
def ahome():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('alogin/ahome.html')

# (keep other existing routes as they are)

<!-- file: templates/ulogin/create_content.html -->
{% extends 'ulogin/ulayout.html' %}

{% block content %}
<div class="content-creator-container">
  <h1>Create Your Content</h1>
  <p>Use the form below to draft your new blog post or educational guide.</p>
  
  <form class="content-form">
    <div class="form-group">
      <label for="title">Title</label>
      <input type="text" id="title" name="title" placeholder="Enter a catchy title" required>
    </div>
    
    <div class="form-group">
      <label for="content">Content</label>
      <textarea id="content" name="content" rows="12" placeholder="Start writing your amazing content here..."></textarea>
    </div>
    
    <div class="form-group">
      <label for="category">Category</label>
      <select id="category" name="category">
        <option value="technology">Technology</option>
        <option value="science">Science</option>
        <option value="history">History</option>
        <option value="art">Art</option>
      </select>
    </div>
    
    <button type="submit" class="btn-submit">Submit for Review</button>
  </form>
</div>
{% endblock %}

<!-- file: templates/ulogin/ulayout.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Edu Blog</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}" />
</head>
<body>

  <!-- TOP-RIGHT user info -->
  {% if session.get('user') %}
    <div class="user-section">
      <span>{{ session['user'] }} |</span>
      <a href="{{ url_for('logout') }}">Logout</a>
    </div>
  {% else %}
    <div class="user-section">
      <a href="{{ url_for('login') }}">Login</a>
    </div>
  {% endif %}

  <!-- CENTERED NAVIGATION -->
  <nav class="navMenu">
    <a href="{{ url_for('ulogin.index') }}">Home</a>
    <a href="{{ url_for('ulogin.create_content') }}">Create</a>
    <a href="#">Blog</a>
    <a href="#">Work</a>
    <a href="#">About</a>
    <div class="dot"></div>
  </nav>

  <!-- MAIN PAGE CONTENT -->
  <div class="container">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul class=flashes>
        {% for message in messages %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>

</body>
</html>

<!-- file: templates/ulogin/index.html -->
{% extends 'ulogin/ulayout.html' %}

{% block content %}
  <header class="main-header">
    <h1>Welcome to Edu Blog</h1>
    <p>Your daily source of educational content and inspiration.</p>
  </header>

  <!-- New Feature Card Section -->
  <section class="feature-card-section">
    <div class="feature-card">
      <div class="feature-card-icon">
        <!-- Using an inline SVG for simplicity, but could be an <img> -->
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>        
      </div>
      <div class="feature-card-content">
        <h3>Interactive Learning</h3>
        <p>Engage with our new interactive tutorials and quizzes designed to make learning fun and effective.</p>
        <a href="#" class="feature-card-link">Explore Now &rarr;</a>
      </div>
    </div>
  </section>
  <!-- End New Feature Card Section -->

  <div class="post-grid">
    {% for post in posts %}
      <a href="{{ url_for('ulogin.post', post_id=post.id) }}" class="post-card">
        <img src="{{ url_for('static', filename='img/' + post.image_url) }}" alt="{{ post.title }}">
        <div class="post-content">
          <h2>{{ post.title }}</h2>
          <p>{{ post.author }} - {{ post.date }}</p>
        </div>
      </a>
    {% endfor %}
  </div>
{% endblock %}

/* file: static/css/style.css */
/* (Assuming you have existing styles, add this at the end) */

/* --- Feature Card Styles --- */
.feature-card-section {
  width: 100%;
  padding: 2rem 0;
  display: flex;
  justify-content: center;
}

.feature-card {
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  padding: 1.5rem;
  max-width: 800px;
  width: 100%;
  border-left: 5px solid #6c5ce7;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.feature-card-icon {
  flex-shrink: 0;
  margin-right: 1.5rem;
  background-color: #f0f0f0;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-card-icon svg {
  width: 30px;
  height: 30px;
  color: #6c5ce7;
}

.feature-card-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #333;
}

.feature-card-content p {
  margin: 0 0 1rem 0;
  color: #666;
  line-height: 1.6;
}

.feature-card-link {
  text-decoration: none;
  color: #6c5ce7;
  font-weight: bold;
}

/* Responsive styles for the feature card */
@media (max-width: 768px) {
  .feature-card {
    flex-direction: column;
    text-align: center;
  }

  .feature-card-icon {
    margin-right: 0;
    margin-bottom: 1rem;
  }
}


/* --- Content Creator Form Styles --- */
.content-creator-container {
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  max-width: 800px;
  margin: 2rem auto;
}

.content-creator-container h1 {
  text-align: center;
  margin-bottom: 0.5rem;
}

.content-creator-container p {
  text-align: center;
  color: #666;
  margin-bottom: 2rem;
}

.content-form .form-group {
  margin-bottom: 1.5rem;
}

.content-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: #333;
}

.content-form input[type="text"],
.content-form textarea,
.content-form select {
  width: 100%;
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box; /* Important for padding and width */
}

.content-form textarea {
  resize: vertical;
}

.btn-submit {
  display: block;
  width: 100%;
  padding: 0.8rem;
  background-color: #6c5ce7;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.btn-submit:hover {
  background-color: #5849c9;
}

/* Flash message styles */
ul.flashes {
  list-style-type: none;
  padding: 10px;
  margin: 10px 0;
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}