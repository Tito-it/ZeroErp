## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — i collegamenti fra documento e pratica, che il guard presidia
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso d'origine del collegamento
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_guard_coerenza_flusso](/dbzero/pratiche/funzioni/trgfn_sospensioni_guard_coerenza_flusso) — la stessa regola sulle sospensioni
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso` garantisce che il flusso
d'origine di un collegamento fra documento e pratica appartenga alla stessa pratica del collegamento.

In `pratiche.pratiche_sorgenti`, `flusso_id` àncora il collegamento `ROOT` al flusso da cui il
documento è nato (per esempio un preventivo aperto da un'attività di flusso), non a tutta la pratica.
La chiave esterna garantisce solo che il flusso esista, non che sia di quella pratica, e un `CHECK` non
può guardare un'altra tabella: serve un guard.

---

### Le regole

1. Il guard lavora solo quando `flusso_id` è valorizzato: i collegamenti `COLLEGATO` a valle (commessa,
   ordine) nascono senza flusso e non sono toccati.
2. Se il flusso indicato non esiste, il guard lascia passare: lo rifiuta la chiave esterna, con l'errore
   giusto, invece di mascherarlo.
3. Se il flusso appartiene a un'altra pratica, il guard rifiuta il collegamento.

Scatta all'inserimento e quando cambiano `flusso_id` o `pratica_id`.

---

### ⭐ In coppia con l'unicità del ROOT per flusso

L'indice unico parziale `uq_pratiche_sorgenti_flusso_root` ammette al più un collegamento `ROOT` per
flusso: l'indice garantisce l'unicità, questo guard la coerenza del flusso con la pratica. I collegamenti
`COLLEGATO` lasciano `flusso_id` vuoto, e non sono vincolati né dall'uno né dall'altro.

---

### Codici errore

* `E_PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE` — il collegamento indica un flusso di un'altra
  pratica. L'errore porta il `tx_id` della riga.

---

### Test

* `pratiche/test-pratiche-sorgenti-flusso` — il flusso di un'altra pratica rifiutato, il flusso
  inesistente lasciato alla chiave esterna, l'unicità del `ROOT` per flusso.

---

### Note di migrazione

* 2026-06-16 — nasce con l'aggancio del documento al flusso d'origine (brief-db-aggancio-documento-flusso).

---

{% include-markdown "signature-core.md" %}
