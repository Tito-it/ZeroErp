## 📘 Documentazione Concettuale – Tabella `vendite.ordini` (testata)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)  
> • [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)  
> • [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento)   
> • [config.valute](/dbzero/config/tabelle/valute)  
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)  
> • [config.causali_trasporto](/dbzero/config/tabelle/causali_trasporto)  
> • [config.aspetti_beni](/dbzero/config/tabelle/aspetti_beni)  
> • [config.modalita_addebito_trasporto](/dbzero/config/tabelle/modalita_addebito_trasporto)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)    

---
### 🎯 Scopo Principale
La tabella **`vendite.ordini`** rappresenta la **testata dell’ordine di vendita**, documento commerciale preliminare che raccoglie le condizioni di vendita, spedizione e pagamento concordate con il cliente.  
È il punto di partenza del ciclo attivo, destinato a generare documenti successivi (DDT, fatture, contratti di fornitura).

Obiettivi principali:

* Gestire in modo univoco gli **ordini cliente** con identificazione tramite `uid` e *(anno, serie, numero)*.  
* Mantenere coerenza con gli **stati di avanzamento** (bozza, confermato, evaso, ecc.).  
* Integrare **dati economici, di trasporto e di fatturazione** in un unico oggetto coerente.  
* Supportare l’**idempotenza** d’import (da CRM o sistemi esterni) tramite coppia *(sorgente_tipo_id, sorgente_uid)*.  
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
  ([trgfn_ordini_default_emittente](/dbzero/vendite/funzioni/trgfn_ordini_default_emittente)),
  via GUC `app.current_user_id` → `fn_resolve_emittente_for_user`. Skip se
  già valorizzato nel payload (admin globale / push).
* **Coerenza BA**: guard `trg_ordini_a10_guard_emittente_ba_ins_upd`
  ([trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba))
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
* **Trigger di protezione**:  
  `trg_ordini_a10_upd_v_protect_num` → impedisce modifiche a campi di numerazione dopo conferma.  
* **UID** (`uuid`) – identificatore universale per import/export o sincronizzazione API.

> *Gli ordini possono essere generati anche da sistemi esterni (CRM, portali clienti, configuratori) e successivamente importati nel gestionale tramite `sorgente_tipo_id` + `sorgente_uid`.*

---

### Stato, logistica e pagamenti

* **Stato documento**: `stato_doc_ordine_id` → `config.stati_doc_ordini`, determina le regole operative (bozza, confermato, spedito, fatturato, annullato).  
* **Trasporto e consegna**: collegamenti a `causale_trasporto_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id`, `vettore_soggetto_ruolo_id`.  
  Questi valori consentono la generazione diretta dei DDT con parametri coerenti.  
* **Pagamento**: `modalita_pagamento_id`, `termine_pagamento_id`, `giorni_pagamento`, `fine_mese` definiscono le condizioni economiche.  
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
* **Idempotenza** – tramite `uid` o coppia `(sorgente_tipo_id, sorgente_uid)` garantisce sincronizzazioni senza duplicazioni.

---

### Vincoli, indici e integrità

* **FK principali**:
  * Cliente → `anagrafiche.soggetti_ruoli`
  * Billing Account → `anagrafiche.billing_account`
  * Stato → `config.stati_doc_ordini`
  * Valuta → `config.valute`
  * Pagamento e termini → `config.modalita_pagamento`, `config.termini_pagamento`
  * Aspetto, causale e modalità trasporto → `config.aspetti_beni`, `config.causali_trasporto`, `config.modalita_addebito_trasporto`
  * Sorgente → `config.sorgenti`

* **Indici**:
  * `ix_ordini_v_cliente_statoid_data` → per dashboard cliente/stato.  
  * `ix_ordini_v_statoid` → query per stato ordine.  
  * `uq_ordini_v_uid` → unicità globale UID.  
  * `uq_ordini_v_sorgente_fk` → idempotenza import (solo se `sorgente_tipo_id` non nullo).  
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

### Regole di gestione

1. **Creazione** – ammessi solo stati iniziali (*bozza*).
2. **Aggiornamento numerazione** – possibile solo da trigger di sistema durante conferma ordine.
3. **Cancellazione** – vietata se ordine gia` confermato o collegato a DDT/fatture (vincolo logico).
4. **Cambio valuta** – ammesso solo finche` non esistono righe evase.
5. **Sorgente esterna** – se popolata, blocca rinumerazione automatica e update su `serie/numero`.  

---


### Ruolo nel sistema

`vendite.ordini` è la **base operativa** del ciclo vendite: raccoglie tutte le informazioni contrattuali e logistiche preliminari alla spedizione e alla fatturazione.  
Assicura la **tracciabilità completa** del flusso commerciale e costituisce un **ponte naturale** tra la fase commerciale, logistica e amministrativa del gestionale.
