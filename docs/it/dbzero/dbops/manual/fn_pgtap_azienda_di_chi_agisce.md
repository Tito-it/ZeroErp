## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_azienda_di_chi_agisce`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità OPERATORE che deve essere attiva
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — la regola di produzione che decide l'azienda
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, che la usa quando il contesto è già aperto
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente dei builder, che la usa col billing account del test
> * [script.fn_pgtap_emittente_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_operatore) — l'helper di `script` che risponde alla stessa domanda, ma con un ripiego
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — dove sta nella famiglia delle fixture

---

### 🎯 Scopo Principale

L'azienda su cui una fixture scrive quando il contesto è già aperto: quella di chi agisce.
Torna l'emittente (id, codice, soggetto ruolo) e l'operatore (utente e identità).

Non scrive niente: è un building block delle altre fixture, non si chiama dal test.

---

### ⭐ L'azienda la decide la regola di produzione

L'azienda è quella che risponde
[script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user):
l'emittente scelto in alto (`app.current_emittente_id`), se l'utente lo può usare, altrimenti
la sua azienda di configurazione. È la stessa domanda che si fa il database quando lega un
billing account all'azienda di chi agisce, quindi ciò che la fixture costruisce finisce
sull'azienda che il trigger del legame sceglierebbe.

Così un super admin che ha scelto un'azienda ha la sua; uno che non l'ha scelta non ne ha.

---

### ⛔ Non ripiega: parla

Dove non c'è una risposta giusta la funzione solleva, e il messaggio comincia con il nome
del chiamante (il parametro `p_chiamante`), così l'errore dice quale fixture l'ha chiesta:

* nessun contesto aperto (la variabile di sessione `app.current_user_id` è vuota);
* un utente di contesto senza un'azienda su cui scrivere: l'operatore senza assegnazione,
  o il super admin che non ne ha scelta una;
* un utente senza identità OPERATORE attiva: il contesto è aperto su qualcuno che
  l'applicazione non farebbe entrare.

⚠️ È la differenza con
[script.fn_pgtap_emittente_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_operatore),
che con il contesto aperto e nessuna azienda risolta ripiega su un emittente di un altro
operatore: la fixture che usa quella risposta scrive dove chi agisce non può leggere.

---

### Codici errore

Nessun codice registrato: i tre casi sopra sono eccezioni senza codice, con il testo che
nomina il chiamante.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-cliente-del-builder-v1.sql` — senza contesto la funzione
  solleva nominando il chiamante; con il contesto del mondo risponde l'azienda del mondo.
* `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-risolutore-v1.sql` — attraverso il mondo:
  il super admin senza azienda scelta è rifiutato, quello con l'azienda scelta lavora su
  quella.

---

### Note di migrazione

* 2026-10-24 — estratta dal ramo «contesto già aperto» di `dbops.fn_pgtap_crea_mondo_cliente`
  (`brief-modello-documento-vendita`, §4-octies), perché servisse anche ai builder che
  ricevono il cliente di un'altra fixture.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
