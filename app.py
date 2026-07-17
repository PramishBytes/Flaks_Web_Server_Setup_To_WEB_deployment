from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

def get_db_connection():

    conn = sqlite3.connect("products.db")
    conn.row_factory = sqlite3.Row 
    return conn

@app.route("/init", methods = ["GET"])
def init_db():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL
    )
    """)
    conn.commit()
    conn.close()
    return jsonify({"message":"Databases Init complete"})


@app.route("/")
def home():
    return jsonify({"message": "Hello from server"})

@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/products", methods = ["POST"])
def add_products():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products(name,price) VALUES (?,?)",(name,price))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    new_product = {
        "id": new_id,
        "name": name,
        "price": price

        }
    #products.append(new_product)
    return jsonify({"message": "Product added", "product":new_product}), 201



    

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug = True)



