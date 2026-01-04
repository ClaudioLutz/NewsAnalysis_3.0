import sqlite3

conn = sqlite3.connect('news.db')
cursor = conn.execute('SELECT title, source, confidence, classification_reason FROM articles WHERE is_match=1')

for row in cursor:
    print('Title:', row[0])
    print('Source:', row[1])
    print('Confidence:', row[2])
    print('Reason:', row[3])
    print('-' * 80)

conn.close()
