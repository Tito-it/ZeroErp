## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_billing_account`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account che crea
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza fittizia che crea, se non se ne indica una
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento all'azienda
>
> Approfondimento funzioni:
>
> * [script.fn_guard_campi_ammessi](/dbzero/script/funzioni/fn_guard_campi_ammessi) — il guard che rifiuta la chiave fuori elenco (`E_CAMPO_NON_AMMESSO`)
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — il verbo del cliente, che la usa
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura delle due righe
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento scritto dal trigger alla nascita, sempre
> * [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) e [anagrafiche.trgfn_billing_account_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_istanza_emittente) — i guard di nascita, che giudicano prima della modifica del collegamento

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_billing_account` apre il billing account di un ruolo per una utility in una sola
chiamata: l'istanza fittizia del soggetto, se non se ne indica una, il billing account e, se chiesta,
l'azienda del suo collegamento. Restituisce il billing account e l'istanza.

Un billing account può esistere senza il cliente: è la catena minima che i documenti pretendono. Per il cliente
completo c'è `fn_crea_cliente`, che la chiama.

---

### I campi

* **Il billing account** (`p_campi`): la categoria del cliente, obbligatoria; facoltativi il codice (se no lo
  genera il trigger), il momento di fatturazione degli ordini, il conto padre, la valuta. Una chiave a `null`
  vale come assente, e la colonna prende il suo default.
* **L'istanza nuova** (`p_istanza`): facoltativi il codice e l'indirizzo. Nasce sempre fittizia: un'istanza
  vera nasce dal motore delle pratiche. Con un'istanza esistente (`p_istanza_utility_id`) questi campi non si
  passano.
* Una chiave che non è fra queste è rifiutata col suo nome (`E_CAMPO_NON_AMMESSO`).

Il billing account si rilegge per la coppia (istanza, utility) a istruzione finita: sotto la RLS la riga si
vede solo dopo il collegamento che il trigger scrive dopo l'inserimento.

---

### L'azienda del billing account

Il billing account nasce sempre collegato: il collegamento lo scrive il trigger della nascita
(`anagrafiche.trgfn_billing_account_link_ef`), verso l'azienda di chi agisce o, senza sessione, verso la
predefinita. La funzione non scrive mai un collegamento suo.

* **Con un operatore in sessione** il billing account è dell'azienda di chi agisce. Un'azienda chiesta
  (`p_emittente_soggetto_ruolo_id`) uguale a quella passa; diversa è una chiamata sbagliata
  (`E_SCRIPT_CHIAMATA_NON_VALIDA`).
* **Senza sessione** (il provisioning, i builder dei test) un'azienda chiesta diversa dalla predefinita si
  ottiene **modificando** il collegamento appena nato: il billing account è nato in questa stessa chiamata e
  non ha documenti, quindi il cambio d'azienda è ammesso. Senza azienda chiesta il billing account resta
  dell'azienda predefinita, col suo collegamento.

---

### Che cosa lascia alle tabelle

Il permesso di creare (`E_BA_ADMIN_GLOBALE_VIETATO`), il ruolo cliente dello stesso soggetto dell'istanza,
l'albero e l'istanza di un'azienda sola, l'unicità della coppia: li dicono i guard e i vincoli di
`billing_account`. Una categoria assente urta il NOT NULL della colonna. La funzione non cambia il modo dei
vincoli differiti: l'istanza nuova vuole il suo billing account al commit, e la finestra è di chi chiama.

Gira coi permessi di chi chiama.

---

### ⚠️ Che cosa oggi non copre

* **Senza sessione, l'azienda chiesta arriva dopo i guard di nascita.** I controlli «un'istanza, un'azienda»
  e «albero omogeneo» del billing account giudicano all'inserimento, sul collegamento appena nato verso la
  predefinita, prima che la funzione lo modifichi. Un secondo billing account su un'istanza esistente, o un
  figlio sotto un padre, di un'azienda diversa dalla predefinita sono quindi rifiutati anche quando l'azienda
  chiesta è quella giusta. È un limite scelto: i guard restano immediati, perché differirli sposterebbe al
  commit anche l'errore ordinario di chi, in sessione, sceglie un padre di un'altra azienda. Con un operatore in
  sessione il caso non nasce: il billing account è dell'azienda di chi agisce fin dall'inserimento.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — ruolo o utility mancanti, campi che non sono oggetti, un'istanza esistente
  insieme ai campi di una nuova, o, con un operatore in sessione, un'azienda chiesta diversa dalla sua.
* `E_EMITTENTE_DEFAULT_MISSING` — dal trigger della nascita: nell'installazione non c'è nessuna azienda.
* `E_CAMPO_NON_AMMESSO` — una chiave fuori elenco, nei campi del billing account o dell'istanza.
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — l'istanza fittizia del soggetto del ruolo, il codice
  generato e il default della fatturazione, il collegamento alla predefinita e quello chiesto senza sessione, un secondo billing account
  su un'istanza esistente, le chiamate malformate, le chiavi estranee, il ruolo inesistente; con un operatore in
  sessione il collegamento del trigger e il rifiuto di un'azienda diversa.

---

### Note di migrazione

* 2026-10-18 — nasce, e prende il posto delle scritture a mano di istanza, billing account e collegamento nel
  servizio dei clienti e nei builder dei test.
* 2026-11-26 — senza sessione, con un'azienda chiesta, modifica il collegamento nato col billing account invece
  di scriverne uno: il billing account nasce sempre collegato.

---

{% include-markdown "signature-core.md" %}
