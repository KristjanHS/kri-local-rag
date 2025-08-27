- [ ] NLTK Data Management (IN PROGRESS)** 
  **CURRENT ISSUE**: Integration tests failing due to missing NLTK data packages
  
  **Problem Identified from Test Failures**:
  - Integration tests fail with: `LookupError: Resource averaged_perceptron_tagger_eng not found`
  - Current Dockerfiles only download `punkt_tab` but tests need additional NLTK packages
  - `UnstructuredMarkdownLoader` requires both sentence tokenization AND POS tagging data
  - Error occurs during markdown file processing in ingestion pipeline
  
  **Research Findings**:
  - `punkt_tab` is required for sentence tokenization (already implemented)
  - `averaged_perceptron_tagger_eng` is required for POS tagging in text classification
  - Runtime downloads in containers are unreliable (network, permissions, filesystem issues)
  - **Best practice**: Pre-download ALL required NLTK data during Docker build
  
  **UPDATED PLAN - Complete NLTK Pre-downloading**:
  
  **Sub-task 6.6.1**: ✅ COMPLETED - NLTK environment variable and data directory
  - ✅ `ENV NLTK_DATA=/opt/venv/nltk_data` already in both Dockerfiles
  - ✅ Directory created with proper permissions
  
  **Sub-task 6.6.2**: 🔄 IN PROGRESS - Update pre-download commands in Dockerfiles
  - ✅ Current: `punkt_tab` already downloaded
  - 🔄 **NEEDED**: Add `averaged_perceptron_tagger_eng` to download command
  - **Updated command**: `RUN python -m nltk.downloader -d /opt/venv/nltk_data punkt_tab averaged_perceptron_tagger_eng`
  - Place download after pip install but before USER directive
  
  **Sub-task 6.6.3**: ⏳ PENDING - Verify the fix works
  - Test download command in running container first (without rebuild)
  - Run integration tests that use markdown files
  - Confirm both `punkt_tab` and `averaged_perceptron_tagger_eng` data available
  - Verify `UnstructuredMarkdownLoader` and POS tagging works
  
  **Sub-task 6.6.4**: ⏳ PENDING - Update documentation
  - Document the complete NLTK data requirements in project README
  - Add comments in Dockerfiles explaining why both packages are necessary
  
  **Files to modify**: 
  - ✅ `docker/app.Dockerfile` (punkt_tab + averaged_perceptron_tagger_eng)
  - ✅ `docker/app.test.Dockerfile` (punkt_tab + averaged_perceptron_tagger_eng)
  
  **Debugging Plan** (Test outside Docker first to avoid multiple failed builds):
  1. **Step 1**: ✅ Identified exact error: `averaged_perceptron_tagger_eng` missing
  2. **Step 2**: 🔄 Test NLTK requirements locally outside Docker:
     - Create local Python environment
     - Install required packages: `unstructured`, `nltk`, `sentence-transformers`
     - Test NLTK download: `nltk.download('averaged_perceptron_tagger_eng')`
     - Verify UnstructuredMarkdownLoader works with test markdown file
     - Confirm all required NLTK packages are identified
  3. **Step 3**: ⏳ Test download in running container (if local test succeeds)
  4. **Step 4**: ⏳ Update Dockerfiles with confirmed working download command
  5. **Step 5**: ⏳ Single rebuild and verify all integration tests pass
  
  **Rationale**: 
  - Production reliability > image size optimization
  - Runtime downloads introduce failure points and slower startup
  - Modern NLTK + Unstructured library requires both tokenization AND POS tagging data
  - Container environments are not ideal for runtime downloads