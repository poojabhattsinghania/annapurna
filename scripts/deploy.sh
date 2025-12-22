#!/bin/bash
set -e

# =============================================================================
# Project Annapurna - EC2 Deployment Script
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Please don't run as root. Use a user with sudo privileges."
    exit 1
fi

# =============================================================================
# STEP 1: Install Docker and Docker Compose
# =============================================================================
install_docker() {
    log_info "Installing Docker..."

    # Update system
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Add current user to docker group
    sudo usermod -aG docker $USER

    log_info "Docker installed successfully!"
    log_warn "You may need to log out and back in for docker group changes to take effect."
}

# =============================================================================
# STEP 2: Setup project directory
# =============================================================================
setup_project() {
    log_info "Setting up project directory..."

    PROJECT_DIR="/home/$USER/annapurna"

    if [ ! -d "$PROJECT_DIR" ]; then
        mkdir -p "$PROJECT_DIR"
    fi

    log_info "Project directory: $PROJECT_DIR"
}

# =============================================================================
# STEP 3: Create environment file
# =============================================================================
create_env_file() {
    log_info "Creating production environment file..."

    if [ -f "$PROJECT_DIR/.env" ]; then
        log_warn ".env file already exists. Skipping creation."
        return
    fi

    cat > "$PROJECT_DIR/.env" << 'EOF'
# Database Configuration
DATABASE_NAME=annapurna
DATABASE_USER=annapurna
DATABASE_PASSWORD=CHANGE_ME_STRONG_PASSWORD_HERE

# LLM API Keys
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Qdrant Vector Database
QDRANT_URL=http://13.200.235.39:6333

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
API_VERSION=v1
EOF

    log_warn "Please edit $PROJECT_DIR/.env with your actual credentials!"
}

# =============================================================================
# STEP 4: Pull and start services
# =============================================================================
start_services() {
    log_info "Starting services..."

    cd "$PROJECT_DIR"

    # Build and start all services
    docker compose -f docker-compose.prod.yml up -d --build

    log_info "Waiting for services to be healthy..."
    sleep 30

    # Check service status
    docker compose -f docker-compose.prod.yml ps

    log_info "Services started!"
}

# =============================================================================
# STEP 5: Run database migrations
# =============================================================================
run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_DIR"

    # Wait for database to be ready
    sleep 10

    # Run alembic migrations
    docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

    log_info "Migrations completed!"
}

# =============================================================================
# STEP 6: Health check
# =============================================================================
health_check() {
    log_info "Running health check..."

    # Wait for API to be ready
    sleep 5

    HEALTH_URL="http://localhost:8000/health"

    if curl -s "$HEALTH_URL" | grep -q "healthy"; then
        log_info "API is healthy!"
    else
        log_error "API health check failed!"
        docker compose -f docker-compose.prod.yml logs api --tail=50
        exit 1
    fi
}

# =============================================================================
# Commands
# =============================================================================
case "$1" in
    install-docker)
        install_docker
        ;;
    setup)
        setup_project
        create_env_file
        ;;
    start)
        cd ${PROJECT_DIR:-/home/$USER/annapurna}
        docker compose -f docker-compose.prod.yml up -d --build
        ;;
    stop)
        cd ${PROJECT_DIR:-/home/$USER/annapurna}
        docker compose -f docker-compose.prod.yml down
        ;;
    restart)
        cd ${PROJECT_DIR:-/home/$USER/annapurna}
        docker compose -f docker-compose.prod.yml restart
        ;;
    logs)
        cd ${PROJECT_DIR:-/home/$USER/annapurna}
        docker compose -f docker-compose.prod.yml logs -f ${2:-}
        ;;
    migrate)
        run_migrations
        ;;
    health)
        health_check
        ;;
    full-deploy)
        install_docker
        setup_project
        create_env_file
        log_warn "Please update .env file and run: ./deploy.sh start"
        ;;
    *)
        echo "Usage: $0 {install-docker|setup|start|stop|restart|logs|migrate|health|full-deploy}"
        echo ""
        echo "Commands:"
        echo "  install-docker  Install Docker and Docker Compose"
        echo "  setup           Create project directory and env file"
        echo "  start           Start all services"
        echo "  stop            Stop all services"
        echo "  restart         Restart all services"
        echo "  logs [service]  View logs (optional: specify service name)"
        echo "  migrate         Run database migrations"
        echo "  health          Run health check"
        echo "  full-deploy     Run complete deployment setup"
        exit 1
        ;;
esac
