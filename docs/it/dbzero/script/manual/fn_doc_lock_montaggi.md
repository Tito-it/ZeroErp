## 📘 Documentazione Concettuale – Funzione `script.fn_doc_lock_montaggi()`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [script.fn_doc_lock_regola](/dbzero/script/funzioni/fn_doc_lock_regola) — la grammatica degli argomenti
> • [script.fn_doc_lock_colonna_bloccata](/dbzero/script/funzioni/fn_doc_lock_colonna_bloccata) — la decisione
> • [script.fn_doc_colonna_modificabile](/dbzero/script/funzioni/fn_doc_colonna_modificabile) — la domanda di una capability
> • [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) · [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza) — i due lock che legge
> • [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — gli argomenti di un trigger come `text[]`

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 1)

**Il lettore del montaggio.** Dice quali lock «si tocca solo in bozza» sono montati su una
tabella, e che regola dicono i loro argomenti.

Un documento fuori bozza ha poche colonne che si cambiano ancora, e solo in certi stati: la
promessa di consegna delle righe d'ordine in `CONFERMATO` e `PARZIALMENTE_EVASO`,
l'ubicazione d'arrivo dei prelievi della bolla in `EMESSO` e `SPEDITO`. Queste eccezioni
stanno **negli argomenti del trigger**. Il lock le legge da lì quando qualcuno scrive; una
capability deve leggerle da lì per spegnere il pulsante **prima** che il lock rifiuti.

⭐ Se la capability tenesse una sua lista degli stati, al primo stato nuovo le due liste
risponderebbero in modo diverso: il pulsante acceso su un gesto che il database rifiuta, o
spento su uno che accetterebbe. Leggendo il montaggio, lock e capability leggono **lo stesso
dato**.

---

### 🧩 I quattro pezzi, e perché sono quattro

| Pezzo | Che cosa fa | Chi lo usa |
| --- | --- | --- |
| `script.fn_doc_lock_regola` | **la grammatica**: dagli argomenti alla regola (quale argomento è cosa, i default, le liste separate da virgola) | i due lock, il lettore |
| `script.fn_doc_lock_colonna_bloccata` | **la decisione**: con il documento in questo stato, quale di queste colonne non si cambia? | i due lock, la check generica |
| `script.fn_doc_lock_montaggi` | **il lettore**: i lock di una tabella, ciascuno con la sua regola | la check generica |
| `script.fn_doc_colonna_modificabile` | **la domanda di una capability**: questa colonna, in questo stato, si cambia da sola? | le check di dominio (oggi la promessa di consegna) |

Leggere lo stesso dato non basta: anche il **significato** degli argomenti e la **regola**
sarebbero scritti due volte, nel trigger e nel lettore. Per questo grammatica e decisione
stanno in due funzioni che il trigger stesso chiama. Lock e capability non possono capire
gli argomenti in due modi, né decidere in due modi.

---

### 🔍 Che cosa restituisce

Una riga per trigger, in ordine di nome:

* `trigger_nome` — il nome del trigger;
* `regola` — il `jsonb` di `script.fn_doc_lock_regola`.

Solo i trigger che **scattano** (`tgenabled` `O` o `A`): un trigger disabilitato non ferma
niente, e non deve spegnere niente.

---

### 🧪 Test

`db/pgtap/script/test-doc-lock-montaggio-v1.sql`: grammatica, decisione, lettore su ogni
lock montato, la check generica stato per stato, e la promessa di consegna di un ordine
vero, dove capability e lock dicono la stessa cosa.
