## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_billing_account`

> **Ultimo aggiornamento**: 23 novembre 2026
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
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento scritto dal trigger, con un operatore in sessione

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_billing_account` apre il billing account di un ruolo per una utility in una sola
chiamata: l'istanza fittizia del soggetto, se non se ne indica una, il billing account e, se chiesto, il suo
collegamento a un'azienda. Restituisce il billing account e l'istanza.

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

* **Con un operatore in sessione** il collegamento lo scrive il trigger della nascita, verso l'azienda di chi
  agisce. Un'azienda chiesta (`p_emittente_soggetto_ruolo_id`) uguale a quella passa; diversa è un errore.
* **Senza sessione** (il provisioning, i builder dei test) il collegamento lo scrive questa funzione, verso
  l'azienda chiesta, come collegamento proprio del billing account. Senza azienda chiesta il billing account
  non ha collegamento, e segue l'azienda predefinita.

---

### Che cosa lascia alle tabelle

Il permesso di creare (`E_BA_ADMIN_GLOBALE_VIETATO`), il ruolo cliente dello stesso soggetto dell'istanza,
l'albero e l'istanza di un'azienda sola, l'unicità della coppia: li dicono i guard e i vincoli di
`billing_account`. Una categoria assente urta il NOT NULL della colonna. La funzione non cambia il modo dei
vincoli differiti: l'istanza nuova vuole il suo billing account al commit, e la finestra è di chi chiama.

Gira coi permessi di chi chiama.

---

### ⚠️ Che cosa oggi non copre

* **Senza sessione, l'azienda chiesta arriva dopo i guard dell'azienda.** I controlli «un'istanza, un'azienda»
  e «albero omogeneo» girano subito dopo l'inserimento, prima del collegamento che la funzione scrive: in quel
  momento il billing account nuovo è dell'azienda predefinita. Un secondo billing account su un'istanza
  esistente, o un figlio sotto un padre, collegati a un'azienda diversa dalla predefinita sono quindi rifiutati
  anche quando l'azienda chiesta è quella giusta. Con un operatore in sessione non succede: il collegamento lo
  scrive il trigger, prima dei controlli.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — ruolo o utility mancanti, campi che non sono oggetti, un'istanza esistente
  insieme ai campi di una nuova, o un'azienda chiesta diversa da quella a cui il trigger ha già collegato il
  billing account.
* `E_CAMPO_NON_AMMESSO` — una chiave fuori elenco, nei campi del billing account o dell'istanza.
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql` — l'istanza fittizia del soggetto del ruolo, il codice
  generato e il default della fatturazione, il collegamento chiesto senza sessione, un secondo billing account
  su un'istanza esistente, le chiamate malformate, le chiavi estranee, il ruolo inesistente; con un operatore in
  sessione il collegamento del trigger e il rifiuto di un'azienda diversa.

---

### Note di migrazione

* 2026-10-18 — nasce, e prende il posto delle scritture a mano di istanza, billing account e collegamento nel
  servizio dei clienti e nei builder dei test.

---

{% include-markdown "signature-core.md" %}
