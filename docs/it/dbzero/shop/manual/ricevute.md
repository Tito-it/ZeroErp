## 📘 Documentazione Concettuale – Tabella `shop.ricevute`

> 👀 **Vedi anche**
>
> Architettura di riferimento:
>
> [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) §6.4 — Tracciabilita' canale sui dati transazionali
>
> Tabelle correlate:
>
> [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — BA shop (con `canale_origine='SHOP'`)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — SR del cliente shop
> [vendite.ordini](/dbzero/vendite/tabelle/ordini) — ordine shop opzionale
> [config.canale_origine](#) — ENUM discriminante canale (ADMIN/PORTALE/SHOP)

---

### 🎯 Scopo Principale

(latest revision 20-04-2026)

La tabella **`shop.ricevute`** contiene i documenti fiscali emessi dal canale
**shop B2C** (negozio online self-service). E' una tabella dedicata, separata
da `vendite.fatture` (che resta il contenitore B2B fiscale con fatturazione
elettronica), per tre motivi:

1. **Shop emette solo ricevute consumer** — niente SdI, niente XML, niente
   partita IVA fatturante sul documento. Il formato e le regole normative
   sono diverse dalle fatture B2B.
2. **BA separati per canale** — le ricevute shop vivono su BA con
   `canale_origine = 'SHOP'`, distinti dai BA portale B2B dello stesso
   cliente anagrafico (se ha anche quella veste).
3. **RLS pulite** — la policy RLS di `vendite.fatture` per il portale B2B
   non deve distinguere tipo documento; lo shop ha il suo silo con policy
   dedicata (`rls_shop_ricevute_self_ownership`).

---

### Collegamenti principali

* `soggetto_ruolo_id` → `anagrafiche.soggetti_ruoli(id)` — SR del cliente shop
  (tipo_ruolo 'CL'). Match con l'identita `SHOP_CUSTOMER` per RLS.
* `billing_account_id` → `anagrafiche.billing_account(id)` — **deve** avere
  `canale_origine = 'SHOP'`. L'invariante e' blindato lato DB dal trigger
  `trg_shop_ricevute_a10_guard_ba_canale_ins_upd` (vedi §Trigger).
* `ordine_shop_id` → `vendite.ordini(id)` opzionale — ordine shop di
  riferimento (con `canale_origine = 'SHOP'`). Nullable per ricevute
  estemporanee senza ordine formale.

---

### Regole di dominio

* **`canale_origine` fisso a `SHOP`** — CHECK constraint
  `chk_shop_ricevute_canale_shop`. La tabella per definizione ospita solo
  dati shop: il CHECK previene pollution da altri canali.
* **`numero` univoco globale** — UNIQUE constraint. La generazione e'
  responsabilita' del service shop (formato consigliato `YYYY-NNNNN`,
  con reset annuale gestito dal service).
* **Totali non negativi** — CHECK `chk_shop_ricevute_totali_non_neg`:
  `totale_lordo >= 0`, `totale_iva >= 0`, `totale_iva <= totale_lordo`.
* **Esito pagamento tra valori ammessi** — CHECK
  `chk_shop_ricevute_pagamento_esito`: `PENDING`, `OK`, `KO`, `RIMBORSATO`.
* **Coerenza BA→canale** (enforced DB-side dal 21-04-2026): il
  `billing_account_id` deve avere `canale_origine = 'SHOP'`. Il trigger
  `trg_shop_ricevute_a10_guard_ba_canale_ins_upd` (vedi §Trigger) solleva
  `E_SHOP_RICEVUTA_BA_CANALE_INVALIDO` (codice errore 386) su INSERT o
  UPDATE del FK con BA di canale diverso.
* **Coerenza ordine→canale** (non enforced): se `ordine_shop_id` e'
  valorizzato, il corrispondente `vendite.ordini` deve avere
  `canale_origine = 'SHOP'`.

---

### Pagamento

Lo shop B2C usa pagamenti immediati (carta, PayPal, contanti, eventualmente
bonifico). I campi `pagamento_metodo` e `pagamento_esito` sono testuali per
semplicita' MVP — un'evoluzione potrebbe introdurre ENUM dedicati o una
tabella di lookup. `meta` (JSONB) puo' contenere ID transazione del PSP,
riferimento pagamento, dati di spedizione, ecc.

---

### Ciclo di vita

1. Il service shop (endpoint `/api/shop/checkout/`) crea la ricevuta dopo
   la conferma del pagamento (o `PENDING` se il pagamento e' in corso).
2. L'identita `SHOP_CUSTOMER` dell'utente vede la ricevuta tramite la policy
   RLS `rls_shop_ricevute_self_ownership` (match su `soggetto_ruolo_id`
   comune).
3. L'operatore admin puo' consultare le ricevute via namespace `/api/admin/`
   (policy RLS operatore prevista in migration post-MVP; in mancanza, il
   BE applica filtro EF_WHITELIST lato service).
4. Le ricevute sono immutabili post-INSERT per quanto riguarda importi e
   dati fiscali (applicazione lato service, non DB). Eventuale rimborso
   crea un nuovo record con `pagamento_esito = 'RIMBORSATO'` oppure
   aggiorna solo `pagamento_esito` (non tocca totali).

---

### Trigger

* **`trg_shop_ricevute_a10_guard_ba_canale_ins_upd`** — BEFORE INSERT e
  BEFORE UPDATE OF `billing_account_id`. Esegue
  `shop.trgfn_ricevute_guard_ba_canale()` che verifica
  `billing_account.canale_origine = 'SHOP'` e solleva
  `E_SHOP_RICEVUTA_BA_CANALE_INVALIDO` (id 386) se diverso. Migration
  `20260421-02`. Fail-closed se il BA non esiste (protezione ulteriore
  oltre la FK).

I trigger framework (audit `data_insert`/`user_insert`/`data_update`/
`user_update`, `tx_id`, storicizzazione) sono applicati
dall'automation post-creazione tabella — non elencati qui.

---

### Policy RLS (dry-run)

* **`rls_shop_ricevute_self_ownership`** (CREATE POLICY migration
  `20260420-07-01`): gate `SHOP_CUSTOMER` + il soggetto della ricevuta confrontato col
  perimetro dell'identità (`fn_scope_sr_perimetro` su `fn_get_identita_sr_perimetro`,
  calcolato una volta per istruzione, dal 21-10-2026). DRY-RUN:
  nessun `ENABLE` / `FORCE`, attivazione post-PR-B stabile.

Policy admin operatore prevista in migration dedicata: probabile `FOR ALL`
con gate `OPERATORE` + scope EF_WHITELIST (o whitelist dedicata per shop).

---

### Evoluzioni future

* Tabella `shop.ordini_shop` o riuso di `vendite.ordini` con canale SHOP —
  in MVP si usa la seconda opzione
* `shop.carrelli` + `shop.carrelli_righe` per gestire sessioni di acquisto
  non ancora finalizzate
* Trigger guard DB coerenza ordine→canale (oggi solo service-side; il
  vincolo BA→canale e' gia' blindato dal 21-04-2026)
* Collegamento al modulo `pagamenti` per riconciliazione PSP
* Policy RLS operatore attiva
