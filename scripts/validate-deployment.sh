#!/bin/bash
# Smart Energy AI V2 - Deployment Validation Script

echo "🔍 Smart Energy AI V2 - Container Deployment Validation"
echo "==========================================================="
echo ""

# Check Docker status
echo "📦 Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
else
    echo "✅ Docker is running"
fi

echo ""

# Check containers
echo "🐳 Checking container status..."
echo ""

CONTAINERS=("postgres" "redis" "dagster" "mlflow")

for container in "${CONTAINERS[@]}"; do
    if docker-compose ps --services | grep -q "$container"; then
        status=$(docker-compose ps "$container" --format "table" | tail -n +2 | awk '{print $3}')
        if [[ "$status" == "running" ]]; then
            echo "✅ $container: Running"
        else
            echo "⚠️  $container: $status"
        fi
    else
        echo "❌ $container: Not found"
    fi
done

echo ""

# Check ports
echo "🔌 Checking service ports..."
echo ""

PORTS=(
    "3000:Dagster UI"
    "5432:PostgreSQL"
    "6379:Redis" 
    "5000:MLflow"
)

for port_service in "${PORTS[@]}"; do
    port=$(echo "$port_service" | cut -d':' -f1)
    service=$(echo "$port_service" | cut -d':' -f2)
    
    if netstat -an | grep -q ":$port "; then
        echo "✅ $service (port $port): Available"
    else
        echo "❌ $service (port $port): Not available"
    fi
done

echo ""

# Test Dagster UI accessibility
echo "🎯 Testing Dagster UI..."
if curl -s --connect-timeout 5 http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Dagster UI: Accessible at http://localhost:3000"
else
    echo "⚠️  Dagster UI: Not yet accessible (may still be starting)"
fi

echo ""

# Check logs for errors
echo "📋 Recent container logs (last 10 lines)..."
echo ""

for container in "${CONTAINERS[@]}"; do
    if docker-compose ps --services | grep -q "$container"; then
        echo "--- $container logs ---"
        docker-compose logs --tail=3 "$container" 2>/dev/null | tail -3
        echo ""
    fi
done

echo "🎯 Validation complete!"
echo ""
echo "🌐 Access points:"
echo "  • Dagster UI:    http://localhost:3000"
echo "  • MLflow UI:     http://localhost:5000"  
echo "  • PostgreSQL:    localhost:5432"
echo "  • Redis:         localhost:6379"
echo ""
echo "🔧 Management commands:"
echo "  • View logs:     docker-compose logs -f [service]"
echo "  • Restart:       docker-compose restart [service]"
echo "  • Stop all:      docker-compose down"