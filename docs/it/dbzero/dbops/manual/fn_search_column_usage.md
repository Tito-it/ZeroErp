## 📘 Documentazione Concettuale – Funzione `dbops.fn_search_column_usage`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — la stessa ricerca, per il nome di una funzione
> * [dbops.fn_find_file_usage](/dbzero/dbops/funzioni/fn_find_file_usage) — chi punta una tabella con una chiave esterna
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti in cui si cerca la colonna
>
> Guide:
>
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — come si cerca davvero nei corpi

---

### 🎯 Scopo Principale

Dato un nome di colonna (o un frammento), elenca gli oggetti nella cui definizione compare: viste,
viste materializzate, regole, funzioni e vincoli. È un attrezzo di consultazione da lanciare a mano
prima di rinominare o togliere una colonna; nessun oggetto del database la chiama.

---

### Dove cerca

* nelle **definizioni** di viste, viste materializzate e regole;
* nel **corpo delle funzioni**, letto da [fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione):
  senza commenti, e anche per le funzioni SQL scritte con `BEGIN ATOMIC`, il cui sorgente testuale è
  vuoto. Una colonna nominata solo in un commento non esce;
* nella **definizione in chiaro dei vincoli** (controlli, chiavi esterne, unicità, chiavi primarie,
  esclusioni), quella che nomina le colonne.

Il parametro è un nome di colonna del catalogo.

---

### ⚠️ Una ricerca testuale: un elenco da guardare

La ricerca è sul testo, senza distinguere maiuscole e minuscole, e il nome si cerca come frammento:
un nome contenuto in un altro dà falsi positivi (cercando un nome corto esce quasi tutto), un nome
uguale in un'altra tabella esce lo stesso, e il trattino basso vale come carattere qualsiasi. La
risposta dice dove il nome **compare**, non dove la colonna è usata, e non dice di quale tabella è la
colonna.

⚠️ **I trigger, gli indici e i valori predefiniti** non sono nel perimetro della ricerca.

Una risposta vuota, quindi, non prova che la colonna non sia usata. Il censimento affidabile delle
dipendenze di una colonna sta nelle dipendenze registrate dal database, non nei testi.

---

### Test

* `db/pgtap/dbops/test-corpo-funzione-senza-commenti-v1.sql`, test 12-13 — trova la colonna in un
  vincolo; la trova nel corpo di una funzione scritta con `BEGIN ATOMIC`.

---

### Note di migrazione

* 2026-11-04 — il ramo dei vincoli legge la definizione in chiaro (D54 di `brief-db-revisione-dbops`):
  prima cercava nella forma interna, dove le colonne sono numeri di posizione, e non trovava mai
  niente.
* 2026-11-04 — il ramo delle funzioni cerca nel corpo di `fn_corpo_funzione` (D15 di
  `brief-db-revisione-dbops`): prima cercava nel sorgente testuale, cieco sulle `BEGIN ATOMIC`, e una
  colonna nominata in un commento contava. Il parametro diventa un nome di colonna del catalogo, lo
  schema restituito prende il tipo dei nomi di schema del catalogo, e la funzione prende un commento nel database, che prima non aveva.

---

{% include-markdown "signature-core.md" %}
