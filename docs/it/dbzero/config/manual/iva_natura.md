## 📘 Documentazione Concettuale – Tabella `config.iva_natura`

> **Ultimo aggiornamento**: 13 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti tabelle:    
>
[config.iva](/dbzero/config/tabelle/iva)    
>
Approfondimenti funzioni:   
>
[config.trgfn_iva_ins_upd_check_conti_iva](/dbzero/config/funzioni/trgfn_iva_guard_conti_iva)    
> [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)     



La tabella **`config.iva_natura`** contiene i codici natura IVA utilizzati per l’inoltro delle fatture elettroniche al Sistema di Interscambio (SDI), abbinando ogni codice a una descrizione estesa.

---
### 🎯 Scopo Principale
* Fornire il **catalogo ufficiale** dei codici natura IVA previsti dalla normativa per le fatture elettroniche.
* Consentire il **mapping automatico** tra i record di `config.iva` e il codice natura da inviare al SDI.

---

### Vincoli e Regole Aziendali

* **Unicità**: `codice` deve essere univoco nel catalogo.
* **Validità**: ogni codice  corrisponde a uno specifico significato fiscale, es. `N1` (Esportazioni), `N2` (Operazioni non imponibili), etc.
* **Audit**: ogni modifica al catalogo aggiorna automaticamente `data_update` e `user_update` tramite trigger.
  Dal 2026-11-13 `user_insert` è `NOT NULL DEFAULT CURRENT_USER` (linee-guida-sql §7,
  `90_end/20261112-54`): il seed non porta più le colonne di audit, e una natura nuova registra chi
  l'ha inserita.
* ⭐ **`is_reverse_charge`** (dal 2026-08-29): dice se quella natura è
  un'**inversione contabile**, cioè se l'imposta la assolve chi riceve invece di
  chi emette. Sono le nature `N6.1`…`N6.9` — rottami, oro, subappalto edile,
  fabbricati, cellulari, prodotti elettronici, comparto edile, settore
  energetico, altri casi.
  ⛔ **E non si deduce da `codice LIKE 'N6%'`**: sarebbe un letterale su una
  colonna di catalogo, che al primo rename smette di agganciarsi **in silenzio** —
  su un flag fiscale.
  ⚠️ È `NOT NULL` **senza default**: chi conia una natura nuova deve **dire** di
  che specie è. Con un default lo erediterebbe per distrazione, e la
  classificazione sbagliata si vedrebbe solo su una fattura elettronica
  rifiutata.
  ℹ️ Sta sulla **natura** e non sul singolo codice IVA perché `N6.x` *è*
  l'inversione contabile: su `config.iva` andrebbe ripetuto su ogni codice che
  porta quella natura, col rischio che due codici della stessa natura dicano cose
  diverse.
* **`storicizza`**: dal 2026-08-29 la tabella ha una gemella in `storico`.

---

### Relazioni

* I record di `config.iva` referenziano `config.iva_natura(id)` per definire la natura fiscale da trasmettere al SDI.

---

### Trigger Associati

1. **`trg_upd_iva_natura_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: aggiorna automaticamente i campi di audit `data_update` e `user_update` tramite la funzione generica `script.trgfn_audit_data_user_generic()`.

---

### Vantaggi Operativi

* **Conformità SDI**: assicura che tutte le fatture riportino codici natura conformi alle specifiche AgID.
* **Tracciabilità**: audit integrato per monitorare modifiche a codici e descrizioni.
* **Modularità**: eventuali aggiornamenti o estensioni dei codici natura richiedono solo modifiche a questa tabella.

---

> **“Centralizzare i codici natura IVA in un catalogo dedicato semplifica la gestione dei flussi di fatturazione elettronica e garantisce compliance normativa.”**
