## 📘 Documentazione Concettuale – Tabella `vendite.fatture`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione) — i criteri di numerazione
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — le righe, che portano la provenienza
> * [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva) — i riepiloghi IVA
> * [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale) — il vocabolario degli stati
> * [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale) — il canale
> * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — le modalità di pagamento
> * [config.valute](/dbzero/config/tabelle/valute) — la valuta
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il pagante
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — emittente e reseller
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

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
* Consentire **idempotenza** d’import tramite **`uid`**.
* Segnalare **anomalie bloccanti** tramite `critical`.

---

### Canale di origine

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
* Default `ADMIN`: le fatture generate dalla pipeline interna.
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

* **Canale**: `tipo_doc_fiscale_id` → `config.tipi_doc_fiscale`. ⚠️ Non è la natura del documento (fattura, nota di credito): il seed contiene `FRONTOFFICE` / `BACKOFFICE`, ma front/back office è **solo un esempio**, ogni azienda può usare quel campo per un asse suo (area, brand, mandante) e nessuna logica deve inferirne il valore.
* **Natura fiscale**: `natura_doc_id` → `config.nature_doc_fiscale` (`FATTURA` / `NOTA_CREDITO` / `NOTA_DEBITO`). È l'asse che questa doc cercava sotto il nome sbagliato, ed è **ortogonale** al canale: il canale è una scelta dell'azienda, la natura è la legge. Vocabolario neutro per dichiarazione del modello; il `TipoDocumento` della FatturaPA (`TD01`/`TD04`/`TD05`) vive in `nature_doc_fiscale.meta.sdi_tipo_documento`, non in una colonna. ⛔ **Non si cambia dopo**: presidiata da `trg_fatture_a10_lock_natura_doc_upd`. Invariante verificato prima della numerazione (condizione 7 del guard D-K di `fn_assign_numero_fattura`): `natura = NOTA_CREDITO ⟺ totale_a_pagare ≤ 0`.
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
* **Idempotenza**: `uid` (uuid) come **identificativo applicativo** universale.

---

### Da quale documento nasce: di norma da nessuno

La testata ha le colonne del modello della provenienza (`sorgente_tipo_id` con una fra
`sorgente_id` / `sorgente_uid`, forma tenuta da `chk_fatture_sorgente_forma`, guard unico
`script.trgfn_guard_sorgente`), ma **di norma sono vuote**: una fattura aggrega le attività di
più documenti, e la provenienza sta sulle **righe** (`vendite.fatture_righe`, e il legame delle
attività fatturabili con la riga che le fattura, `vendite.attivita_fatturabili.fattura_riga_id`).
Non è una chiave d'idempotenza: non c'è un vincolo unico sulla provenienza della testata.

---

### Best practice operative

* **Numerazione** solo in transizione di stato (es. da BOZZA → EMESSA/REGISTRATA) con transazione atomica e lock del registro.
* **Protezione campi** di numerazione via trigger (già presenti) e policy di ruolo.
* **Idempotenza**: popolare sempre `uid` in integrazione.
* **Allineamento valute**: fissare `tasso_cambio` al momento dell’emissione e non modificarlo successivamente (se serve, storicizza variazioni in `meta`).
* **Totali**: ricalcolare da righe e riepiloghi IVA prima della numerazione; tracciare `arrotondamento_attuale`.
* **Totale a pagare**: include fondi fattura e arrotondamenti, non solo imponibile+imposta.
* **Arrotondamenti**: usare `vendite.fn_get_arrotondamento_scope()` e
  `vendite.fn_set_arrotondamento_scope()` per gestire il saldo tecnico per ambito.

---

### ⚠️ Osservazioni & possibili migliorie

1. **Coerenza tra `stato_doc_fiscale` e numerazione**: valutare un **CHECK** o trigger che impedisca `numero IS NULL` se lo stato è *emessa/registrata*.
2. **Gestione annulli**: la presenza del trigger *non annullabile* è corretta. La nota di credito si dichiara con **`natura_doc_id`**, non con `tipo_doc_fiscale` — quella colonna fa l'asse del canale. Il legame alla fattura originaria esiste su **due livelli**: riga↔riga (`fatture_righe.riga_rettificata_id`, che è anche la sorgente da cui si copiano prezzo, sconto e IVA, mai ricalcolati) e documento↔documento (`vendite.fatture_rettifiche`, popolata come **proiezione** del legame di riga da `vendite.fn_popola_fatture_rettifiche`, non come seconda verità).
3. **Contabilizzazione**: `data_contabilizzazione` valorizzata solo a esport avvenuto; opzionale **unique** (registro, numero) + data contabile in sottomoduli di prima nota.
4. **Performance totali**: considerare `GENERATED ALWAYS AS` (se Postgres 12+ con funzioni stabili) o mantenere via trigger applicativi per `totale_doc`, per ridurre ricalcoli.

---

### Importanza nel sistema

`vendite.fatture` è il **fulcro fiscale** del ciclo vendite: custodisce l’identità legale del documento, aggrega il contenuto economico e determina interfacce con **IVA, pagamenti, contabilità e integrazioni esterne**. Una corretta gestione di numerazione, stato e idempotenza garantisce **consistenza, rintracciabilità e compliance**.

---

### La colonna `data`

#### Chi la scrive

⛔ **Un solo punto in tutto il repo**:
[`fn_get_or_create_fattura_header`](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header),
alla creazione della testata — e da lì in poi soltanto
[`fn_imposta_data_documento_lotto`](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto),
quando l'operatore la ridichiara. Nessun endpoint, nessuna schermata.

Il valore è
[`fn_calcola_data_documento`](/dbzero/vendite/funzioni/fn_calcola_data_documento):
la politica del registro, che una data dichiarata sul lotto può scavalcare.

⚠️ Il `DEFAULT` di colonna è `script.fn_data_operativa()`. È **inerte** sul percorso reale — chi scrive passa
la data a mano — e serve perché la DDL non dichiari una cosa diversa da quella
che succede: **chi scrive una fixture il default lo usa davvero**.

#### ⛔ Da quando c'è un numero, la data non si tocca più

`trg_fatture_a10_guard_data_numerata_upd` →
[`trgfn_fatture_guard_data_numerata`](/dbzero/vendite/funzioni/trgfn_fatture_guard_data_numerata).
Rifiuta con `E_FATTURA_DATA_NON_MODIFICABILE`.

⚠️ **Il discriminante è `numero IS NOT NULL`, non lo stato**, e non è un
dettaglio: `fn_numera_fattura_opz_emessa` assegna il numero **mentre** la fattura
è in `EMESSA` — lo stato passa a `DEFINITIVA` dopo, nella finalizzazione dello
step. Una soglia scritta sugli stati lascerebbe una finestra reale in cui il
documento ha un numero fiscale e la data è ancora scrivibile.

📌 `trgfn_fattura_satellite_guard_congelamento` — che sembra congelare la testata
oltre `EMESSA` — è agganciata a `vendite.fatture` sulle **sole** colonne
`emittente_snapshot` e `cliente_snapshot`. Su `fatture_indirizzi` e
`fatture_scadenze` copre tutti gli eventi; sulla testata no.

#### ⚠️ Cambiare la data significa rifare il piano rate

Le scadenze si calcolano da `f.data` (`data_rata = data + offset`) nello step
**EMESSA**, cioè **prima** del numero. Il guard **D-K** verifica che
Σ rate = `totale_a_pagare`: la **somma non cambia**, cambiano le **date**. Una
data nuova con rate vecchie passerebbe quindi in silenzio.

⭐ Per questo la ridichiarazione si fa **solo** da
`fn_imposta_data_documento_lotto`, che rigenera, e mai con un `UPDATE` diretto.

---

### Note di migrazione

* 2026-04-20 — arriva `canale_origine`.
* 2026-08-18 — arriva `natura_doc_id`, con la nota di credito dichiarata dalla natura e non dal
  canale; prima la pagina diceva che `tipo_doc_fiscale_id` distingueva fattura, nota di credito
  e parcella (brief-design-note-credito-resi).
* 2026-08-25 — la data la scrive il calcolo della politica del registro, il `DEFAULT` passa da
  `CURRENT_DATE` a `script.fn_data_operativa()`, e la data di una fattura numerata si ferma:
  prima nessun guard la proteggeva (brief-db-numerazione-data-documento-e-sequenza).
* 2026-11-07 — la provenienza della testata passa al modello: la chiave testuale `sorgente_uid`
  diventa la coppia tipizzata `sorgente_id` / `sorgente_uid` (uuid) col guard unico; l'indice
  univoco `uq_fatture_v_sorgente_fk`, che la presentava come chiave d'idempotenza, non c'è più
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
