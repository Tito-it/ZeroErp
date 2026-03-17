## 📘 Documentazione Concettuale – Tabella `config.conti_contabili`

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[config.iva](/dbzero/config/tabelle/iva)    
>
Approfondimenti funzioni:   
>
[script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)     


La tabella **`config.conti_contabili`** definisce il piano dei conti utilizzabile per la contabilizzazione delle operazioni, distinguendo tra conti di **acquisto** e **vendita**, e supportando l’audit delle modifiche.

---

### 🎯 Scopo Principale

* Mantenere il catalogo centralizzato dei **codici conto** con descrizioni e tipologia.
* Supportare la validazione dei riferimenti contabili in altre tabelle (ad esempio `config.iva`).

---

### Vincoli e Regole Aziendali

* **Unicità**: `codice` deve essere univoco.
* **Tipologia**: `tipo_conto` può essere:

  * `A` (Acquisto)
  * `V` (Vendita)
* **Check Constraint**: garantisce che `tipo_conto` sia solo uno dei valori previsti.

---

### Relazioni e Indici

* **FK in ingresso**:

  * `config.iva.conto_iva_acquisti_id` → `config.conti_contabili(id)`
  * `config.iva.conto_iva_vendita_id` → `config.conti_contabili(id)`
* **Indici**:

  * `IX_CONTI_CONTABILI_DESCRIZIONE` su `descrizione` per ricerche testuali rapide
  * `IX_CONTI_CONTABILI_TIPO_CONTO` su `tipo_conto` per filtrare conti di acquisto/vendita

---

### Trigger Associati

1. **`trg_upd_conti_contabili_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: aggiorna automaticamente i campi `data_update` e `user_update` tramite `script.trgfn_upd_audit_data_user_generic()`

---

### Vantaggi Operativi

* **Governance contabile**: definizione centralizzata del piano dei conti.
* **Integrità referenziale**: associazioni corrette ai conti di acquisto e vendita.
* **Audit completo**: tracciamento automatico delle modifiche ai conti.
* **Performante**: indici ottimizzati per ricerca e filtro.

---

> **“Un piano dei conti ben strutturato è alla base di una contabilità affidabile e facilmente mantenibile.”**
