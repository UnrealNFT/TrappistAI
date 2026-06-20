#!/bin/bash
# News fetcher cron job runner
# Runs every 5 minutes in the background

echo "🗞️ Starting crypto news fetcher cron..."

while true; do
    echo "📡 Fetching crypto news... $(date)"
    python news-fetcher.py
    echo "⏳ Waiting 5 minutes..."
    sleep 300  # 5 minutes
done
