from flask import Flask, request, jsonify
from flask_cors import CORS
from flint import nmod_poly
from sympy import Poly
from sympy.abc import x
import time
import traceback

app = Flask(__name__)

# Full CORS Support for codcups.com
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

def compute_coeffs_lucas(c, p):
    digits = []
    t = c
    while t > 0:
        digits.append(t % p)
        t //= p

    pascal = []
    for n in range(p):
        row = [0] * p
        row[0] = 1
        if n > 0:
            row[n] = 1
            for k in range(1, n):
                row[k] = (pascal[n - 1][k - 1] + pascal[n - 1][k]) % p
        pascal.append(row)

    pw = []
    pv = 1
    for _ in range(len(digits)):
        pw.append(pv)
        pv *= p

    coeffs = {}

    def rec(di, k, co):
        if di == len(digits):
            if co and 0 < k < c:
                coeffs[k] = (coeffs.get(k, 0) + co) % p
            return

        ci = digits[di]
        pi = pw[di]
        for ki in range(ci + 1):
            b = pascal[ci][ki]
            if not b:
                continue
            nc = (co * b) % p
            if nc:
                rec(di + 1, k + ki * pi, nc)

    rec(0, 0, 1)
    return coeffs

def standard_poly_flint(c, p):
    coeffs_map = compute_coeffs_lucas(c, p)
    if not coeffs_map:
        return nmod_poly([0], p)

    max_deg = max(coeffs_map.keys())
    arr = [0] * (max_deg + 1)
    for deg, coeff in coeffs_map.items():
        arr[deg] = int(coeff) % p

    while len(arr) > 1 and arr[-1] == 0:
        arr.pop()

    return nmod_poly(arr, p)

def custom_poly_flint(poly_str, p):
    poly_str = poly_str.strip().replace("^", "**")
    poly = Poly(poly_str, x, modulus=p)
    coeffs_high_to_low = [int(c) % p for c in poly.all_coeffs()]
    coeffs_low_to_high = list(reversed(coeffs_high_to_low))
    return nmod_poly(coeffs_low_to_high, p)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Polynomial Factorization Engine is running (FLINT Powered)"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/factor', methods=['POST', 'OPTIONS'])
def factor():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(force=True)
        mode = data.get("mode", "standard")
        p = int(data.get("p", 3))

        if not is_prime(p):
            return jsonify({"success": False, "error": f"{p} is not prime"}), 400

        start = time.time()

        if mode == "standard":
            c = int(data.get("c", 2200))
            if c < 2 or c > 500000:
                return jsonify({"success": False, "error": "c must be between 2 and 500000"}), 400
            f = standard_poly_flint(c, p)
        else:
            poly_str = data.get("poly", "").strip()
            if not poly_str:
                return jsonify({"success": False, "error": "No polynomial provided"}), 400
            f = custom_poly_flint(poly_str, p)

        orig_deg = int(f.degree())
        if orig_deg < 0:
            return jsonify({"success": False, "error": "Zero polynomial cannot be factorized"}), 400

        unit, factor_list = f.factor()

        factors = []
        sum_degrees = 0

        for fac, mult in factor_list:
            deg = int(fac.degree())
            coeffs_low = [int(v) % p for v in list(fac)]
            coeffs_high = list(reversed(coeffs_low))

            factors.append({
                "coeffs": coeffs_high,
                "degree": deg,
                "multiplicity": int(mult),
                "str": str(fac)
            })
            sum_degrees += deg * int(mult)

        factors.sort(key=lambda z: -z["degree"])
        elapsed = round(time.time() - start, 3)

        return jsonify({
            "success": True,
            "factors": factors,
            "count": len(factors),
            "lead_coeff": int(unit) % p,
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
