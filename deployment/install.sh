#!/bin/bash
set -euo pipefail

# Installation script for libvirt-mcp-server
# This script installs the server as a systemd service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
INSTALL_DIR="/opt/libvirt-mcp-server"
CONFIG_DIR="/etc/libvirt-mcp-server"
LOG_DIR="/var/log/libvirt-mcp-server"
RUN_DIR="/var/run/libvirt-mcp-server"
SERVICE_USER="libvirt-mcp"
SERVICE_GROUP="libvirt"

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_dependencies() {
    log_info "Checking system dependencies..."
    
    # Check for required packages
    local missing_packages=()
    
    if ! command -v python3 &> /dev/null; then
        missing_packages+=("python3")
    fi
    
    if ! command -v pip3 &> /dev/null; then
        missing_packages+=("python3-pip")
    fi
    
    if ! dpkg -l | grep -q libvirt-dev; then
        missing_packages+=("libvirt-dev")
    fi
    
    if ! dpkg -l | grep -q libvirt-daemon-system; then
        missing_packages+=("libvirt-daemon-system")
    fi
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_error "Missing required packages: ${missing_packages[*]}"
        log_info "Install them with: apt update && apt install ${missing_packages[*]}"
        exit 1
    fi
    
    # Check if libvirtd is running
    if ! systemctl is-active --quiet libvirtd; then
        log_warn "libvirtd service is not running. Starting it..."
        systemctl start libvirtd
        systemctl enable libvirtd
    fi
}

create_user() {
    log_info "Creating service user and group..."
    
    # Create group if it doesn't exist
    if ! getent group "$SERVICE_GROUP" > /dev/null; then
        groupadd "$SERVICE_GROUP"
        log_info "Created group: $SERVICE_GROUP"
    fi
    
    # Create user if it doesn't exist
    if ! getent passwd "$SERVICE_USER" > /dev/null; then
        useradd -r -g "$SERVICE_GROUP" -d "$INSTALL_DIR" -s /bin/bash "$SERVICE_USER"
        log_info "Created user: $SERVICE_USER"
    fi
    
    # Add user to libvirt group for VM access
    usermod -a -G libvirt "$SERVICE_USER"
}

create_directories() {
    log_info "Creating directories..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    chown root:root "$CONFIG_DIR"
    chmod 755 "$CONFIG_DIR"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    # Create run directory
    mkdir -p "$RUN_DIR"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$RUN_DIR"
    chmod 755 "$RUN_DIR"
}

install_application() {
    log_info "Installing application..."
    
    # Copy source code
    cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    
    # Install uv if not present
    if ! command -v uv &> /dev/null; then
        log_info "Installing uv package manager..."
        pip3 install uv
    fi
    
    # Install dependencies and application
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" uv venv
    sudo -u "$SERVICE_USER" uv sync
    
    # Install the package in development mode
    sudo -u "$SERVICE_USER" .venv/bin/pip install -e .
}

install_config() {
    log_info "Installing configuration..."
    
    # Copy example configuration
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cp "$PROJECT_DIR/config.example.yaml" "$CONFIG_DIR/config.yaml"
        
        # Set appropriate permissions
        chown root:root "$CONFIG_DIR/config.yaml"
        chmod 644 "$CONFIG_DIR/config.yaml"
        
        log_info "Installed example configuration to $CONFIG_DIR/config.yaml"
        log_warn "Please review and customize the configuration file"
    else
        log_warn "Configuration file already exists at $CONFIG_DIR/config.yaml"
    fi
}

install_systemd_service() {
    log_info "Installing systemd service..."
    
    # Copy service file
    cp "$SCRIPT_DIR/systemd/libvirt-mcp-server.service" /etc/systemd/system/
    
    # Set permissions
    chown root:root /etc/systemd/system/libvirt-mcp-server.service
    chmod 644 /etc/systemd/system/libvirt-mcp-server.service
    
    # Reload systemd
    systemctl daemon-reload
    
    log_info "Systemd service installed"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    # Check if ufw is installed and active
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        log_info "UFW is active. Adding rule for port 8000..."
        ufw allow 8000/tcp comment "libvirt-mcp-server"
    elif command -v firewall-cmd &> /dev/null; then
        log_info "Firewalld detected. Adding rule for port 8000..."
        firewall-cmd --permanent --add-port=8000/tcp
        firewall-cmd --reload
    else
        log_warn "No firewall management tool detected or firewall is not active"
        log_warn "You may need to manually configure firewall rules for port 8000"
    fi
}

run_tests() {
    log_info "Running basic health check..."
    
    # Test configuration validation
    sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/libvirt-mcp-server" --validate-config --config "$CONFIG_DIR/config.yaml"
    
    log_info "Configuration validation passed"
}

main() {
    log_info "Starting libvirt-mcp-server installation..."
    
    check_root
    check_dependencies
    create_user
    create_directories
    install_application
    install_config
    install_systemd_service
    setup_firewall
    run_tests
    
    log_info "Installation completed successfully!"
    echo
    log_info "Next steps:"
    echo "  1. Review and customize the configuration: $CONFIG_DIR/config.yaml"
    echo "  2. Start the service: systemctl start libvirt-mcp-server"
    echo "  3. Enable auto-start: systemctl enable libvirt-mcp-server"
    echo "  4. Check service status: systemctl status libvirt-mcp-server"
    echo "  5. View logs: journalctl -u libvirt-mcp-server -f"
    echo
    log_warn "Remember to configure appropriate security settings before production use!"
}

# Run main function
main "$@"
