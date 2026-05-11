import sqlite3

conn = sqlite3.connect('instance/blackwallet_v2.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM \"transaction\"")
txs = cursor.fetchall()
for tx in txs:
    print(tx)
conn.close()
