## 📘 Documentazione Concettuale – Tabella `anagrafiche.istanze_dati_precontrattuali`

> 👀 **Vedi anche**
>
> Guide generali:
>
> * [Generazione di un cliente](/guide/generazione-cliente)
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> * [config.utilities](/dbzero/config/tabelle/utilities)
> * [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)
> * [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> * [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> * [vendite.regole_fatturazione_articolo](/dbzero/vendite/tabelle/regole_fatturazione_articolo)
>
> Trigger/Funzioni correlate:
>
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)
> * [script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)

---

### 🎯 Scopo Principale

(last review 09-01-26)
La tabella `anagrafiche.istanze_dati_precontrattuali` raccoglie **tutte le informazioni pre‑contrattuali** relative ad una specifica **istanza utility** (fornitura/utenza). Il campo **`meta` (JSONB)** consente di archiviare attributi **specifici per tipo di utility** (es. potenza impegnata, pressione, soglie tecniche, parametri di profilazione).

Tali informazioni, una volta **caricate**, sono considerate **definitive** e:

* propagate al **contratto** (per la configurazione tecnica e commerciale),
* riutilizzate in **fatturazione** per i **calcoli di prezzo/consumi** quando rappresentano parametri tariffari.
* eventuali comunicazioni da sistemi esterni sono tracciate in tabelle dedicate, separate dal dato definitivo.

---

### 🔗 Collegamenti con Altre Tabelle

| Campo                | Riferimento                         | Cardinalità | ON UPDATE | ON DELETE |
| -------------------- | ----------------------------------- | ----------- | --------- | --------- |
| `istanza_utility_id` | `anagrafiche.istanze_utilities(id)` | N:1         | CASCADE   | RESTRICT  |
| `utility_id`         | `config.utilities(id)`              | N:1         | CASCADE   | RESTRICT  |
| `classe_utenza_id`   | `config.classi_utenze(id)`          | N:1         | CASCADE   | RESTRICT  |

> **Nota**: le RESTRICT impediscono cancellazioni che lascerebbero orfani i dati pre‑contrattuali.
> Il **tipo utenza** è reperito tramite la classe (`config.classi_utenze.tipo_utenza_id`).

---

### 🧩 Campi Chiave e Regole

* `param_1_num` / `param_2_txt` → placeholder **core** per parametri più comuni (es. **potenza impegnata**, **tensione/pressione**).
* `classe_utenza_id` → determina il **tipo utenza** tramite la relazione con `config.classi_utenze`.
* `meta JSONB` → estensioni **per‑utility** (chiavi definite dal dominio). Consigli:

  * versionare lo schema (`meta.schema_version`),
  * mantenere **descrizioni** sintetiche (`meta._descr`),
  * usare tipi nativi (numeri, boolean) per abilitare aggregazioni.
* Audit e tracciabilità: `tx_id`, `storicizza` (predefinito **true**), `data_*`, `user_*`.

---

### 🧱 Vincoli & Integrità

* **PK**: `id`.
* **FK**: verso `istanze_utilities`, `utilities`, `tipi_utenze`, `classi_utenze` come da tabella collegamenti.
* **Immutabilità consigliata**: i campi **sensibili** dovrebbero essere **bloccati** dopo il consolidamento applicativo (es. tramite trigger), salvo `meta` per correzioni controllate.

---

### ⚙️ Trigger & Automazioni

* `dbops.trgfn_tx_id_managed` → assegna `tx_id` su INSERT/UPDATE se nullo.
* `script.trgfn_upd_audit_data_user_generic` → aggiorna `data_update`/`user_update` su UPDATE.
* *(Consigliato)* `script.trgfn_upd_dlt_storico_generic('istanza_dati_precontrattuali_id')` → snapshot su UPDATE/DELETE quando `storicizza=true`.
* *(Facoltativo)* `trgfn_lock_after_consolidation` → blocca modifiche a campi core dopo il consolidamento applicativo (eccetto campi note/amministrativi).

---

### 🔎 Query Tipiche

**1) Ultimo snapshot per istanza**

```sql
SELECT *
FROM anagrafiche.istanze_dati_precontrattuali idp
WHERE idp.istanza_utility_id = :istanza_id
  AND idp.utility_id = :utility_id
ORDER BY idp.data_update DESC
LIMIT 1;
```

**2) Aggiornamento dati tecnici**

```sql
UPDATE anagrafiche.istanze_dati_precontrattuali
   SET data_update = now()
 WHERE id = :id
;
```

**3) Upsert di un attributo tecnico in `meta`**

```sql
UPDATE anagrafiche.istanze_dati_precontrattuali
   SET meta = jsonb_set(meta, '{elettrico,potenza_impegnata_kw}', to_jsonb(:kw)::jsonb, true),
       data_update = now()
 WHERE id = :id;
```

**4) Ricavo parametri per pricing in fatturazione**

```sql
SELECT c.id AS contratto_id,
       idp.meta -> 'elettrico' ->> 'potenza_impegnata_kw' AS pot_kw
FROM vendite.contratti c
JOIN anagrafiche.istanze_dati_precontrattuali idp
  ON idp.istanza_utility_id = c.istanza_utility_id
WHERE c.id = :contratto_id
;
```

---

### 🧪 Esempi d’Uso (flusso)

1. **Inserimento**: arrivano dati da CRM/portale/api → popolazione campi base + `meta`.
2. **Validazione**: controlli automatici/umani (range, coerenza con `istanze_utilities`, esistenza codifiche).
3. **Consolidamento applicativo**: dati definitivi → disponibili per **contratto** e **fatturazione**.

---

### ✅ Best Practice

* Definisci un **mini‑schema per utility** (chiavi JSON standard, es. `elettrico.*`, `gas.*`).
* **Versiona** lo schema (`meta.schema_version`) e mantieni una pagina di mapping in documentazione.
* Valuta una **unique parziale** per `(istanza_utility_id, utility_id)` se serve vincolare una sola riga definitiva.
* Prevedi funzioni di **validazione** (PL/pgSQL) richiamate da job pgAgent.
* Evita DELETE; preferisci storicizzazione.

---

{% include-markdown "signature-core.md" %}

---
