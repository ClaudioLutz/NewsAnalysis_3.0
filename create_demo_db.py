"""Create a demo database with test articles for digest generation."""
from pathlib import Path
from newsanalysis.database.connection import init_database
from datetime import datetime, date
import json

# Initialize fresh database
db_path = Path('demo.db')
db = init_database(db_path)
conn = db.conn

# Insert test articles with summaries
test_articles = [
    {
        'url': 'https://www.nzz.ch/test/signa-investigation',
        'title': 'Swiss Federal Prosecutor Investigates Signa Bankruptcy',
        'source': 'NZZ Business',
        'summary_title': 'Swiss Prosecutor Investigates Signa',
        'summary': "The Swiss Federal Prosecutor's Office has intervened in the Signa bankruptcy case, focusing on financial stability and credit risk implications. The investigation examines business practices that led to the company's insolvency, with potential ramifications for the Swiss financial sector.",
        'key_points': ['Federal investigation into Signa bankruptcy', 'Focus on financial stability issues', 'Credit risk assessment for related entities', 'Examination of insolvency causes', 'Implications for Swiss financial sector'],
        'entities': {'companies': ['Signa'], 'people': [], 'locations': ['Switzerland'], 'topics': ['bankruptcy', 'investigation', 'credit risk']}
    },
    {
        'url': 'https://www.nzz.ch/test/venezuela-oil',
        'title': 'Venezuela Oil Sector Reconstruction Costs',
        'source': 'NZZ Recent',
        'summary_title': 'Venezuela Oil Industry Requires Billions for Reconstruction',
        'summary': 'Venezuela, once a leading oil producer, faces massive reconstruction costs estimated in billions. The deterioration of the oil sector has contributed to economic instability and inflation, creating significant credit risk concerns for international investors and trading partners.',
        'key_points': ['Billions needed for oil sector reconstruction', 'Economic instability from oil decline', 'Inflation impact on economy', 'Credit risk for international partners', 'Historical oil production decline'],
        'entities': {'companies': [], 'people': [], 'locations': ['Venezuela'], 'topics': ['oil production', 'economic crisis', 'inflation', 'credit risk']}
    }
]

run_id = '20260104_demo_test'
today = date.today()

for art in test_articles:
    url_hash = f"hash_{art['url']}"
    conn.execute('''
        INSERT INTO articles (
            url, normalized_url, url_hash, title, source,
            published_at, collected_at, feed_priority, is_match,
            confidence, topic, classification_reason, content,
            summary_title, summary, key_points, entities,
            pipeline_stage, processing_status, run_id, created_at, updated_at,
            summarized_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            date('now'), datetime('now'), 1, 1,
            0.85, 'credit-risk', 'Test case', ?,
            ?, ?, ?, ?,
            'summarized', 'completed', ?, datetime('now'), datetime('now'),
            datetime('now')
        )
    ''', (
        art['url'], art['url'], url_hash, art['title'], art['source'],
        f"Full article content about {art['title']}",
        art['summary_title'], art['summary'],
        json.dumps(art['key_points']), json.dumps(art['entities']),
        run_id
    ))

count = conn.execute('SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL').fetchone()[0]
print(f'Created {count} test articles with summaries')

db.close()
print('Database created successfully: demo.db')
print(f'Articles dated: {today}')
print('\nReady to generate digest!')
