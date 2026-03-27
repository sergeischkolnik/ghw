import sqlite3

conn = sqlite3.connect('ghw.db')
cursor = conn.cursor()

# Get schema
print("=== TALLER_OUTPUTS ===")
cursor.execute("PRAGMA table_info(taller_outputs)")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

print("\n=== SERVICIO_OUTPUTS ===")
cursor.execute("PRAGMA table_info(servicio_outputs)")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Show sample data
print("\n=== Sample TALLER ===")
cursor.execute("SELECT * FROM taller_outputs LIMIT 1")
row = cursor.fetchone()
if row:
    cursor.execute("PRAGMA table_info(taller_outputs)")
    cols = cursor.fetchall()
    for i, col in enumerate(cols):
        print(f"  {col[1]}: {row[i]}")

print("\n=== Sample SERVICIO ===")
cursor.execute("SELECT * FROM servicio_outputs LIMIT 1")
row = cursor.fetchone()
if row:
    cursor.execute("PRAGMA table_info(servicio_outputs)")
    cols = cursor.fetchall()
    for i, col in enumerate(cols):
        print(f"  {col[1]}: {row[i]}")

conn.close()
