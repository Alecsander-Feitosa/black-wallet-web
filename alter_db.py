import sqlite3

conn = sqlite3.connect('instance/blackwallet_v2.db')
cursor = conn.cursor()

# Atualiza o wallet_address do usuário 66281966
cursor.execute("""
    UPDATE user 
    SET wallet_address = '0x3fe705e2ffcaee8d7287de047def35db3e794c76' 
    WHERE username = '66281966'
""")

conn.commit()

# Verifica a atualização
cursor.execute("SELECT username, wallet_address FROM user WHERE username = '66281966'")
result = cursor.fetchone()
print(f"Usuário: {result[0]} | Wallet: {result[1]}")

conn.close()
print("Wallet address atualizado com sucesso!")
