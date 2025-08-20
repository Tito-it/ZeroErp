## 📘 Documentazione Concettuale – Tabella `vendite.regole_fatturazione_articolo`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>
> Approfondimenti funzioni:
>
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)

La tabella **`vendite.regole_fatturazione_articolo`** contiene le regole di fatturazione e di calcolo specifiche per ogni articolo del catalogo. Serve a stabilire come vengono visualizzati i componenti, come si calcola la quantità e come vengono gestiti gli arrotondamenti di importi e quantità.

---

### 🎯 Scopo Principale

* Definire le **policy di calcolo** per ogni articolo.
* Stabilire la **visibilità** dei componenti di un articolo complesso (solo padre, padre+componenti, solo componenti).
* Impostare la logica di **calcolo della quantità del padre** (fissa o somma di componenti flaggati).
* Definire regole di **arrotondamento** per importi e quantità.
* Consentire estensioni tramite il campo JSONB `meta`.

---

### 🔒 Vincoli e Logiche Aziendali

* **Unicità**: ogni articolo (`prodotto_id`) può avere una sola regola associata.
* **Visibilità componenti**: valori ammessi → `solo_padre`, `padre_componenti`, `solo_componenti`.
* **Calcolo quantità padre**: valori ammessi → `fissa`, `somma_componenti_flaggate`.
* **Arrotondamento**:

  * Decimali importi → da `0` a `6`.
  * Decimali quantità → da `0` a `6`.
  * Metodo → `HALF_UP`, `HALF_EVEN`, `FLOOR`, `CEIL`.
* **Storicizzazione**: il flag `storicizza` abilita la registrazione delle modifiche.

---

### 🔗 Relazioni e Indici

* **FK**: `prodotto_id` → `catalogo.articoli.id`.
* **Indice**: `ix_regole_fatturazione_articolo_prodotto` su `prodotto_id` per lookup veloce.

---

### ⚙️ Trigger Associati

* **`trg_upd_regole_fatturazione_articolo_audit_data_user`**

  * **Quando**: `BEFORE UPDATE`
  * **Cosa**: aggiorna automaticamente `data_update` e `user_update` tramite la funzione `script.trgfn_upd_audit_data_user_generic()`.

---

### 💡 Vantaggi Operativi

* **Personalizzazione**: permette di gestire regole diverse per articoli differenti.
* **Flessibilità**: supporto a più logiche di calcolo e arrotondamento.
* **Governance**: garantisce tracciabilità e storicizzazione delle regole applicate.

---

> 🧠 **“Centralizzare le regole di fatturazione a livello di articolo riduce errori e assicura uniformità nei processi di calcolo e documentazione fiscale.”**
