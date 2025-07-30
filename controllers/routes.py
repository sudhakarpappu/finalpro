from flask import render_template, request, redirect, url_for, flash, session # type: ignore
from app import app, mysql  # Import AFTER app & mysql are defined
from blog_data import blog_posts
from datetime import datetime

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
            return render_template('/alogin/ahome.html', user=user)  # change route name as needed
        elif user[5] == 2:
            return render_template('/ulogin/uhome.html', user=user)  # change route name as needed
        else:
            flash('Unknown role. Contact admin.', 'warning')
            return redirect('/login')
    else:
        flash('Invalid email or password', 'danger')
        return redirect('/login')
