# Redis Setup Guide for Local Development

This guide will help you set up Redis for local development testing.

## 🎯 Quick Start (Recommended)

### Option 1: Docker (Easiest)

1. **Install Docker Desktop**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop

2. **Start Redis with Docker**
   ```bash
   cd /path/to/your/webapp
   docker-compose up redis -d
   ```

3. **Test the connection**
   ```bash
   cd backend
   python test_redis.py
   ```

### Option 2: Redis Desktop Manager

1. **Download Redis Desktop Manager**
   - Download from: https://redisdesktop.com/
   - Install the application

2. **Start Redis Server**
   - Launch Redis Desktop Manager
   - It includes a built-in Redis server
   - Connect to `localhost:6379`

3. **Test the connection**
   ```bash
   cd backend
   python test_redis.py
   ```

## 🔧 Manual Installation Options

### Windows with WSL

1. **Install WSL** (if not already installed)
   ```powershell
   wsl --install
   ```

2. **Install Redis in WSL**
   ```bash
   sudo apt update
   sudo apt install redis-server
   ```

3. **Start Redis service**
   ```bash
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

4. **Test Redis**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

### Windows with Chocolatey

1. **Install Chocolatey** (if not already installed)
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. **Install Redis**
   ```powershell
   choco install redis-64
   ```

3. **Start Redis**
   ```powershell
   redis-server
   ```

## 🧪 Testing Your Setup

### Run the Test Script

```bash
cd backend
python test_redis.py
```

Expected output:
```
🚀 Redis Test Script
==================================================
📊 Redis Information:
==============================
Connection URL: redis://localhost:6379
Connected: True
Redis Version: 7.x.x
Used Memory: 1.2M
Connected Clients: 1

🔍 Testing Redis Connection...
==================================================
✅ Redis connection successful!

🧪 Testing basic operations...
✅ Set operation successful
✅ Get operation successful
✅ Exists operation successful
✅ TTL operation successful (TTL: 59s)
✅ Increment operation successful
✅ Delete operation successful

👤 Testing session operations...
✅ Set user session successful
✅ Get user session successful

💾 Testing cache operations...
✅ Set cache successful
✅ Get cache successful

🧹 Cleaning up test data...
✅ Cleanup completed

🎉 All Redis tests passed!

✅ Redis is working correctly!
💡 You can now use Redis in your application.
```

### Manual Testing with Redis CLI

```bash
# Connect to Redis
redis-cli

# Test basic operations
127.0.0.1:6379> SET test:hello "Hello Redis!"
OK
127.0.0.1:6379> GET test:hello
"Hello Redis!"
127.0.0.1:6379> DEL test:hello
(integer) 1
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> EXIT
```

## 🔗 Configuration

### Environment Variables

Your `.env` file should include:

```env
# Redis Settings
REDIS_URL=redis://localhost:6379
```

### Connection Details

- **Host**: `localhost` or `127.0.0.1`
- **Port**: `6379` (default Redis port)
- **URL Format**: `redis://localhost:6379`

## 🛠️ Using Redis in Your Application

### Basic Usage

```python
from app.services.redis_service import redis_service

# Store data
redis_service.set("user:123", {"name": "John", "email": "john@example.com"}, expire=3600)

# Retrieve data
user_data = redis_service.get("user:123")

# Check if key exists
if redis_service.exists("user:123"):
    print("User data found!")

# Delete data
redis_service.delete("user:123")
```

### Session Management

```python
# Store user session
session_data = {
    "user_id": "123",
    "email": "user@example.com",
    "last_login": "2024-01-01T00:00:00Z"
}
redis_service.set_user_session("123", session_data, expire=3600)

# Retrieve session
session = redis_service.get_user_session("123")

# Delete session
redis_service.delete_user_session("123")
```

### Caching

```python
# Cache expensive data
user_profile = {
    "name": "John Doe",
    "preferences": {"theme": "dark", "language": "en"}
}
redis_service.set_cache("user_profile_123", user_profile, expire=300)

# Retrieve cached data
cached_profile = redis_service.get_cache("user_profile_123")

# Clear cache
redis_service.clear_cache("cache:*")
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Connection refused
   ```
   **Solution**: Make sure Redis is running
   ```bash
   # Docker
   docker-compose up redis -d
   
   # WSL
   sudo systemctl start redis-server
   
   # Windows
   redis-server
   ```

2. **Port Already in Use**
   ```
   Error: Address already in use
   ```
   **Solution**: Check if Redis is already running
   ```bash
   # Check running processes
   netstat -an | findstr 6379
   
   # Kill existing process
   taskkill /F /PID <process_id>
   ```

3. **Authentication Error**
   ```
   Error: NOAUTH Authentication required
   ```
   **Solution**: Your Redis doesn't require authentication in development

### Health Check

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Check Redis info
redis-cli info server
```

## 📚 Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [Redis Commands](https://redis.io/commands)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Docker Redis Image](https://hub.docker.com/_/redis)

## 🎉 Next Steps

Once Redis is working:

1. **Implement caching** in your API endpoints
2. **Add session management** for user authentication
3. **Set up rate limiting** using Redis counters
4. **Monitor Redis performance** with RedisInsight or similar tools

Happy coding! 🚀 