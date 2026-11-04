## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_cliente_ba`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto di fatturazione, in fondo alla catena
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, che porta lo stesso codice del conto
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il legame del conto all'azienda
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il building block di dominio che scrive istanza, conto e legame
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il soggetto del cliente
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il ruolo CL
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, che la compone dopo aver aperto il contesto
> * [dbops.fn_pgtap_crea_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente) — la stessa catena più la riga del cliente
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — l'ordine fra il cliente e il contesto

---

### 🎯 Scopo Principale

Un cliente fatturabile per un test: la catena minima che i documenti pretendono, cioè
soggetto, ruolo CL, istanza utility e billing account. Torna le chiavi del conto,
dell'istanza, del ruolo, del soggetto e l'utility.

Non scrive la riga di `anagrafiche.clienti`: per quella c'è
[fn_pgtap_crea_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente).

---

### ⭐ Istanza, conto e legame li scrive il dominio

Soggetto e ruolo li costruiscono le fixture di base; istanza, billing account e legame
all'azienda li scrive
[anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account),
lo stesso building block dell'applicazione. Alla fixture restano le scelte del test:

* un **codice libero** `PGTAPBA` più cinque cifre, uguale per istanza e conto, perché il
  codice è unico e una sigla fissa farebbe collidere la seconda chiamata con la prima. Il
  massimo si legge dalle **istanze**, che non sono sotto la sicurezza per riga: i conti lo
  sono, e un operatore vedrebbe solo quelli della sua azienda;
* la prima categoria cliente e la prima **valuta**, per id. La valuta di un documento si
  risolve lungo la catena «conto → azienda → gestore», e su un database ricostruito nessuno
  dei tre la porta: valorizzando l'anello più vicino al documento la fixture non dipende da
  com'è configurata la macchina;
* l'utility: quella chiesta, o la prima a catalogo.

---

### ⛔ Il terzo parametro: legare il conto a un'azienda, solo senza contesto

Il terzo parametro è il soggetto ruolo dell'**emittente** a cui legare il conto. Serve alle
testate col billing account obbligatorio (contratti, offerte commerciali), il cui guard
confronta l'emittente del documento con quello del conto: senza legame il conto ricade
sull'emittente di default.

Con un operatore in sessione il legame lo scrive già il trigger del conto, verso l'azienda
di chi agisce. Allora il parametro si omette: chiedere la stessa azienda non cambia niente,
chiederne un'altra è rifiutato dal building block. L'ordine giusto è uno dei due:

* il cliente si costruisce **prima** di aprire il contesto, col terzo parametro;
* oppure si apre il contesto e si chiama la fixture **senza** terzo parametro.

Usata come `zeroerp_app`, la fixture vuole comunque un operatore in sessione: il conto si
rilegge a istruzione finita, e sotto la sicurezza per riga si vede solo attraverso il legame.

---

### ⚠️ La finestra dei vincoli differiti

L'istanza deve avere un satellite (un conto, un dato precontrattuale o un cliente), e il
controllo scatta a fine transazione. Il preambolo dei pgTAP rende i vincoli immediati, e il
controllo scatterebbe sull'istanza prima che il conto esista. La fixture apre la finestra
differita prima della catena e la **richiude** a catena finita: i controlli scattano lì, su
un mondo completo, e non si perdono nel `ROLLBACK` del test. Esce con i vincoli immediati,
come ogni fixture.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — dal building block del conto: un terzo parametro diverso
  dall'azienda a cui il trigger ha già legato il conto, oppure il conto scritto che non si
  rilegge perché nessun operatore dell'azienda è in sessione.
* Un catalogo delle utility vuoto è un'eccezione senza codice, sollevata dalla fixture.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — il building block del conto, senza e
  con un operatore in sessione (il legame chiesto, quello scritto dal trigger, l'emittente
  discorde rifiutato), e la fixture che non scrive più a mano le tabelle della catena.
* `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql` — attraverso il mondo: il conto
  costruito dopo il contesto è legato all'azienda del mondo.

---

### Note di migrazione

* 2026-09-09 — nasce; lo stesso giorno il terzo parametro, il legame all'emittente.
* 2026-09-12 — col contesto aperto il legame lo lascia al trigger, verso chi agisce.
* 2026-09-23 — il codice libero si legge dalle istanze, fuori dalla sicurezza per riga.
* 2026-10-18 — istanza, conto e legame li scrive `anagrafiche.fn_crea_billing_account`
  (regola del 2, `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 5).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
