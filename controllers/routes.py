from flask import render_template, request, redirect, url_for, flash, session # type: ignore
from app import app, mysql  # Import AFTER app & mysql are defined
from blog_data import blog_posts
from datetime import datetime
import google.generativeai as genai # type: ignore 
import os
from dotenv import load_dotenv, find_dotenv  # type: ignore

import base64
import requests # type: ignore

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

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']  # Plain password
    created = datetime.now()

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users (username, email, password, created_at) VALUES (%s, %s, %s, %s)",
                (name, email, password, created))
    mysql.connection.commit()
    cur.close()

    return redirect('/login')

@app.route('/signin', methods=['POST']) 
def signin(): 
    email = request.form['email'] 
    password = request.form['password'] 
 
    cur = mysql.connection.cursor()
    
    # Join users and role to get user's role info
    query = """
        SELECT users.*, role.name 
        FROM users 
        JOIN role ON users.rid = role.rid 
        WHERE users.email = %s
    """
    cur.execute(query, (email,))
    user = cur.fetchone()
    cur.close()

    print("User from DB:", user)
    print("Email entered:", email)
    print("Password entered:", password)

    if user and user[3] == password:  # Assuming password is at index 3
        session['user'] = user[1]  # user[1] = name
        session['rid'] = user[5]   # user[5] = rid or role name if selected
        print(user[4])
        if user[5] == 1:  # user[4] = rid (int), 1 for admin
            return render_template('/alogin/ahome.html', user=user,posts=blog_posts)  # change route name as needed
        elif user[5] == 2:
            return render_template('/ulogin/uhome.html', user=user,posts=blog_posts)  # change route name as needed
        else:
            flash('Unknown role. Contact admin.', 'warning')
            return redirect('/login')
    else:
        flash('Invalid email or password', 'danger')
        return redirect('/login')

@app.route('/Features')
def features(): 
    return render_template('/alogin/features.html')

load_dotenv(find_dotenv())

genai.configure(api_key=os.getenv("API_KEY"))

model = genai.GenerativeModel("gemini-pro")


@app.route("/generate_feature", methods=["POST"])
def generate_feature():
    description = request.form.get("featureDescription")

    prompt = f"""Generate a minimal HTML+CSS block that describes the following blog feature: {description}.
    Do not include <html>, <head>, or <body> tags. Keep it responsive and semantic."""

    response = model.generate_content(prompt)
    generated_html = response.text

    return render_template("features.html", generated_code=generated_html)



# GitHub integration for feature approval

GITHUB_TOKEN = os.environ.get("aGITHUB_PAT")
REPO_OWNER = "sudhakarpappu"
REPO_NAME = "finalpro"
BRANCH = "main"

@app.route("/approve_feature", methods=["POST"])
def approve_feature():
    code = request.form.get("code_to_deploy")
    filename = f"features_pending/feature_{int(time.time())}.html"

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    data = {
        "message": "Add new feature via admin panel",
        "content": base64.b64encode(code.encode()).decode(),
        "branch": BRANCH
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code == 201:
        return redirect("/features")
    else:
        return f"GitHub Error: {response.json()}"
