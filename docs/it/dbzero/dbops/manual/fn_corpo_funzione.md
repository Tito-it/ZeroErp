## 📘 Documentazione Concettuale – Funzione `dbops.fn_corpo_funzione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_audit_log_scrittori_fuori_perimetro](/dbzero/dbops/views/vw_audit_log_scrittori_fuori_perimetro) — il cancello sugli scrittori del registro, che la legge
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — la misura degli stati mai scritti, che la legge
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — la misura dei codici nominati, che la legge
> * [dbops.vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) — la risalita alle funzioni di controllo, che la legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_testo_senza_commenti](/dbzero/dbops/funzioni/fn_testo_senza_commenti) — chi toglie davvero i commenti
> * [dbops.fn_find_function_usage](/dbzero/dbops/funzioni/fn_find_function_usage) — lo strumento che cerca le chiamate nei corpi
> * [dbops.fn_search_column_usage](/dbzero/dbops/funzioni/fn_search_column_usage) — lo strumento che cerca una colonna nei corpi
>
> Guide:
>
> * [Linee guida SQL — funzioni `BEGIN ATOMIC`](/linee-guida-sql#5c-funzioni-sql-begin-atomic-perche-come-si-cambiano-come-si-cercano) — perché il sorgente testuale non basta

---

### 🎯 Scopo Principale

Dato l'identificativo di una funzione del catalogo, ne restituisce il corpo senza i commenti, come lo
leggono i presidi e gli strumenti che cercano nei corpi un codice, una tabella o un valore. È la
regola unica per chi cerca qualcosa nel corpo di una funzione.

---

### ⭐ Anche il corpo che il sorgente testuale non ha

Per una funzione scritta in SQL standard con `BEGIN ATOMIC` il sorgente testuale del catalogo è
**vuoto**: il corpo sta nella forma già analizzata. Chi leggeva solo il sorgente non vedeva quelle
funzioni affatto, e un cancello lasciava passare lo scrittore che doveva fermare.

Qui il corpo viene dal sorgente testuale per tutte le altre funzioni, e per una `BEGIN ATOMIC` dalla
forma analizzata, ristampata come testo. In entrambi i casi i commenti li toglie
[fn_testo_senza_commenti](/dbzero/dbops/funzioni/fn_testo_senza_commenti), con i letterali intatti.

⚠️ **I nomi escono sempre qualificati per schema.** La ristampa della forma analizzata scrive i nomi
rispetto al percorso di ricerca di chi la chiede: con lo schema nel percorso stamperebbe il nome nudo
della tabella, e chi cerca il nome completo non lo troverebbe. La funzione fissa per sé il percorso
di ricerca al solo catalogo di sistema, così il risultato è lo stesso per chiunque la chiami.

---

### ⚠️ La collation del risultato non è quella del sorgente

Il sorgente del catalogo ha la collation `"C"`; il risultato di questa funzione ha quella di default.
Chi sostituisce il sorgente con questa funzione e deve comportarsi come prima legge il corpo con la
collation `"C"`: senza, le classi di caratteri e il confronto senza maiuscole cambiano sui caratteri
non ASCII, e la ridefinizione di una vista rifiuta il cambio di collation di una colonna. Le viste che
la usano lo fanno.

---

### ⛔ Chi cerca nei corpi passa da qui

Togliere i commenti dal sorgente con un'espressione regolare propria, o tagliarlo a righe, è la copia
che questa funzione ha ritirato: prima ognuno lo faceva a modo suo, e nessuno rispettava i letterali.
Un prefiltro economico sul sorgente resta ammesso davanti alla lettura (togliendo i commenti il testo
può solo accorciarsi, quindi il prefiltro è un sovrainsieme), ma la ricerca vera gira sul corpo che
esce da qui.

Un identificativo che non è una funzione restituisce nulla. I limiti sul testo (stringhe
dollar-quoted interne, commenti annidati) sono quelli di
[fn_testo_senza_commenti](/dbzero/dbops/funzioni/fn_testo_senza_commenti).

---

### Test

* `db/pgtap/dbops/test-corpo-funzione-senza-commenti-v1.sql` — test 7-10: il corpo di una funzione
  PL/pgSQL è il suo sorgente senza i commenti; per una `BEGIN ATOMIC` il corpo c'è anche se il
  sorgente testuale è vuoto, ed è qualificato anche quando lo schema sta nel percorso di ricerca; un
  identificativo che non è una funzione dà nulla. Test 11, il presidio sul testo: nessuna vista e
  nessuna funzione passa il sorgente del catalogo a una funzione di espressioni regolari. Test 12-15:
  i due strumenti che la usano, `fn_search_column_usage` e `fn_find_function_usage`.

---

### Note di migrazione

* 2026-11-04 — nasce per D14 e D15 di `brief-db-revisione-dbops`: nove viste e due strumenti
  toglievano i commenti ognuno a modo suo e leggevano il sorgente testuale, vuoto per le
  `BEGIN ATOMIC`.

---

{% include-markdown "signature-core.md" %}
