# Automating Project Startup with Virtual Environment Activation & VS Code Workspace

This short guide shows how to jump straight into your **hands‑on‑llm** project from any WSL shell with a single command.  After following the steps, typing `llm` will:

1. **cd** into `~/projects/hands-on-llm`
2. **Activate** the .venv Python virtual environment (if it exists)
3. **Launch** VS Code, opening *hands‑on‑llm.code-workspace* in a fresh window
4. Leave you inside the project directory with the venv active:

```bash
(.venv) kristjan@pcname:~/projects/hands-on-llm$
```

---

## 1  Write the helper function

Add the following function to the bottom of your `~/.bashrc` (or `~/.zshrc`):

```bash
# ——— quick project launcher ———
llm () {
    local project=~/projects/hands-on-llm
    local ws="$project/hands-on-llm.code-workspace"

    cd "$project" || return 1                           # jump into the project
    [ -f .venv/bin/activate ] && source .venv/bin/activate # activate venv if present

    # open the workspace in a new VS Code window (backgrounded)
    code "$ws" >/dev/null 2>&1 &
}
```

### Why this works

* **Function vs script** Because the code runs *in the current shell*, the `cd` and `source` calls persist after the function returns.
* **Background `&`** Lets you keep using the terminal instantly.

---

## 2  Reload your shell

```bash
source ~/.bashrc   # or source ~/.zshrc
```

Check the definition:

```bash
type llm   # should say "llm is a function" and print its body
```

---

## 3  Use it!

From any directory inside WSL:

```bash
llm        # → VS Code workspace opens, venv activated, cwd changed
```

If the virtual environment is missing you’ll see no error—the function simply skips activation.

---

## Troubleshooting

| Symptom                          | Fix                                                                                 |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| *Function not found*             | Did you reload the shell (`source ~/.bashrc`)?                                      |
| *Still an old alias*             | Run `type llm` – if it says “alias”, `unalias llm`, reload, then verify again.      |
| *Need venv outside VS Code too*  | The venv is activated **before** launching VS Code, so the parent shell retains it. |

---

### That’s it!

You now have a one‑word command that sets up the project environment and opens your workspace every time.
