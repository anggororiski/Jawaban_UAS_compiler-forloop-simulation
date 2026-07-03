# Simulasi Proses Kompilasi Konstruksi For-Loop

Proyek ini adalah tugas mata kuliah **Compiler Engineering** yang mensimulasikan
empat tahapan utama proses kompilasi — **Analisis Leksikal**, **Analisis
Sintaksis**, **Analisis Semantik**, dan **Generasi Kode Antara (Three-Address
Code / TAC)** — untuk konstruksi perulangan **`for`**.

## 📂 Isi Repository

| File | Deskripsi |
|------|-----------|
| `ForLoopCompiler.py` | Implementasi utama dalam satu class `ForLoopCompiler` (lexer → parser/AST → semantic checker → TAC generator) |
| `Dokumentasi_Simulasi_Kompilasi_ForLoop.md` | Dokumentasi lengkap: grammar BNF, penjelasan tiap tahap, dan contoh hasil eksekusi |

## 🧠 Grammar (BNF)

```
<for_stmt>  ::= "for" "(" <assign> ";" <cond> ";" <assign> ")" "{" <block> "}"
<block>     ::= { <statement> }
<statement> ::= <assign> ";"
<assign>    ::= IDENT "=" <expr>
<cond>      ::= <expr> <relop> <expr>
<expr>      ::= <term> { ("+" | "-") <term> }
<term>      ::= <factor> { ("*" | "/") <factor> }
<factor>    ::= IDENT | NUMBER | "(" <expr> ")"
<relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="
```

## ▶️ Cara Menjalankan

```bash
python3 ForLoopCompiler.py
```

## 📊 Contoh Output

**Input:**
```c
for (i = 0; i < 5; i = i + 1) {
    total = total + i;
    y = i * 2;
}
```

**Three-Address Code (TAC) yang dihasilkan:**
```
i = 0
L1:
t1 = i < 5
ifFalse t1 goto L2
t2 = total + i
total = t2
t3 = i * 2
y = t3
t4 = i + 1
i = t4
goto L1
L2:
```

Penjelasan lengkap tiap tahap tersedia di
[`Dokumentasi_Simulasi_Kompilasi_ForLoop.md`](./Dokumentasi_Simulasi_Kompilasi_ForLoop.md).

## 👤 Author

Ricky — Teknik Informatika, Universitas Pamulang (UNPAM)
