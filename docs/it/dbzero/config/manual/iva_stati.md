## 📘 Documentazione Concettuale – Tabella `config.iva_stati`

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[config.iva](/dbzero/config/tabelle/iva)    
> [config.stati](/dbzero/config/tabelle/stati)    
>
Approfondimenti funzioni:   
>
[script.fn_get_iva_override](/dbzero/script/funzioni/fn_get_iva_override)  
> [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)     

La tabella **`config.iva_stati`** permette di definire **override locali** di aliquota e assoggettamento IVA per specifici Stati o Paesi, personalizzando il comportamento dei codici IVA principali in base al contesto geografico.

---
### 🎯 Scopo Principale
* Sovrascrivere, per ogni coppia `(iva_id, stato_id)`, i valori di aliquota e assoggettamento di default definiti in `config.iva`.
* Gestire scenari in cui normative locali richiedono aliquote differenti o modalità di assoggettamento speciali.

---

### Vincoli e Logiche Aziendali

* ~~**PK composito** `(iva_id, stato_id)`~~ ⛔ **non è più vero dal 2026-08-29**
  (changeSet `20260829-42`). La tabella ha ora una **chiave surrogata** `id`, e la
  coppia `(iva_id, stato_id)` è retrocessa a **vincolo di unicità** — che continua
  a garantire un solo override per combinazione, cioè la regola non è cambiata.
  ⭐ Il motivo del cambio non è estetico: **una chiave composita non è
  storicizzabile**. Le tabelle di storico portano *una sola* colonna di
  riferimento, quindi finché la chiave era doppia questa tabella non poteva avere
  una gemella in `storico` — e gli override di aliquota sono esattamente il
  genere di dato di cui serve sapere *com'era allora*.
* **`storicizza`**: da `20260829-42` la tabella partecipa allo storico.
* **Aliquota e assoggettamento**: entrambe sempre valorizzate; `aliquota_override` rappresenta la percentuale locale, mentre `assoggettamento_override` segue gli stessi codici di default (`NS`, `NI`, `ND`, `ES`, `RC`, `ED`, \`\`).
* **Assoggettamento**: se `assoggettamento_override` è diverso da vuoto, **`aliquota_override` deve essere 0** o lasciata al default, a indicare che prevale la modalità non imponibile o esente.

---

### Relazioni e Indici

* **FK**:

  * `iva_id` → `config.iva(id)` (ON UPDATE CASCADE, ON DELETE CASCADE)
  * `stato_id` → `config.stati(id)` (ON UPDATE CASCADE, ON DELETE RESTRICT)
* **Indice**: `IX_IVA_STATI_STATO` su `stato_id` per ricerche per Paese

---

### Trigger Associati

1. **`trg_upd_iva_stati_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: aggiorna i campi di audit `data_update` e `user_update` tramite la funzione generica `script.trgfn_audit_data_user_generic()`.

---

### Vantaggi Operativi

* **Flessibilità normativa**: consente di adattare codici IVA a normative locali diverse senza duplicare codici principali.
* **Integrità referenziale**: eliminazione a cascata su `iva` pulisce automaticamente gli override obsoleti.
* **Chiarezza**: la struttura composita PK + FK garantisce coerenza tra codici IVA e Stati di riferimento.

---

> **“Un meccanismo di overriding geografico semplifica la gestione di eccezioni fiscali locali, mantenendo il catalogo IVA principale pulito e centralizzato.”**
