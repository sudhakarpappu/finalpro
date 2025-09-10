project_structure = """
FINAL_YEAR_PROJ/
├─ controllers/
│  ├─ db_setup.py
│  └─ routes.py
├─ pro/
├─ src/
├─ static/
│  ├─ css/
│  ├─ img/
│  └─ js/
├─ templates/
│  ├─ alogin/
│  │  ├─ ahome.html
│  │  ├─ alayout.html
│  │  └─ features.html
│  └─ ulogin/
│     ├─ uhome.html
│     ├─ ulayout.html
│     ├─ index.html
│     ├─ layout.html
│     ├─ login.html
│     └─ post.html
├─ tests/
├─ .env
├─ .gitignore
├─ app.py
├─ blog_data.py
└─ requirements.txt
"""
description = (
    "Add a new responsive feature card in the blog and link a CSS style. "
    "Also register a new endpoint in routes.py for the new page."
)

prompt = f"""
You are an AI developer. The project has this structure:

{project_structure}

Task: {description}

Instructions:
- Indicate the file path in comments like # file: <path>.
- For HTML and CSS files: generate only the required code changes.
-dont create a blueprint
- For routes.py: output ONLY the route decorator line in the form @app.route("/endpoint").
- Do not include <html>, <head>, or <body> tags.
- Keep code semantic, modular, and responsive.
"""
code="""<!DOCTYPE html>
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
    <a href="{{ url_for('index') }}">Home</a>
    <a href="#">Blog</a>
    <a href="#">Work</a>
    <a href="#">About</a>
    <div class="dot"></div>
  </nav>

  <!-- MAIN PAGE CONTENT -->
  <div class="container">
    {% block content %}{% endblock %}
  </div>

</body>
</html>"""
