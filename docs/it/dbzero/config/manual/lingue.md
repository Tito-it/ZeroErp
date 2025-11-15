## 📘 Documentazione Concettuale – Tabella `config.lingue`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
> Approfondimenti funzioni/trigger generici:
>
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)

---

La tabella **`config.lingue`** rappresenta il **dominio centralizzato delle lingue** gestite dal sistema, secondo gli standard ISO (principalmente **ISO 639-1** per la lingua e **ISO 3166-1** per la variante paese).

Questa tabella è utilizzata come riferimento per tutte le funzionalità di **localizzazione**, tra cui:

* messaggi di errore e di sistema,
* note e descrizioni multilingua,
* interfacce utente e documentazione generata.

---

### 🎯 Scopo Principale

* Definire l’elenco delle **lingue supportate** a livello di piattaforma Zero ERP.
* Fornire un **codice ISO univoco** per ogni lingua/variante (es. `it`, `en`, `de`, `it-IT`, `en-US`).
* Permettere la gestione di **descrizioni multilingua** in modo coerente e normalizzato (note, messaggi, label, ecc.).
* Abilitare scenari di **internazionalizzazione** (i18n) sia lato frontend che backend.

---

### 🔒 Vincoli e Regole Aziendali

* **Codice ISO** (`codice_iso`):

  * è **univoco** in tabella (`uq_cfg_lingue_codice_iso`);
  * deve rispettare il vincolo di lunghezza `chk_cfg_lingue_codice_iso_len` (min 2, max 5 caratteri);
  * segue convenzioni standard:

    * solo lingua: `it`, `en`, `de`, `fr`, `es`…
    * lingua + paese: `it-IT`, `en-US`, `de-CH`…

* **Descrizioni testuali**:

  * `descrizione`: nome della lingua in **italiano** (es. *Italiano*, *Inglese*, *Tedesco*).
  * `descrizione_locale`: nome della lingua nella **lingua stessa** (es. *Italiano*, *English*, *Deutsch*).
  * Servono per popolare in modo coerente combo, tabelle di configurazione e interfacce utente.

* **Stato di attivazione** (`attiva`):

  * indica se la lingua è **abilitata** per l’utilizzo nei processi applicativi;
  * l’indice `ix_cfg_lingue_attiva` ottimizza le query che filtrano solo le lingue attive (es. elenco lingue selezionabili da UI).

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` tracciano inserimenti e modifiche;
  * la gestione è centralizzabile tramite trigger generico di audit.

---

### 🔗 Relazioni

`config.lingue` viene tipicamente referenziata da tutte le entità che prevedono **contenuti multilingua**. Alcuni esempi:

* **Messaggi di sistema ed errori**:

  * tabelle come `config.messaggi_errore` possono avere un collegamento tra messaggio, lingua e testo tradotto;

* **Note e descrizioni parametrizzate**:

  * ambiti in cui la stessa informazione è disponibile in più lingue (es. descrizioni prodotto, note standard su documenti).

* **Preferenze utente o aziendali**:

  * impostazioni di lingua predefinita per utente, tenant, gestore, ecc.

> 🔁 La tabella `config.lingue` è un **building block** fondamentale per qualsiasi estensione futura di localizzazione (interfacce, stampe, reportistica, documentazione automatica).

---

### ⚙️ Trigger Associati

1. **Trigger di audit generico** (naming tipico: `trg_upd_lingue_audit_data_user`)

   * **Quando**: `BEFORE UPDATE`
   * **Cosa fa**:

     * aggiorna `data_update` e `user_update` ad ogni modifica;
   * **Come**:

     * invoca la funzione generica `script.trgfn_upd_audit_data_user_generic()` per uniformare la gestione dell’audit su tutte le tabelle di configurazione.

> ✅ In questo modo, ogni variazione alle lingue configurate è tracciabile, aspetto importante soprattutto in contesti multi-tenant o con requisiti di audit.

---

### 💡 Vantaggi Operativi

* **Centralizzazione**: un unico dominio per tutte le lingue usate in Zero ERP.
* **Coerenza**: utilizzo di codici ISO standard, riducendo gli errori di mapping verso sistemi esterni o librerie di internazionalizzazione.
* **Abilitazione i18n**: rende più semplice introdurre o estendere la localizzazione di:

  * messaggi di errore e di sistema;
  * etichette e testi UI;
  * documenti e report multilingua.
* **Governance**: la colonna `attiva` consente di limitare rapidamente le lingue supportate a quelle effettivamente gestite (es. solo `it` e `en` in una prima fase, con possibilità di estendere in futuro).

---

> 🧠 **“Un dominio lingue ben strutturato è il primo mattone per costruire un ERP realmente internazionale, senza dover stravolgere il modello dati in futuro.”**
