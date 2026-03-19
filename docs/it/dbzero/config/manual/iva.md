## 📘 Documentazione Concettuale – Tabella `config.iva` 

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[config.iva_assoggetamenti](/dbzero/config/tabelle/iva_assoggettamenti)    
> [config.iva_natura](/dbzero/config/tabelle/iva_natura)    
> [config.conti_contabili](/dbzero/config/tabelle/conti_contabili)    
>
Approfondimenti funzioni:   
>
[config.trgfn_iva_ins_upd_check_conti_iva](/dbzero/config/funzioni/trgfn_iva_ins_upd_check_conti_iva)   
> [script.fn_get_iva_override](/dbzero/script/funzioni/fn_get_iva_override)    
> [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)     

La tabella **`config.iva`** fornisce il catalogo dei codici IVA, includendo descrizioni, regole di assoggettamento, split payment e mapping necessari per l’invio delle fatture al Sistema di Interscambio (SDI).

---
### 🎯 Scopo Principale
* Centralizzare i **codici IVA** disponibili in un unico repository configurabile.
* Gestire:

  * Descrizioni estesa e breve
  * Assoggettamento fiscale
  * Aliquota percentuale (quando applicabile)
  * Natura IVA per SDI (`natura_iva_id`)
  * Conti contabili di acquisto e vendita
  * Split payment (`id_iva_split`)

---

### Vincoli e Logiche Aziendali

* **Unicità**: `codice` deve essere univoco.
  * …
* **Aliquota vs. assoggettamento**: se `assoggettamento_iva_id` è diverso da vuoto, **l’`aliquota_iva` non può essere valorizzata** (dev’essere zero o lasciata al default).
* **Split payment**: `id_iva_split` può essere valorizzato per indicare che il codice IVA segue la normativa di split payment. In questo caso punta ricorsivamente a un codice “reale” in `config.iva`, definendo a quale aliquota reale si collega il meccanismo di split.
* **Natura IVA per SDI**: `natura_iva_id` fa riferimento a `config.iva_natura(id)`, fornendo il codice natura necessario per la trasmissione al SDI.
* **Conti contabili**:

  * `conto_iva_acquisti_id` → deve essere un conto di tipo acquisto
  * `conto_iva_vendita_id` → deve essere un conto di tipo vendita

---

### Relazioni e Indici

* **FK**:

  * `natura_iva_id` → `config.iva_natura(id)`
  * `conto_iva_acquisti_id` → `config.conti_contabili(id)`
  * `conto_iva_vendita_id` → `config.conti_contabili(id)`
  * `id_iva_split` → `config.iva(id)` (ricorsivo)
* **Indice**: `IX_IVA_DESC` su `desc_iva` per ricerche testuali performanti

---

### Trigger Associati

1. **`trg_iva_ins_upd_check_conti_iva`**

   * **Quando**: `BEFORE INSERT OR UPDATE`
   * **Cosa**: verifica la corretta tipologia dei conti IVA (acquisto vs vendita).
2. **`trg_upd_iva_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: popola automaticamente i campi `data_update` e `user_update` per l’audit.

---

### Vantaggi Operativi

* **Conformità normativa**: split payment e natura IVA per SDI gestiti automaticamente.
* **Integrità referenziale**: FK e trigger garantiscono correttezza dei conti e dei codici natura.
* **Riduzione degli errori**: constraint e trigger prevengono valori non validi per assoggettamento e aliquota.
* **Velocità di ricerca**: indice su `descrizione` per filtrare rapidamente le descrizioni.

---

> **“Un modello di dati IVA ben governato semplifica la compliance fiscale e riduce i rischi di errore durante la compilazione e trasmissione delle fatture.”**
