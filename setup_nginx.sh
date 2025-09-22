#!/bin/bash

echo "==========================================================="
echo "🔧 SETTING UP NGINX FOR svagnoni.linkeddata.es"
echo "==========================================================="

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx not found. Installing..."
    sudo apt update && sudo apt install -y nginx
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Nginx"
        exit 1
    fi
else
    echo "✅ Nginx is already installed"
fi

# Copy configuration
echo "🔧 Setting up site configuration..."
sudo cp nginx-simple-config.conf /etc/nginx/sites-available/svagnoni.linkeddata.es

# Enable the site
echo "🔧 Enabling site..."
sudo ln -sf /etc/nginx/sites-available/svagnoni.linkeddata.es /etc/nginx/sites-enabled/

# Disable default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🔧 Disabling default site..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test nginx configuration
echo "🔍 Testing Nginx configuration..."
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration test failed"
    exit 1
fi

# Start/restart nginx
echo "🚀 Starting Nginx..."
sudo systemctl enable nginx
sudo systemctl restart nginx

# Check status
if sudo systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
    echo ""
    echo "🌐 Your platform should now be accessible at:"
    echo "   - http://svagnoni.linkeddata.es/"
    echo "   - http://svagnoni.linkeddata.es/visualize"
    echo ""
    echo "🔍 Test with: python3 check_deployment.py"
else
    echo "❌ Failed to start Nginx"
    sudo systemctl status nginx
fi