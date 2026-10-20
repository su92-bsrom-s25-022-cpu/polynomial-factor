from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import time
import traceback

app = Flask(__name__)

# Complete CORS configuration for GitHub Pages & Custom Domain
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    i = 3
    while i * i <= n:
        if n % i == 0: return False
        i += 2
    return True

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Polynomial Factorization API is running"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/factor', methods=['POST', 'OPTIONS'])
def factor():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        mode = data.get("mode", "standard")
        p = int(data.get("p", 3))

        if not is_prime(p):
            return jsonify({"success": False, "error": f"{p} is not prime"}), 400

        start = time.time()
        x = sp.Symbol('x')

        if mode == "standard":
            c = int(data.get("c", 2200))
            if c < 2 or c > 500000:
                return jsonify({"success": False, "error": "c must be between 2 and 500000"}), 400
            
            # Direct polynomial expansion over GF(p)
            poly_obj = (sp.Poly(x + 1, x, domain=sp.GF(p))**c) - (sp.Poly(x, x, domain=sp.GF(p))**c) - sp.Poly(1, x, domain=sp.GF(p))
        else:
            poly_str = data.get("poly", "").strip()
            if not poly_str:
                return jsonify({"success": False, "error": "No polynomial provided"}), 400
            poly_str = poly_str.replace("^", "**")
            poly_expr = sp.sympify(poly_str)
            poly_obj = sp.Poly(poly_expr, x, domain=sp.GF(p))

        orig_deg = poly_obj.degree()
        if orig_deg < 0:
            return jsonify({"success": False, "error": "Zero polynomial cannot be factorized"}), 400

        # SymPy Factorization over GF(p)
        factors_dict = poly_obj.factor_list()
        lead_coeff = int(factors_dict[0]) % p
        raw_factors = factors_dict[1]

        factors = []
        sum_degrees = 0

        for fac, mult in raw_factors:
            deg = fac.degree()
            mult = int(mult)
            coeffs_high = [int(co) % p for co in fac.all_coeffs()]
            
            factors.append({
                "coeffs": coeffs_high,
                "degree": deg,
                "multiplicity": mult,
                "str": str(fac.as_expr())
            })
            sum_degrees += deg * mult

        factors.sort(key=lambda z: -z["degree"])
        elapsed = round(time.time() - start, 2)

        return jsonify({
            "success": True,
            "factors": factors,
            "count": len(factors),
            "lead_coeff": lead_coeff,
            "sum_degrees": sum_degrees,
            "time": elapsed,
            "poly_degree": orig_deg
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
