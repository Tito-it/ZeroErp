## 📘 Documentazione Concettuale – Tabella `anagrafiche.billing_account`

> **Ultimo aggiornamento**: 22 novembre 2026
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
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — il verbo che crea istanza, billing account e collegamento
> * [anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza) — il ruolo è un cliente, dello stesso soggetto dell'istanza
> * [anagrafiche.trgfn_billing_account_guard_normalize](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize) — le regole del conto padre
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento all'azienda di chi crea
> * [anagrafiche.fn_guard_istanza_ha_ba](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ha_ba) — un'istanza non resta senza billing account
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
commit, e l'ultimo billing account di un'istanza che resta non si cancella; istanza e billing account se ne
possono andare insieme (`fn_guard_istanza_ha_ba`, `E_ISTANZA_SENZA_BA`). Un'istanza ha un billing account per
ogni utility, tutti della **stessa azienda** (`E_ISTANZA_EMITTENTI_DIVERSI`).

Il ruolo è un ruolo cliente (`CL`) dello stesso soggetto dell'istanza
(`trgfn_billing_account_guard_soggetto_coerenza_istanza`). Il billing account precede il cliente (esiste già
nella fase precontrattuale) e gli sopravvive: ha al massimo un cliente (`uq_clienti_billing_account`, su
`clienti`), e dopo la chiusura del cliente resta il conto delle fatture finali.

---

### ⭐ Le chiavi composte: i documenti parlano della stessa coppia

Tre chiavi uniche composte servono solo da bersaglio a FK composte, così un documento non nomina un billing
account e, accanto, un'istanza, un ruolo o una utility diversi dai suoi: (id, istanza, utility) per
preventivi, offerte e contratti, e (istanza, utility) per i dati precontrattuali; (id, ruolo, utility) per
clienti, ordini, DDT e resi; (id, istanza) per clienti e pratiche.

Le FK in uscita hanno solo `ON UPDATE CASCADE`, quelle in entrata nessuna azione: un billing account usato da
un documento non si cancella, né un'istanza, un ruolo, una categoria o un conto padre che ne hanno.

---

### L'azienda che fattura

Un billing account non ha una colonna dell'azienda: la dice il suo collegamento in
`emittenti_fiscali_billing_account`, che il trigger `trgfn_billing_account_link_ef` scrive alla nascita con
l'azienda di chi crea. Per creare serve quindi un'azienda su cui scrivere: un operatore la ha dalla sua
appartenenza, il super admin dall'azienda di lavoro scelta in sessione (`app.current_emittente_id`); senza,
la creazione è rifiutata (`trgfn_billing_account_guard_admin_globale`, `E_BA_ADMIN_GLOBALE_VIETATO`).
Risoluzione e cambi dell'azienda: il blocco in fondo alla pagina.

---

### Chi vede e chi scrive

RLS accesa, non forzata; l'applicazione ha il DML diretto, la creazione ordinaria passa da
`fn_crea_billing_account`. Quattro policy:

* **`rls_billing_account_ef_whitelist`** (tutte le operazioni) — l'operatore vede e modifica i billing account
  la cui azienda, risolta da `script.fn_get_ba_emittente_sr_id`, sta nel suo perimetro. Il `RETURNING` di una
  creazione passa da qui: in sessione un billing account non ancora collegato è già dell'azienda di chi agisce;
* **`rls_billing_account_ef_whitelist_ins`** — l'inserimento chiede solo che a scrivere sia un operatore:
  l'azienda della riga nuova la decide il collegamento scritto alla nascita;
* **`rls_billing_account_self_ownership`** (lettura) — il cliente del portale vede i billing account dei
  propri ruoli, di qualunque canale;
* **`rls_billing_account_shop`** (lettura) — il cliente dello shop vede solo i propri di canale `SHOP`.

---

### Il conto padre

`parent_account_id` aggrega la fatturazione: la testata della fattura va al padre, mentre ogni riga conserva
il billing account figlio da cui viene l'importo (`fatture_righe.dest_billing_account_id`). La risoluzione al
padre è incondizionata: un figlio che non si vuole aggregare non ha padre.

Il padre non è il conto stesso, è della **stessa identità fiscale** (letta sul soggetto delle due istanze),
chiede `valido_dal`, e non si toglie a un figlio con attività fatturabili non ancora fatturate: lo tiene
`trgfn_billing_account_guard_normalize`. Che padre e figli siano della stessa azienda lo tiene
`trgfn_billing_account_guard_albero_emittente` (`E_ALBERO_EMITTENTE_MISTO`).

---

### Le altre colonne

* **`categoria_cliente_id`** — obbligatoria, e la categoria deve essere attiva quando la si assegna (vincolo
  differito al commit). Quando il prezzo non lo decide un contratto, il resolver dei prezzi lo cerca nella
  matrice categoria × listino della categoria del billing account.
* **`fatturazione_ordini`** — il momento in cui un ordine del cliente diventa fatturabile (`CONFERMATO`,
  `SPEDITO`, `CONSEGNATO`): l'ordine lo eredita quando non ne indica uno suo.
* **`valuta_id`** — la valuta propria del billing account; senza, vale quella dell'azienda e poi del gestore.
* **`canale_origine`** — da dove è nato il billing account (`ADMIN`, `PORTALE`, `SHOP`), e non cambia
  (`E_CANALE_ORIGINE_IMMUTABILE`). Uno stesso ruolo può avere billing account di canali diversi, distinti
  nelle pipeline di fatturazione; il canale decide che cosa vede il cliente dello shop.
* **`codice`** — generato quando manca (`BAC/` e sette cifre), salvato in maiuscolo, unico, bloccato.
* **`valido_dal`**, **`valido_al`** — la validità del billing account, obbligatoria con un padre; la fine non
  precede l'inizio. `validita` ne è l'intervallo chiuso, calcolato.

---

### ⚠️ Che cosa oggi non copre

* **La gerarchia non ha un limite di livelli.** Niente impedisce un padre che ha a sua volta un padre, né un
  ciclo di due billing account che si fanno da padre l'un l'altro: il guard rifiuta solo il padre uguale a sé.
  La fattura va al padre diretto.
* **Cambiare il padre non è giudicato come toglierlo.** Il blocco per attività non fatturate scatta solo quando
  il padre diventa vuoto; da un padre a un altro il legame si sposta anche con attività aperte.
* **`valuta_id` non ha una FK** verso `config.valute`: un id di valuta che non esiste entra, e la lettura
  della valuta lo prende per buono.
* **Il COMMENT della tabella** («storico dei codici cliente definitivi per utility») non descrive la tabella.
* **Tre trigger senza fascia nel nome** (`trg_billing_account_guard_normalize_ins_upd`, l'audit, la transazione).

---

### Codici errore

* `E_BA_ISTANZA_IMMUTABILE`, `E_CODICE_NON_MODIFICABILE`, `E_CANALE_ORIGINE_IMMUTABILE` — si cambia una colonna
  bloccata (la coppia o il ruolo, il codice, il canale).
* `E_ISTANZA_SENZA_BA` — al commit, un'istanza resta senza billing account.

Gli altri li sollevano i trigger, nelle loro pagine.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — istanza e billing account insieme, le FK composte,
  un'istanza un'azienda, il blocco della coppia.
* `db/pgtap/rls/test-rls-billing-account-returning-secondo-emittente.sql` — il `RETURNING` di un operatore di
  un'azienda non predefinita, e la postura della RLS.
* `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql` — le FK composte dei documenti e il ruolo cliente.

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

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

{% include-markdown "signature-core.md" %}
