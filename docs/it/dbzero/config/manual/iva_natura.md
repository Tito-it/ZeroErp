## 📘 Documentazione Concettuale – Tabella `config.iva_natura`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:    
>
> * [config.iva](/dbzero/config/tabelle/iva)    
>
> Approfondimenti funzioni:   
>
> * [config.trgfn_iva_ins_upd_check_conti_iva](/dbzero/config/funzioni/trgfn_iva_ins_upd_check_conti_iva)    
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)     



La tabella **`config.iva_natura`** contiene i codici natura IVA utilizzati per l’inoltro delle fatture elettroniche al Sistema di Interscambio (SDI), abbinando ogni codice a una descrizione estesa.

---

### 🎯 Scopo Principale

* Fornire il **catalogo ufficiale** dei codici natura IVA previsti dalla normativa per le fatture elettroniche.
* Consentire il **mapping automatico** tra i record di `config.iva` e il codice natura da inviare al SDI.

---

### 🔒 Vincoli e Regole Aziendali

* **Unicità**: `codice` deve essere univoco nel catalogo.
* **Validità**: ogni codice  corrisponde a uno specifico significato fiscale, es. `N1` (Esportazioni), `N2` (Operazioni non imponibili), etc.
* **Audit**: ogni modifica al catalogo aggiorna automaticamente `data_update` e `user_update` tramite trigger.

---

### 🔗 Relazioni

* I record di `config.iva` referenziano `config.iva_natura(id)` per definire la natura fiscale da trasmettere al SDI.

---

### ⚙️ Trigger Associati

1. **`trg_upd_iva_natura_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: aggiorna automaticamente i campi di audit `data_update` e `user_update` tramite la funzione generica `script.trgfn_upd_audit_data_user_generic()`.

---

### 💡 Vantaggi Operativi

* **Conformità SDI**: assicura che tutte le fatture riportino codici natura conformi alle specifiche AgID.
* **Tracciabilità**: audit integrato per monitorare modifiche a codici e descrizioni.
* **Modularità**: eventuali aggiornamenti o estensioni dei codici natura richiedono solo modifiche a questa tabella.

---

> 🧠 **“Centralizzare i codici natura IVA in un catalogo dedicato semplifica la gestione dei flussi di fatturazione elettronica e garantisce compliance normativa.”**
