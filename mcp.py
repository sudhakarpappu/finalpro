import os
from git import Repo

aGITHUB_PAT = os.getenv("GITHUB_PAT")  # store this in GitHub secrets
REPO_DIR = "/tmp/finalpro"
REPO_URL = "https://github.com/sudhakarpappu/finalpro.git"

def commit_code_change(file_path: str, content: str, commit_message: str):
    if not os.path.exists(REPO_DIR):
        Repo.clone_from(REPO_URL, REPO_DIR)
    repo = Repo(REPO_DIR)

    file_full_path = os.path.join(REPO_DIR, file_path)
    with open(file_full_path, "w") as f:
        f.write(content)

    repo.git.add(file_path)
    repo.index.commit(commit_message)
    origin = repo.remote(name="origin")
    origin.push()
