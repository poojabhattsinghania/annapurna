#!/bin/bash

# Project Annapurna Setup Script
# This script automates the initial setup process

set -e  # Exit on error

echo "========================================="
echo "Project Annapurna - Setup Script"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$python_version < 3.11" | bc -l) )); then
    echo -e "${RED}✗ Python 3.11+ required. Current version: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"

# Check PostgreSQL
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL not found. Please install PostgreSQL 15+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL found${NC}"

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists, skipping${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠ IMPORTANT: Edit .env and add your API keys:${NC}"
    echo "  - DATABASE_URL"
    echo "  - GEMINI_API_KEY (required)"
    echo "  - YOUTUBE_API_KEY (optional)"
    echo ""
    read -p "Press Enter after editing .env to continue..."
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Database setup
echo "Setting up database..."
echo -e "${YELLOW}Please ensure PostgreSQL is running and pgvector extension is installed${NC}"
echo ""
read -p "Have you created the database and installed pgvector? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "To set up the database manually:"
    echo "  sudo -u postgres psql"
    echo "  CREATE DATABASE annapurna;"
    echo "  \c annapurna"
    echo "  CREATE EXTENSION vector;"
    echo "  \q"
    echo ""
    exit 1
fi

# Run migrations
echo "Running database migrations..."
alembic upgrade head
echo -e "${GREEN}✓ Migrations completed${NC}"

# Seed database
echo "Seeding initial data..."
python -m annapurna.utils.seed_database
echo -e "${GREEN}✓ Database seeded${NC}"

# Success message
echo ""
echo "========================================="
echo -e "${GREEN}✓ Setup completed successfully!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start API server: uvicorn annapurna.api.main:app --reload"
echo "  3. Visit API docs: http://localhost:8000/v1/docs"
echo ""
echo "To start scraping:"
echo "  python -m annapurna.scraper.youtube --url <URL> --creator <NAME>"
echo ""
echo "See QUICKSTART.md for detailed usage instructions"
echo ""
