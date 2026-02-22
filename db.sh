#!/bin/bash
set -e

echo "🔍 Database Management Script"
echo ""

# Function để chạy psql commands
db_exec() {
    docker compose exec db psql -U postgres -d football_law -c "$1"
}

case "${1:-}" in
    "status")
        echo "📊 Database Status:"
        docker compose ps db
        echo ""
        echo "📈 Extensions:"
        db_exec "\dx"
        ;;
    
    "tables")
        echo "📋 Tables:"
        db_exec "\dt"
        ;;
    
    "migrations")
        echo "🔄 Running migrations..."
        docker compose exec app alembic upgrade head
        echo "✅ Migrations completed"
        ;;
    
    "reset")
        echo "⚠️  Resetting database (this will delete all data)..."
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            docker compose down db
            docker volume rm oci-football-law-bot_db_data
            docker compose up -d db
            echo "✅ Database reset. Run './db.sh migrations' to recreate schema."
        fi
        ;;
    
    "shell")
        echo "🐚 Opening psql shell..."
        docker compose exec db psql -U postgres -d football_law
        ;;
    
    "count")
        echo "📊 Data counts:"
        echo ""
        echo "Documents:"
        db_exec "SELECT COUNT(*) FROM documents;"
        echo ""
        echo "Chunks:"
        db_exec "SELECT COUNT(*) FROM chunks;"
        ;;
    
    *)
        echo "Usage: ./db.sh [command]"
        echo ""
        echo "Commands:"
        echo "  status      - Show database status and extensions"
        echo "  tables      - List all tables"
        echo "  migrations  - Run database migrations"
        echo "  reset       - Reset database (delete all data)"
        echo "  shell       - Open psql shell"
        echo "  count       - Count documents and chunks"
        echo ""
        echo "Example: ./db.sh status"
        ;;
esac
