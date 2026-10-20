from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import time

app = Flask(__name__)

# Explicitly enable CORS for codcups.com and allow all headers/methods
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Polynomial Factorization API is running"})

@app.route('/factor', methods=['POST', 'OPTIONS'])
def factor():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        start_time = time.time()
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        p = int(data.get('p', 3))
        mode = data.get('mode', 'standard')
        x = sp.Symbol('x')

        if mode == 'standard':
            c = int(data.get('c', 2200))
            # Memory-efficient expansion over GF(p)
            poly_obj = (sp.Poly(x + 1, x, domain=sp.GF(p))**c) - (sp.Poly(x, x, domain=sp.GF(p))**c) - sp.Poly(1, x, domain=sp.GF(p))
        else:
            poly_str = data.get('poly', '')
            if not poly_str:
                return jsonify({"success": False, "error": "Custom polynomial expression required"}), 400
            poly_expr = sp.sympify(poly_str)
            poly_obj = sp.Poly(poly_expr, x, domain=sp.GF(p))

        # Factorization over GF(p)
        factors_dict = poly_obj.factor_list()
        lead_coeff = str(factors_dict[0])
        raw_factors = factors_dict[1]

        formatted_factors = []
        for f, mult in raw_factors:
            formatted_factors.append({
                "str": str(f.as_expr()),
                "degree": f.degree(),
                "multiplicity": mult
            })

        exec_time = round(time.time() - start_time, 3)

        return jsonify({
            "success": True,
            "time": exec_time,
            "poly_degree": poly_obj.degree(),
            "lead_coeff": lead_coeff,
            "count": len(formatted_factors),
            "factors": formatted_factors
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
