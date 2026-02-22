
set -e

echo "======================================"
echo "Airflow Container - Startup Script"
echo "======================================"


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


echo "Initializing Airflow database..."
airflow db migrate
echo "✅ Database migration complete"
echo ""


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


echo "Starting Airflow webserver and scheduler..."
echo "======================================"


airflow webserver --port 8080 &
WEBSERVER_PID=$!


airflow scheduler


kill $WEBSERVER_PID 2>/dev/null || true
