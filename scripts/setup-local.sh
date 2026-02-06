#!/bin/bash
# Smart Energy AI V2 - Local Development Setup

set -e

echo "🚀 Starting Smart Energy AI V2 local setup..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data/raw data/processed
mkdir -p logs
mkdir -p mlflow/artifacts

# Build and start services
echo "🐳 Building Docker containers..."
docker-compose build

echo "🔄 Starting services..."
docker-compose up -d postgres redis mlflow

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 10

# Start Dagster services
echo "🎯 Starting Dagster services..."
docker-compose up -d dagster

echo "✅ Setup complete!"
echo ""
echo "📊 Services are now running:"
echo "  • Dagster UI:     http://localhost:3000"
echo "  • MLflow UI:      http://localhost:5000"  
echo "  • PostgreSQL:     localhost:5432"
echo "  • Redis:          localhost:6379"
echo ""
echo "🔧 To view logs:"
echo "  docker-compose logs -f dagster"
echo ""
echo "🛑 To stop all services:"
echo "  docker-compose down"