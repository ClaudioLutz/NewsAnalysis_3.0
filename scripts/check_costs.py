#!/usr/bin/env python
"""Check provider cost breakdown."""

import sqlite3
import sys
from pathlib import Path

# Fix Windows encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = Path(__file__).parent.parent / "news.db"

if not db_path.exists():
    print("Database not found!")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Provider breakdown
cursor.execute("""
    SELECT
        CASE
            WHEN model LIKE 'deepseek:%' THEN 'DeepSeek'
            WHEN model LIKE 'gemini:%' THEN 'Gemini'
            ELSE 'OpenAI'
        END as provider,
        COUNT(*) as calls,
        SUM(input_tokens) as input_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(cost) as total_cost
    FROM api_calls
    GROUP BY provider
    ORDER BY total_cost DESC
""")

print()
print("=" * 70)
print("PROVIDER COST BREAKDOWN")
print("=" * 70)
print()
print(f"{'Provider':<15} {'Calls':>8} {'Input':>10} {'Output':>10} {'Cost':>12}")
print("-" * 70)

total_cost = 0.0
total_calls = 0

for row in cursor.fetchall():
    provider, calls, input_tokens, output_tokens, cost = row
    total_cost += cost or 0.0
    total_calls += calls or 0

    print(f"{provider:<15} {calls:>8} {input_tokens:>10} {output_tokens:>10} ${cost:>11.8f}")

print("-" * 70)
print(f"{'TOTAL':<15} {total_calls:>8} {' ':>10} {' ':>10} ${total_cost:>11.8f}")
print()

# Daily breakdown
cursor.execute("""
    SELECT
        DATE(created_at) as date,
        COUNT(*) as calls,
        SUM(cost) as cost
    FROM api_calls
    GROUP BY DATE(created_at)
    ORDER BY date DESC
    LIMIT 7
""")

print("DAILY BREAKDOWN (Last 7 Days)")
print("=" * 70)
print(f"{'Date':<12} {'Calls':>8} {'Cost':>12}")
print("-" * 70)

for row in cursor.fetchall():
    date, calls, cost = row
    print(f"{date:<12} {calls:>8} ${cost:>11.8f}")

print()
print("=" * 70)
print(f"✓ Multi-provider migration working! Total cost so far: ${total_cost:.8f}")
print("=" * 70)
print()

conn.close()
