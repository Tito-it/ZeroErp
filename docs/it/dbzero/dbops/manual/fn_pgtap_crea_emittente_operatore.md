## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_emittente_operatore`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — l'identità attiva dell'operatore, che la fixture verifica
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_emittente](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente) — l'azienda nuova
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — il percorso di produzione che lega un utente a un'azienda
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto da aprire sull'operatore tornato
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, che la usa quando nessun contesto è aperto
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — l'operatore umano, quando è lui il soggetto del test
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — l'ordine fra il mondo e il contesto

---

### 🎯 Scopo Principale

Un'azienda su cui lavorare e l'operatore che la ha nel perimetro, in una chiamata. Torna
l'emittente (id, sigla, soggetto ruolo) e l'operatore (utente e identità).

Senza un operatore il contesto di sessione resta vuoto, e il dominio rifiuta ogni scrittura
perché non trova un emittente attivo per chi agisce. Il contesto la fixture non lo apre: il
chiamante lo punta sull'utente tornato, con
[script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore).

---

### ⚠️ L'operatore è un utente tecnico

L'operatore nasce da [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico),
che è l'unico percorso di produzione che lega un utente a un emittente. Il processo di cui è
l'utente tecnico è il secondo parametro (default `chiusura_scadenze_daily`). Per ciò che i
test attraversano è un operatore a tutti gli effetti: identità OPERATORE attiva, non super
admin, un emittente nel perimetro.

⛔ Non si usa dove il soggetto del test è l'**operatore umano** (la natura tecnica, i profili
di accesso, il super admin): lì si costruisce con
[fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano).

---

### ⛔ L'utente tecnico nasce dentro la finestra differita

La creazione dell'utente tecnico è una saga: scrive il soggetto del processo e solo dopo il
suo contatto, e il guard dei contatti del soggetto è differito apposta. Il preambolo dei
pgTAP rende i vincoli immediati, e il guard scatterebbe sul soggetto ancora senza contatto.
La fixture apre la finestra differita intorno alla saga e la **richiude** subito dopo: i
controlli scattano lì, su un mondo completo, e non si perdono nel `ROLLBACK` del test. In
produzione il problema non c'è, perché nessuno rende i vincoli immediati.

---

### ⚠️ Il risultato si verifica

Se l'utente creato non ha un'identità attiva la fixture solleva, invece di tornare una riga
con un vuoto dentro: senza identità l'operatore non è selezionabile dal contesto, e il
chiamante cercherebbe il difetto tre passi più in là.

---

### Codici errore

* I rifiuti dell'utente tecnico, per esempio un processo che non esiste o che non ammette un
  utente tecnico (`E_PROCESSO_NON_TROVATO`, `E_PROCESSO_NON_ELEGGIBILE_UTENTE_TECNICO`), e
  quelli dell'emittente di [fn_pgtap_crea_emittente](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente).
* Un utente senza identità attiva è un'eccezione senza codice, sollevata dalla fixture.

---

### Test

Nessun pgTAP dedicato. La provano i file che la usano come fixture:

* `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql` — attraverso il mondo: l'azienda
  costruita, l'operatore che la ha nel perimetro, l'identità OPERATORE attiva;
* `db/pgtap/dbops/test-fn-pgtap-crea-contratto-v1.sql` e
  `db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` — la seconda azienda, costruita prima
  del contesto.

---

### Note di migrazione

* 2026-09-09 — nasce, per i test di vendite che sul database ricostruito morivano nella
  fixture senza un operatore.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
