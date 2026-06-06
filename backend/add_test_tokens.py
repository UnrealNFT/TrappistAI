"""
Test manuel : Ajoute des tokens directement dans la base pour tester
"""
import sqlite3

TEST_WALLET = "test_wallet_01234567890abcdef"
TOKENS = 100

# Connexion à la base
conn = sqlite3.connect('trappistai.db')
cursor = conn.cursor()

# Vérifier si l'utilisateur existe déjà
cursor.execute("SELECT id, tokens FROM users WHERE wallet_address = ?", (TEST_WALLET,))
user = cursor.fetchone()

if user:
    # Mettre à jour
    new_balance = user[1] + TOKENS
    cursor.execute("UPDATE users SET tokens = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_address = ?", 
                   (new_balance, TEST_WALLET))
    print(f"✅ Updated {TEST_WALLET}")
    print(f"   Old balance: {user[1]} tokens")
    print(f"   New balance: {new_balance} tokens")
else:
    # Créer nouvel utilisateur
    cursor.execute("INSERT INTO users (wallet_address, tokens) VALUES (?, ?)",
                   (TEST_WALLET, TOKENS))
    print(f"✅ Created user {TEST_WALLET} with {TOKENS} tokens")

conn.commit()

# Vérifier
cursor.execute("SELECT tokens FROM users WHERE wallet_address = ?", (TEST_WALLET,))
final = cursor.fetchone()
print(f"\n💰 Final balance: {final[0]} tokens")

conn.close()
