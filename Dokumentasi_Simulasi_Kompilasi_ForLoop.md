# Dokumentasi Tugas: Simulasi Proses Kompilasi Konstruksi *For-Loop*

**Mata Kuliah:** Compiler Engineering
**Konstruksi yang dipilih:** Perulangan `for`
**Bahasa implementasi:** Python 3

---

## 1. Pendahuluan

Tugas ini bertujuan menyimulasikan empat tahapan utama dalam proses kompilasi
sebuah *compiler* sungguhan, yaitu **Analisis Leksikal**, **Analisis
Sintaksis**, **Analisis Semantik**, dan **Generasi Kode Antara (Three-Address
Code / TAC)**, dengan objek studi konstruksi perulangan `for`.

Contoh source code yang digunakan sebagai kasus uji:

```c
for (i = 0; i < 5; i = i + 1) {
    total = total + i;
    y = i * 2;
}
```

Program mengasumsikan variabel `total` sudah dideklarasikan sebelumnya di
luar blok `for` (misalnya `int total = 0;`), sedangkan `i` dan `y`
dideklarasikan secara implisit saat pertama kali menerima nilai (mirip gaya
Python/JavaScript).

---

## 2. Grammar / Pola Sintaksis (BNF)

Berikut adalah tata bahasa (grammar) dalam notasi **BNF** yang mendefinisikan
struktur konstruksi `for` yang diimplementasikan:

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

Grammar ini bersifat *left-recursive-free* dan mudah diimplementasikan
dengan teknik **recursive-descent parsing**, karena setiap non-terminal
memiliki tepat satu jalur produksi yang bisa ditentukan hanya dengan melihat
token berikutnya (1 token *lookahead*).

Ekuivalensi dalam bentuk **Regular Expression** untuk tiap token juga
digunakan pada tahap leksikal (lihat Tabel 1 di bagian berikut).

---

## 3. Tahapan Implementasi

Program `for_loop_compiler.py` dibagi menjadi empat modul yang saling
berurutan, meniru arsitektur pipeline compiler yang sesungguhnya:

```
Source Code → [Lexer] → Token Stream → [Parser] → AST
            → [Semantic Analyzer] → AST tervalidasi
            → [TAC Generator] → Three-Address Code
```

### 3.1 Analisis Leksikal (Lexer)

Fungsi `lex(source_code)` menggunakan modul `re` (regular expression) di
Python untuk memecah teks program menjadi token. Setiap jenis token
didefinisikan dengan pola regex berikut:

| Jenis Token | Pola Regex             | Contoh   |
|-------------|-------------------------|----------|
| NUMBER      | `\d+(\.\d+)?`            | `5`      |
| FOR         | `\bfor\b`                | `for`    |
| IDENT       | `[A-Za-z_][A-Za-z_0-9]*` | `total`  |
| RELOP       | `<=\|>=\|==\|!=\|<\|>`   | `<`      |
| ASSIGN      | `=`                       | `=`      |
| PLUS/MINUS  | `\+` / `-`                | `+`, `-` |
| MUL/DIV     | `\*` / `/`                | `*`, `/` |
| LPAREN/RPAREN | `\(` / `\)`             | `(`, `)` |
| LBRACE/RBRACE | `\{` / `\}`             | `{`, `}` |
| SEMI        | `;`                       | `;`      |

Seluruh pola digabung menjadi satu regex besar menggunakan *named groups*,
lalu di-*scan* dari awal hingga akhir source code dengan `re.finditer`.
Spasi/`newline` diabaikan (`SKIP`), dan karakter yang tidak cocok dengan
pola apapun akan memicu `SyntaxError` (`MISMATCH`), sebagai simulasi
kesalahan leksikal.

Kata kunci `for` awalnya cocok dengan pola `IDENT`, sehingga program
melakukan pengecekan tambahan: jika nilai token sama dengan `"for"`, jenis
tokennya diubah menjadi `FOR`. Ini adalah teknik umum *keyword
recognition* dalam lexer sederhana.

**Contoh hasil tokenisasi** untuk `i = 0`:

```
<IDENT:i> <ASSIGN:=> <NUMBER:0>
```

### 3.2 Analisis Sintaksis (Parser → AST)

Kelas `Parser` mengimplementasikan **recursive-descent parser**, di mana
setiap aturan grammar pada Bagian 2 direpresentasikan sebagai satu method:

- `parse_for()` → menangani struktur `for (...)  { ... }`
- `parse_block()` → mengumpulkan daftar statement di dalam `{ }`
- `parse_statement()` / `parse_assign()` → menangani `x = expr;`
- `parse_cond()` → menangani ekspresi relasional (`i < 5`)
- `parse_expr()`, `parse_term()`, `parse_factor()` → menangani ekspresi
  aritmatika dengan aturan **precedence**: perkalian/pembagian (`term`)
  dievaluasi lebih dulu dibanding penjumlahan/pengurangan (`expr`), sesuai
  kaidah matematika standar.

Setiap method mengembalikan objek **Node** (AST), dengan struktur kelas:

| Node          | Representasi                                   |
|---------------|-------------------------------------------------|
| `ForNode`     | `init`, `cond`, `update`, `body` (list statement)|
| `AssignNode`  | `name`, `expr`                                   |
| `BinOpNode`   | `op`, `left`, `right`                            |
| `VarNode`     | `name`                                           |
| `NumNode`     | `value`                                          |

Fungsi `eat(type_)` memverifikasi token saat ini sesuai dengan token yang
diharapkan grammar; jika tidak sesuai, akan dilempar `SyntaxError`, sebagai
simulasi validasi sintaksis.

**Contoh AST** untuk `i = i + 1`:

```
AssignNode(i =)
  BinOpNode(+)
    VarNode(i)
    NumNode(1)
```

### 3.3 Analisis Semantik

Kelas `SemanticAnalyzer` melakukan dua jenis pengecekan dasar yang umum
dilakukan compiler sungguhan:

1. **Keberadaan variabel (deklarasi sebelum pemakaian).**
   Program menyimpan *symbol table* (`dict`) berisi variabel yang sudah
   "dideklarasikan" (pernah menjadi sisi kiri suatu `AssignNode`, atau
   sudah ada sejak sebelum blok `for` — direpresentasikan lewat parameter
   `predeclared`). Setiap kali sebuah `VarNode` dipakai di sisi kanan
   ekspresi atau di dalam kondisi, program memeriksa keberadaannya di
   symbol table. Jika tidak ditemukan, dihasilkan:
   ```
   [SEMANTIC ERROR] Variabel 'z' digunakan sebelum dideklarasikan/di-assign.
   ```

2. **Konsistensi tipe data sederhana.**
   Karena seluruh nilai pada implementasi ini bertipe tunggal `number`,
   pengecekan tipe dilakukan dengan memastikan kedua operand dari sebuah
   `BinOpNode` memiliki tipe yang sama. Struktur ini sengaja dibuat
   generik agar mudah dikembangkan (misalnya menambahkan tipe `string`
   atau `boolean`) tanpa mengubah alur analisis.

Apabila ditemukan kesalahan semantik, proses kompilasi **dihentikan** dan
tidak lanjut ke tahap generasi kode — sama seperti perilaku compiler
sungguhan yang tidak akan menghasilkan object code jika terdapat error.

### 3.4 Generasi Kode Antara (Three-Address Code)

Kelas `TACGenerator` menelusuri (traverse) AST secara rekursif dan
menghasilkan instruksi **Three-Address Code**, yaitu representasi kode
yang setiap instruksinya memiliki paling banyak satu operator dan tiga
alamat (dua operand + satu hasil).

Mekanisme utama:

- **`new_temp()`** — membuat variabel sementara baru (`t1`, `t2`, ...) untuk
  menyimpan hasil antara dari suatu operasi biner.
- **`new_label()`** — membuat label baru (`L1`, `L2`, ...) untuk menandai
  titik lompatan (jump target) dalam kode.
- **`gen_expr(node)`** — fungsi rekursif yang mengevaluasi node ekspresi:
  - Jika `NumNode`/`VarNode`, langsung mengembalikan nilai/nama variabelnya.
  - Jika `BinOpNode`, kode dibangkitkan dulu untuk anak kiri & kanan, lalu
    diemit instruksi `t_baru = kiri OP kanan`.
- **`gen_for(node)`** — pola generasi kode untuk struktur `for` mengikuti
  skema baku compiler untuk loop:

  ```
          <kode init>
  L_cond:
          <kode evaluasi kondisi> -> t
          ifFalse t goto L_end
          <kode body>
          <kode update>
          goto L_cond
  L_end:
  ```

  Skema ini adalah pola standar penerjemahan `for` menjadi TAC yang
  diajarkan dalam teori compiler (Aho, Sethi, Ullman — *Dragon Book*),
  yaitu mengubah struktur loop berbasis kondisi menjadi kombinasi label
  dan instruksi lompat bersyarat/tanpa syarat.

---

## 4. Hasil Eksekusi Program

### 4.1 Kasus 1 — Program Valid

**Input:**
```c
for (i = 0; i < 5; i = i + 1) {
    total = total + i;
    y = i * 2;
}
```
*(variabel `total` diasumsikan sudah dideklarasikan sebelum blok `for`)*

**Tahap 1 — Token:**
```
<FOR:for> <LPAREN:(> <IDENT:i> <ASSIGN:=> <NUMBER:0> <SEMI:;>
<IDENT:i> <RELOP:<> <NUMBER:5> <SEMI:;>
<IDENT:i> <ASSIGN:=> <IDENT:i> <PLUS:+> <NUMBER:1> <RPAREN:)>
<LBRACE:{>
<IDENT:total> <ASSIGN:=> <IDENT:total> <PLUS:+> <IDENT:i> <SEMI:;>
<IDENT:y> <ASSIGN:=> <IDENT:i> <MUL:*> <NUMBER:2> <SEMI:;>
<RBRACE:}>
```

**Tahap 2 — AST:**
```
ForNode
├─ init:      AssignNode(i =) → NumNode(0)
├─ cond:      BinOpNode(<)   → VarNode(i), NumNode(5)
├─ update:    AssignNode(i =) → BinOpNode(+) → VarNode(i), NumNode(1)
└─ body:
    AssignNode(total =) → BinOpNode(+) → VarNode(total), VarNode(i)
    AssignNode(y =)     → BinOpNode(*) → VarNode(i), NumNode(2)
```

**Tahap 3 — Semantik:**
```
Tidak ditemukan kesalahan semantik.
Symbol table akhir: {'total': 'number', 'i': 'number', 'y': 'number'}
```

**Tahap 4 — Three-Address Code (output akhir):**
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

### 4.2 Kasus 2 — Program dengan Kesalahan Semantik

**Input:**
```c
for (i = 0; i < 5; i = i + 1) {
    total = z + i;
}
```

Karena variabel `z` **tidak pernah dideklarasikan** di manapun (baik di
luar maupun di dalam blok `for`), tahap semantik menghasilkan:

```
[SEMANTIC ERROR] Variabel 'z' digunakan sebelum dideklarasikan/di-assign.

Kompilasi dihentikan karena terdapat kesalahan semantik.
```

Proses **tidak lanjut** ke tahap generasi TAC, menunjukkan bahwa
implementasi sudah benar dalam menegakkan urutan pipeline compiler: tahap
selanjutnya hanya dijalankan apabila tahap sebelumnya lolos validasi.

---

## 5. Analisis Hasil TAC

Menelusuri hasil TAC pada Kasus 1:

| Baris TAC                  | Penjelasan                                              |
|-----------------------------|----------------------------------------------------------|
| `i = 0`                     | Inisialisasi variabel loop counter                       |
| `L1:`                       | Label awal iterasi (tempat kembali setiap putaran)        |
| `t1 = i < 5`                | Evaluasi kondisi loop, disimpan ke variabel sementara `t1`|
| `ifFalse t1 goto L2`        | Jika kondisi salah, lompat keluar loop ke label `L2`       |
| `t2 = total + i`            | Evaluasi ekspresi `total + i`                              |
| `total = t2`                | Menyimpan hasil ke variabel `total`                        |
| `t3 = i * 2`                | Evaluasi ekspresi `i * 2`                                   |
| `y = t3`                    | Menyimpan hasil ke variabel `y`                             |
| `t4 = i + 1`                | Evaluasi update counter `i + 1`                             |
| `i = t4`                    | Menyimpan hasil update ke `i`                               |
| `goto L1`                   | Kembali ke pengecekan kondisi (mengulang loop)              |
| `L2:`                       | Label akhir loop (titik keluar)                             |

Struktur ini identik dengan pola umum penerjemahan `for` → TAC pada
compiler sungguhan (mirip dengan output *intermediate representation* pada
GCC/LLVM dalam bentuk sederhana), dan mudah diterjemahkan lebih lanjut
menjadi kode assembly atau bytecode pada tahap *code generation* akhir.

---

## 6. Cara Menjalankan Program

1. Pastikan Python 3 terpasang.
2. Jalankan perintah:
   ```bash
   python3 for_loop_compiler.py
   ```
3. Program akan otomatis menjalankan dua skenario contoh (kasus valid dan
   kasus error semantik) dan mencetak keempat tahapan kompilasi ke layar.
4. Untuk menguji source code lain, panggil fungsi:
   ```python
   compile_for_loop(source_code_anda, predeclared=["nama_variabel_luar"])
   ```

---

## 7. Kesimpulan

Implementasi ini berhasil menyimulasikan keempat tahap utama proses
kompilasi untuk konstruksi perulangan `for`:

1. **Lexer** memecah source code menjadi token menggunakan pendekatan
   regex-based scanning.
2. **Parser** membentuk AST melalui teknik recursive-descent sesuai
   grammar BNF yang telah didefinisikan.
3. **Semantic Analyzer** memvalidasi keberadaan variabel dan konsistensi
   tipe data menggunakan symbol table, serta menghentikan kompilasi jika
   ditemukan kesalahan.
4. **TAC Generator** menerjemahkan AST tervalidasi menjadi kode antara
   Three-Address Code dengan pola standar label + lompatan bersyarat untuk
   struktur loop.

Arsitektur modular ini (lexer → parser → semantic analyzer → TAC
generator) merepresentasikan alur kerja compiler front-end pada umumnya,
dan dapat dikembangkan lebih lanjut untuk mendukung konstruksi lain
seperti `if-else`, `while`, atau deklarasi tipe data eksplisit.
