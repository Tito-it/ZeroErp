## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_attivo_argomenti`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block, sul padre
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il require dell'attivo, sul figlio
> * [dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent) — il require dell'obsoleto, sul figlio
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — gli argomenti di un trigger montato, come elenco
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — un lettore dei montaggi
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — un altro
>
> Guide:
>
> * [Linee guida trigger](/linee-guida-trigger#il-nome-della-funzione-trigger) — chi legge gli argomenti da fuori passa da una funzione condivisa

---

### 🎯 Scopo Principale

La **grammatica** degli argomenti dei tre trigger della famiglia ATTIVO: dato il nome della
funzione trigger e l'elenco degli argomenti, dice quale argomento è cosa, per nome. È la sede unica
di quella grammatica: la usano le funzioni trigger quando scattano, le due letture che guardano il
padre e le figlie, e chi rilegge i montaggi da `pg_trigger`.

---

### La grammatica

| Funzione trigger | Argomenti, in ordine |
| --- | --- |
| `trgfn_prevent_deactivate_if_children` (block, sul padre) | schema e tabella della figlia, colonna FK della figlia, colonna referenziata del padre, colonna attivo del padre |
| `trgfn_child_requires_active_parent` (require, sul figlio) | schema e tabella del padre, colonna attivo del padre, colonna FK del figlio, colonna referenziata del padre |
| `trgfn_child_requires_non_obsolete_parent` (require, sul figlio) | come la riga sopra, con `obsoleto_dal` al posto della colonna attivo; e, facoltativa, una colonna di esenzione del figlio |

La risposta è una riga, con gli stessi nomi per tutti e tre: `figlia_schema`, `figlia_tabella`
(solo il block), `padre_schema`, `padre_tabella` (solo i require), `fk_col`, `ref_col`,
`stato_col` (la colonna attivo o `obsoleto_dal` del padre), `esenzione_col`.

---

### ⛔ Tutti gli argomenti sono obbligatori

Non ci sono valori di riserva: un argomento mancante, vuoto o in più rende il montaggio non
valido. Un ripiego che indovina una colonna dà una colonna sbagliata che non si vede, e scriveva
nel registro errori a ogni scatto. Il generatore monta sempre tutti gli argomenti, e così i
trigger scritti a mano.

---

### Non solleva

Se il montaggio non rispetta la grammatica la riga dice `valido` falso, con il motivo in
`dettaglio`, e i campi vuoti. Chi chiama sceglie che cosa farne: il trigger solleva il codice del
suo montaggio, il presidio degli orfani lo riporta come `ARGOMENTI_INVALIDI`.

---

### ⚠️ Le due basi dell'elenco

Dentro un trigger gli argomenti partono dalla posizione zero; l'elenco di
`dbops.fn_trigger_argomenti` parte da uno. La funzione rinumera prima di leggere, quindi le due
forme danno la stessa risposta e nessuno dei chiamanti conta posizioni.

---

### Test

* `db/pgtap/dbops/test-guard-attivo-grammatica-e-codici-v1.sql` — la grammatica dei tre, le due
  basi, i montaggi rifiutati col loro motivo, il presidio che ogni trigger montato la rispetta e
  quello che nessuno dei cinque chiamanti legge gli argomenti per posizione.

---

{% include-markdown "signature-core.md" %}
