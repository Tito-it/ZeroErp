## 📘 Documentazione Concettuale – Tabella `vendite.ordini`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — le righe dell'ordine
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — gli stati del documento
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
> * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — la modalità di pagamento
> * [config.valute](/dbzero/config/tabelle/valute) — la valuta
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — il termine di pagamento
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il cliente e l'agente
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account
>
> Approfondimento viste:
>
> * [vendite.vw_ordini_lista](/dbzero/vendite/views/vw_ordini_lista) — la lista configurabile, con la provenienza leggibile
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---
### 🎯 Scopo Principale
La tabella **`vendite.ordini`** rappresenta la **testata dell’ordine di vendita**, documento commerciale preliminare che raccoglie le condizioni di vendita, spedizione e pagamento concordate con il cliente.  
È il punto di partenza del ciclo attivo, destinato a generare documenti successivi (DDT, fatture, contratti di fornitura).

Obiettivi principali:

* Gestire in modo univoco gli **ordini cliente** con identificazione tramite `uid` e *(anno, serie, numero)*.  
* Mantenere coerenza con gli **stati di avanzamento** (bozza, confermato, evaso, ecc.).  
* Integrare **dati economici, di trasporto e di fatturazione** in un unico oggetto coerente.  
* Dichiarare la **provenienza** dell'ordine nato da un preventivo o da un'offerta, con le colonne `sorgente_*` del modello comune.  
* Favorire il **riuso in downstream** per generazione DDT, documenti di trasporto o fatture.

---

### Canale di origine (post 20-04-2026)

Colonna `canale_origine` di tipo `config.canale_origine` (ENUM
`ADMIN` / `PORTALE` / `SHOP`), `NOT NULL DEFAULT 'ADMIN'`. Discrimina il
canale di creazione dell'ordine.

* **Immutabile post-INSERT** via trigger
  `trg_vendite_ordini_a10_canale_origine_immutable_upd` (codice errore
  `E_CANALE_ORIGINE_IMMUTABILE` id 385).
* Usato dalla **policy RLS `rls_ordini_shop`** per filtrare gli ordini
  visibili al canale shop (solo `canale_origine = 'SHOP'`). La policy
  portale B2B (`rls_ordini_cliente_ownership`) non filtra canale: il
  cliente B2B vede tutti gli ordini del proprio SR (caso 2 §5.1 guida
  multi-face).
* Default `ADMIN` su ordini pre-refactor e ordini creati da back-office.
  Rif. guida: [Architettura Multi-Face Auth §6.4](/guide/architettura-multi-face-auth)
  e [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
  per la semantica completa del canale.

---

### Emittente fiscale e scope operatore (RLS, 2026-06-01)

Colonna `emittente_fiscale_id` (FK ad `anagrafiche.emittenti_fiscali`,
**NOT NULL**): snapshot **user-derived** dell'emittente dell'operatore che
crea l'ordine, allineata a preventivi/contratti/offerte. Serve allo scope
RLS operatore (convenzione PK).

* **Valorizzazione**: trigger `trg_ordini_a10_default_emittente_ins`
  ([script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale), il building block unico dal 2026-09-15),
  via GUC `app.current_user_id` → `fn_resolve_emittente_for_user`. Skip se
  già valorizzato nel payload (admin globale / push).
* **Coerenza BA**: guard `trg_ordini_a10_guard_emittente_ba_ins_upd`
  ([script.trgfn_doc_guard_emittente_ba](/dbzero/script/manual/trgfn_doc_guard_emittente_ba))
  — emittente == `fn_get_emittente_fiscale_pk(billing_account_id)`, **skip se
  BA NULL** (a differenza di contratti, qui il BA è nullable).
* **Scope scrittura**: write-guard `trg_ordini_a10_guard_emittente_scope_ins_upd`
  (`script.trgfn_guard_emittente_scope`, modalità `fiscale`).

**RLS in lettura — `vendite.ordini` ha ora TRE policy PERMISSIVE (combinate in OR)**:

| Policy | Faccia (gate `ruolo_applicativo`) | Filtra per |
|---|---|---|
| `rls_ordini_cliente_ownership` | `CLIENTE_PORTALE` | `soggetto_ruolo_id` (proprio SR) |
| `rls_ordini_shop` | `SHOP_CUSTOMER` | SR + `canale_origine = 'SHOP'` |
| **`rls_ordini_ef_whitelist`** *(nuova)* | `OPERATORE` | `emittente_fiscale_id` in whitelist (via `fn_scope_ef_whitelist`) |

Ogni policy è **gated sul proprio ruolo**: un OPERATORE filtra solo per
emittente e **non eredita** la visibilità delle facce portale/shop (e
viceversa). RLS attivata con `ALTER TABLE … ENABLE ROW LEVEL SECURITY`
(no FORCE) — changeSet `20260601-39`.

---

### Immutabilità cliente (DB-ORD-LOCK, 2026-06-04)

Le colonne che identificano il **cliente dell'ordine** sono **immutabili dopo la
creazione**:

| Colonna | Note |
| --- | --- |
| `billing_account_id` | aggancio billing (nullable; valorizzato alla creazione) |
| `soggetto_ruolo_id` | cliente logico (NOT NULL) — identifica il cliente anche per ordini con BA NULL |

* **Decisione di dominio**: *«cambiare cliente = nuovo ordine»*. La relazione
  `billing_account → soggetto_ruolo` è 1:1 deterministica e viene fissata alla
  creazione (`crea_ordine` deriva il soggetto dal BA); un `UPDATE` che cambiasse
  il BA lascerebbe il soggetto stantio → incoerenza cliente↔soggetto.
* **Difesa DB autoritativa**: lock su `UPDATE` via il registro
  `dbops.automation_lock_columns` → trigger generato
  `trg_ordini_a10_lock_columns_upd` (`script.trgfn_lock_columns`), codice errore
  **`E_ORD_CLIENTE_IMMUTABILE`** (id 469). Lo stesso trigger continua a lockare
  `numero` (`CODICE_NON_MODIFICABILE`). L'`INSERT` resta libero.
* Si lockano **entrambe** le colonne: il solo BA non basterebbe perché gli ordini
  con `billing_account_id` NULL sono identificati dal solo `soggetto_ruolo_id`.
* **Via di manutenzione**: override straordinario
  `SET LOCAL zeroerp.allow_lock_columns_override = 'on'`.
* Difesa simmetrica al fix applicativo (`ordini_service.aggiorna_ordine` esclude
  `billing_account_id` dalla whitelist update): il guard BE intercetta a monte, il
  trigger è la difesa finale su `UPDATE` diretta che bypassa il service.
* Pattern allineato a `preventivi.emittente_fiscale_id`
  (`EMITTENTE_NON_MODIFICABILE`).

---

### Collocazione nel flusso documentale

1. **Creazione ordine** – avvio processo commerciale; definizione di cliente, condizioni economiche e pagamento.  
2. **Popolamento righe** – associazione articoli/servizi su `vendite.ordini_righe`.  
3. **Conferma** – cambio stato → “confermato”, calcolo totali e fissazione prezzi.  
4. **Evasione** – generazione automatica DDT o collegamento con logistica.  
5. **Alimentazione attività fatturabili** – acquisizione da `ordini` verso `vendite.attivita_fatturabili`.
6. **Fatturazione** – generazione fatture a partire da `attivita_fatturabili` (pipeline lotto/fatture), non direttamente da `ordini`.

---

### 📦 Identità documento & numerazione

* **Serie / Numero / Anno** costituiscono la chiave logica per la numerazione manuale o automatica.  
  L’indice univoco `uq_ordini_v_anno_serie_numero` assicura l’unicità solo se `numero IS NOT NULL`.
* **Generazione numero**: il trigger
  [`trgfn_ordini_gen_numero`](/dbzero/vendite/manual/trgfn_ordini_gen_numero)
  (BEFORE INSERT) assegna `numero` se NULL/vuoto → **valorizzato già all'INSERT,
  anche in BOZZA** (in pratica mai NULL; l'indice parziale
  `WHERE numero IS NOT NULL` è difensivo). La colonna è poi **immutabile**
  (lock colonne su `numero`).
  ⚠️ **rev 2026-08-31**: il numero non viene più da `script.fn_generate_codice`
  né dalla sequenza generica. Viene dal **motore dei registri** — contatore per
  azienda e per anno — e la sua **forma** (prefisso, suffisso, cifre) dal
  registro stesso. Il vecchio trigger `trgfn_ordini_gen_codice` non esiste più.  
* **UID** (`uuid`) – identificatore universale per import/export o sincronizzazione API.

> *Le colonne `sorgente_*` dicono da quale documento l'ordine nasce (vedi «Documento di origine»), non da quale sistema esterno è stato importato.*

---

### Stato, logistica e pagamenti

* **Stato documento**: `stato_doc_ordine_id` → `config.stati_doc_ordini`, determina le regole operative (bozza, confermato, spedito, fatturato, annullato).  
* **Trasporto e consegna**: gestiti sul **DDT a valle**, non sulla testata. Le
  colonne trasporto (`causale_trasporto_id`, `aspetto_bene_id`,
  `modalita_addebito_trasporto_id`, `vettore_soggetto_ruolo_id`) sono state
  **rimosse** dalla testata (refactor `20251027-01-ordini-refactor-testata`).  
* **Pagamento**: `modalita_pagamento_id`, `termine_pagamento_id` definiscono le
  condizioni economiche. `giorni_pagamento`/`fine_mese` **non sono più in testata**
  (rimossi nello stesso refactor): derivano da `billing_account`.  
* **Valuta e cambio**: `valuta_id`, `tasso_cambio` (default = 1).  

---

### 💰 Totali economici e coerenza

I campi di sintesi (`imponibile_tot`, `sconto_tot`, `iva_tot`, `totale_doc`) rappresentano il riepilogo dei valori calcolati dalle righe:

* **Calcolo dinamico**: eseguito da funzioni di riepilogo o trigger applicativi.
* **Persistenza**: i totali sono memorizzati per prestazioni e confronti di audit.
* **Coerenza**: eventuali modifiche alle righe richiedono ricalcolo sincrono o tramite job automatico.

---

### Meta, audit e storicizzazione

* **`meta jsonb`** – estensioni dinamiche (es. note interne, parametri specifici del cliente o canale).  
* **Audit standard** – colonne `data_insert`, `user_insert`, `data_update`, `user_update`.  
* **`storicizza`** – abilita i trigger del framework Zero ERP per la storicizzazione automatica dei record modificati o eliminati.  
* **Idempotenza** – l'`uid` identifica l'ordine nelle sincronizzazioni senza duplicazioni.

---

### Vincoli, indici e integrità

* **FK principali**:
  * Cliente → `anagrafiche.soggetti_ruoli`
  * Agente → `anagrafiche.soggetti_ruoli` (`fk_ordini_v_agente_ruolo`, nullable)
  * Billing Account → `anagrafiche.billing_account`
  * Stato → `config.stati_doc_ordini`
  * Valuta → `config.valute`
  * Pagamento e termini → `config.modalita_pagamento`, `config.termini_pagamento`
  * Tipo del documento d'origine → `config.sorgenti` (`sorgente_tipo_id`)

* **Indici**:
  * `ix_ordini_v_cliente_statoid_data` → per dashboard cliente/stato.  
  * `ix_ordini_v_statoid` → query per stato ordine.  
  * `uq_ordini_v_uid` → unicità globale UID.  
  * `uq_ordini_v_sorgente_offerta` → un'offerta genera al più un ordine vivo.  
  * `ix_ordini_v_sorgente_id`, `ix_ordini_v_sorgente_uid` → ricerca degli ordini nati da un documento.  
  * `uq_ordini_v_anno_serie_numero` → numerazione univoca condizionata.

---

### Fatturazione: ordine vs DDT

Il campo `fatturazione_trigger` controlla **quando** scatta il push a commessa:

| Valore | Comportamento |
| --- | --- |
| `CONFERMATO` (default) | Push a commessa alla conferma ordine (`fn_list_ordini_da_pushare`) |
| `SPEDITO` | Ordine non pusha; il DDT pusha quando spedito (`fn_list_ddt_da_pushare`) |
| `CONSEGNATO` | Ordine non pusha; il DDT pusha quando consegnato (`fn_list_ddt_da_pushare`) |

Il valore e` ereditato da `billing_account.fatturazione_ordini` al momento
dell'inserimento (via `trgfn_ordini_normalize`). Puo` essere sovrascritto
manualmente per singolo ordine.

---

### Agente / venditore (2026-06-03)

Colonna `agente_soggetto_ruolo_id` (FK ad `anagrafiche.soggetti_ruoli`, **nullable**):
l'agente/venditore associato all'ordine, per provvigioni e reporting commerciale.

* **Nullable**: non tutti gli ordini hanno un agente.
* **FK semplice**, simmetrica al cliente (`fk_ordini_v_cliente_ruolo`): nessun guard
  `child_requires_active_parent` dedicato sulla testata (l'attivo del soggetto è già
  garantito a monte da `soggetti_ruoli`). Indice FK delegato a
  `dbops.apply_fk_index_policy()`.
* **Display**: nella vista `vw_ordini_lista` come `agente_denominazione` (via
  `soggetti_ruoli` → `soggetti`).

---

### Documento di origine — la provenienza dell'ordine

Quando l'ordine **nasce da un preventivo o da un'offerta**, la provenienza sta nelle colonne
del modello comune della [sorgente polimorfa](/guide/sorgente-polimorfa):

| Colonna | Che cosa dice |
| --- | --- |
| `sorgente_tipo_id` | il tipo del documento d'origine in `config.sorgenti`: `PREVENTIVO` o `OFFERTA_COMMERCIALE` |
| `sorgente_id` *oppure* `sorgente_uid` | quale documento: una sola delle due, quella della chiave del tipo (preventivo e offerta si riconoscono per uid) |

* **Forma**: o le colonne sono tutte vuote (l'**ordine nato da solo**), o c'è il tipo con
  una sola chiave (`chk_ordini_sorgente_forma`). La provenienza è il documento intero:
  l'ordine non dichiara una riga d'origine.
* **Esistenza**: il guard unico `script.trgfn_guard_sorgente` controlla che il documento
  esista e sia visibile a chi scrive; finché un ordine lo dichiara, il documento d'origine
  non si cancella.
* **Chi la scrive**: i verbi che generano l'ordine, `vendite.fn_push_preventivo_a_ordine` e
  `vendite.fn_genera_ordine_da_offerta`.
* **Unicità solo dove il dominio la vuole**: un preventivo può generare **più ordini**
  (riordini, consegne parziali); un'**offerta** ne genera al più **uno vivo**
  (`uq_ordini_v_sorgente_offerta`). Un ordine annullato conserva la provenienza e non
  consuma l'offerta, che può generare un nuovo ordine.
* **Display**: nella vista `vw_ordini_lista` la provenienza è esposta anche in forma
  leggibile (`documento_origine_tipo`, `documento_origine_id`, `documento_origine_codice`),
  calcolata da `sorgente_*`.

---

### Regole di gestione

1. **Creazione** – ammessi solo stati iniziali (*bozza*).
2. **Numerazione** – assegnata dal trigger `trgfn_ordini_gen_numero` all'INSERT (anche in BOZZA) se `numero` è NULL; immutabile dopo (lock colonne).
3. **Cancellazione** – vietata se ordine gia` confermato o collegato a DDT/fatture (vincolo logico).
4. **Cambio valuta** – ammesso solo finche` non esistono righe evase.

---


### Ruolo nel sistema

`vendite.ordini` è la **base operativa** del ciclo vendite: raccoglie tutte le informazioni contrattuali e logistiche preliminari alla spedizione e alla fatturazione.  
Assicura la **tracciabilità completa** del flusso commerciale e costituisce un **ponte naturale** tra la fase commerciale, logistica e amministrativa del gestionale.

---

### Corsia di fatturazione: `fatturazione_immediata` (27-07-2026)

Colonna `boolean NOT NULL DEFAULT false` aggiunta dalla slice di simmetria del
flag (brief `brief-db-emissione-fattura-per-documento-sorgente` PARTE B,
migration `20260727-01`). Prima esisteva **solo** su `vendite.preventivi`: le altre
sorgenti esponevano il campo nel contratto delle `fn_list_*_da_pushare` ma con
valore costante `FALSE`, quindi **solo un preventivo poteva essere fatturato
subito** — non per una scelta di dominio, ma per un buco di modello.

| Valore | Corsia | Arriva a |
|---|---|---|
| `true` | immediata (lotto `GIORNALIERO`) | `DEFINITIVA` — numera da sola |
| `false` *(default)* | differita (lotto `MASSIVO`) | `EMESSA` — la numerazione è un atto separato |

**Si stabilisce PRIMA del push.** Il valore viene letto una sola volta, da
`vendite.fn_list_ordini_da_pushare`, e propagato alla commessa dove è **parte della chiave di dedup** di
`fn_get_or_create_commessa`. Dopo il push è inerte, e la modifica è respinta
dal guard
[`trgfn_guard_fatturazione_immediata_immutabile`](/dbzero/vendite/funzioni/trgfn_guard_fatturazione_immediata_immutabile)
(`E_FATT_IMMEDIATA_NON_MODIFICABILE`). Il caso «cambio idea dopo» è coperto
dall'**emissione mirata per gruppo fatturabile**, non da questo flag.

⚠️ **Non governa `prezzo_bloccato`.** L'accoppiamento
`prezzo_bloccato = COALESCE(fatturazione_immediata, false)` esiste **solo sui
preventivi**: qui i due valori sono indipendenti e vanno tenuti tali.

Il default `false` garantisce che l'aggiunta della colonna **non cambi la corsia
di nessun documento esistente**.

---

### Note di migrazione

* 2026-06-03 — introdotta la provenienza da preventivo e offerta, allora in due colonne
  dedicate `documento_origine_tipo` (vocabolario chiuso `PREVENTIVO` / `OFFERTA`) e
  `documento_origine_id`, separate da `sorgente_*` che serviva all'idempotenza d'import.
* 2026-11-06 — la provenienza passa nelle colonne `sorgente_*` del modello comune:
  ritirate `documento_origine_tipo` e `documento_origine_id`, e con loro gli indici
  `uq_ordini_v_sorgente_fk` (idempotenza d'import) e `uq_ordini_v_documento_origine_offerta`,
  sostituiti da `uq_ordini_v_sorgente_offerta` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
