## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_billing_account`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il cliente di cui la riga dice l'azienda
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende a cui punta la riga
>
> Approfondimento funzioni:
>
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'azienda di un billing account: il suo collegamento
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — scrive il collegamento alla nascita del billing account
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il collegamento non si cancella e non si sposta
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il cancello della storia
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il cancello dell'albero
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — il cancello dell'istanza
> * [anagrafiche.trgfn_efba_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_clienti_chiave) — il cancello della chiave del cliente manuale
> * [anagrafiche.trgfn_emittenti_fiscali_default_guard](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_guard) — una e una sola predefinita
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.emittenti_fiscali_billing_account` dice per quale azienda (emittente fiscale) fattura ciascun
billing account: una riga per ogni billing account, sempre. Tiene anche la riga dell'azienda predefinita, che
decide l'azienda dei billing account che nasceranno senza un'azienda di chi agisce.

---

### Una riga per billing account, e una predefinita

Una riga ha un billing account e non è predefinita, oppure è la predefinita e non ha billing account: il
vincolo `chk_emittenti_fiscali_ba_default` non ammette altre combinazioni. `uq_emittenti_fiscali_ba` dà a un
billing account al massimo un collegamento, `uq_emittenti_fiscali_ba_default` al massimo una predefinita, e il
guard differito `trgfn_emittenti_fiscali_default_guard` pretende che a fine transazione ce ne sia esattamente
una (`E_EMITTENTE_DEFAULT_SINGLETON`). La crea il bootstrap sulla prima azienda dell'installazione.

L'azienda si nomina col suo `soggetto_ruolo_id` (`emittente_soggetto_ruolo_id`, verso
`anagrafiche.emittenti_fiscali`), e deve essere attiva quando la riga nasce o cambia azienda: lo verifica a fine
transazione il trigger generico del genitore attivo.

---

### ⭐ Il collegamento nasce da solo, e c'è sempre

Quando nasce un billing account, `anagrafiche.trgfn_billing_account_link_ef` scrive il suo collegamento con
l'azienda di chi lo sta creando; senza un utente in sessione (seed, import, manutenzione), o se chi agisce
non ha un'azienda, con l'azienda predefinita. Senza nessuna azienda il billing account non nasce
(`E_EMITTENTE_DEFAULT_MISSING`). Chi non ha un'azienda su cui scrivere, come un super admin che lavora su
tutte, non crea billing account finché esistono aziende attive (`E_BA_ADMIN_GLOBALE_VIETATO`, dal guard su
`anagrafiche.billing_account`); con un'azienda di lavoro scelta in sessione li crea, e il collegamento va a
quella.

Fra la nascita del billing account e la scrittura del collegamento c'è un istante in cui la riga non esiste
ancora: lì il risolutore risponde già ciò che il trigger sta per scrivere. Fuori da quell'istante l'azienda di
un billing account è il suo collegamento, e nient'altro.

---

### ⛔ Il collegamento non si cancella e non si sposta

Una riga del collegamento appartiene al suo billing account per sempre:

* **non si cancella** (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`), e vale anche per la riga della predefinita;
* **non passa a un altro billing account**, e non diventa la riga predefinita né smette di esserlo
  (`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`): ognuno di questi passi lascerebbe un billing account senza azienda.

I due rifiuti sono i primi trigger della tabella e non hanno porte, nemmeno per il proprietario. Il billing
account, a sua volta, non si cancella: il collegamento non resta mai senza il suo conto.

Si cambia soltanto l'**azienda** (`emittente_soggetto_ruolo_id`), modificando la riga:

* sul collegamento di un billing account, il cliente passa all'altra azienda, e solo se non ha nessun
  documento, di qualunque famiglia e in qualunque stato, anche in bozza;
* sulla riga della predefinita, cambia l'azienda dei billing account che nasceranno, e di nessun altro.

---

### I cancelli guardano solo il collegamento di un billing account

I quattro trigger di controllo (storia, albero, istanza, chiave del cliente manuale) giudicano il
collegamento di un billing account che **nasce** o **cambia azienda**. La riga della predefinita non si
giudica: spostarla non cambia l'azienda di nessun cliente, e non c'è niente da cercare. La nascita non ha
storia da proteggere; la cancellazione non arriva ai cancelli, perché la rifiuta prima il trigger di
immutabilità.

---

### La tabella non ha RLS, i suoi controlli sì

La tabella non ha regole di visibilità; `billing_account`, fatture e commesse le hanno. Per questo i
controlli che rileggono i billing account o i documenti girano coi privilegi del proprietario: con quelli di
chi scrive, un cliente o un documento di un'altra azienda sarebbe invisibile, e il controllo direbbe «a posto»
proprio nel caso da fermare.

---

### ⚠️ Che cosa oggi non copre

* Il COMMENT di `emittente_soggetto_ruolo_id` indica la chiave verso `anagrafiche.soggetti_ruoli`: la FK
  `fk_emittenti_fiscali_billing_account_emittente` punta a `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`.

---

### Codici errore

* `E_EMITTENTE_DEFAULT_SINGLETON` — a fine transazione le predefinite non sono esattamente una.
* `E_BA_COLLEGAMENTO_NON_SI_TOGLIE` — si cancella una riga, di un billing account o della predefinita.
* `E_BA_COLLEGAMENTO_NON_SI_SPOSTA` — una riga cambia `billing_account_id`.
* `E_BA_EMITTENTE_CON_STORIA`, `E_ALBERO_EMITTENTE_MISTO`, `E_ISTANZA_EMITTENTI_DIVERSI`,
  `E_CLIENTE_STESSA_CHIAVE` — dai quattro cancelli sul collegamento che nasce o cambia azienda (vedi sotto).

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — il collegamento scritto alla nascita del
  billing account, anche senza sessione.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — il collegamento che non si cancella e
  non si sposta, il cambio d'azienda per modifica finché non ci sono documenti, la predefinita che si sposta
  senza toccare nessun cliente, nessun billing account senza collegamento.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql`,
  `db/pgtap/anagrafiche/test-ba-storia-qualunque-documento-v1.sql`,
  `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql`,
  `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql`,
  `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — i cancelli.
* `db/pgtap/script/test-ba-emittente-risoluzione-v1.sql` — la risoluzione dell'azienda.

---

### Note di migrazione

* 2026-04-08 — il collegamento nasce da solo con l'azienda di chi crea il billing account; prima la
  predefinita era il caso normale.
* 2026-08-26 — il collegamento di un cliente con storia non si sposta più.
* 2026-08-31 — la storia diventa «documento numerato di qualunque famiglia»; prima erano fatture e commesse.
* 2026-09-13 — entra il livello «azienda di chi agisce» nella risoluzione.
* 2026-10-08 — un'istanza ha billing account di una sola azienda.
* 2026-10-10 — i controlli sullo spostamento della predefinita chiedono l'azienda per l'installazione.
* 2026-11-26 — ogni billing account ha sempre il suo collegamento (anche nato senza sessione: prima restava
  sulla predefinita, e la seguiva quando si spostava); i billing account scollegati sono collegati una volta
  alla predefinita di quel giorno. Il collegamento non si cancella e non si sposta; la storia diventa
  «qualunque documento, anche in bozza»; i controlli sullo spostamento della predefinita sono ritirati.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
