from flask import Flask, request, jsonify, render_template
import re
import ply.lex as lex
import ply.yacc as yacc

app = Flask(__name__)

# Lexer para analizar ciclos for dentro de la etiqueta <script>
tokens = (
    'INT', 'ID', 'NUMBER', 'SEMI', 'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'LE', 'ASSIGN', 'PLUS', 'DOT', 'OUT', 'PRINTLN', 'FOR'
)

reserved = {
    'for': 'FOR',
    'int': 'INT',
    'out': 'OUT',
    'println': 'PRINTLN'
}

t_SEMI    = r';'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE  = r'\{'
t_RBRACE  = r'\}'
t_ASSIGN  = r'='
t_PLUS    = r'\+\+'
t_DOT     = r'\.'
t_LE      = r'<='

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_error(t):
    t.lexer.skip(1)

t_ignore = ' \t\n'

lexer = lex.lex()

variables = {}

def p_program(p):
    'program : declaration for_statement'
    p[0] = ('program', p[1], p[2])

def p_declaration(p):
    'declaration : INT ID SEMI'
    variables[p[2]] = None
    p[0] = ('declaration', p[2])

def p_for_statement(p):
    'for_statement : FOR LPAREN ID ASSIGN NUMBER SEMI ID LE NUMBER SEMI ID PLUS RPAREN LBRACE statement RBRACE'
    if p[3] not in variables:
        raise Exception(f"Error semántico: Variable '{p[3]}' no declarada.")
    elif p[7] not in variables:
        raise Exception(f"Error semántico: Variable '{p[7]}' no declarada.")
    elif p[11] not in variables:
        raise Exception(f"Error semántico: Variable '{p[11]}' no declarada.")
    else:
        p[0] = ('for_statement', p[3], p[5], p[9], p[15])

def p_statement(p):
    'statement : OUT DOT PRINTLN LPAREN ID RPAREN SEMI'
    if p[5] not in variables:
        p[0] = f"Error semántico: Variable '{p[5]}' no declarada."
    else:
        p[0] = ('statement', p[5])

def p_error(p):
    if p:
        p[0] = f"Error de sintaxis en '{p.value}'"
    else:
        p[0] = "Error de sintaxis al final del archivo"

parser = yacc.yacc()

def analyze_code(code):
    global variables
    variables = {}
    lexer.input(code)
    try:
        result = parser.parse(code, lexer=lexer)
        if isinstance(result, str):
            return result
        else:
            return "El código es semánticamente correcto."
    except Exception as e:
        return str(e)

# Función para tokenizar el código HTML
def tokenize_html(html_code):
    token_patterns = [
        (r'<!DOCTYPE[^>]+>', 'DOCTYPE'),
        (r'<script.*?>', 'SCRIPT_START'),
        (r'</script>', 'SCRIPT_END'),
        (r'</?[^>]+>', 'TAG'),
        (r'".*?"', 'ATTRIBUTE_VALUE'),
        (r"'.*?'", 'ATTRIBUTE_VALUE'),
        (r'=[^\s>]+', 'ATTRIBUTE_ASSIGN'),
        (r'\s+', 'WHITESPACE'),
        (r'[^<\s][^<]*[^<\s]', 'TEXT'),
    ]
    tokens = []
    script_mode = False
    for pattern, token_type in token_patterns:
        for match in re.finditer(pattern, html_code):
            if token_type == 'SCRIPT_START':
                script_mode = True
            elif token_type == 'SCRIPT_END':
                script_mode = False
            if script_mode or token_type in ['SCRIPT_START', 'SCRIPT_END']:
                tokens.append((match.group(0), token_type))
            else:
                tokens.append((match.group(0), token_type))
    return tokens

def analyze_script_content(script_content):
    global variables
    variables = {}  # Reiniciar el diccionario de variables para cada script

    lexer.input(script_content)
    try:
        result = parser.parse(script_content, lexer=lexer)
        if isinstance(result, str):
            return [result]
        else:
            # Verificar si se usaron variables no declaradas
            undeclared_vars = [var for var in variables if variables[var] is None]
            if undeclared_vars:
                error_messages = [f"Error semántico: Variable '{var}' declarada pero no utilizada." for var in undeclared_vars]
                return error_messages
            return ["El código dentro de <script> es semánticamente correcto."]
    except Exception as e:
        return [str(e)]


def analyze_syntax(tokens):
    stack = []
    script_content = ""
    inside_script = False
    all_errors = [] 

    for token, token_type in tokens:
        if token_type == 'SCRIPT_START':
            inside_script = True
            script_content = "" 
            continue
        elif token_type == 'SCRIPT_END':
            inside_script = False
            errors = analyze_script_content(script_content)
            if errors:
                all_errors.extend(errors) 
            continue
        if inside_script:
            script_content += token  

    return all_errors

# Asegúrate de que el resto de tu código esté correctamente implementado
# Análisis semántico simplificado
def analyze_semantics(tokens):
    essential_elements = ['<html>', '<head>', '<title>', '<body>']
    missing_elements = []
    for element in essential_elements:
        found = False
        for token, token_type in tokens:
            if token.lower().startswith(element):
                found = True
                break
        if not found:
            missing_elements.append(f"Falta el elemento esencial: {element}")
    return missing_elements


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    html_code = request.form['code']
    
    # Mejora en la extracción del contenido de las etiquetas <script>
    script_contents = re.findall(r'<script.*?>(.*?)</script>', html_code, re.DOTALL)
    clean_html_code = re.sub(r'<script.*?>.*?</script>', '', html_code, flags=re.DOTALL)
    
    # Tokenizar y analizar el HTML sin el contenido de <script>
    tokens = tokenize_html(clean_html_code)
    syntax_errors = analyze_syntax(tokens)
    semantic_errors = analyze_semantics(tokens)
    
    # Analizar el contenido de las etiquetas <script>
    script_analysis_results = [analyze_code(script) for script in script_contents]

    return jsonify({
        'tokens': [token for token, _ in tokens],
        'syntax_errors': syntax_errors,
        'semantic_errors': semantic_errors,
        'script_analysis_results': script_analysis_results
    })

if __name__ == '__main__':
    app.run(debug=True)
