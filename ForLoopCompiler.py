"""
==================================================================
 SIMULASI PROSES KOMPILASI KONSTRUKSI FOR-LOOP
 (Format class tunggal, mengikuti gaya contoh referensi tugas)
==================================================================
Konstruksi yang dipilih : Perulangan for

Grammar (BNF):

    <for_stmt>  ::= "for" "(" <assign> ";" <cond> ";" <assign> ")" "{" <block> "}"
    <block>     ::= { <statement> }
    <statement> ::= <assign> ";"
    <assign>    ::= <identifier> "=" <expr>
    <cond>      ::= <expr> <relop> <expr>
    <expr>      ::= <term> { ("+" | "-") <term> }
    <term>      ::= <factor> { ("*" | "/") <factor> }
    <factor>    ::= <identifier> | <number> | "(" <expr> ")"
    <relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="

Tahapan yang disimulasikan di dalam class ForLoopCompiler:
    1. lexical_analysis()        -> Analisis Leksikal (tokenisasi berbasis regex)
    2. syntax_semantic_analysis()-> Analisis Sintaksis (AST) + Analisis Semantik
    3. generate_tac()            -> Generasi Kode Antara (Three-Address Code)
==================================================================
"""

import re


class ForLoopCompiler:
    """
    Class utama yang menyimulasikan pipeline compiler untuk konstruksi
    for-loop: Lexical Analysis -> Syntax & Semantic Analysis -> TAC Generation.
    """

    # ---- Spesifikasi token untuk tahap leksikal ----
    TOKEN_SPEC = [
        ("NUMBER",   r"\d+(\.\d+)?"),
        ("FOR",      r"\bfor\b"),
        ("IDENT",    r"[A-Za-z_][A-Za-z_0-9]*"),
        ("RELOP",    r"<=|>=|==|!=|<|>"),
        ("ASSIGN",   r"="),
        ("PLUS",     r"\+"),
        ("MINUS",    r"-"),
        ("MUL",      r"\*"),
        ("DIV",      r"/"),
        ("LPAREN",   r"\("),
        ("RPAREN",   r"\)"),
        ("LBRACE",   r"\{"),
        ("RBRACE",   r"\}"),
        ("SEMI",     r";"),
        ("SKIP",     r"[ \t\n]+"),
        ("MISMATCH", r"."),
    ]

    def __init__(self, source_code, predeclared=None):
        self.source_code = source_code
        # Variabel yang dianggap sudah dideklarasikan sebelum blok for
        # (misalnya "int total = 0;" di luar loop)
        self.predeclared = predeclared or []

        self.tokens = []
        self.pos = 0            # posisi token saat parsing
        self.temp_counter = 1   # penghitung variabel sementara (t1, t2, ...)
        self.label_counter = 1  # penghitung label (L1, L2, ...)
        self.symbol_table = {name: "number" for name in self.predeclared}
        self.semantic_errors = []
        self.tac_code = []

        self._token_regex = re.compile(
            "|".join(f"(?P<{n}>{p})" for n, p in self.TOKEN_SPEC)
        )

    # ==============================================================
    # Utility internal
    # ==============================================================
    def new_temp(self):
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self):
        lbl = f"L{self.label_counter}"
        self.label_counter += 1
        return lbl

    # ==============================================================
    # TAHAP 1: ANALISIS LEKSIKAL
    # ==============================================================
    def lexical_analysis(self):
        """Memecah source_code menjadi daftar token (list of dict)."""
        tokens = []
        for match in self._token_regex.finditer(self.source_code):
            kind = match.lastgroup
            value = match.group()
            if kind == "SKIP":
                continue
            if kind == "MISMATCH":
                raise SyntaxError(f"[LEXICAL ERROR] Karakter tidak dikenal: {value!r}")
            if kind == "IDENT" and value == "for":
                kind = "FOR"
            tokens.append({"type": kind, "value": value})
        tokens.append({"type": "EOF", "value": None})
        self.tokens = tokens
        return self.tokens

    # ==============================================================
    # TAHAP 2: ANALISIS SINTAKSIS (AST) + ANALISIS SEMANTIK
    # ==============================================================
    def _current(self):
        return self.tokens[self.pos]

    def _eat(self, type_):
        tok = self._current()
        if tok["type"] != type_:
            raise SyntaxError(
                f"[SYNTAX ERROR] Diharapkan '{type_}', ditemukan "
                f"'{tok['type']}' ({tok['value']!r})"
            )
        self.pos += 1
        return tok

    # ---- Grammar: <for_stmt> ----
    def _parse_for(self):
        self._eat("FOR")
        self._eat("LPAREN")
        init = self._parse_assign()
        self._eat("SEMI")
        cond = self._parse_cond()
        self._eat("SEMI")
        update = self._parse_assign()
        self._eat("RPAREN")
        self._eat("LBRACE")
        body = self._parse_block()
        self._eat("RBRACE")
        return {"node": "For", "init": init, "cond": cond, "update": update, "body": body}

    def _parse_block(self):
        statements = []
        while self._current()["type"] != "RBRACE":
            statements.append(self._parse_statement())
        return statements

    def _parse_statement(self):
        node = self._parse_assign()
        self._eat("SEMI")
        return node

    def _parse_assign(self):
        name = self._eat("IDENT")["value"]
        self._eat("ASSIGN")
        expr = self._parse_expr()
        return {"node": "Assign", "name": name, "expr": expr}

    def _parse_cond(self):
        left = self._parse_expr()
        op = self._eat("RELOP")["value"]
        right = self._parse_expr()
        return {"node": "BinOp", "op": op, "left": left, "right": right}

    def _parse_expr(self):
        node = self._parse_term()
        while self._current()["type"] in ("PLUS", "MINUS"):
            op = self._eat(self._current()["type"])["value"]
            right = self._parse_term()
            node = {"node": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _parse_term(self):
        node = self._parse_factor()
        while self._current()["type"] in ("MUL", "DIV"):
            op = self._eat(self._current()["type"])["value"]
            right = self._parse_factor()
            node = {"node": "BinOp", "op": op, "left": node, "right": right}
        return node

    def _parse_factor(self):
        tok = self._current()
        if tok["type"] == "NUMBER":
            self._eat("NUMBER")
            return {"node": "Num", "value": tok["value"]}
        if tok["type"] == "IDENT":
            self._eat("IDENT")
            return {"node": "Var", "name": tok["value"]}
        if tok["type"] == "LPAREN":
            self._eat("LPAREN")
            node = self._parse_expr()
            self._eat("RPAREN")
            return node
        raise SyntaxError(f"[SYNTAX ERROR] Token tak terduga: {tok}")

    # ---- Analisis semantik: berjalan sambil menelusuri AST ----
    def _check_var(self, name):
        if name not in self.symbol_table:
            self.semantic_errors.append(
                f"[SEMANTIC ERROR] Variabel '{name}' digunakan sebelum dideklarasikan/di-assign."
            )

    def _semantic_expr(self, node):
        if node["node"] == "Var":
            self._check_var(node["name"])
        elif node["node"] == "BinOp":
            self._semantic_expr(node["left"])
            self._semantic_expr(node["right"])
        # NumNode tidak perlu dicek

    def _semantic_assign(self, node):
        self._semantic_expr(node["expr"])
        self.symbol_table[node["name"]] = "number"  # deklarasi otomatis setelah assign

    def syntax_semantic_analysis(self, tokens):
        """
        Menggabungkan tahap sintaksis (membentuk AST) dan tahap semantik
        (validasi variabel) menjadi satu method, sesuai pola pada contoh
        referensi tugas.
        Mengembalikan tuple: (ast, semantic_errors)
        """
        self.tokens = tokens
        self.pos = 0
        ast = self._parse_for()

        # analisis semantik dijalankan setelah AST terbentuk
        self._semantic_assign(ast["init"])
        self._semantic_expr(ast["cond"])
        for stmt in ast["body"]:
            self._semantic_assign(stmt)
        self._semantic_assign(ast["update"])

        return ast, self.semantic_errors

    # ==============================================================
    # TAHAP 3: GENERASI KODE ANTARA (THREE-ADDRESS CODE)
    # ==============================================================
    def _gen_expr(self, node):
        if node["node"] == "Num":
            return node["value"]
        if node["node"] == "Var":
            return node["name"]
        if node["node"] == "BinOp":
            left = self._gen_expr(node["left"])
            right = self._gen_expr(node["right"])
            temp = self.new_temp()
            self.tac_code.append(f"{temp} = {left} {node['op']} {right}")
            return temp
        raise ValueError(f"Node tidak dikenal: {node}")

    def _gen_assign(self, node):
        result = self._gen_expr(node["expr"])
        self.tac_code.append(f"{node['name']} = {result}")

    def generate_tac(self):
        """
        Menjalankan lexical_analysis() dan syntax_semantic_analysis()
        secara berurutan, lalu membangkitkan Three-Address Code dari AST.
        Jika ditemukan kesalahan semantik, TAC tidak dibangkitkan dan
        pesan error dikembalikan sebagai string.
        """
        tokens = self.lexical_analysis()
        ast, errors = self.syntax_semantic_analysis(tokens)

        if errors:
            return "\n".join(errors)

        l_cond = self.new_label()
        l_end = self.new_label()

        self._gen_assign(ast["init"])                      # inisialisasi
        self.tac_code.append(f"{l_cond}:")
        cond_result = self._gen_expr(ast["cond"])            # evaluasi kondisi
        self.tac_code.append(f"ifFalse {cond_result} goto {l_end}")
        for stmt in ast["body"]:                             # badan loop
            self._gen_assign(stmt)
        self._gen_assign(ast["update"])                      # update counter
        self.tac_code.append(f"goto {l_cond}")
        self.tac_code.append(f"{l_end}:")

        return "\n".join(self.tac_code)


# ======================================================================
# --- Contoh Penggunaan ---
# ======================================================================
if __name__ == "__main__":
    # Variabel 'total' diasumsikan sudah dideklarasikan sebelum blok for
    # (misalnya "int total = 0;")
    source = """
    for (i = 0; i < 5; i = i + 1) {
        total = total + i;
        y = i * 2;
    }
    """

    compiler = ForLoopCompiler(source, predeclared=["total"])

    print("--- Hasil Analisis Leksikal (Tokens) ---")
    print(compiler.lexical_analysis())

    print("\n--- Generasi Three-Address Code (TAC) ---")
    print(compiler.generate_tac())

    print("\n\n=== Contoh kasus dengan kesalahan semantik ===")
    source_error = """
    for (i = 0; i < 5; i = i + 1) {
        total = z + i;
    }
    """
    compiler_error = ForLoopCompiler(source_error, predeclared=["total"])
    print("--- Hasil Analisis Leksikal (Tokens) ---")
    print(compiler_error.lexical_analysis())

    print("\n--- Generasi Three-Address Code (TAC) ---")
    print(compiler_error.generate_tac())
