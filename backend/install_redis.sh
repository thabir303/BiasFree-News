#!/bin/bash
# Local Redis Setup Script

echo "🔧 Installing Redis locally..."

# Install Redis
sudo apt update
sudo apt install redis-server -y

# Configure Redis to start automatically
sudo systemctl enable redis-server

# Start Redis
sudo systemctl start redis-server

# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping

echo "✅ Redis installed and running!"
echo "📍 Host: localhost"
echo "🔌 Port: 6379"
