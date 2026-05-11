import sqlite3

conn = sqlite3.connect('instance/blackwallet_v2.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM "transaction"')
conn.commit()
conn.close()
print("Deleted all transactions")
