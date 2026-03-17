## 📘 Documentazione Concettuale – Tabella `vendite.preventivi_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [config.iva](/dbzero/config/tabelle/iva)  
>
**Approfondimento funzioni/trigger:**
>
• [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa)  

---

### 🎯 Scopo Principale

`vendite.preventivi_righe` contiene il dettaglio economico-tecnico del preventivo:
articolo, quantita`, prezzo, sconto, IVA e snapshot UoM operativa.

Le righe sono la base informativa per la successiva generazione di
`attivita_fatturabili` nel ramo `PREVENTIVI`.

---

### Quantita` e UoM operativa

La tabella supporta doppia rappresentazione quantita`:

* `qta_operativa` + `uom_operativa_id` (input operativo utente/sorgente)
* `quantita` (valore base usato nei calcoli)
* `factor_to_base` (fattore snapshot al momento della riga)

Il trigger `script.trgfn_qta_from_operativa` mantiene l’allineamento dei valori.

---

### Regole principali

1. Ogni riga appartiene a un preventivo (`preventivo_id` obbligatorio).
2. `articolo_id` obbligatorio e referenziato a catalogo.
3. Controlli su valori economici e sconto (`chk_prevrighe_quantita_prezzo`, `chk_prevrighe_sconto`).
4. Flag `attivo` per escludere righe senza cancellazione fisica.

---

### Ruolo nel flusso fatturazione

1. Le righe alimentano la valutazione di eleggibilita` del preventivo.
2. In stato testata idoneo (es. `ACCETTATO`) diventano fonte per creare
   attività in `vendite.attivita_fatturabili`.
3. Le attività, non le righe preventivo direttamente, entrano nel flusso lotto/fatture.

---

### Campi chiave funzionali

* `preventivo_id`, `articolo_id`
* `descrizione`
* `quantita`, `qta_operativa`, `uom_operativa_id`, `factor_to_base`
* `prezzo_unitario`, `sconto_percentuale`, `iva_id`
* `ordine`, `attivo`
* `meta`

---

### Audit e qualità dati

* audit standard (`data_insert`, `user_insert`, `data_update`, `user_update`);
* trigger di validazione referenziale su articoli/IVA/UoM attivi;
* prevenzione disattivazione riga se esistono note collegate (`note_preventivo`).

---

### Ruolo nel sistema

`vendite.preventivi_righe` rappresenta il livello di granularita` commerciale
necessario per trasformare il preventivo in elementi fatturabili in modo tracciabile,
coerente e idempotente lungo la pipeline.

