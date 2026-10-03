from database import get_connection


try:
    connection = get_connection()

    print("========================================")
    print("MULEWATCH DATABASE CONNECTION")
    print("========================================")
    print("PostgreSQL connection: SUCCESS")

    connection.close()

except Exception as error:
    print("PostgreSQL connection: FAILED")
    print(f"Error: {error}")