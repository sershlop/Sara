import sqlite3
conn   = sqlite3.connect("sara.db")
cursor = conn.cursor()
cursor.execute("SELECT nombre, accion, tipo FROM comandos WHERE nombre LIKE '%brawl%'")
filas  = cursor.fetchall()
for fila in filas:
    print(f"Nombre: '{fila[0]}'")
    print(f"Accion: '{fila[1]}'")
    print(f"Tipo:   '{fila[2]}'")
conn.close()

import sqlite3

conn   = sqlite3.connect("sara.db")
cursor = conn.cursor()

cursor.execute("""
    UPDATE comandos
    SET accion = ?,
        tipo   = ?
    WHERE nombre = 'brawlhalla'
""", (
    "steam://rungameid/291550",
    "web"
))

conn.commit()
conn.close()
print("✅ Comando actualizado a Steam")