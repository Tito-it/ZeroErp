## 📘 Documentazione Concettuale – Tabella `dbops.idempotency_keys`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.request_log](/dbzero/dbops/tabelle/request_log) — il registro delle richieste, legato dalla stessa key
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — l'altra idempotenza, sui lavori vivi della coda
> * [config.parameters](/dbzero/config/tabelle/parameters) — dove sta la soglia di ripresa
>
> Approfondimento funzioni:
>
> * [dbops.fn_idempotency_prenota](/dbzero/dbops/funzioni/fn_idempotency_prenota) — prenota una key e dice al backend che cosa fare
> * [dbops.fn_idempotency_soglia_secondi](/dbzero/dbops/funzioni/fn_idempotency_soglia_secondi) — la soglia oltre cui una key in corso è abbandonata
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — scrive la scadenza alla nascita della riga
>
> Guide:
>
> * [Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono) — il meccanismo intero, dal gesto alla scadenza
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — la retention dei registri

---

### 🎯 Scopo Principale

Ricorda le Idempotency-Key che il client manda con un'operazione che non si deve eseguire due
volte (una fatturazione, una numerazione, la registrazione di una distinta). Se la stessa richiesta
arriva di nuovo — un doppio clic, un invio ripetuto dalla rete — il server non la riesegue: rimanda
la risposta della prima, o dice che è ancora in corso.

---

### Le colonne che contano

* `idempotency_key`: la chiave mandata dal client, chiave primaria.
* `status`: `in_progress` (prenotata, l'operazione sta lavorando), `completed` (fatta), `failed`
  (fallita: si può riprovare con la stessa key).
* `response_payload`: la risposta da rimandare, presente **se e solo se** la key è `completed`.
* `auth_user_id`, `endpoint`: chi ha prenotato la key e su quale richiesta (metodo e percorso). La
  risposta si rimanda solo allo stesso utente sullo stesso endpoint; `auth_user_id` vuoto vuol dire
  una richiesta anonima, che non è un jolly.
* `prenotata_at`: quando la key è stata prenotata o ripresa; da qui si misura se una key in corso è
  stata abbandonata. Non `data_update`, che il trigger di audit riscrive a ogni aggiornamento.
* `tx_id`: la transazione dell'operazione completata.
* `cleanup_at`: quando la riga si può cancellare.

---

### Chi decide e chi scrive

La decisione sta nel database: il backend chiama `dbops.fn_idempotency_prenota`, in autocommit e
fuori dalla transazione dell'operazione, perché la prenotazione deve essere visibile subito alle
altre richieste. La funzione risponde `ESEGUI`, `REPLAY` o `IN_CORSO`, oppure rifiuta una key
prenotata da un altro utente o su un altro endpoint.

L'esito lo scrive il backend: `completed` con la risposta, o `failed`. Se l'operazione è in un
passo solo, `completed` si scrive nella stessa transazione dell'operazione, e una key rimasta in
corso vuol dire che non si è salvato niente. Le regole di ripresa sono nella scheda di
`fn_idempotency_prenota`.

---

### I vincoli

* `chk_idempotency_keys_status`: solo i tre esiti.
* `chk_idempotency_keys_txid_completed`, `chk_idempotency_keys_risposta_solo_completed`: una key
  `completed` ha la sua transazione e la sua risposta; una non `completed` non ha risposta. Per
  questo la funzione di prenotazione decide il `REPLAY` guardando la risposta, senza nominare gli
  esiti.
* `chk_idempotency_keys_endpoint_non_vuoto` e il `NOT NULL`: ogni key è legata alla richiesta che
  l'ha prenotata.

---

### 🧹 Una key vive un giorno

Una key serve finché il client può rimandare la **stessa** richiesta: il frontend la tiene per un
gesto, al massimo dieci minuti. La scadenza la scrive il trigger alla nascita
(`trg_idempotency_keys_m50_cleanup_at_ins`), un giorno dopo la nascita, dalla regola di cleanup
della tabella; la pulizia settimanale cancella le righe scadute. Se una key sparisce mentre qualcuno
la sta riprendendo, per la funzione di prenotazione è di nuovo una key nuova.

---

### Test

* `db/pgtap/dbops/test-idempotency-prenota-v1.sql` — le colonne e i vincoli (una key `completed`
  senza risposta, senza endpoint o con endpoint vuoto è respinta), la regola di scadenza di un
  giorno e il trigger alla nascita, e il comportamento della prenotazione.
* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — la scadenza dei registri di `dbops`.
* `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` — ogni esito del vincolo ha uno scrittore
  dichiarato.

---

### Note di migrazione

* 2026-10-23 — nascono `auth_user_id`, `endpoint`, `prenotata_at` e il vincolo «risposta solo da
  `completed`»; la decisione passa dal backend a `dbops.fn_idempotency_prenota`
  (`brief-be-verifica-documentazione-api`).
* 2026-10-24 — `endpoint` diventa obbligatorio.

---

{% include-markdown "signature-core.md" %}
