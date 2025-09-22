# Manual Apache Configuration for svagnoni.linkeddata.es

## 🔧 Step-by-Step Apache Setup

### Method 1: Automated Script (Recommended)
Run the automated configuration script:
```bash
sudo ./configure_apache.sh
```

### Method 2: Manual Configuration

#### Step 1: Enable Apache Modules
```bash
sudo a2enmod proxy proxy_http headers rewrite ssl
```

#### Step 2: Copy Site Configuration
```bash
sudo cp apache-vhost-config.conf /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
```

#### Step 3: Find Your SSL Certificates
Check these common locations:
```bash
# Let's Encrypt certificates
ls /etc/letsencrypt/live/svagnoni.linkeddata.es/

# Standard SSL directories
ls /etc/ssl/certs/ | grep linkeddata
ls /etc/ssl/private/ | grep linkeddata
```

#### Step 4: Update SSL Certificate Paths
Edit the configuration file:
```bash
sudo nano /etc/apache2/sites-available/svagnoni.linkeddata.es.conf
```

Update these lines with your actual certificate paths:
```apache
SSLCertificateFile /path/to/your/certificate.crt
SSLCertificateKeyFile /path/to/your/private.key
SSLCertificateChainFile /path/to/your/chain.crt  # Optional
```

#### Step 5: Test Configuration
```bash
sudo apache2ctl configtest
```

#### Step 6: Enable the Site
```bash
sudo a2ensite svagnoni.linkeddata.es.conf
sudo a2dissite 000-default.conf  # Disable default site
```

#### Step 7: Start Apache
```bash
sudo systemctl start apache2
sudo systemctl enable apache2
sudo systemctl reload apache2
```

## 🔐 SSL Certificate Options

### Option 1: Let's Encrypt (Free SSL)
If you don't have SSL certificates, get them free with Let's Encrypt:
```bash
sudo apt update
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d svagnoni.linkeddata.es
```

### Option 2: Existing Certificates
If you have existing certificates, common locations are:
- Certificate: `/etc/ssl/certs/your-domain.crt`
- Private Key: `/etc/ssl/private/your-domain.key`
- Chain: `/etc/ssl/certs/your-domain-chain.crt`

## 🧪 Testing

### 1. Check Apache Status
```bash
sudo systemctl status apache2
```

### 2. Check Configuration
```bash
sudo apache2ctl configtest
```

### 3. Check Logs
```bash
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log
```

### 4. Test Your Platform
```bash
python3 check_deployment.py
```

## 🔍 Troubleshooting

### Common Issues:

1. **SSL Certificate Errors**
   - Check certificate paths in `/etc/apache2/sites-available/svagnoni.linkeddata.es.conf`
   - Ensure certificates have correct permissions

2. **Port 443 Already in Use**
   ```bash
   sudo netstat -tlnp | grep :443
   sudo systemctl stop apache2
   sudo systemctl start apache2
   ```

3. **Permission Errors**
   ```bash
   sudo chown -R www-data:www-data /home/svagnoni/Deliberation-Knowledge-Graph/
   sudo chmod -R 755 /home/svagnoni/Deliberation-Knowledge-Graph/
   ```

4. **Proxy Not Working**
   - Ensure your Flask server is running: `./deploy_linkeddata.sh`
   - Check if port 8085 is accessible: `curl http://localhost:8085/api/stats`

## ✅ Success Indicators

When everything is working correctly:
- Apache status: `active (running)`
- Configuration test: `Syntax OK`
- Domain accessible: `https://svagnoni.linkeddata.es/`
- Platform loads: Enhanced visualization visible

## 🚀 Final Check

After configuration, your enhanced Deliberation Knowledge Graph should be accessible at:
- **https://svagnoni.linkeddata.es/** - Main interface
- **https://svagnoni.linkeddata.es/visualize** - Enhanced visualization with improved lateral window
- **https://svagnoni.linkeddata.es/sparql** - SPARQL endpoint