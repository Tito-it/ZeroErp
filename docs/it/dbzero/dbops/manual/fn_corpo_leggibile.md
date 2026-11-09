## 📘 Documentazione Concettuale – Funzione `dbops.fn_corpo_leggibile`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare) — i codici che un corpo può sollevare
> * [dbops.vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo) — come un codice viene sollevato, e se indica il campo
> * [dbops.vw_funzioni_check_codici](/dbzero/dbops/views/vw_funzioni_check_codici) — la risalita dalla funzione alle sue `fn_check_*` e ai loro codici
> * [dbops.vw_punti_primo_motivo](/dbzero/dbops/views/vw_punti_primo_motivo) — i punti che sollevano a mano il primo motivo
> * [dbops.vw_bersagli_non_dichiarati](/dbzero/dbops/views/vw_bersagli_non_dichiarati) — i tipi di bersaglio che il catalogo non dichiara
> * [dbops.vw_stati_check_scrittori](/dbzero/dbops/views/vw_stati_check_scrittori) — gli stati previsti e mai scritti
> * [dbops.vw_codici_errore_forme_condizione](/dbzero/dbops/views/vw_codici_errore_forme_condizione) — la sola vista sui codici che resta sul PL/pgSQL, per decisione
>
> Approfondimento funzioni:
>
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti, che questa funzione sa di poter leggere
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la chiamata che una funzione SQL può fare come una PL/pgSQL

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **il corpo delle funzioni scritte in questo linguaggio si può leggere?**
Vero per PL/pgSQL e SQL, comprese le funzioni SQL scritte con `BEGIN ATOMIC`. Falso per C e
`internal`, e falso per un valore mancante.

È il perimetro dei presidi che leggono il corpo delle funzioni, scritto in un posto solo: prima ogni
vista lo scriveva per conto suo, in tre forme diverse.

---

### ⭐ Il perimetro è il modello, non il linguaggio

I presidi sul corpo cercano chi solleva un codice, chi nomina una `fn_check_*`, chi costruisce un
bersaglio, chi scrive uno stato. Una funzione SQL può fare tutte queste cose come una PL/pgSQL: per
esempio chiamare `fn_log_and_raise_error` con un codice scritto in chiaro. Conta chi può sollevare un
codice, non il linguaggio in cui è scritto.

Il corpo di una funzione C o `internal` invece non è un testo: è il nome di un simbolo, e non c'è
niente da leggere. I linguaggi ammessi sono quelli di cui
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) restituisce il corpo come testo.

⛔ **Un linguaggio nuovo con un corpo leggibile si aggiunge qui, e solo qui.** Le viste lo leggono da
questa funzione e non lo ripetono.

---

### Chi la usa

| Chi | Per che cosa |
| --- | --- |
| `dbops.vw_codici_errore_da_dichiarare` | quali corpi possono nominare un codice |
| `dbops.vw_punti_canale_campo` | quali corpi sollevano un codice, e con quale canale |
| `dbops.vw_funzioni_check_codici` | quali corpi nominano una `fn_check_*` |
| `dbops.vw_punti_primo_motivo` | quali corpi sollevano a mano il primo motivo |
| `dbops.vw_bersagli_non_dichiarati` | quali corpi costruiscono un bersaglio |
| `dbops.vw_stati_check_scrittori` | quali corpi scrivono uno stato |

⚠️ `dbops.vw_codici_errore_forme_condizione` **non** la usa, di proposito: riconosce la guardia dalle
righe `IF` ed `EXCEPTION WHEN`, che una funzione SQL non ha, e resta sul solo PL/pgSQL.

È scritta come una sola interrogazione, perché il planner la sostituisca nella query che la chiama:
l'elenco dei linguaggi si calcola una volta sola, non riga per riga.

---

### Codici errore

Nessuno: risponde vero o falso, e non solleva.

---

### Test

* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql` — vero per PL/pgSQL e SQL, falso per C e
  `internal` (test 1); falso, e non vuoto, per un valore mancante (test 2). Gli altri test provano le
  viste che la leggono su funzioni SQL costruite apposta, anche `BEGIN ATOMIC`.

---

### Note di migrazione

* 2026-11-09 — nasce, al posto del perimetro scritto in linea nelle viste che leggono il corpo delle
  funzioni: sei di loro leggevano il solo PL/pgSQL, e `vw_stati_check_scrittori` PL/pgSQL e SQL con
  un elenco scritto a mano. Da qui lo leggono tutte (`20261110-59`, `brief-db-revisione-dbops`,
  giro 12).

---

{% include-markdown "signature-core.md" %}
