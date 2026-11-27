## 📘 Documentazione Concettuale – Tabella `anagrafiche.billing_account`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza con cui il billing account nasce, e di cui fattura una utility
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il cliente, che è di un billing account
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo cliente a cui si fattura
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento all'azienda che fattura
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) — la categoria commerciale, chiave del prezzo di listino
> * [config.valute](/dbzero/config/tabelle/valute) — la valuta propria del billing account
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il verbo che crea istanza, billing account e collegamento
> * [anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza) — il ruolo è un cliente, dello stesso soggetto dell'istanza
> * [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) — le regole del conto padre
> * [anagrafiche.fn_check_ba_padre](/dbzero/anagrafiche/funzioni/fn_check_ba_padre) — l'albero a un livello, un padre per cliente e per azienda
> * [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) — padre e figli sulla stessa azienda
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento che nasce col billing account
> * [anagrafiche.trgfn_billing_account_guard_admin_globale](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) — serve un'azienda su cui scrivere
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il rifiuto della cancellazione
> * [anagrafiche.fn_guard_istanza_ha_ba](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ha_ba) — un'istanza non nasce senza billing account
>
> Guide:
>
> * [Generazione di un cliente](/guide/generazione-cliente) — il percorso dal soggetto al cliente
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — istanza, billing account e cliente

---

### 🎯 Scopo Principale

Il **billing account** (BA) è il conto di fatturazione di un ruolo cliente per una utility di un'istanza: dice
a chi si fattura, per quale servizio e, attraverso il suo collegamento, per quale azienda.

Ogni documento di vendita (preventivo, offerta, contratto, ordine, DDT, reso, attività fatturabile, fattura) e
il cliente stesso nominano un billing account: è il punto in cui l'anagrafica incontra la fatturazione.

---

### ⭐ Una coppia (istanza, utility), un billing account, per sempre

Per ogni coppia (istanza, utility) c'è al massimo un billing account (`uq_billing_instance_utility`), e la
coppia non cambia dopo la nascita: istanza, ruolo e utility sono bloccati (`E_BA_ISTANZA_IMMUTABILE`), come
il codice (`E_CODICE_NON_MODIFICABILE`). Un billing account non si sposta: se il rapporto cambia davvero, ne
nasce un altro.

L'istanza e il suo billing account **nascono insieme**: un'istanza senza billing account non arriva al
commit (`anagrafiche.fn_guard_istanza_ha_ba`, `E_ISTANZA_SENZA_BA`). Un'istanza ha un billing account per
ogni utility, tutti della **stessa azienda** (`E_ISTANZA_EMITTENTI_DIVERSI`).

Il ruolo è un ruolo cliente (`CL`) dello stesso soggetto dell'istanza
(`trgfn_billing_account_guard_soggetto_coerenza_istanza`). Il billing account precede il cliente (esiste già
nella fase precontrattuale) e gli sopravvive: ha al massimo un cliente (`uq_clienti_billing_account`, su
`clienti`), e dopo la chiusura del cliente resta il conto delle fatture finali.

---

### ⛔ Il billing account non si cancella: il cliente si annulla

Un billing account non si cancella mai, nemmeno dal proprietario e nemmeno se non ha documenti
(`E_BA_NON_SI_CANCELLA`, con il codice del conto): il rifiuto è il primo trigger che parla sulla
cancellazione, e non ha porte. Il billing account non ha uno stato suo: lo ha il suo cliente
(`anagrafiche.clienti`), e un cliente che non si vuole più si chiude **annullandolo** (stato «AN annulla
servizio») o con una delle chiusure del suo ciclo di vita. Così il collegamento all'azienda, che non si
cancella, non resta mai senza il suo conto, e un'istanza non resta mai senza il suo billing account.

---

### ⭐ Le chiavi composte: i documenti parlano della stessa coppia

Tre chiavi uniche composte servono solo da bersaglio a FK composte, così un documento non nomina un billing
account e, accanto, un'istanza, un ruolo o una utility diversi dai suoi: (id, istanza, utility) per
preventivi, offerte e contratti, e (istanza, utility) per i dati precontrattuali; (id, ruolo, utility) per
clienti, ordini, DDT e resi; (id, istanza) per clienti e pratiche.

Le FK in uscita hanno solo `ON UPDATE CASCADE`, quelle in entrata nessuna azione: un'istanza, un ruolo o una
categoria che hanno billing account non si cancellano, e il billing account stesso non si cancella mai.

---

### L'azienda che fattura

Un billing account non ha una colonna dell'azienda: la dice il suo collegamento in
`anagrafiche.emittenti_fiscali_billing_account`, che **c'è sempre**. Lo scrive alla nascita
`anagrafiche.trgfn_billing_account_link_ef`, con l'azienda di chi crea o, senza sessione, con l'azienda
predefinita; senza nessuna azienda nell'installazione il billing account non nasce
(`E_EMITTENTE_DEFAULT_MISSING`). In sessione serve un'azienda su cui scrivere: un operatore la ha dalla sua
appartenenza, il super admin dall'azienda di lavoro scelta in sessione (`app.current_emittente_id`); senza,
la creazione è rifiutata (`anagrafiche.trgfn_billing_account_guard_admin_globale`,
`E_BA_ADMIN_GLOBALE_VIETATO`). Risoluzione e cambi dell'azienda: il blocco in fondo alla pagina.

---

### Chi vede e chi scrive

RLS accesa, non forzata; l'applicazione ha il DML diretto, la creazione ordinaria passa da
`fn_crea_billing_account`. Quattro policy:

* **`rls_billing_account_ef_whitelist`** (tutte le operazioni) — l'operatore vede e modifica i billing account
  la cui azienda, risolta da `script.fn_get_ba_emittente_sr_id`, sta nel suo perimetro. Il `RETURNING` di una
  creazione passa da qui: nell'istante prima che il collegamento sia scritto, in sessione il billing account
  è già dell'azienda di chi agisce, la stessa che il collegamento riceverà;
* **`rls_billing_account_ef_whitelist_ins`** — l'inserimento chiede solo che a scrivere sia un operatore:
  l'azienda della riga nuova la decide il collegamento scritto alla nascita;
* **`rls_billing_account_self_ownership`** (lettura) — il cliente del portale vede i billing account dei
  propri ruoli, di qualunque canale;
* **`rls_billing_account_shop`** (lettura) — il cliente dello shop vede solo i propri di canale `SHOP`.

---

### Il conto padre

`parent_account_id` aggrega la fatturazione: la testata della fattura va al padre, mentre ogni riga conserva
il billing account figlio da cui viene l'importo (`fatture_righe.dest_billing_account_id`). La risoluzione al
padre è incondizionata: un figlio che non si vuole aggregare non ha padre. Non c'è un indicatore «è un
padre»: lo dice `parent_account_id` dei figli, e un secondo segno potrebbe solo contraddirlo.

Il padre non è il conto stesso, è dello **stesso cliente** (la stessa identità fiscale, letta sul soggetto
delle due istanze, o senza codice fiscale lo stesso soggetto) e chiede `valido_dal`: lo tiene
`anagrafiche.trgfn_billing_account_guard_normalize`. Che padre e figli siano della stessa azienda lo tiene
`anagrafiche.trgfn_billing_account_guard_albero_emittente` (`E_ALBERO_EMITTENTE_MISTO`).

⭐ **L'albero ha un livello solo.** Chi ha un padre non fa da padre (`E_PARENT_CON_PADRE`), e chi fa da padre
non prende un padre (`E_PARENT_HA_FIGLI`): insieme rendono impossibile anche un ciclo. Così «la fattura va al
padre diretto» non ha ambiguità: padre diretto e padre della testata sono lo stesso conto. Un cliente ha
**un solo padre per azienda** (`E_PARENT_SECONDO_PADRE`): due padri dello stesso cliente sulla stessa azienda
spezzerebbero la sua fatturazione aggregata in due. Lo giudica `anagrafiche.fn_check_ba_padre`, quando il
padre nasce o cambia.

Il padre **non si toglie né si cambia** finché il figlio ha attività fatturabili non ancora fatturate
(`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`): cambiare padre sposta la testata delle sue fatture come toglierlo.

---

### Le altre colonne

* **`categoria_cliente_id`** — obbligatoria, e la categoria deve essere attiva quando la si assegna (vincolo
  differito al commit). Quando il prezzo non lo decide un contratto, il resolver dei prezzi lo cerca nella
  matrice categoria × listino della categoria del billing account.
* **`fatturazione_ordini`** — il momento in cui un ordine del cliente diventa fatturabile (`CONFERMATO`,
  `SPEDITO`, `CONSEGNATO`): l'ordine lo eredita quando non ne indica uno suo.
* **`valuta_id`** — la valuta propria del billing account; senza, vale quella dell'azienda e poi del gestore.
  È una valuta che esiste in `config.valute` (`fk_billing_account_valute`).
* **`canale_origine`** — da dove è nato il billing account (`ADMIN`, `PORTALE`, `SHOP`), e non cambia
  (`E_CANALE_ORIGINE_IMMUTABILE`). Uno stesso ruolo può avere billing account di canali diversi, distinti
  nelle pipeline di fatturazione; il canale decide che cosa vede il cliente dello shop.
* **`codice`** — generato quando manca (`BAC/` e sette cifre), salvato in maiuscolo, unico, bloccato.
* **`valido_dal`**, **`valido_al`** — la validità del billing account, obbligatoria con un padre; la fine non
  precede l'inizio. `validita` ne è l'intervallo chiuso, calcolato.

---

### ⚠️ Che cosa oggi non copre

* **Il COMMENT della tabella** («storico dei codici cliente definitivi per utility») non descrive la tabella.
* **Tre trigger senza fascia nel nome** (`trg_billing_account_guard_normalize_ins_upd`, l'audit, la transazione).

---

### Codici errore

* `E_BA_ISTANZA_IMMUTABILE`, `E_CODICE_NON_MODIFICABILE`, `E_CANALE_ORIGINE_IMMUTABILE` — si cambia una colonna
  bloccata (la coppia o il ruolo, il codice, il canale).
* `E_BA_NON_SI_CANCELLA` — si cancella un billing account: il cliente si annulla.
* `E_ISTANZA_SENZA_BA` — al commit, un'istanza è nata senza billing account.
* `E_PARENT_CON_PADRE`, `E_PARENT_HA_FIGLI`, `E_PARENT_SECONDO_PADRE`, `E_DISSOCIAZIONE_PARENT_CON_ATTIVITA` —
  il conto padre (dal guard del padre).

Gli altri li sollevano i trigger, nelle loro pagine.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — istanza e billing account insieme, le FK composte,
  un'istanza un'azienda, il blocco della coppia.
* `db/pgtap/rls/test-rls-billing-account-returning-secondo-emittente.sql` — il `RETURNING` di un operatore di
  un'azienda non predefinita, e la postura della RLS.
* `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` — le FK composte dei documenti e il ruolo cliente.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — il billing account non si cancella, il
  collegamento non si toglie e non si sposta, nessun billing account è senza collegamento.
* `db/pgtap/anagrafiche/test-billing-account-albero-un-livello-v1.sql` — l'albero a un livello, il ciclo, il
  secondo padre dello stesso cliente, il cambio di padre con attività non fatturate.
* `db/pgtap/anagrafiche/test-valuta-fk-billing-account-emittente-v1.sql` — la valuta che non esiste è rifiutata.

Il conto padre e la creazione hanno i test dei loro trigger.

---

### Note di migrazione

* 2026-04-14 — nasce `categoria_cliente_id`, obbligatoria: i billing account già presenti presero la
  categoria `STANDARD`.
* 2026-04-20 — nasce `canale_origine`, per il portale e lo shop: i billing account già presenti sono `ADMIN`.
* 2026-08-04 — il super admin con un'azienda di lavoro in sessione crea billing account; prima la creazione
  era vietata a chiunque non avesse un'appartenenza.
* 2026-10-08 — istanza e billing account nascono insieme, e la coppia (istanza, utility) del billing account
  si blocca.
* 2026-11-26 — il billing account non si cancella più (prima l'ultimo di un'istanza non si cancellava, gli
  altri sì) e ha sempre il suo collegamento; l'albero passa a un livello solo e il cambio di padre è giudicato
  come lo stacco; `valuta_id` prende la FK verso `config.valute`.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
