## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_cliente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la riga che la funzione fa nascere
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto del cliente, nuovo o esistente
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il billing account nuovo, con la sua istanza
> * [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo) — il ruolo cliente, creato se manca
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il contatto del ruolo
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — gli indirizzi del ruolo
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga dai campi
> * [anagrafiche.fn_update_cliente](/dbzero/anagrafiche/funzioni/fn_update_cliente) — il verbo gemello, per la modifica
>
> Guide:
>
> * [Generazione di un cliente](/guide/generazione-cliente) — il percorso della creazione

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_cliente` fa di un soggetto un cliente in un'istruzione sola: il ruolo cliente (creato se
manca), il billing account, la riga del cliente, il suo contatto e i suoi indirizzi. Restituisce il cliente, il
billing account, l'istanza e il ruolo.

È la sede unica della creazione: la usano l'applicazione, le fixture dei test e il provisioning dei dati di
sviluppo.

---

### La fornitura: un billing account nuovo o uno esistente

* **Un billing account nuovo**: si indica la utility e i campi del conto (la categoria è obbligatoria). Il
  conto nasce con `anagrafiche.fn_crea_billing_account`, su un'istanza indicata o su una fittizia nuova coi
  campi dell'istanza. Si può chiedere anche l'**azienda** del conto: il conto si lega a quella, e il rifiuto
  arriva se l'azienda di chi lavora l'ha già legato a un'altra.
* **Un billing account esistente**: si indica il conto, e il cliente è suo, sull'istanza del conto se non se ne
  indica un'altra. Insieme a un conto esistente non si passano i campi di un conto o di un'istanza nuovi, né
  l'azienda.

Senza l'uno e senza l'altro la chiamata è malformata.

---

### Lo stato in cui nasce

* **Senza stato**, il cliente nasce attivo, con la data di attivazione del giorno operativo. Chi chiama può
  passare un'altra data di attivazione.
* **Con uno stato indicato** (per esempio un pre-contrattuale), le date sono di chi chiama, e le pretende
  `anagrafiche.trgfn_clienti_guard_stato_date`.

---

### I campi del cliente sono un elenco chiuso

Pagamento (termine e modalità), garanzia, servizio da fatturare, stato e date. Un campo assente o nullo prende
il valore predefinito della colonna; una chiave fuori elenco è rifiutata col suo nome (`E_CAMPO_NON_AMMESSO`).
La fornitura non è fra i campi: billing account, istanza e ruolo li decide la funzione.

La riga si rilegge a istruzione finita per il suo billing account, sotto la RLS di chi chiama: il conto appena
nato si vede solo dopo il legame all'azienda, che un trigger scrive alla fine dell'istruzione.

---

### Che cosa lascia agli altri

* **Il permesso** lo decide l'applicazione.
* **Le regole del cliente** le dicono i suoi trigger e vincoli: la utility che richiede il PDP, il PDP della
  stessa utility, un cliente per billing account, la chiave del cliente manuale.
* **Contatto e indirizzi** seguono le regole dei loro verbi; gli indirizzi obbligatori del ruolo si copiano dal
  primo indirizzo se mancano.

---

### ⚠️ Che cosa oggi non copre

* **In quali stati un cliente può nascere** il modello non lo dice: la funzione accetta qualunque stato con le
  sue date, perché il percorso degli stati vale solo per i cambi.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — soggetto mancante, campi che non sono oggetti, conto esistente insieme ai dati
  di uno nuovo o all'azienda, né conto né utility. Dal billing account nuovo, anche l'azienda chiesta diversa da
  quella a cui il conto è già legato.
* `E_CAMPO_NON_AMMESSO` — una chiave fuori elenco fra i campi del cliente (o del billing account, dal suo verbo).
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo a cui il billing account nuovo dovrebbe appartenere non esiste.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — il conto nuovo e quello esistente, con e senza sessione
  operatore, lo stato di nascita, le chiamate malformate, le chiavi fuori elenco, l'azienda chiesta.

---

### Note di migrazione

* 2026-10-18 — nasce, e prende il posto della creazione in più passi fatta dall'applicazione e degli
  inserimenti diretti delle fixture.

---

{% include-markdown "signature-core.md" %}
