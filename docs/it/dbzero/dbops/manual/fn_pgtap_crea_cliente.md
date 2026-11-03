## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_cliente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la riga che questa fixture aggiunge alla catena
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — il catalogo da cui si sceglie lo stato
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) — la catena fatturabile su cui il cliente nasce
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — la madre di dominio che scrive la riga
> * [anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) — il guard che pretende le date dello stato
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — le fixture del cliente

---

### 🎯 Scopo Principale

Un cliente completo per un test: la catena fatturabile di
[fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) (soggetto, ruolo
CL, istanza, billing account) più la riga di `anagrafiche.clienti` su quel conto, nello stato
chiesto e con le date che quello stato pretende.

I primi tre parametri sono quelli della catena (etichetta, utility, emittente a cui legare il
conto); il quarto è lo stato, per `codice_interno` (default `AT`, attivo). Torna l'id del
cliente insieme alle chiavi della catena.

---

### ⭐ La riga la scrive la madre di dominio

La riga di `anagrafiche.clienti` non la scrive la fixture: la scrive
[anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente), la stessa porta
dell'applicazione, sul conto appena nato. Ruolo e istanza li prende la madre dal conto. La
fixture sceglie solo ciò che è il caso del test: lo stato e le date.

---

### ⚠️ Le date le decide la fixture, come le pretende il guard

[trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date)
rifiuta uno stato senza le sue date, e la madre lascia le date a chi indica uno stato. La
fixture le mette tutte alla data operativa di oggi:

* la data di **attivazione** per gli stati attivi, sospesi e chiusi;
* la data di **sospensione** per i due sospesi (`SF`, `SC`);
* la data di **chiusura** per i chiusi (`CH`, `CM`, `CW`, `CF`);
* nessuna data per pre-contrattuale, annullato e aggregante (`PR`, `AN`, `AG`).

Gli stati si riconoscono per `codice_interno`, non per l'etichetta `codice`, che più stati
condividono. Uno stato che non è a catalogo è rifiutato prima di costruire.

L'utility di default è la prima, per id, che non richiede un punto di prelievo: la fixture
il PDP non lo costruisce.

---

### ⚠️ Come l'applicazione, serve l'operatore giusto

Il cliente si rilegge a istruzione finita, e sotto la sicurezza per riga si vede solo se è
dell'azienda di chi agisce. Usata come `zeroerp_app`, la fixture vuole quindi in sessione un
operatore dell'emittente a cui il conto è legato; altrimenti la rilettura non trova la riga.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — dalla madre: la riga scritta non si rilegge, perché
  l'operatore in sessione non è dell'azienda del conto.
* Uno stato non a catalogo è un'eccezione senza codice, sollevata dalla fixture prima di
  costruire. Gli altri rifiuti sono quelli della catena di
  [fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba).

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — la fixture non scrive più a mano le
  tabelle della catena e passa dai building block di dominio.
* La usano come fixture, fra gli altri, i test delle anagrafiche (contatti del cliente,
  evento di stato corrente) e quelli della ricerca universale in `db/pgtap/script/`.

---

### Note di migrazione

* 2026-10-14 — le date per stato, come le pretende il guard delle date del cliente.
* 2026-10-18 — la riga la scrive la madre `anagrafiche.fn_crea_cliente` (regola del 2,
  `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 5).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
