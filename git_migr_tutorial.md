# Migrating **hands-on-llm/phase2/RAG_app** to a new repository: `kri_local_RAG`

This guide shows a **safe, repeatable** way to extract the RAG_app portion of your
`hands‑on‑llm` monorepo into its own GitHub repository named
`kri_local_RAG`.  The process keeps your original project intact while giving
you a clean, history‑free copy of the selected files.

> **Why not use `git filter‑repo` / `git subtree`?**
> They are great when you need to preserve commit history.  In this case you
> asked for a *fresh* repo with just the current state, so a straight copy is
> simpler, less error‑prone and keeps the original repo small.

---

## 0  Prerequisites

| Requirement                            | Command to check                            | Notes                                  |
| -------------------------------------- | ------------------------------------------- | -------------------------------------- |
| Git ≥ 2.34                             | `git --version`                             | Needed for `git switch -c` shown below |
| GitHub account with repo‑create rights | —                                           | Personal account works fine            |
| SSH key or PAT set up                  | `ssh -T git@github.com`<br>`gh auth status` | PAT must have `repo` scope             |

---

## 1  Create the empty GitHub repository

1. Open [https://github.com/new](https://github.com/new) in your browser.
2. Fill in:
   * **Repository name** → `kri_local_RAG`
   * Visibility as you prefer (Public / Private)
   * **DO NOT** add a README, `.gitignore`, or license here – we’ll copy them.
3. Click **Create repository** and leave the page open; the *Quick Setup*
   section shows the SSH/HTTPS URL you’ll need shortly.

---

## 2  Prepare a scratch branch in the *source* project

```bash
# From your existing hands‑on‑llm clone
cd hands-on-llm

# Always work on a throw‑away branch to keep main pristine
git switch -c export-rag-subset
```

*(If you prefer a fresh working copy instead, run `git clone` into a temporary
folder first.)*

---

## 3  Create and initialise the *target* repo locally

```bash
# Work one directory above hands‑on‑llm
cd ..

# Make a workspace for the new repo
mkdir kri_local_RAG && cd kri_local_RAG

# Initialise the empty repository and set the default branch to **main**
git init -b main

# Add the GitHub remote: for HTTPS auth:
git remote add origin https://github.com/KristjanHS/kri_local_RAG.git
# OR replace URL if you use SSH:
# git remote add origin git@github.com:KristjanHS/kri_local_RAG.git
```

> **Tip**  If your Git defaults to `master`, force `main` with `git symbolic-ref`
> or use `git config --global init.defaultBranch main` for future repos.

---

## 4  Copy the desired files

### 4.1  Ensure helper directories exist

```bash
mkdir -p .vscode .github/workflows .gemini docker RAG_app
```

### 4.2  Bulk‑copy the RAG subset and supporting files

```bash
# Core phase2 RAG sources
cp -r ../hands-on-llm/phase2/*            .

# VS Code & Gemini configs
cp ../hands-on-llm/.vscode/extensions.json     .vscode/
cp ../hands-on-llm/.gemini/settings.json       .vscode/settings.json
cp ../hands-on-llm/.gemini/config.yaml         .gemini/

# CI workflow
cp ../hands-on-llm/.github/workflows/python-lint-test.yml .github/workflows/

# Repo‑wide helpers
cp ../hands-on-llm/.aiignore                  .
cp ../hands-on-llm/.flake8                    .
cp ../hands-on-llm/.gitattributes             .
cp ../hands-on-llm/.gitignore                 .
cp ../hands-on-llm/.pre-commit-config.yaml    .

# Project descriptors
cp ../hands-on-llm/pyproject.toml             .
cp ../hands-on-llm/LICENSE                    .

# Workspace & docs – rename to match new repo
cp ../hands-on-llm/hands-on-llm.code-workspace kri_local_RAG.code-workspace
cp ../hands-on-llm/README.md                   README.md

# Runtime helpers
cp ../hands-on-llm/weaviate_docker_run.sh     .
cp ../hands-on-llm/phase2/requirements.txt          .
cp -r ../hands-on-llm/phase2/docker                 ./docker
cp -r ../hands-on-llm/phase2/RAG_app               ./src
```

Feel free to add any other files you discover later with the same `cp` pattern.

---

## 5  Review and clean up (optional but recommended)

1. **Open the new folder in VS Code**: `code .`
2. Search for any references to `hands-on-llm` and update paths or badges.
3. Edit `README.md` to change the title and project description.
4. Run `flake8 .` or your preferred linter to catch obvious issues.

---

## 6  Commit and push

```bash
# Stage everything under the new repo
git add --all

# Commit with a clear message
git commit -m "Initial import from hands-on-llm phase2/RAG_app"

# Verify branch name (should be main)
git branch --show-current

# Push and set upstream
git push -u origin main
```

GitHub will now show your freshly‑populated repository.  Set up **branch
protection** and **continuous integration** as needed.

---

## 7  Next steps

1. **Enable pre‑commit hooks**: `pre-commit install`
2. **Create a dev container** (optional) if you use GitHub Codespaces or
   VS Code Dev Containers.
3. **Archive or tag** the original branch `export-rag-subset` so teammates know
   it was only for the export.
4. **Open issues** in the new repo for any TODO items you noted during review.

---

### Troubleshooting

| Symptom                                        | Cause                                                     | Fix                                                                    |
| ---------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| `fatal: refusing to merge unrelated histories` | You accidentally added a README when creating the GH repo | Delete the repo and recreate it **without** initial files              |
| Copied dot‑files are missing                   | Target sub‑folders weren’t created                        | Run the `mkdir -p` commands in 4.1 before copying                      |
| Push rejected – branch protection              | Your org enforces PRs to main                             | Push to a temp branch (`git push -u origin init‑import`) and open a PR |

---

## 8  FAQ

<details>
<summary>Can I keep commit history instead?</summary>
Use [`git filter-repo`](https://github.com/newren/git-filter-repo) or
[`git subtree split`](https://github.com/git/git/blob/master/contrib/subtree/git-subtree.txt)
so you can extract the past commits of `phase2/RAG_app` while pruning the rest.
</details>

<details>
<summary>Why copy instead of submodule?</summary>
Submodules add indirection and tooling friction.  A standalone repo is simpler
when the codebases evolve independently.
</details>

---

🚀 **You now have a clean, standalone `kri_local_RAG` repository.** Happy
hacking!
