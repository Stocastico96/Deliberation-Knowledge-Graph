#!/bin/bash
# Update nginx configuration for svagnoni.linkeddata.es

echo "🔧 Updating nginx configuration..."

# Copy updated config to sites-available
sudo cp /home/svagnoni/Deliberation-Knowledge-Graph/nginx-simple-config.conf /etc/nginx/sites-available/svagnoni.linkeddata.es

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

echo "✅ Nginx configuration updated and reloaded"