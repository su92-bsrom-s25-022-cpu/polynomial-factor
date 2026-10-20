from flask import Flask, request, jsonify, render_template
from sympy import Poly, factor_list, GF
from sympy.abc import x
import time
import os

app = Flask(__name__)

def compute_poly_coeffs(c, p):
    """Compute coefficients of (x+1)^c - x^c - 1 mod p using Lucas theorem"""
    # Get base-p digits of c
    digits = []
    t = c
    while t > 0:
        digits.append(t % p)
        t //= p
    
    # Pascal triangle mod p
    pascal = []
    for n in range(p):
        row = [0] * p
        row[0] = 1
        if n > 0:
            row[n] = 1
            for k in range(1, n):
                row[k] = (pascal[n-1][k-1] + pascal[n-1][k]) % p
        pascal.append(row)
    
    # Compute powers of p
    pw = []
    pv = 1
    for i in range(len(digits)):
        pw.append(pv)
        pv *= p
    
    # Build coefficient map using Lucas theorem
    coeffs = {}
    
    def rec(di, k, co):
        if di == len(digits):
            if co and k > 0 and k < c:
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
    
    # Build polynomial array
    if not coeffs:
        return [0]
    
    max_deg = max(coeffs.keys())
    arr = [0] * (max_deg + 1)
    for d, c_val in coeffs.items():
        arr[d] = c_val
    
    return arr

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/factor', methods=['POST'])
def factor():
    try:
        data = request.get_json()
        p = int(data.get('p', 3))
        c = int(data.get('c', 2200))
        mode = data.get('mode', 'standard')
        poly_str = data.get('poly', '')
        
        # Validation
        if p < 2 or p > 97:
            return jsonify({'success': False, 'error': 'p must be prime between 2 and 97'})
        
        # Check p is prime
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
            
            # Compute polynomial coefficients
            coeffs = compute_poly_coeffs(c, p)
            
            # Create sympy polynomial
            # coeffs[i] = coefficient of x^i
            poly_expr = sum(int(coeffs[i]) * x**i for i in range(len(coeffs)) if coeffs[i])
            poly = Poly(poly_expr, x, modulus=p)
            
        else:
            # Custom polynomial
            if not poly_str:
                return jsonify({'success': False, 'error': 'No polynomial provided'})
            try:
                poly = Poly(poly_str, x, modulus=p)
            except Exception as e:
                return jsonify({'success': False, 'error': f'Parse error: {str(e)}'})
        
        # Factorize
        fl = poly.factor_list()
        lead_coeff = int(fl[0])
        
        factors = []
        sum_degrees = 0
        
        for f, mult in fl[1]:
            deg = int(f.degree())
            c_list = [int(cf) % p for cf in f.all_coeffs()]
            
            # Format polynomial string
            poly_s = format_poly(c_list, p)
            
            factors.append({
                'coeffs': c_list,
                'degree': deg,
                'multiplicity': int(mult),
                'str': poly_s
            })
            sum_degrees += deg * int(mult)
        
        elapsed = round(time.time() - start, 2)
        
        # Sort by degree descending
        factors.sort(key=lambda x: -x['degree'])
        
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
    """Format coefficient list as polynomial string"""
    # coeffs[0] = leading coeff (highest degree)
    deg = len(coeffs) - 1
    terms = []
    
    for i, c in enumerate(coeffs):
        c = int(c) % p
        if c == 0:
            continue
        power = deg - i
        
        # Use symmetric representation
        dc = c
        if p <= 7 and c > p // 2:
            dc = c - p
        
        if power == 0:
            terms.append(str(dc))
        elif power == 1:
            if dc == 1:
                terms.append('x')
            elif dc == -1:
                terms.append('-x')
            else:
                terms.append(f'{dc}*x')
        else:
            if dc == 1:
                terms.append(f'x^{power}')
            elif dc == -1:
                terms.append(f'-x^{power}')
            else:
                terms.append(f'{dc}*x^{power}')
    
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