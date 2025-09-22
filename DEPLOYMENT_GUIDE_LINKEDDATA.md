# Deployment Guide for svagnoni.linkeddata.es

## 🎉 Deliberation Knowledge Graph Platform Deployment

Your improved visualization with enhanced lateral window is now ready for deployment! The Flask server is running locally and serving the improved interface.

### ✅ Current Status
- ✅ **Local Server**: Running on port 8085
- ✅ **Improved Visualization**: Enhanced lateral window with better UX
- ✅ **Data**: 12,295 triples, 559 contributions, 386 participants, 5 processes
- ⚠️ **Domain**: Needs web server configuration

### 🚀 What's Deployed
1. **Enhanced Visualization** (`/visualize`):
   - Modern lateral window with gradient design
   - Better node details with statistics and relationships
   - Interactive controls with live updates
   - Responsive design for all devices
   - Copy-to-clipboard functionality

2. **API Endpoints**:
   - `/api/stats` - Knowledge graph statistics
   - `/api/contributions` - Structured contribution data
   - `/sparql` - SPARQL endpoint for queries
   - `/api/export/ttl` - Export capabilities

### 🔧 Web Server Configuration Required

To make your platform accessible at `https://svagnoni.linkeddata.es`, you need to configure your web server to proxy requests to the local Flask server.

#### Option 1: Apache Configuration
```bash
# Copy the Apache configuration
sudo cp apache-vhost-config.conf /etc/apache2/sites-available/svagnoni.linkeddata.es.conf

# Update SSL certificate paths in the config file
sudo nano /etc/apache2/sites-available/svagnoni.linkeddata.es.conf

# Enable the site
sudo a2ensite svagnoni.linkeddata.es.conf
sudo a2enmod proxy proxy_http headers rewrite ssl

# Restart Apache
sudo systemctl restart apache2
```

#### Option 2: Nginx Configuration
```bash
# Copy the Nginx configuration
sudo cp nginx-site-config.conf /etc/nginx/sites-available/svagnoni.linkeddata.es

# Update SSL certificate paths in the config file
sudo nano /etc/nginx/sites-available/svagnoni.linkeddata.es

# Enable the site
sudo ln -s /etc/nginx/sites-available/svagnoni.linkeddata.es /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### 🔐 SSL Certificates
Update the SSL certificate paths in your web server configuration:
- Certificate file: Usually `/etc/ssl/certs/your-domain.crt`
- Private key: Usually `/etc/ssl/private/your-domain.key`
- Certificate chain: Usually `/etc/ssl/certs/your-domain-chain.crt`

### 🧪 Testing the Deployment
After configuring your web server, run:
```bash
python3 check_deployment.py
```

### 🌐 URLs Once Live
- **Main Interface**: https://svagnoni.linkeddata.es/
- **Enhanced Visualization**: https://svagnoni.linkeddata.es/visualize
- **Contributions Explorer**: https://svagnoni.linkeddata.es/contributions
- **SPARQL Endpoint**: https://svagnoni.linkeddata.es/sparql

### 🎨 Visualization Improvements
The enhanced visualization now features:

1. **Modern Lateral Window**:
   - Gradient header with floating close button
   - Structured node information display
   - Connection statistics and relationship mapping
   - Scrollable content with custom scrollbars

2. **Better Layout & Spacing**:
   - Optimized flex ratios (2.5:1) for graph and panel
   - Improved mobile responsiveness
   - Modern control groupings
   - Interactive legend with click-to-filter

3. **Enhanced User Experience**:
   - Loading states and animations
   - Copy-to-clipboard functionality
   - Better error handling
   - Professional typography and shadows

### 📋 Management Commands
```bash
# Start the platform
./deploy_linkeddata.sh

# Check deployment status
python3 check_deployment.py

# Stop the server
pkill -f sparql_server_production.py

# View logs
tail -f deployment.log
```

### 🔍 Troubleshooting
If the domain shows 503 Service Unavailable:
1. Ensure your web server is running
2. Check that proxy configuration is correct
3. Verify SSL certificates are valid
4. Check firewall settings
5. Review web server error logs

### 📊 What's Working
- ✅ Flask server running on localhost:8085
- ✅ All API endpoints responding
- ✅ SPARQL queries working
- ✅ Enhanced visualization ready
- ✅ Data loaded (12,295 triples)

The platform is ready - you just need to configure your web server to proxy requests to the local Flask application!