# Development Guide

This guide covers setting up your development environment, automating project startup, and (optionally) migrating the repository.

---

## Quick Project Launcher (WSL/VS Code)

Add this function to your `~/.bashrc` or `~/.zshrc` to jump into the project, activate the venv, and open VS Code:

```bash
llm () {
    local project=~/projects/kri-local-rag
    local ws="$project/kri-local-rag.code-workspace"
    cd "$project" || return 1
    [ -f .venv/bin/activate ] && source .venv/bin/activate
    code "$ws" >/dev/null 2>&1 &
}
```

- **Reload your shell:**
  ```bash
  source ~/.bashrc   # or source ~/.zshrc
  ```
- **Usage:**
  ```bash
  llm  # Opens VS Code, activates venv, sets cwd
  ```

---

## Troubleshooting the Launcher

| Symptom                | Fix                                                      |
|------------------------|----------------------------------------------------------|
| Function not found     | Reload your shell (`source ~/.bashrc`)                   |
| Still an old alias     | `unalias llm`, reload, then verify with `type llm`       |
| Need venv outside VS   | venv is activated before launching VS Code               |

---

## Development Tips

- Use a Python virtual environment (`.venv`) for dependencies
- Use `pip install -r requirements.txt` to install dependencies
- Use VS Code workspace for best experience
- Use Docker Compose for all service management

---

## Appendix: Repository Migration

If you need to migrate this project from a monorepo or another repo, follow these steps:

### 1. Prepare the New Repo
- Create a new empty repo on GitHub (no README, .gitignore, or license)
- Clone it locally

### 2. Copy Files
- Copy the desired files and folders from the old repo to the new one
- Use `cp` or your file manager

### 3. Initialize and Push
```bash
git init -b main
git remote add origin <your-new-repo-url>
git add --all
git commit -m "Initial import"
git push -u origin main
```

### 4. (Optional) Clean Up
- Update paths, badges, and README as needed
- Set up branch protection and CI if desired

### Troubleshooting
- If you see `fatal: refusing to merge unrelated histories`, recreate the repo without initial files
- If files are missing, ensure you created all needed subfolders before copying

---

**You now have a streamlined development workflow and migration reference!** 