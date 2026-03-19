## 📘 Documentazione Concettuale – Tabella `config.tipi_contatti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti)    
>
Approfondimenti funzioni:   
>
[script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns)     
> [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)     

---
### 🎯 Scopo Principale
(latest review 07-01-26)
La tabella **`config.tipi_contatti`** definisce le **categorie di contatto** utilizzabili
nell’anagrafica dei soggetti. Il reparto/ufficio di riferimento e' invece gestito da
`config.unita_organizzative`.

---

### Vincoli e Caratteristiche Chiave

* **Codice interno (`cod_int_tipo_contatto`)**: non modificabile, garantisce stabilita dei riferimenti.
* **Descrizione obbligatoria**: la `descrizione` non può essere vuota.
* **Unicità**: ogni codice interno deve essere unico.

---

### Esempi di Tipologie

Alcuni esempi di categorie di contatto:

* `Principale`
* `Referente`
* `Segreteria`
* `Altro`

---

### Relazioni e Indici

* **FK in ingresso**:

  * `anagrafiche.contatti.tipo_contatto_id` → `config.tipi_contatti(id)`

* **Indici**:

  * Unico su `cod_int_tipo_contatto`

---

### Trigger Associati

1. **`trg_tipi_contatti_upd_lock_cod_interno`**

   * **Quando**: `BEFORE UPDATE` su `cod_int_tipo_contatto`
   * **Cosa**: blocca la modifica del codice interno, utilizzando `script.trgfn_lock_columns` con error code `CODICE_NON_MODIFICABILE`.

2. **`trg_upd_tipi_contatti_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: aggiorna i campi di audit `data_update` e `user_update` automaticamente.

---

### Vantaggi Operativi

* **Stabilità dei riferimenti**: codice interno immutabile garantisce coerenza in interfacce e logica.
* **Integrità dei dati**: constraint e trigger impediscono codici duplicati o vuoti.
* **Audit completo**: tracciamento automatico delle modifiche.
* **Centralizzazione**: un’unica fonte per definire tutte le tipologie di contatto.

---

### Nota di refactor

In passato `config.tipi_contatti` veniva spesso usata come elenco dei reparti.
Con l'introduzione di `config.unita_organizzative`, il significato dei reparti
viene spostato su quella tabella, riducendo ambiguita semantiche.

---

> **“Una tabella di configurazione per i tipi di contatto assicura coerenza e stabilità nei riferimenti applicativi e semplifica la manutenzione delle logiche di contatto.”**
