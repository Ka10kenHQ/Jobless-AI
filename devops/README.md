# DevOps Setup for MCP Job Search System

This directory contains the complete Docker infrastructure for the MCP Job Search System, supporting development, training, and production environments.

## 🚀 Quick Start

### Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)
- NVIDIA Docker Runtime (for GPU support)
- 16GB RAM recommended
- NVIDIA GPU with 6GB+ VRAM

### First Time Setup

1. **Clone and navigate to the project:**
   ```bash
   cd usaqmuri-AI
   ```

2. **Setup environment variables:**
   ```bash
   cp devops/.env.example devops/.env
   # Edit devops/.env with your configuration
   ```

3. **Install and start everything:**
   ```bash
   cd devops
   make install
   ```

4. **Access the application:**
   - **Main App**: http://localhost:8000
   - **Chatbox UI**: http://localhost:8000/chatbox
   - **MongoDB Admin**: http://localhost:8081 (admin/admin)

## 📋 Available Commands

Run `make help` to see all available commands:

### Development
- `make dev` - Build and start development environment
- `make up` - Start development services
- `make down` - Stop all services
- `make logs` - View all service logs
- `make shell` - Open shell in app container

### Training
- `make train` - Start model training
- `make train-quick` - Quick training test
- `make tensorboard` - Access TensorBoard (http://localhost:6006)
- `make jupyter` - Access Jupyter notebook (http://localhost:8888)

### Production
- `make prod` - Start production environment
- `make prod-logs` - View production logs

### Database
- `make db-backup` - Backup MongoDB
- `make db-restore BACKUP_DIR=path` - Restore MongoDB
- `make db-seed` - Seed with sample data

### Testing
- `make test` - Run all tests
- `make test-api` - Test API endpoints
- `make gpu-test` - Test GPU availability

## 🏗️ Architecture

### Services

1. **app-dev/app-prod** - Main MCP Job Search application
2. **mongodb** - MongoDB database with authentication
3. **redis** - Redis cache for performance
4. **nginx** - Reverse proxy for production
5. **trainer** - Dedicated training environment
6. **scraper** - Scheduled job collection service

### Profiles

- `dev` - Development environment with hot reload
- `prod` - Production environment with optimizations
- `training` - ML training with Jupyter and TensorBoard

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Database
MONGO_PASSWORD=your_secure_password
MONGODB_URL=mongodb://admin:password@mongodb:27017/job_search?authSource=admin

# Training
WANDB_API_KEY=your_wandb_key
CUDA_VISIBLE_DEVICES=0

# Job Scraping
HR_GE_ENABLED=true
JOBS_GE_ENABLED=true
SCRAPER_HEADLESS=true

# Security
SECRET_KEY=your_secret_key
ALLOWED_HOSTS=localhost,your-domain.com
```

### CUDA Support

The Docker setup automatically detects and uses your NVIDIA GPU:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Volume Mounts

- **Development**: Full project mounted for hot reload
- **Production**: Only necessary files copied
- **Data Persistence**: MongoDB, Redis, models, and logs

## 🐳 Docker Images

### Multi-stage Dockerfile

1. **base** - CUDA 12.4 + Python 3.10 + system dependencies
2. **development** - Base + Chrome/ChromeDriver for scraping
3. **production** - Base + minimal app files + security
4. **training** - Development + Jupyter + TensorBoard

### Image Sizes

- Base: ~3GB (CUDA runtime)
- Development: ~4GB (+ Chrome)
- Production: ~3.5GB (optimized)
- Training: ~4.5GB (+ ML tools)

## 🌍 Multi-language Support

The system supports Georgian and English job searches:

- Georgian job sites: hr.ge, jobs.ge
- Multilingual AI model: facebook/xglm-564M
- UI translations for both languages

## 📊 Monitoring & Logging

### Development

```bash
# View all logs
make logs

# View specific service logs
make logs-app
docker-compose logs -f mongodb

# Monitor resources
make stats
docker stats

# Check service health
make status
```

### Production

```bash
# Production logs
make prod-logs

# Health checks via Nginx
curl http://localhost/health

# Database health
make shell-db
```

## 🔒 Security Features

### Production Security

1. **Non-root user** in production containers
2. **Nginx security headers** (XSS, CSRF protection)
3. **Rate limiting** for API endpoints
4. **Environment variable** secrets
5. **Health checks** for all services

### Network Security

```yaml
networks:
  mcp-network:
    driver: bridge
```

All services communicate through isolated Docker network.

## 🚨 Troubleshooting

### Common Issues

1. **GPU not detected:**
   ```bash
   # Check NVIDIA Docker runtime
   docker run --rm --gpus all nvidia/cuda:12.4-base nvidia-smi
   
   # Test in container
   make gpu-test
   ```

2. **MongoDB connection issues:**
   ```bash
   # Check MongoDB status
   make shell-db
   
   # View logs
   docker-compose logs mongodb
   ```

3. **Memory issues:**
   ```bash
   # Check resource usage
   make stats
   
   # Adjust batch sizes in config
   ```

4. **Port conflicts:**
   ```bash
   # Check which ports are in use
   netstat -tulpn | grep :8000
   
   # Modify docker-compose.yaml ports
   ```

### Performance Tuning

1. **GPU Memory Optimization:**
   - Adjust batch sizes in `config/gpu_detector.py`
   - Enable gradient checkpointing
   - Use mixed precision training

2. **Database Performance:**
   - MongoDB indexes are auto-created
   - Redis caching for frequent searches
   - Connection pooling

3. **Container Resources:**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 8G
         cpus: '4'
   ```

## 📈 Scaling

### Horizontal Scaling

```yaml
# Scale app instances
app-prod:
  deploy:
    replicas: 3
```

### Load Balancing

Nginx automatically load balances between app instances.

### Database Scaling

- MongoDB replica sets
- Redis clustering
- Separate read/write connections

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
- name: Build and test
  run: |
    make build
    make test
    
- name: Deploy to production
  run: |
    make prod
```

### Health Checks

All services include health checks for reliable deployments.

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [PyTorch Docker Images](https://hub.docker.com/r/pytorch/pytorch)
- [MongoDB Docker Setup](https://hub.docker.com/_/mongo)

---

## 💡 Tips

1. **Development**: Use `make dev` for daily development
2. **Training**: Use `make train` for model training
3. **Production**: Use `make prod` for deployment
4. **Debugging**: Use `make shell` to inspect containers
5. **Monitoring**: Use `make logs` and `make stats`

For more help, run `make help` or check the individual service documentation. 