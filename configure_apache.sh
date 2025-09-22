#!/bin/bash

# Apache Configuration Script for svagnoni.linkeddata.es
# Deliberation Knowledge Graph Platform

echo "========================================================="
echo "🔧 CONFIGURING APACHE FOR svagnoni.linkeddata.es"
echo "========================================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run with sudo privileges"
    echo "   Usage: sudo ./configure_apache.sh"
    exit 1
fi

# Enable required Apache modules
echo "🔧 Enabling Apache modules..."
a2enmod proxy proxy_http headers rewrite ssl
if [ $? -ne 0 ]; then
    echo "❌ Failed to enable Apache modules"
    exit 1
fi

# Copy the site configuration
echo "📋 Creating site configuration..."
cp apache-vhost-config.conf /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
if [ $? -ne 0 ]; then
    echo "❌ Failed to copy site configuration"
    exit 1
fi

# Check for SSL certificates
echo "🔍 Checking for SSL certificates..."
SSL_CERT=""
SSL_KEY=""
SSL_CHAIN=""

# Common locations for SSL certificates
if [ -f "/etc/ssl/certs/svagnoni.linkeddata.es.crt" ]; then
    SSL_CERT="/etc/ssl/certs/svagnoni.linkeddata.es.crt"
elif [ -f "/etc/ssl/certs/linkeddata.es.crt" ]; then
    SSL_CERT="/etc/ssl/certs/linkeddata.es.crt"
elif [ -f "/etc/letsencrypt/live/svagnoni.linkeddata.es/fullchain.pem" ]; then
    SSL_CERT="/etc/letsencrypt/live/svagnoni.linkeddata.es/fullchain.pem"
    SSL_KEY="/etc/letsencrypt/live/svagnoni.linkeddata.es/privkey.pem"
fi

if [ -f "/etc/ssl/private/svagnoni.linkeddata.es.key" ]; then
    SSL_KEY="/etc/ssl/private/svagnoni.linkeddata.es.key"
elif [ -f "/etc/ssl/private/linkeddata.es.key" ]; then
    SSL_KEY="/etc/ssl/private/linkeddata.es.key"
fi

if [ -f "/etc/ssl/certs/svagnoni.linkeddata.es-chain.crt" ]; then
    SSL_CHAIN="/etc/ssl/certs/svagnoni.linkeddata.es-chain.crt"
elif [ -f "/etc/ssl/certs/linkeddata.es-chain.crt" ]; then
    SSL_CHAIN="/etc/ssl/certs/linkeddata.es-chain.crt"
fi

# Update the configuration with correct SSL paths
if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
    echo "✅ Found SSL certificates:"
    echo "   Certificate: $SSL_CERT"
    echo "   Private Key: $SSL_KEY"
    [ -n "$SSL_CHAIN" ] && echo "   Chain: $SSL_CHAIN"

    # Update the configuration file
    sed -i "s|/path/to/ssl/certificate.crt|$SSL_CERT|g" /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
    sed -i "s|/path/to/ssl/private.key|$SSL_KEY|g" /etc/apache2/sites-available/svagnoni.linkeddata.es.conf

    if [ -n "$SSL_CHAIN" ]; then
        sed -i "s|/path/to/ssl/certificate-chain.crt|$SSL_CHAIN|g" /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
    else
        # Comment out the chain line if no chain file found
        sed -i 's|SSLCertificateChainFile|#SSLCertificateChainFile|g' /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
    fi
else
    echo "⚠️  SSL certificates not found in standard locations"
    echo "   You'll need to manually update the certificate paths in:"
    echo "   /etc/apache2/sites-available/svagnoni.linkeddata.es.conf"
    echo ""
    echo "   Look for your certificates in:"
    echo "   - /etc/ssl/certs/"
    echo "   - /etc/ssl/private/"
    echo "   - /etc/letsencrypt/live/"
    echo ""
    echo "   Or generate new certificates with:"
    echo "   sudo certbot --apache -d svagnoni.linkeddata.es"
fi

# Test Apache configuration
echo "🧪 Testing Apache configuration..."
apache2ctl configtest
if [ $? -ne 0 ]; then
    echo "❌ Apache configuration test failed"
    echo "   Please check the configuration file:"
    echo "   sudo nano /etc/apache2/sites-available/svagnoni.linkeddata.es.conf"
    exit 1
fi

# Enable the site
echo "🔌 Enabling the site..."
a2ensite svagnoni.linkeddata.es.conf
if [ $? -ne 0 ]; then
    echo "❌ Failed to enable site"
    exit 1
fi

# Disable default site if it exists
if [ -f "/etc/apache2/sites-enabled/000-default.conf" ]; then
    echo "🔇 Disabling default site..."
    a2dissite 000-default.conf
fi

# Start Apache
echo "🚀 Starting Apache..."
systemctl start apache2
if [ $? -ne 0 ]; then
    echo "❌ Failed to start Apache"
    systemctl status apache2
    exit 1
fi

# Enable Apache to start on boot
systemctl enable apache2

# Reload Apache configuration
echo "🔄 Reloading Apache configuration..."
systemctl reload apache2

echo ""
echo "✅ Apache configuration completed!"
echo ""
echo "🌐 Your platform should now be accessible at:"
echo "   https://svagnoni.linkeddata.es/"
echo ""
echo "📋 Next steps:"
echo "   1. Check if your Flask server is running:"
echo "      ./deploy_linkeddata.sh"
echo "   2. Test the deployment:"
echo "      python3 check_deployment.py"
echo ""
echo "🔍 Troubleshooting:"
echo "   • Check Apache status: sudo systemctl status apache2"
echo "   • Check Apache logs: sudo tail -f /var/log/apache2/error.log"
echo "   • Check site config: sudo nano /etc/apache2/sites-available/svagnoni.linkeddata.es.conf"

# Show Apache status
echo ""
echo "📊 Apache Status:"
systemctl is-active apache2 && echo "✅ Apache is running" || echo "❌ Apache is not running"