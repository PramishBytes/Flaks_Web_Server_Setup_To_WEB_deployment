from flask import Flask, jsonify, request

app = Flask(__name__)

products = [{"id": 1, "name":"keyboard","price":49.99},
                    {"id":2, "name": "Mouse","price": 29.99}]

@app.route("/")
def home():
    return jsonify({"message": "Hello from server"})

@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(products)


@app.route("/products", methods = ["POST"])
def add_products():
    data = request.get_json()
    new_product = {
        "id": len(products)+1,
        "name": data.get("name"),
        "price": data.get("price")

        }
    products.append(new_product)
    return jsonify({"message": "Product added", "product":new_product}), 201



    

if __name__ == "__main__":
    app.run(debug = True)



