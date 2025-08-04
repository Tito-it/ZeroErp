## 📘 Documentazione Concettuale – Tabella `anagrafiche.billing_account`

> 👀 **Vedi anche**
> 
> Guide generali: 
>  * [Generazione di un cliente](/guide/generazione-cliente)
> 
> * Approfondimento tabelle :
>
>   * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>   * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
>   * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>   * [config.utilities](/dbzero/config/tabelle/utilities)
>
> Approfondimeto funzioni:
>
> * [anagrafiche.trgfn_billing_account_ins_upd_clean_fields](/dbzero/anagrafiche/funzioni/trgfn_billing_account_ins_upd_clean_fields)
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)
---

### 🎯 Scopo Principale

La tabella `anagrafiche.billing_account` mantiene lo **storico dei codici cliente** per ciascuna `utility`, consentendo:

* **Generazione anticipata** del `account_code` in fase precontrattuale.
* **Unicità di `account_code`** grazie al vincolo `uq_billing_account_code`.
* **Unicità per istanza+utility**: non possono esistere due record con la stessa coppia (`istanza_utility_id`, `utility_id`).
* **Strutture gerarchiche** dei codici tramite `parent_account_id`, utile per Modellare:

  * Holding e consociate (stesso soggetto con codici distinti).
  * Suddivisioni interne (dipartimenti, filiali).
  * Codici sostitutivi o di aggiornamento, mantenendo la tracciabilità storica.

---

La tabella `anagrafiche.billing_account` mantiene lo **storico dei codici cliente** per ciascuna `utility`, consentendo:

* Generazione anticipata del `account_code` in fase precontrattuale
* Gestione di più codici nel tempo tramite il campo `parent_account_id`
* Unicità per coppia `istanza_utility_id` + `utility_id`

---

### 🔗 Collegamenti con Altre Tabelle

| Campo                | Tabella di riferimento              | Azione                                |
| -------------------- | ----------------------------------- | ------------------------------------- |
| `istanza_utility_id` | `anagrafiche.istanze_utilities(id)` | ON UPDATE CASCADE, ON DELETE SET NULL |
| `soggetto_ruolo_id`  | `anagrafiche.soggetti_ruoli(id)`    | ON UPDATE CASCADE, ON DELETE RESTRICT |
| `utility_id`         | `config.utilities(id)`              | ON UPDATE CASCADE, ON DELETE RESTRICT |
| `parent_account_id`  | `anagrafiche.billing_account(id)`   | ON UPDATE CASCADE, ON DELETE SET NULL |

---

### 🚩 Regole di Validazione Condizionale

1. **Unicità account**

   * `account_code` deve essere univoco (`uq_billing_account_code`).
2. **Unicità per istanza-utility**

   * Non possono esistere due billing account per la stessa coppia (`istanza_utility_id`, `utility_id`).
3. **Range di validità**

   * `valid_from` obbligatorio, `valid_to` opzionale, permette definire periodi di validità distinti.

---

### 🔍 Indicizzazione

* **`ix_billing_account_parent_account_id`**: supporta gerarchie di account tramite `parent_account_id`.
* **`ix_billing_account_soggetto_ruolo_id`**: ricerca dei codici per soggetto.
* **`ix_billing_account_utility_id`**: filtri per tipo di servizio.

---

### 💡 Vantaggi Operativi

* **Fatturazione precontrattuale**: abilita la generazione di codici cliente anche prima della definizione formale del cliente.
* **Storico codici**: gestisce cambi di codifica via `parent_account_id`, mantenendo tracciamento.
* **Integrità**: vincoli e indici garantiscono univocità e coerenza referenziale.

---

### ⚙️ Implementazioni Aggiuntive

* `trg_billing_account_ins_upd_gen_account_code` genera automaticamente `account_code` se non specificato.
* `trg_upd_billing_account_audit_data_user` tiene traccia delle modifiche audit.

---

### ✅ Controlli di Coerenza

* `istanza_utility_id` e `utility_id` non possono essere duplicati per lo stesso billing account.
* `account_code` generato via trigger evita collisioni manuali.
* `parent_account_id` consente strutture di sub-account, ma evita loop grazie al vincolo di PK.

---

### 🧾 Note Finali

La tabella `billing_account` è cruciale per separare il **codice di fatturazione** dal cliente contrattuale, offrendo flessibilità e storicità nei rapporti con le diverse utilities.

{% include-markdown "signature-core.md" %}
