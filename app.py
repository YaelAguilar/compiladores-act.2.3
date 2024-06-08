from flask import Flask, request, render_template, jsonify
import ply.lex as lex
import ply.yacc as yacc

app = Flask(__name__)

tokens = (
    'TAG_OPEN', 'TAG_CLOSE', 'TAG_SELF_CLOSE', 'TEXT'
)

def t_TAG_OPEN(t):
    r'<[a-zA-Z][a-zA-Z0-9]*(\s+[a-zA-Z][a-zA-Z0-9-]*="[^"]*")*\s*>'
    return t

def t_TAG_SELF_CLOSE(t):
    r'<[a-zA-Z][a-zA-Z0-9]*(\s+[a-zA-Z][a-zA-Z0-9-]*="[^"]*")*\s*/>'
    return t

def t_TAG_CLOSE(t):
    r'</[a-zA-Z][a-zA-Z0-9]*>'
    return t

def t_TEXT(t):
    r'[^<]+'
    return t

t_ignore = ' \t\n'

def t_error(t):
    print(f"Illegal character {t.value[0]}")
    t.lexer.skip(1)

lexer = lex.lex()

def p_html(p):
    '''html : elements'''
    pass

def p_elements(p):
    '''elements : elements element
                | element'''
    pass

def p_element(p):
    '''element : TAG_OPEN elements TAG_CLOSE
               | TAG_SELF_CLOSE
               | TEXT'''
    if len(p) == 4:
        tag_open = p[1]
        tag_close = p[3]
        tag_name_open = tag_open[1:-1].split()[0]
        tag_name_close = tag_close[2:-1]
        if tag_name_open != tag_name_close:
            raise SyntaxError(f"Mismatched tags: {tag_open} and {tag_close}")

def p_error(p):
    if p:
        print(f"Syntax error at '{p.value}'")
        raise SyntaxError(f"Syntax error at '{p.value}'")
    else:
        print("Syntax error at EOF")
        raise SyntaxError("Syntax error at EOF")

parser = yacc.yacc()

def analyze_html(html_code):
    lexer.input(html_code)
    tokens = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        tokens.append((tok.type, tok.value))
    
    stack = []
    for token in tokens:
        if token[0] == 'TAG_OPEN':
            tag_name = token[1][1:-1].split()[0]
            stack.append(tag_name)
        elif token[0] == 'TAG_CLOSE':
            tag_name = token[1][2:-1]
            if not stack or stack[-1] != tag_name:
                return tokens, f"Mismatched closing tag: {token[1]}"
            stack.pop()
    
    if stack:
        return tokens, "Unmatched opening tags"
    
    syntax_result = "El código HTML es sintácticamente correcto."
    return tokens, syntax_result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    html_code = request.form['code']
    tokens, result = analyze_html(html_code)
    return jsonify({'tokens': tokens, 'syntax_result': result})

if __name__ == '__main__':
    app.run(debug=True)
