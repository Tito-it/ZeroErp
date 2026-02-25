## 📘 Documentazione Concettuale – Tabella `vendite.ordini` (testata)

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)  
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

### 🧭 Collocazione nel flusso documentale

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

> 🔎 *Gli ordini possono essere generati anche da sistemi esterni (CRM, portali clienti, configuratori) e successivamente importati nel gestionale tramite `sorgente_tipo_id` + `sorgente_uid`.*

---

### 📄 Stato, logistica e pagamenti

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

### 🧷 Meta, audit e storicizzazione

* **`meta jsonb`** – estensioni dinamiche (es. note interne, parametri specifici del cliente o canale).  
* **Audit standard** – colonne `data_insert`, `user_insert`, `data_update`, `user_update`.  
* **`storicizza`** – abilita i trigger del framework Zero ERP per la storicizzazione automatica dei record modificati o eliminati.  
* **Idempotenza** – tramite `uid` o coppia `(sorgente_tipo_id, sorgente_uid)` garantisce sincronizzazioni senza duplicazioni.

---

### 🔒 Vincoli, indici e integrità

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

### ⚙️ Regole di gestione

1. **Creazione** – ammessi solo stati iniziali (*bozza*).  
2. **Aggiornamento numerazione** – possibile solo da trigger di sistema durante conferma ordine.  
3. **Cancellazione** – vietata se ordine già confermato o collegato a DDT/fatture (vincolo logico).  
4. **Cambio valuta** – ammesso solo finché non esistono righe evase.  
5. **Sorgente esterna** – se popolata, blocca rinumerazione automatica e update su `serie/numero`.  

---


### 👓 Ruolo nel sistema

`vendite.ordini` è la **base operativa** del ciclo vendite: raccoglie tutte le informazioni contrattuali e logistiche preliminari alla spedizione e alla fatturazione.  
Assicura la **tracciabilità completa** del flusso commerciale e costituisce un **ponte naturale** tra la fase commerciale, logistica e amministrativa del gestionale.
