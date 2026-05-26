#!/bin/bash
# health_check.sh - Check if backend and frontend are running

echo "Checking Watch!fy services..."

# Check backend
echo "Checking backend..."
if curl -s --fail http://localhost:8000/api/health; then
  echo "✅ Backend is running"
else
  echo "❌ Backend is NOT running"
fi

# Check frontend
echo "Checking frontend..."
if curl -s --fail http://localhost:3000/health; then
  echo "✅ Frontend is running"
else
  echo "❌ Frontend is NOT running"
fi

# Check Redis
echo "Checking Redis..."
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
  echo "✅ Redis is running"
else
  echo "❌ Redis is NOT running"
fi

echo "Health check complete!"