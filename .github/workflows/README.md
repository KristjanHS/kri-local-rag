# GitHub Workflows Documentation

## CodeQL Analysis Workflow

### Configuration Options

The CodeQL workflow can be customized with the following options:

#### Initialize CodeQL Step
```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: ${{ matrix.language }}
    # Add custom queries if needed
    # queries: security-extended,security-and-quality
    # Add source root if needed
    # source-root: src/
```

#### Autobuild Step
```yaml
- name: Autobuild
  uses: github/codeql-action/autobuild@v3
  # If the build fails, the workflow will stop, and the code scanning
  # API will use the pre-built source code downloaded in the init step
  with:
    # Add build command if needed
    # command: pip install -r requirements.txt && python setup.py build
```

#### Analysis Step
```yaml
- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3
  with:
    category: "/language:${{ matrix.language }}"
    # Add upload options for better debugging
    upload: true
    # Add memory settings for large codebases
    # memory: 6144
```

### Best Practices

1. **Timeout**: 360 minutes (6 hours) to prevent hanging jobs
2. **Concurrency**: Cancels in-progress jobs on new commits
3. **Fetch Depth**: 2 for better PR context
4. **Matrix Strategy**: Prepared for multi-language support
5. **Manual Triggering**: Available via workflow_dispatch

## Semgrep Security Analysis Workflow

### Configuration Options

The Semgrep workflow can be customized with the following options:

#### Semgrep Scan Command
```bash
semgrep ci \
  --config auto \
  --sarif \
  --output semgrep.sarif \
  --baseline-commit ${{ github.event.pull_request.base.sha || github.event.before }} \
  --verbose \
  --metrics off
```

### Best Practices

1. **Timeout**: 30 minutes for faster feedback
2. **Concurrency**: Cancels in-progress jobs on new commits
3. **Python Setup**: Proper environment with caching
4. **Baseline Analysis**: Compares against base commit for PRs
5. **PR Integration**: Automatic commenting with findings summary
6. **Privacy**: Metrics collection disabled

### Testing Workflows

#### Method 1: Manual Trigger (Recommended)
1. Go to GitHub repository → Actions tab
2. Select the workflow you want to test
3. Click "Run workflow" button
4. Choose branch and click "Run workflow"

#### Method 2: Push to Main Branch
```bash
git checkout main
git merge dev
git push origin main
```

#### Method 3: Create a Test PR
```bash
git checkout -b test-workflows
git push origin test-workflows
# Create PR on GitHub
```

#### Method 4: Local Testing with Act
```bash
# Install act (GitHub Actions local runner)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Test CodeQL workflow
act workflow_dispatch -W .github/workflows/codeql.yml

# Test Semgrep workflow
act workflow_dispatch -W .github/workflows/semgrep.yml
```

### Troubleshooting

1. **YAML Validation Errors**: Remove inline comments from YAML files
2. **Permission Issues**: Check repository settings → Actions → General
3. **Timeout Issues**: Increase timeout-minutes in workflow
4. **Missing Secrets**: Add required secrets in repository settings
