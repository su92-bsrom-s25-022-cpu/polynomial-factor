from flask import Flask, request, jsonify, render_template
import subprocess
import json
import time
import os

app = Flask(__name__)

def is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0: return False
    return True

def format_poly(coeffs_str, p):
    """Format polynomial string"""
    return coeffs_str

def run_sage_factor(p, c=None, poly_str=None, mode='standard'):
    """Run SageMath factorization"""
    
    if mode == 'standard':
        sage_code = f"""
import json
try:
    R.<x> = PolynomialRing(GF({p}))
    f = (x+1)^{c} - x^{c} - 1
    orig_deg = f.degree()
    fl = f.factor()
    result = []
    for fac, mult in fl:
        coeffs = list(fac)
        coeffs_int = [int(c) % {p} for c in coeffs]
        result.append({{
            'coeffs': coeffs_int,
            'degree': int(fac.degree()),
            'multiplicity': int(mult),
            'str': str(fac)
        }})
    print(json.dumps({{
        'success': True,
        'factors': result,
        'orig_deg': orig_deg
    }}))
except Exception as e:
    print(json.dumps({{'success': False, 'error': str(e)}}))
"""
    else:
        sage_code = f"""
import json
try:
    R.<x> = PolynomialRing(GF({p}))
    f = R('{poly_str}')
    orig_deg = f.degree()
    fl = f.factor()
    result = []
    for fac, mult in fl:
        coeffs = list(fac)
        coeffs_int = [int(c) % {p} for c in coeffs]
        result.append({{
            'coeffs': coeffs_int,
            'degree': int(fac.degree()),
            'multiplicity': int(mult),
            'str': str(fac)
        }})
    print(json.dumps({{
        'success': True,
        'factors': result,
        'orig_deg': orig_deg
    }}))
except Exception as e:
    print(json.dumps({{'success': False, 'error': str(e)}}))
"""

    result = subprocess.run(
        ['sage', '-c', sage_code],
        capture_output=True,
        text=True,
        timeout=600
    )
    
    if result.returncode != 0 and not result.stdout:
        return {'success': False, 'error': result.stderr[:500]}
    
    # Parse output
    output = result.stdout.strip()
    if not output:
        return {'success': False, 'error': 'No output from Sage'}
    
    # Find JSON in output
    lines = output.split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except:
                continue
    
    return {'success': False, 'error': 'Could not parse Sage output'}

def format_factor_str(coeffs, p):
    """Format coefficient list as readable polynomial"""
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

        if not is_prime(p):
            return jsonify({'success': False, 'error': f'{p} is not prime'})

        if mode == 'standard':
            if c < 2 or c > 500000:
                return jsonify({'success': False, 'error': 'c must be between 2 and 500000'})

        start = time.time()

        # Run SageMath
        if mode == 'standard':
            sage_result = run_sage_factor(p, c=c, mode='standard')
        else:
            if not poly_str:
                return jsonify({'success': False, 'error': 'No polynomial provided'})
            sage_result = run_sage_factor(p, poly_str=poly_str, mode='custom')

        elapsed = round(time.time() - start, 2)

        if not sage_result.get('success'):
            return jsonify({'success': False, 'error': sage_result.get('error', 'Unknown error')})

        factors = sage_result['factors']
        orig_deg = sage_result.get('orig_deg', 0)

        # Format factors
        formatted = []
        sum_degrees = 0
        for f in factors:
            deg = f['degree']
            mult = f['multiplicity']
            coeffs = f['coeffs']
            poly_s = format_factor_str(coeffs, p)
            formatted.append({
                'coeffs': coeffs,
                'degree': deg,
                'multiplicity': mult,
                'str': poly_s
            })
            sum_degrees += deg * mult

        formatted.sort(key=lambda f: -f['degree'])

        return jsonify({
            'success': True,
            'factors': formatted,
            'count': len(formatted),
            'lead_coeff': 1,
            'sum_degrees': sum_degrees,
            'time': elapsed,
            'poly_degree': orig_deg
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Timeout — polynomial too large'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
