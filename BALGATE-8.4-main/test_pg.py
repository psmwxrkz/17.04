import psycopg

conn = psycopg.connect(
    host="172.28.43.147",
    dbname="balgate",
    user="balgate_user",
    password="shxrkzeqnx10",
    port=5432
)

print("✅ Conexão com PostgreSQL realizada com sucesso!")
conn.close()
