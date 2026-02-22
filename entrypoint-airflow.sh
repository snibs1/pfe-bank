#!/bin/bash
set -e

echo "======================================"
echo "Airflow Container - Startup Script"
echo "======================================"

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1

while ! pg_isready -h db -U admin -d airflow_db 2>/dev/null; do
    if [ $attempt -ge $max_attempts ]; then
        echo "ERROR: PostgreSQL failed to start after $max_attempts attempts"
        exit 1
    fi
    echo "Attempt $attempt/$max_attempts: PostgreSQL not ready yet, waiting..."
    sleep 2
    ((attempt++))
done

echo "✅ PostgreSQL is ready!"
echo ""

# Initialize Airflow database
echo "Initializing Airflow database..."
airflow db migrate
echo "✅ Database migration complete"
echo ""

# Create default admin user (if it doesn't exist)
echo "Creating default admin user..."
airflow users create \
    --username admin \
    --password admin \
    --firstname admin \
    --lastname admin \
    --role Admin \
    --email admin@example.com \
    2>/dev/null || echo "⚠️  User already exists (or creation failed)"
echo ""

# Start Airflow webserver and scheduler
echo "Starting Airflow webserver and scheduler..."
echo "======================================"

# Start webserver in background
airflow webserver --port 8080 &
WEBSERVER_PID=$!

# Start scheduler in foreground
airflow scheduler

# If scheduler exits, kill webserver
kill $WEBSERVER_PID 2>/dev/null || true
