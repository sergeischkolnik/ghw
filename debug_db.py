"""Debug script to check what's in ghw.db"""
import sqlite3

conn = sqlite3.connect('ghw.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("📋 Tablas en la BD:")
for table in tables:
    print(f"  - {table[0]}")

# Check taller_outputs (legacy table)
print("\n🔧 TALLER_OUTPUTS (legacy):")
cursor.execute("SELECT COUNT(*) FROM taller_outputs")
count = cursor.fetchone()[0]
print(f"  Total: {count}")
if count > 0:
    cursor.execute("SELECT id, machine_name, machine_number LIMIT 3")
    rows = cursor.fetchall()
    for row in rows:
        print(f"    {row}")

# Check servicio_outputs (legacy table)
print("\n🚜 SERVICIO_OUTPUTS (legacy):")
cursor.execute("SELECT COUNT(*) FROM servicio_outputs")
count = cursor.fetchone()[0]
print(f"  Total: {count}")
if count > 0:
    cursor.execute("SELECT id, client LIMIT 3")
    rows = cursor.fetchall()
    for row in rows:
        print(f"    {row}")

# Check new tables
print("\n✨ NEW TABLES:")
for table in ['workshops', 'services']:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} registros")

conn.close()
print("\n" + "="*50)
