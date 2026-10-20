from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from sympy import Poly, factor_list, Symbol, expand
from sympy.abc import x
import time
import os

app = Flask(__name__)
CORS(app)  # Cross-Origin Resource Sharing allow karne ke liye

@app.route('/')
def home():
    return jsonify({'status': 'Polynomial Factorization API is running'})

@app.route('/factor', methods=['POST'])
def factor():
    try:
        data = request.get_json() or {}
        p = int(data.get('p', 3))
        c = int(data.get('c', 2200))
        mode = data.get('mode', 'standard')
        poly_str = data.get('poly', '')

        def is_prime(n):
            if n < 2: return False
            if n == 2: return True
            if n % 2 == 0: return False
            for i in range(3, int(n**0.5)+1, 2):
                if n % i == 0: return False
            return True

        if not is_prime(p):
            return jsonify({'success': False, 'error': f'{p} is not prime'})

        start = time.time()

        if mode == 'standard':
            if c < 2 or c > 100000:
                return jsonify({'success': False, 'error': 'c must be between 2 and 100000'})
            
            # Fast Symbolic Expansion (2-3 seconds response time)
            X = Symbol('x')
            poly_expr = expand((X + 1)**c - X**c - 1)
            poly = Poly(poly_expr, X, modulus=p)
        else:
            if not poly_str:
                return jsonify({'success': False, 'error': 'No polynomial provided'})
            try:
                poly = Poly(poly_str, x, modulus=p)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Parse error: {str(e)}'})

        fl = poly.factor_list()
        lead_coeff = int(fl[0])
        factors = []
        sum_degrees = 0

        for f, mult in fl[1]:
            deg = int(f.degree())
            c_list = [int(cf) % p for cf in f.all_coeffs()]
            poly_s = format_poly(c_list, p)
            factors.append({
                'coeffs': c_list,
                'degree': deg,
                'multiplicity': int(mult),
                'str': poly_s
            })
            sum_degrees += deg * int(mult)

        elapsed = round(time.time() - start, 2)
        factors.sort(key=lambda f: -f['degree'])

        return jsonify({
            'success': True,
            'factors': factors,
            'count': len(factors),
            'lead_coeff': lead_coeff,
            'sum_degrees': sum_degrees,
            'time': elapsed,
            'poly_degree': int(poly.degree())
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def format_poly(coeffs, p):
    deg = len(coeffs) - 1
    terms = []
    for i, c in enumerate(coeffs):
        c = int(c) % p
        if c == 0:
            continue
        power = deg - i
        dc = c
        if p <= 7 and c > p // 2:
            dc = c - p
        if power == 0:
            terms.append(str(dc))
        elif power == 1:
            if dc == 1: terms.append('x')
            elif dc == -1: terms.append('-x')
            else: terms.append(f'{dc}*x')
        else:
            if dc == 1: terms.append(f'x^{power}')
            elif dc == -1: terms.append(f'-x^{power}')
            else: terms.append(f'{dc}*x^{power}')
    if not terms:
        return '0'
    result = terms[0]
    for t in terms[1:]:
        if t.startswith('-'):
            result += f' - {t[1:]}'
        else:
            result += f' + {t}'
    return result

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
