## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_argomenti`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_codici_errore_argomenti_trigger](/dbzero/dbops/views/vw_codici_errore_argomenti_trigger) — i codici errore che un trigger passa alla sua funzione
>
> Approfondimento funzioni:
>
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — legge i lucchetti di colonna montati
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — riconosce i trigger ATTIVO di una FK eccezione
> * [dbops.fn_trigger_attivo_orfani](/dbzero/dbops/funzioni/fn_trigger_attivo_orfani) — riconosce i trigger ATTIVO orfani
> * [script.fn_doc_lock_regola](/dbzero/script/funzioni/fn_doc_lock_regola) — legge i lucchetti dei documenti
> * [script.fn_doc_lock_montaggi](/dbzero/script/funzioni/fn_doc_lock_montaggi) — elenca i montaggi dei lucchetti dei documenti
>
> Guide:
>
> * [Linee guida trigger](/linee-guida-trigger#il-nome-della-funzione-trigger) — chi legge gli argomenti da fuori passa da una funzione condivisa

---

### 🎯 Scopo Principale

Restituisce gli argomenti di un trigger (`pg_trigger.tgargs`) come elenco di testi, nell'ordine in
cui li scrive il `CREATE TRIGGER`; un elenco vuoto se il trigger non ne ha.

È il building block di chi riconosce un trigger **generico** — una funzione, tanti trigger — da
quello che gli viene passato e non dal nome: il nome può essere troncato con un hash oltre i 63
caratteri o scritto a mano, gli argomenti no. Chi deve leggere `tgargs` passa da qui.

⚠️ L'elenco parte da 1, mentre dentro la funzione trigger `TG_ARGV` parte da 0: il primo argomento
è `[1]` qui e `[0]` lì.

---

### ⛔ Perché non la decodifica testuale di `tgargs`

La forma usata prima — convertire `tgargs` in testo con l'escape e togliere in coda i separatori —
aveva due difetti:

* togliere in coda i caratteri «barra rovesciata» e «zero» toglie un **insieme** di caratteri, non
  una sequenza: un ultimo argomento che finisce con uno zero lo perdeva (un codice `E_X10`
  diventava `E_X1`);
* ogni carattere non ASCII usciva come sequenza di escape (`città` diventava illeggibile).

Questa funzione taglia i **byte** su ogni separatore nullo (ogni argomento in `tgargs` ne è chiuso)
e riconverte i pezzi con la codifica del server.

---

### Chi la usa

Oltre alle funzioni del «Vedi anche», la usano il guardrail
`scripts/sql/guardrail_codice_errore_strutturato.sql` e vari pgTAP che riconoscono un trigger
generico dai suoi argomenti.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` e `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql`
  — riconoscono i lucchetti di colonna dagli argomenti letti qui.
* `db/pgtap/script/test-doc-lock-montaggio-v1.sql` — i montaggi dei lucchetti dei documenti.

---

### Note di migrazione

* 2026-09-26 — nasce come sede unica della lettura di `tgargs`
  (`brief-db-lock-di-colonna-fuori-registro` §7); i lettori che decodificavano `tgargs` da sé
  passano da qui.

---

{% include-markdown "signature-core.md" %}
