## 📘 Documentazione Concettuale – Tabella `vendite.articoli_gruppi`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [vendite.articoli](/dbzero/vendite/tabelle/articoli)
>
> Approfondimenti funzioni:
>
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)

La tabella **`vendite.articoli_gruppi`** gestisce la classificazione di **livello superiore** degli articoli.
Ogni gruppo rappresenta un insieme logico di articoli con finalità di catalogazione, controllo gestionale, reporting e totalizzazione nei documenti di vendita e fatturazione.

---

### 🎯 Scopo Principale

* Consentire la **classificazione gerarchica** degli articoli in gruppi omogenei.
* Facilitare **statistiche e analisi di vendita** per categoria.
* Supportare **criteri di stampa e raggruppamento** nei documenti fiscali e gestionali.
* Offrire un **meccanismo di attivazione/disattivazione** senza perdere lo storico.

---

### 🔒 Vincoli e Logiche Aziendali

* **Unicità**: ogni gruppo ha un `codice` univoco.
* **Obbligatorietà**: `descrizione` deve sempre essere valorizzata.
* **Attivazione**: il flag `attivo` consente di marcare i gruppi obsoleti senza eliminarli.
* **Audit automatico**: i campi `user_insert`, `user_update`, `data_insert`, `data_update` vengono gestiti automaticamente.

---

### 🔗 Relazioni e Indici

* **Indice univoco**: `uq_articoli_gruppi_codice` garantisce l’unicità del codice.
* **Indice funzionale**: `ix_articoli_gruppi_codice_upper` abilita ricerche case-insensitive sul campo `codice`.
* **Relazioni**: utilizzata come riferimento in `vendite.articoli` per la classificazione.

---

### ⚙️ Trigger Associati

* **`trg_upd_articoli_gruppi_audit_data_user`**

  * **Quando**: `BEFORE UPDATE`
  * **Cosa**: aggiorna in automatico `data_update` e `user_update` tramite la funzione generica `script.trgfn_upd_audit_data_user_generic()`.

---

### 💡 Vantaggi Operativi

* **Gestione flessibile**: possibilità di attivare/disattivare gruppi senza perdita dati.
* **Supporto analitico**: agevola la produzione di report per categorie merceologiche.
* **Allineamento documentale**: semplifica la stampa di riepiloghi e la totalizzazione di righe di fattura.
* **Governance**: garantisce consistenza e integrità logica sugli articoli.

---

> 🧠 **“I gruppi articoli costituiscono il primo livello di classificazione, abilitando una visione aggregata e coerente delle vendite.”**
