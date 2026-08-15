## 📘 Documentazione Concettuale – Tabella `vendite.fatture` (testata)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)   
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)    
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)    
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)    
> • [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento)   
> • [config.valute](/dbzero/config/tabelle/valute)   
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)   
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   

---
### 🎯 Scopo Principale
(latest review 24-01-2026)
`vendite.fatture` rappresenta la **testata del documento fiscale di vendita**. Gestisce **identità fiscale (registro/anno/serie/numero)**, **stato e tipo documento**, **intestatari economici** (BA, emittente, reseller), **valuta e pagamento**, **totali** e **metadati**. È il **punto di aggregazione** delle righe (`vendite.fatture_righe`) e dei riepiloghi IVA.

Obiettivi principali:

* Garantire **numerazione univoca** per *(registro, anno, serie, numero)* quando la fattura è numerata.
* Tracciare **stato e tipo fiscale** senza vincoli di specifico ordinamento nazionale (modello neutro, estendibile).
* Gestire **multi‑valuta** e **termini di pagamento**.
* Conservare **totali** e **correzioni** (bollo, arrotondamenti), incluso il flag **"fattura di minimo"** (utilities).
  ⚠️ Non è un'opzione che qualcuno accende: `minimo` è **calcolato** da
  `fn_ricalcola_totali_fattura` confrontando `totale_a_pagare` con le due soglie
  di `anagrafiche.emittenti_fiscali_utilities`. È la banda che decide quali
  documenti si riportano sulla fattura successiva
  ([fondo fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)) — e
  contiene lo zero, quindi ci rientrano **anche i piccoli crediti**.
* Consentire **idempotenza** d’import (**`uid`** e/o *(sorgente_tipo_id, sorgente_uid)*).
* Segnalare **anomalie bloccanti** tramite `critical`.

---

### Canale di origine (post 20-04-2026)

Colonna `canale_origine` di tipo `config.canale_origine` (ENUM
`ADMIN` / `PORTALE` / `SHOP`), `NOT NULL DEFAULT 'ADMIN'`. Nella pratica
`vendite.fatture` accetta solo `ADMIN` o `PORTALE` — lo shop emette
**ricevute** (non fatture elettroniche) su tabella dedicata
[shop.ricevute](/dbzero/shop/tabelle/ricevute).

* **Immutabile post-INSERT** via trigger
  `trg_vendite_fatture_a10_canale_origine_immutable_upd` (codice errore
  `E_CANALE_ORIGINE_IMMUTABILE` id 385).
* Usato dalla **policy RLS `rls_fatture_ba_ownership`**: ammette solo
  `CLIENTE_PORTALE` (non `SHOP_CUSTOMER`). Lo shop customer non vede mai
  fatture B2B, anche se il soggetto sottostante ha anche veste portale.
* Default `ADMIN` su fatture pre-refactor (tutte generate da pipeline
  interna).
* Rif. guida: [Architettura Multi-Face Auth §6.4](/guide/architettura-multi-face-auth)
  e [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
  per la semantica completa del canale.

---

### Collocazione nel flusso documentale

1. **Pre‑emissione**: creazione testata (bozza), valorizzazione di BA, emittente, valuta, termini pagamento.
2. **Popolamento righe**: da attività fatturabili / ordini / altre fonti → `vendite.fatture_righe`.
3. **Calcolo totali**: `imponibile_tot`, `imposta_tot`, **riepiloghi IVA** e campi accessori (bollo, arrotondamenti, spese fuori imponibile).
4. **Numerazione**: assegnazione di *(registro, anno, serie, numero)* al cambio di stato (es. EMESSA/REGISTRATA) secondo le regole del registro.
5. **Post‑emissione**: eventuale contabilizzazione (`data_contabilizzazione`), esport, invio e conservazione.

---

### Identità fiscale & numerazione

* **Registro**: `registro_id` → `vendite.registri_fatturazione`. Definisce criteri di numerazione (per esercizio e serie).
* **Anno/Serie/Numero**: riempiti secondo il flusso; **indice univoco parziale** `uq_fatture_numero` assicura esclusività **solo** quando `numero IS NOT NULL`.
* **Trigger di protezione**:

  * `trg_fatture_a10_upd_protect_num` → impedisce modifiche non consentite ai campi di numerazione dopo l’assegnazione.
  * `trg_fatture_a11_upd_numerata_non_annulabile` → vincola la reversibilità di stato/numero per evitare annullamenti impropri.

---

### 🧾 Stato, tipo e attori

* **Tipo documento**: `tipo_doc_fiscale_id` → `config.tipi_doc_fiscale` (es.: fattura, nota credito, parcella, XML tipo‑doc neutrali).
* **Stato documento**: `stato_doc_fiscale_id` → `config.stati_doc_fiscale` (bozza, emessa, registrata, inviata, annullata, ecc.).
* **Emittente fiscale**: `emittente_soggetto_ruolo_id` → `anagrafiche.soggetti_ruoli` (stabilisce chi emette).
* **Billing Account**: `billing_account_id` (payer).
* **Reseller** *(opzionale)*: `reseller_soggetto_ruolo_id` per branding e catene commerciali.
* **Flag criticita`**: `critical = true` indica errori bloccanti (numerazione/invio sospesi).

---

### 💱 Valuta, cambio & pagamento

* **Valuta**: `valuta_id` → `config.valute`; **tasso**: `tasso_cambio` (default 1).
* **Termini pagamento**: `modalita_pagamento_id`, `giorni_pagamento`, `fine_mese` (calcolo scadenze).
* **Totali**: `imponibile_tot`, `imposta_tot`, `totale_doc`, con campi ausiliari:

  * **Bollo**: `bollo_applicato`, `bollo_importo`.
  * **Fondi fattura**: `fatture_fondi_fattura` (somma per `totale_a_pagare`).
  * **Arrotondamenti**: `arrotondamento_precedente` / `arrotondamento_attuale`.
  * **Totale a pagare**: `totale_a_pagare` (totale_doc + arrotondamenti + fondi).
  * **Saldo ambito**: l’origine del saldo tecnico e` `vendite.fatture_arrotondamenti_scope`
    (ambito: BA, utility, tipo documento, emittente, valuta).

> Suggerimento: calcolare e salvare anche gli importi nelle 2 valute (valuta documento & di conto) se richiesto dal reporting.

---

### Meta, storicizzazione & idempotenza

* `meta jsonb NOT NULL` → spazio per snapshot parametri di calcolo, riferimenti esterni, flags di integrazione.
* `storicizza boolean` → abilita storicizzazione su update/delete all’interno del tuo framework (audit/rollback).
* **Idempotenza**:

  * `uid` (uuid) come **identificativo applicativo** universale.
  * Coppia **(`sorgente_tipo_id`, `sorgente_uid`)** con indice univoco parziale `uq_fatture_v_sorgente_fk` per sincronizzazioni da sistemi esterni.

---


### Esempi d’uso (query applicative)

```sql
-- 1) Ricerca fatture per BA in un periodo
SELECT f.*
FROM vendite.fatture f
WHERE f.billing_account_id = :ba
  AND f.data BETWEEN :dal AND :al
ORDER BY f.data;

-- 2) Verifica univocità numerazione prima di assegnare il numero
SELECT 1
FROM vendite.fatture f
WHERE f.registro_id = :reg
  AND f.anno = :anno
  AND COALESCE(f.serie,'') = COALESCE(:serie,'')
  AND f.numero = :numero
  AND f.numero IS NOT NULL;

-- 3) Idempotenza import (sorgente)
SELECT f.id
FROM vendite.fatture f
WHERE f.sorgente_tipo_id = :src_tipo
  AND f.sorgente_uid = :src_uid;
```

---

### Best practice operative

* **Numerazione** solo in transizione di stato (es. da BOZZA → EMESSA/REGISTRATA) con transazione atomica e lock del registro.
* **Protezione campi** di numerazione via trigger (già presenti) e policy di ruolo.
* **Idempotenza**: popolare sempre `uid` oppure *(sorgente_tipo_id, sorgente_uid)* in integrazione.
* **Allineamento valute**: fissare `tasso_cambio` al momento dell’emissione e non modificarlo successivamente (se serve, storicizza variazioni in `meta`).
* **Totali**: ricalcolare da righe e riepiloghi IVA prima della numerazione; tracciare `arrotondamento_attuale`.
* **Totale a pagare**: include fondi fattura e arrotondamenti, non solo imponibile+imposta.
* **Arrotondamenti**: usare `vendite.fn_get_arrotondamento_scope()` e
  `vendite.fn_set_arrotondamento_scope()` per gestire il saldo tecnico per ambito.

---

### ⚠️ Osservazioni & possibili migliorie

1. **Coerenza tra `stato_doc_fiscale` e numerazione**: valutare un **CHECK** o trigger che impedisca `numero IS NULL` se lo stato è *emessa/registrata*.
2. **Gestione annulli**: la presenza del trigger *non annullabile* è corretta; per note di credito usare `tipo_doc_fiscale` adeguato, con legame alla fattura originaria (campo di riferimento in righe/testata).
3. **Contabilizzazione**: `data_contabilizzazione` valorizzata solo a esport avvenuto; opzionale **unique** (registro, numero) + data contabile in sottomoduli di prima nota.
4. **Performance totali**: considerare `GENERATED ALWAYS AS` (se Postgres 12+ con funzioni stabili) o mantenere via trigger applicativi per `totale_doc`, per ridurre ricalcoli.

---

### Importanza nel sistema

`vendite.fatture` è il **fulcro fiscale** del ciclo vendite: custodisce l’identità legale del documento, aggrega il contenuto economico e determina interfacce con **IVA, pagamenti, contabilità e integrazioni esterne**. Una corretta gestione di numerazione, stato e idempotenza garantisce **consistenza, rintracciabilità e compliance**.
