#!/bin/sh
# wait-for-db.sh

set -e

host="$1"
shift
cmd="$@"

# Use netcat to check if PostgreSQL port is open
until nc -z "$host" 5432; do
  echo "Waiting for PostgreSQL at $host:5432..."
  sleep 1
done

echo "PostgreSQL is up - executing command"
exec $cmd