# 🗳️ Deliberation Knowledge Graph - Deployment Guide

## 🚀 Quick Start

### 1. Automatic Platform Launch
```bash
# Make script executable and run
chmod +x start_platform.sh
./start_platform.sh
```

### 2. Manual Setup
```bash
# 1. Create knowledge graph (if not exists)
python3 quick_integration_test.py

# 2. Start web server
python3 sparql_server.py --kg-file quick_test_kg_working.ttl --port 8081 --host 0.0.0.0

# 3. Test the platform
python3 test_platform_api.py http://localhost:8081
```

## 🌐 Platform Features

### Web Interface (http://localhost:8081)
- **📊 Statistics Dashboard**: Real-time KG metrics
- **🔍 SPARQL Query Editor**: Interactive query interface with examples
- **🌐 Network Visualization**: Cross-platform connections graph
- **📱 Responsive Design**: Works on desktop and mobile

### API Endpoints
- `GET /` - Web interface
- `GET /api/stats` - Knowledge graph statistics
- `POST /sparql` - SPARQL query endpoint
- `GET /api/processes` - List deliberation processes

### Example Queries Included
- 🏛️ All deliberation processes
- 🔗 Cross-platform participant links
- 📋 Related topics across platforms
- 💬 Contributions by participants
- 🏢 Participants by organization
- 🌐 Statistics by platform

## 🏗️ Production Deployment

### Using Docker (Recommended)

1. **Create Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python3", "sparql_server.py", "--kg-file", "quick_test_kg_working.ttl", "--port", "8080", "--host", "0.0.0.0"]
```

2. **Build and run**:
```bash
docker build -t deliberation-kg .
docker run -p 8080:8080 deliberation-kg
```

### Using Production WSGI Server

1. **Install Gunicorn**:
```bash
pip install gunicorn
```

2. **Create wsgi.py**:
```python
from sparql_server import app
import os

# Load knowledge graph on startup
if __name__ == "__main__":
    app.run()
```

3. **Run with Gunicorn**:
```bash
gunicorn --bind 0.0.0.0:8080 --workers 4 wsgi:app
```

### Cloud Deployment Options

#### Heroku
```bash
# 1. Create Procfile
echo "web: python3 sparql_server.py --kg-file quick_test_kg_working.ttl --port \$PORT --host 0.0.0.0" > Procfile

# 2. Deploy
git add .
git commit -m "Deploy deliberation KG platform"
heroku create your-app-name
git push heroku main
```

#### Railway
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Deploy
railway login
railway init
railway up
```

#### DigitalOcean App Platform
```yaml
# app.yaml
name: deliberation-kg
services:
- name: web
  source_dir: /
  github:
    repo: your-username/deliberation-knowledge-graph
    branch: main
  run_command: python3 sparql_server.py --kg-file quick_test_kg_working.ttl --port 8080 --host 0.0.0.0
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
```

## 📊 Platform Performance

### Current Dataset Stats
- **43 RDF triples** in working demo
- **2 deliberation processes** (EU Parliament + Decide Madrid)
- **7 participants** with cross-platform links
- **1 cross-platform connection** (owl:sameAs)
- **2 topics** with semantic relationships

### Scalability
- **Small datasets** (< 10K triples): Run directly with Flask
- **Medium datasets** (10K-100K triples): Use Gunicorn + memory optimization
- **Large datasets** (> 100K triples): Consider Apache Jena Fuseki backend

## 🔧 Configuration Options

### Server Configuration
```bash
python3 sparql_server.py --help

Options:
  --kg-file PATH      Path to knowledge graph file (TTL, RDF, JSON-LD)
  --host HOST         Server host (default: localhost)
  --port PORT         Server port (default: 5000)
  --debug             Enable debug mode
```

### Environment Variables
```bash
export KG_FILE="path/to/knowledge_graph.ttl"
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8080"
export FLASK_ENV="production"
```

## 🛡️ Security Considerations

### Production Checklist
- [ ] Use HTTPS in production
- [ ] Set up proper CORS headers
- [ ] Implement rate limiting for SPARQL queries
- [ ] Add authentication for write operations
- [ ] Monitor query complexity to prevent DoS
- [ ] Use environment variables for sensitive config

### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📈 Monitoring

### Health Check Endpoint
```bash
# Check if platform is running
curl http://localhost:8081/api/stats

# Expected response:
{
  "totalTriples": 43,
  "totalProcesses": 2,
  "totalParticipants": 7,
  ...
}
```

### Log Monitoring
```bash
# Follow server logs
tail -f sparql_server.log

# Monitor query performance
grep "query:" sparql_server.log | tail -20
```

## 🔄 Updates and Maintenance

### Update Knowledge Graph
```bash
# 1. Generate new KG
python3 integrate_all_data_to_owl.py --output-dir updated_kg

# 2. Restart server with new data
python3 sparql_server.py --kg-file updated_kg/deliberation_kg_complete.ttl
```

### Backup and Restore
```bash
# Backup current KG
cp quick_test_kg_working.ttl backup_$(date +%Y%m%d).ttl

# Restore from backup
cp backup_20241121.ttl quick_test_kg_working.ttl
```

## 🎯 Next Steps

1. **Scale with Real Data**: Use full datasets instead of demo data
2. **Add Authentication**: Implement user login for personalized queries
3. **Enhanced Visualizations**: Add more D3.js graph visualizations
4. **API Documentation**: Add Swagger/OpenAPI documentation
5. **Real-time Updates**: Implement WebSocket for live data updates

## 📞 Support

- **Issues**: Create GitHub issues for bugs
- **Documentation**: Check README and code comments
- **Platform URL**: Access at configured host:port
- **API Testing**: Use the included test script

---

🗳️ **Deliberation Knowledge Graph Platform** - Making democratic deliberation data accessible and interconnected.