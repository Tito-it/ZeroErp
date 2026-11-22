## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_billing_account`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'azienda di un billing account, sui tre livelli
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — scrive il collegamento alla nascita del billing account
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) — il cancello della storia
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente) — il cancello dell'albero
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente) — il cancello dell'istanza
> * [anagrafiche.trgfn_emittenti_fiscali_default_guard](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_guard) — una e una sola predefinita
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — un'istanza, un'azienda

---

### 🎯 Scopo Principale

`anagrafiche.emittenti_fiscali_billing_account` dice per quale azienda (emittente fiscale) fattura ciascun
billing account, e tiene la riga dell'azienda predefinita, su cui ricade un billing account senza collegamento.

---

### Una riga per billing account, e una predefinita

Una riga ha un billing account e non è predefinita, oppure è la predefinita e non ha billing account: il
vincolo `chk_emittenti_fiscali_ba_default` non ammette altre combinazioni. `uq_emittenti_fiscali_ba` dà a un
billing account al massimo un collegamento, `uq_emittenti_fiscali_ba_default` al massimo una predefinita, e il
guard differito `trgfn_emittenti_fiscali_default_guard` pretende che a fine transazione ce ne sia esattamente
una (`E_EMITTENTE_DEFAULT_SINGLETON`): la predefinita si può spostare, non togliere. La crea il bootstrap
sulla prima azienda dell'installazione.

L'azienda si nomina col suo `soggetto_ruolo_id` (`emittente_soggetto_ruolo_id`, verso
`anagrafiche.emittenti_fiscali`), e deve essere attiva quando la riga nasce o cambia azienda: lo verifica a fine
transazione il trigger generico del genitore attivo.

---

### ⭐ Il collegamento nasce da solo

Quando nasce un billing account, `trgfn_billing_account_link_ef` scrive il suo collegamento con l'azienda di
chi lo sta creando. Senza un utente in sessione (seed, bootstrap) non scrive niente, e il billing account
resta sulla predefinita. Chi non ha un'azienda su cui scrivere, come un super admin che lavora su tutte, non
crea billing account finché esistono aziende attive (`E_BA_ADMIN_GLOBALE_VIETATO`, dal guard su
`billing_account`); con un'azienda di lavoro scelta in sessione li crea, e il collegamento va a quella.

Fra la nascita del billing account e la scrittura del collegamento c'è un istante in cui la riga non esiste
ancora: in sessione il risolutore risponde già l'azienda di chi agisce, cioè ciò che il trigger sta per
scrivere. È il secondo dei tre livelli descritti sotto.

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
* `E_BA_EMITTENTE_CON_STORIA`, `E_ALBERO_EMITTENTE_MISTO`, `E_ISTANZA_EMITTENTI_DIVERSI` — dai tre cancelli
  sui movimenti del collegamento (vedi sotto).

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — il collegamento scritto alla nascita del
  billing account.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql`,
  `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql`,
  `db/pgtap/anagrafiche/test-istanza-ba-gestore-globale-v1.sql` — i tre cancelli.
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

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
