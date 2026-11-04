## 📘 Documentazione Concettuale – Funzione `dbops.fn_regexp_occorrenze`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) — la vista che la usa

---

### 🎯 Scopo Principale

Le occorrenze di un'espressione regolare in un testo, una riga per ognuna con i gruppi catturati:
lo stesso risultato della ricerca globale di sistema. Esiste per dichiarare la cardinalità vera, una
riga, dove la stima di un piano conta.

---

### ⭐ Perché una funzione che fa la stessa cosa di quella di sistema

La funzione di sistema dichiara dieci righe per chiamata. In
[vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) quel dieci, moltiplicato da
due ricorsioni, portava la stima del costo sopra la soglia del JIT appena le statistiche del
catalogo contavano più corpi: PostgreSQL compilava la query, e ogni lettura pagava la compilazione.
Le occorrenze vere per corpo sono molto meno di una: dichiarare una riga avvicina la stima al vero.

⚠️ È scritta in PL/pgSQL di proposito: una funzione in SQL semplice verrebbe espansa nella query
chiamante, e la cardinalità dichiarata sarebbe ignorata.

---

### Che cosa non fa

* non è `STRICT`, ma con un argomento nullo non dà righe, come la funzione di sistema;
* non sostituisce ogni ricerca globale del progetto: si usa dove la stima moltiplica un piano.

---

### Test

* `db/pgtap/dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql` — dichiara una riga e non si
  espande nella query; la vista non chiama direttamente le funzioni di sistema; la stima della vista
  e dei due presidi che la leggono resta sotto la soglia del JIT.

---

### Note di migrazione

* 2026-10-12 — nasce per il rosso di `test-vw-funzioni-check-codici-sotto-jit-v1` su `zeroerp_ci`.
  Il precedente, una cardinalità dichiarata a una riga con lo stesso scopo, è del 2026-10-08.

---

{% include-markdown "signature-core.md" %}
