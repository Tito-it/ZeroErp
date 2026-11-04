## 📘 Documentazione Concettuale – Vista `dbops.vw_audit_log_scrittori_fuori_perimetro`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il registro che il cancello protegge
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo dei presidi, dove la vista è un cancello
>
> Approfondimento funzioni:
>
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — la porta di scrittura dell'applicazione
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti, anche delle `BEGIN ATOMIC`, da cui la vista legge
>
> Guide:
>
> * [Audit Logging](/guide/messaggi-audit) — chi può scrivere nel registro

---

### 🎯 Scopo Principale

Elenca le **funzioni che scrivono nel registro delle esecuzioni** `dbops.audit_log` e che stanno
**fuori dagli schemi ammessi**, `dbops` e `maintenance`: l'elenco degli schemi sta scritto dentro
la vista.

⛔ È un **cancello**: deve restare vuota. Una riga fa fallire il controllo del rilascio, non è un
promemoria.

---

### ⭐ Perché esiste, detto sul modello

`dbops.audit_log` è il registro tecnico delle automazioni e degli strumenti di amministrazione del
database: lo scrivono le funzioni di `dbops` e `maintenance`, lo legge l'amministrazione. **Non deve
poter contenere dati di dominio** — i parametri di una fattura, l'esito di un'operazione su un
cliente.

Proteggerlo come le tabelle di storico, con una regola di visibilità per riga, sarebbe la risposta
sbagliata: il registro non ha una riga madre da cui prendere il perimetro, e un filtro per riga su
un log si paga a ogni lettura. La domanda giusta è se il registro debba poter contenere dati di
dominio, e la risposta è no. Il rischio si toglie quindi **alla fonte**: nessuna funzione di un
dominio ci scrive, e se una lo facesse questa vista la nomina.

---

### Che cosa guarda, e che cosa no

| Conta come «scrive» | Non conta |
| --- | --- |
| un inserimento, un aggiornamento o una cancellazione su `dbops.audit_log` nel corpo (`come_scrive` = `DML_DIRETTO`) | una lettura del registro |
| una chiamata a `fn_audit_log_once` (`come_scrive` = `VIA_FN_AUDIT`) | i commenti, di riga e a blocco: il corpo si legge senza, così un esempio commentato non fa scattare il cancello |
| | la funzione di audit stessa, che è la porta e sta in `dbops` |

Legge solo il catalogo delle funzioni, con `security_invoker`: non tocca dati.

La porta che la vista riconosce è una sola, `fn_audit_log_once`, ed è esclusa per nome.

Il corpo di ogni funzione si legge da [fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione):
senza commenti, con i letterali intatti, e anche per le funzioni SQL scritte nella forma
`BEGIN ATOMIC`, il cui sorgente testuale è vuoto. Una funzione così che scrive nel registro da fuori
perimetro compare come le altre.

⚠️ Non vede una scrittura composta con SQL dinamico, dove il nome della tabella si costruisce a
pezzi.

---

### Se compare una riga

Due esiti possibili, e nessuno dei due è aggiungere lo schema all'elenco senza pensarci:

1. la funzione **non doveva** scrivere nel registro — il caso atteso: si toglie la chiamata, e ciò
   che voleva registrare va nel posto suo (`dbops.error_log` per un errore, una tabella di dominio
   per un fatto di dominio);
2. il perimetro deve **davvero** allargarsi: è un changeSet su questa vista, firmato e motivato,
   non una riga che passa in silenzio.

---

### Test

* `db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql` — la vista è vuota; dentro il
  perimetro gli scrittori ci sono, quindi la ricerca vede; il perimetro dichiarato è `dbops` e
  `maintenance`; una funzione temporanea costruita fuori perimetro che chiama la porta compare, ed è
  classificata come scrittura attraverso la porta; la vista è a catalogo in `dbops.presidi` come
  cancello; uno scrittore `BEGIN ATOMIC` fuori perimetro è visto come scrittura diretta (test 7); una
  chiamata alla porta rimasta in un commento a blocco non conta (test 8).

---

### Note di migrazione

* 2026-09-11 — nasce con la decisione che il registro delle esecuzioni non contenga dati di dominio
  (`brief-db-rls-storico-scope-congelato`, §8.3 e §8.6).
* 2026-11-04 — ritirate `fn_audit_begin` e `fn_audit_end` (`brief-db-revisione-dbops`).
* 2026-11-04 — il corpo si legge da `fn_corpo_funzione` (D14 e D15 di `brief-db-revisione-dbops`):
  prima era il sorgente testuale senza i soli commenti di riga, cieco sulle `BEGIN ATOMIC` (una di
  loro fuori perimetro che scrivesse il registro passava il cancello), e una chiamata in un commento
  a blocco contava. Escono dalla vista anche i nomi di `fn_audit_begin` e `fn_audit_end`: la porta
  è la sola `fn_audit_log_once`.
* 2026-11-04 — il corpo senza commenti si chiede solo per le funzioni che nominano `audit_log` nel
  testo grezzo, più tutte le `BEGIN ATOMIC` (il loro testo grezzo è vuoto). È un sovrainsieme
  esatto: togliere i commenti può solo levare testo. Prima il building block girava su ogni
  funzione del database a ogni lettura. Output invariato.

---

{% include-markdown "signature-core.md" %}
