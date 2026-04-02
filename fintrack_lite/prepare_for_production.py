#!/usr/bin/env python3
"""
FinTrack Lite - Production Preparation Script

This script prepares the FinTrack Lite application for GitHub and cloud production deployment.
It creates all necessary configuration files, Docker setup, GitHub workflows, and environment templates.

Usage:
    python prepare_for_production.py
"""

import os
import sys
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent
GITHUB_DIR = PROJECT_ROOT / '.github'
WORKFLOWS_DIR = GITHUB_DIR / 'workflows'


def create_gitignore():
    """Create .gitignore file for the project."""
    gitignore_content = """# Environment Variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environments
venv/
ENV/
env/
.venv
pip-log.txt
pip-delete-this-directory.txt

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
*.iml
.sublime-project
.sublime-workspace

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
pytest-results.xml

# Database
*.db
*.sqlite
*.sqlite3

# Docker
.docker/
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Temporary files
tmp/
temp/
*.tmp

# Node modules (if using any frontend tools)
node_modules/
"""
    gitignore_path = PROJECT_ROOT / '.gitignore'
    gitignore_path.write_text(gitignore_content)
    print(f"✓ Created .gitignore")


def create_env_example():
    """Create .env.example file for environment variables."""
    env_example_content = """# FinTrack Lite Environment Configuration
# Copy this file to .env and fill in the actual values

# FastAPI Configuration
ENVIRONMENT=production
DEBUG=False

# Database Configuration
DATABASE_URL=sqlite:///./fintrack.db
# For PostgreSQL in production:
# DATABASE_URL=postgresql://user:password@localhost/fintrack_db

# JWT Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# API Configuration
API_TITLE=FinTrack Lite API
API_VERSION=1.0.0
API_DESCRIPTION=Financial Tracking Ecosystem with AI Analysis

# Ollama Configuration (Local AI)
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,https://yourdomain.com

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# AWS Configuration (if using S3 for file uploads)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BUCKET_NAME=fintrack-uploads
AWS_REGION=us-east-1

# Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ADMIN_EMAIL=admin@fintrack.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
"""
    env_path = PROJECT_ROOT / '.env.example'
    env_path.write_text(env_example_content)
    print(f"✓ Created .env.example")


def create_dockerfile():
    """Create Dockerfile for containerized deployment."""
    dockerfile_content = """FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 fintrack && chown -R fintrack:fintrack /app
USER fintrack

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""
    dockerfile_path = PROJECT_ROOT / 'Dockerfile'
    dockerfile_path.write_text(dockerfile_content)
    print(f"✓ Created Dockerfile")


def create_docker_compose():
    """Create docker-compose.yml for local development and production."""
    docker_compose_content = """version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fintrack-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite:///./fintrack.db
      - SECRET_KEY=${SECRET_KEY:-your-dev-secret-key}
      - OLLAMA_API_BASE=http://ollama:11434
      - ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
    volumes:
      - .:/app
      - ./fintrack.db:/app/fintrack.db
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - ollama
    networks:
      - fintrack-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  ollama:
    image: ollama/ollama:latest
    container_name: fintrack-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - fintrack-network
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

  # PostgreSQL for production (optional, uncomment for production use)
  # postgres:
  #   image: postgres:15-alpine
  #   container_name: fintrack-postgres
  #   environment:
  #     POSTGRES_USER: fintrack
  #     POSTGRES_PASSWORD: ${DB_PASSWORD:-change-me}
  #     POSTGRES_DB: fintrack_db
  #   ports:
  #     - "5432:5432"
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   networks:
  #     - fintrack-network

networks:
  fintrack-network:
    driver: bridge

volumes:
  ollama_data:
  # postgres_data:
"""
    docker_compose_path = PROJECT_ROOT / 'docker-compose.yml'
    docker_compose_path.write_text(docker_compose_content)
    print(f"✓ Created docker-compose.yml")


def create_github_workflows():
    """Create GitHub Actions workflows for CI/CD."""
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    # Test workflow
    test_workflow = """name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run linting
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Run tests
      run: |
        pytest test_app.py -v --tb=short
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
"""
    (WORKFLOWS_DIR / 'tests.yml').write_text(test_workflow)
    print(f"✓ Created GitHub Actions test workflow")

    # Build and push Docker image workflow
    docker_workflow = """name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Build Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: false
        tags: fintrack-lite:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    # Uncomment below to push to Docker Hub/GitHub Container Registry
    # - name: Login to GitHub Container Registry
    #   uses: docker/login-action@v3
    #   with:
    #     registry: ghcr.io
    #     username: ${{ github.actor }}
    #     password: ${{ secrets.GITHUB_TOKEN }}
    #
    # - name: Push Docker image
    #   uses: docker/build-push-action@v5
    #   with:
    #     context: .
    #     push: true
    #     tags: ghcr.io/${{ github.repository }}:latest
    #     cache-from: type=gha
    #     cache-to: type=gha,mode=max
"""
    (WORKFLOWS_DIR / 'docker.yml').write_text(docker_workflow)
    print(f"✓ Created GitHub Actions Docker workflow")

    # Security audit workflow
    security_workflow = """name: Security Audit

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install bandit safety
    
    - name: Run Bandit security check
      run: bandit -r . -ll -f json -o bandit-report.json
      continue-on-error: true
    
    - name: Run Safety check for dependency vulnerabilities
      run: safety check --json
      continue-on-error: true
"""
    (WORKFLOWS_DIR / 'security.yml').write_text(security_workflow)
    print(f"✓ Created GitHub Actions security workflow")


def create_github_templates():
    """Create GitHub issue and PR templates."""
    TEMPLATES_DIR = GITHUB_DIR / 'ISSUE_TEMPLATE'
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    # Bug report template
    bug_template = """---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''

---

## Describe the bug
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. See error

## Expected behavior
A clear and concise description of what you expected to happen.

## Screenshots
If applicable, add screenshots to help explain your problem.

## Environment
- OS: [e.g. macOS, Linux, Windows]
- Python Version: [e.g. 3.11]
- FastAPI Version: [run `pip show fastapi`]

## Additional context
Add any other context about the problem here.
"""
    (TEMPLATES_DIR / 'bug_report.md').write_text(bug_template)

    # Feature request template
    feature_template = """---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''

---

## Is your feature request related to a problem?
A clear and concise description of what the problem is.

## Describe the solution you'd like
A clear and concise description of what you want to happen.

## Describe alternatives you've considered
A clear and concise description of any alternative solutions or features you've considered.

## Additional context
Add any other context or screenshots about the feature request here.
"""
    (TEMPLATES_DIR / 'feature_request.md').write_text(feature_template)

    # PR template
    pr_template = """## Description
Brief description of the changes in this PR.

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issue
Fixes #(issue number)

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] All existing tests still pass

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have updated the documentation accordingly
- [ ] I have added tests to cover my changes
- [ ] All new and existing tests passed

## Screenshots (if applicable)
Add any relevant screenshots here.
"""
    (GITHUB_DIR / 'pull_request_template.md').write_text(pr_template)
    print(f"✓ Created GitHub issue and PR templates")


def create_deployment_guide():
    """Create deployment documentation."""
    deploy_guide = """# FinTrack Lite Deployment Guide

## Overview
This guide covers deploying FinTrack Lite to various cloud platforms.

## Prerequisites
- Docker and Docker Compose installed
- Git repository set up on GitHub
- Environment variables configured

## Local Development

### Using Docker Compose
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

## Cloud Deployment Options

### 1. Railway.app (Recommended for Beginners)

1. Push your code to GitHub
2. Connect your GitHub repository to Railway
3. Configure environment variables in Railway dashboard
4. Deploy

**Buildpack**: Auto-detected as Python

### 2. Render.com

1. Create a new Web Service
2. Connect your GitHub repository
3. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy

### 3. Heroku (Legacy)

```bash
heroku login
heroku create fintrack-lite
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

### 4. AWS (EC2)

1. Create EC2 instance (Ubuntu 22.04)
2. Connect via SSH
3. Install Docker and Docker Compose
4. Clone repository
5. Configure .env file
6. Run: `docker-compose -f docker-compose.yml up -d`

### 5. Google Cloud Run (Serverless)

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/fintrack-lite

# Deploy
gcloud run deploy fintrack-lite \\
  --image gcr.io/PROJECT_ID/fintrack-lite \\
  --platform managed \\
  --region us-central1 \\
  --set-env-vars SECRET_KEY=your-secret-key
```

### 6. DigitalOcean App Platform

1. Connect GitHub repository
2. Select "Docker" as the Build Type
3. Configure environment variables
4. Deploy

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations completed
- [ ] CORS origins updated
- [ ] SSL/TLS certificate installed
- [ ] Rate limiting configured
- [ ] Monitoring and logging set up
- [ ] Backup strategy implemented
- [ ] Security headers configured

## Environment Variables for Production

```
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-strong-random-key>
DATABASE_URL=<production-database-url>
OLLAMA_API_BASE=<ollama-endpoint>
ALLOWED_ORIGINS=<your-domain>
```

## Monitoring

### Application Logs
Access through your hosting provider's dashboard or using:
```bash
# Docker
docker-compose logs -f api
```

### Health Checks
```bash
curl https://your-domain.com/health
```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check database server is running and accessible

### Ollama Connection Issues
- Ensure Ollama service is running
- Verify OLLAMA_API_BASE URL is correct

### CORS Issues
- Update ALLOWED_ORIGINS in environment variables
- Restart the application

## Rollback Procedure

### Git-based deployments
```bash
git revert <commit-hash>
git push
```

### Docker deployments
```bash
docker-compose down
# Restore to previous image version
docker-compose up -d
```

## Support
For issues, please open a GitHub issue with:
- Hosting platform
- Error logs
- Steps to reproduce
"""
    deploy_path = PROJECT_ROOT / 'DEPLOYMENT.md'
    deploy_path.write_text(deploy_guide)
    print(f"✓ Created DEPLOYMENT.md")


def create_contributing_guide():
    """Create contributing guidelines."""
    contributing = """# Contributing to FinTrack Lite

We love your input! We want to make contributing to FinTrack Lite as easy and transparent as possible.

## Code of Conduct

### Our Pledge
In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone.

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check if the issue already exists. When creating a bug report, please include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps which reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed and why it's a problem
- Include screenshots if possible

### Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- Use a clear and descriptive title
- Provide a step-by-step description of the suggested enhancement
- Provide specific examples to demonstrate the steps
- Describe the current behavior and the expected behavior

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Update documentation as needed
4. Ensure your code passes linting and tests
5. Issue a pull request with a clear title and description

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/fintrack-lite.git
cd fintrack-lite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_app.py -v

# Start development server
uvicorn main:app --reload
```

## Styleguides

### Python Code Style
- Use PEP 8 conventions
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions and classes

### Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Documentation
- Use clear and concise language
- Include code examples where helpful
- Update README.md for significant changes

## License
By contributing, you agree that your contributions will be licensed under its MIT License.

## Questions?
Feel free to open an issue for any questions!
"""
    contrib_path = PROJECT_ROOT / 'CONTRIBUTING.md'
    contrib_path.write_text(contributing)
    print(f"✓ Created CONTRIBUTING.md")


def create_github_config():
    """Create GitHub-specific configuration files."""
    # .github/dependabot.yml
    GITHUB_DIR.mkdir(parents=True, exist_ok=True)
    
    dependabot = """version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    allow:
      - dependency-type: "all"
    reviewers:
      - "your-username"
    commit-message:
      prefix: "chore:"
      include: "scope"
"""
    (GITHUB_DIR / 'dependabot.yml').write_text(dependabot)
    print(f"✓ Created .github/dependabot.yml")


def create_makefile():
    """Create Makefile for common tasks."""
    makefile_content = """# FinTrack Lite Makefile

.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help:
\t@echo "FinTrack Lite - Development Commands"
\t@echo "===================================="
\t@echo "make install       - Install dependencies"
\t@echo "make dev          - Start development server"
\t@echo "make test         - Run tests"
\t@echo "make lint         - Run linters"
\t@echo "make format       - Format code"
\t@echo "make clean        - Clean up generated files"
\t@echo "make docker-build - Build Docker image"
\t@echo "make docker-up    - Start Docker containers"
\t@echo "make docker-down  - Stop Docker containers"

install:
\tpip install -r requirements.txt

dev:
\tuvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
\tpytest test_app.py -v --tb=short

lint:
\tflake8 . --max-line-length=100 --exclude=venv,__pycache__
\tpylint *.py --disable=missing-docstring

format:
\tblack . --line-length=100

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete
\trm -rf .pytest_cache
\trm -rf htmlcov
\trm -rf .coverage

docker-build:
\tdocker-compose build

docker-up:
\tdocker-compose up -d

docker-down:
\tdocker-compose down

seed:
\tpython seed.py
"""
    makefile_path = PROJECT_ROOT / 'Makefile'
    makefile_path.write_text(makefile_content)
    print(f"✓ Created Makefile")


def create_production_requirements():
    """Create production-specific requirements."""
    prod_requirements = """# Production Requirements for FinTrack Lite
# Install with: pip install -r requirements-prod.txt

# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic[email]==2.5.0
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
httpx==0.25.2

# Database drivers (uncomment as needed)
# psycopg2-binary==2.9.9  # PostgreSQL
# pymysql==1.1.0  # MySQL
# pyodbc==4.0.39  # SQL Server

# Production server
gunicorn==21.2.0
python-multipart==0.0.6

# Security
python-dotenv==1.0.0
cryptography==41.0.7

# Monitoring & Logging
prometheus-client==0.19.0
python-json-logger==2.0.7

# Optional: AWS integration
# boto3==1.29.7

# Testing (development only, remove for production)
# pytest==7.4.3
# pytest-cov==4.1.0
"""
    prod_path = PROJECT_ROOT / 'requirements-prod.txt'
    prod_path.write_text(prod_requirements)
    print(f"✓ Created requirements-prod.txt")


def create_health_check_endpoint():
    """Create a note about adding health check endpoint to main.py."""
    health_note = """# Health Check Endpoint Addition

Add the following route to main.py if not already present:

```python
@app.get("/health")
async def health_check():
    \"\"\"Health check endpoint for deployment platforms.\"\"\"
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
```

This endpoint is used by:
- Docker healthchecks
- Load balancers
- Monitoring systems
- Deployment platforms
"""
    health_path = PROJECT_ROOT / 'HEALTH_CHECK.md'
    health_path.write_text(health_note)
    print(f"✓ Created HEALTH_CHECK.md (reminder to add endpoint)")


def create_main_summary():
    """Create a summary document of all changes."""
    summary = """# FinTrack Lite - Production Preparation Summary

## Files Created

### Configuration Files
- **.env.example** - Environment variables template
- **.gitignore** - Git ignore patterns
- **Dockerfile** - Container configuration
- **docker-compose.yml** - Multi-container orchestration
- **Makefile** - Development convenience commands

### Documentation
- **DEPLOYMENT.md** - Cloud deployment guides
- **CONTRIBUTING.md** - Contribution guidelines
- **HEALTH_CHECK.md** - Health endpoint reminder

### GitHub Configuration
- **.github/workflows/tests.yml** - Automated testing
- **.github/workflows/docker.yml** - Docker build and push
- **.github/workflows/security.yml** - Security scanning
- **.github/ISSUE_TEMPLATE/bug_report.md** - Bug report template
- **.github/ISSUE_TEMPLATE/feature_request.md** - Feature request template
- **.github/pull_request_template.md** - Pull request template
- **.github/dependabot.yml** - Dependency updates

### Additional Files
- **requirements-prod.txt** - Production dependencies

## Next Steps

### 1. Initialize Git Repository
```bash
cd fintrack_lite
git init
git add .
git commit -m "Initial commit: FinTrack Lite production setup"
```

### 2. Create GitHub Repository
- Go to https://github.com/new
- Create a new repository
- Follow the instructions to push your local repository

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 4. Set Up GitHub Secrets
The following workflows may need GitHub Secrets (Settings > Secrets):
- Docker Hub credentials (if pushing to Docker Hub)
- PyPI token (if publishing package)
- Cloud provider credentials (if deploying directly)

### 5. Add Health Check Endpoint
Make sure main.py includes the health check endpoint:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
```

### 6. Test Locally
```bash
make docker-up
curl http://localhost:8000/health
make docker-down
```

### 7. Deploy to Cloud
Choose your preferred platform from DEPLOYMENT.md and follow the guide.

## Production Deployment Checklist

Security:
- [ ] Change SECRET_KEY to a strong random value
- [ ] Set DEBUG=False in production
- [ ] Configure CORS origins for your domain
- [ ] Use HTTPS/SSL certificates
- [ ] Rotate API keys regularly
- [ ] Set up rate limiting

Database:
- [ ] Migrate to PostgreSQL for production
- [ ] Set up automated backups
- [ ] Configure connection pooling
- [ ] Test disaster recovery

Monitoring:
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Configure application logging
- [ ] Set up health check monitoring
- [ ] Configure alerting

Deployment:
- [ ] Set up CI/CD pipeline
- [ ] Test deployment process
- [ ] Configure auto-scaling
- [ ] Set up load balancing

## Support & Documentation

- GitHub Issues: Report bugs here
- CONTRIBUTING.md: How to contribute
- DEPLOYMENT.md: Deployment guides
- README.md: Project overview

## Questions?

Refer to the documentation files created or open a GitHub issue.

---
Generated on: 2024
Script: prepare_for_production.py
"""
    summary_path = PROJECT_ROOT / 'PRODUCTION_SETUP_SUMMARY.md'
    summary_path.write_text(summary)
    print(f"✓ Created PRODUCTION_SETUP_SUMMARY.md")


def main():
    """Main function to run all setup tasks."""
    print("\n" + "=" * 60)
    print("FinTrack Lite Production Preparation")
    print("=" * 60 + "\n")

    try:
        # Create all necessary files
        create_gitignore()
        create_env_example()
        create_dockerfile()
        create_docker_compose()
        create_github_workflows()
        create_github_templates()
        create_github_config()
        create_deployment_guide()
        create_contributing_guide()
        create_makefile()
        create_production_requirements()
        create_health_check_endpoint()
        create_main_summary()

        print("\n" + "=" * 60)
        print("✓ Production preparation completed successfully!")
        print("=" * 60)
        print("\n📋 Next Steps:")
        print("1. Review PRODUCTION_SETUP_SUMMARY.md")
        print("2. Edit .env.example → .env with your configuration")
        print("3. Add the health check endpoint to main.py")
        print("4. Run: git init && git add . && git commit -m 'Initial commit'")
        print("5. Create repository on GitHub and push")
        print("6. Configure GitHub Secrets if needed")
        print("7. Deploy using DEPLOYMENT.md guidelines\n")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
