## 📘 Documentazione Concettuale – Tabella `vendite.preventivi` (testata)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)  
> • [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)  
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)  
> • [config.valute](/dbzero/config/tabelle/valute)  

---
### 🎯 Scopo Principale
La tabella **`vendite.preventivi`** rappresenta la **testata del preventivo commerciale**:
raccoglie cliente/BA/utility, condizioni economiche, validita` e stato documento.

E` il punto di ingresso del ramo commerciale che, dopo accettazione, alimenta la pipeline
`attivita_fatturabili` prima della fase di fatturazione fiscale.

---

### Flusso documentale (allineato pipeline attuale)

1. **Creazione preventivo** (bozza/emesso).  
2. **Gestione righe** su `vendite.preventivi_righe` (articoli, qta, prezzi, IVA).  
3. **Accettazione commerciale** (`stato_doc_preventivo_id -> ACCETTATO`).  
4. **Acquisizione in attività fatturabili** (branch `PREVENTIVI`) con creazione/aggiornamento
   record in `vendite.attivita_fatturabili`.  
5. **Fatturazione**: le attività fatturabili entrano nel flusso lotto/fatture.

Nota:
- il passaggio standard non è diretto `preventivo -> fattura`, ma mediato da
  `attivita_fatturabili`.

---

### Revisione preventivi

`vendite.preventivi` supporta revisioni multiple dello stesso numero documento:

* `numero` + `rev` identifica univocamente la revisione (`uq_preventivi_numero_rev`);
* è ammessa **una sola revisione attiva per numero** tramite indice univoco parziale
  `ux_preventivi_numero_attiva` (`is_revision_attiva = true`).

Regola operativa:
* le pipeline downstream devono considerare la revisione attiva, evitando doppio carico
  di revisioni storiche non attive.

---

### Fatturazione immediata (`fatturazione_immediata`)

Il flag `fatturazione_immediata` identifica preventivi che devono avere priorita` di
esecuzione nel ciclo attivo:

1. generazione attività in `attivita_fatturabili` (come gli altri preventivi eleggibili);
2. instradamento operativo verso **lotto giornaliero** per fatturazione.

Stato implementativo:
* la semantica funzionale e` definita;
* l’orchestrazione completa del ramo `PREVENTIVI` con comportamento immediato
  è tracciata nel WIP `ripresa-lavori-attivita-fatturabili`.

---

### Campi chiave funzionali

* **Identificazione/revisione**: `numero`, `rev`, `is_revision_attiva`
* **Perimetro fiscale/operativo**: `billing_account_id`, `istanza_utility_id`, `utility_id`
* **Validita`**: `validita_dal`, `validita_al`
* **Economici**: `totale_imponibile`, `totale_iva`, `totale_documento`, `valuta_id`
* **Stato**: `stato_doc_preventivo_id`
* **Competenza**: `competenza_mese`
* **Comportamento processo**: `fatturazione_immediata`
* **Pagamento**: `termine_pagamento_id`

---

### Audit e metadati

* `meta jsonb` per estensioni dominio/canale;
* colonne audit standard (`data_insert`, `user_insert`, `data_update`, `user_update`).

---

### Regole di coerenza principali

1. `chk_preventivi_validita`: intervallo validita` coerente.
2. `chk_preventivi_competenza_mese_primo`: competenza allineata al primo giorno del mese.
3. FK attive su stato documento, termini, utility, valuta e BA.

---

### Ruolo nel sistema

`vendite.preventivi` è la base del ciclo commerciale “offerta -> fatturabile”:
governa la proposta al cliente, la sua revisione controllata e il passaggio strutturato
verso il dominio `attivita_fatturabili`, inclusi i casi a fatturazione immediata.

