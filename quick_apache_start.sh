#!/bin/bash

echo "🚀 Quick Apache Setup for svagnoni.linkeddata.es"
echo "================================================"

# Enable required modules
sudo a2enmod proxy proxy_http headers rewrite ssl

# Copy configuration
sudo cp apache-vhost-config.conf /etc/apache2/sites-available/svagnoni.linkeddata.es.conf

# Enable site
sudo a2ensite svagnoni.linkeddata.es.conf

# Disable default site
sudo a2dissite 000-default.conf 2>/dev/null || true

# Start Apache
sudo systemctl start apache2
sudo systemctl enable apache2

echo "✅ Apache started!"
echo "🌐 Check: https://svagnoni.linkeddata.es/"