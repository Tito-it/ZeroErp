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

La tabella `anagrafiche.istanze_dati_precontrattuali` raccoglie **tutte le informazioni pre‑contrattuali** relative ad una specifica **istanza utility** (fornitura/utenza). Il campo **`meta` (JSONB)** consente di archiviare attributi **specifici per tipo di utility** (es. potenza impegnata, pressione, soglie tecniche, parametri di profilazione).

Tali informazioni vengono **validate** nel processo pre‑contrattuale e, una volta **confermate**, sono:

* propagate al **contratto** (per la configurazione tecnica e commerciale),
* riutilizzate in **fatturazione** per i **calcoli di prezzo/consumi** quando rappresentano parametri tariffari.

---

### 🔗 Collegamenti con Altre Tabelle

| Campo                | Riferimento                         | Cardinalità | ON UPDATE | ON DELETE |
| -------------------- | ----------------------------------- | ----------- | --------- | --------- |
| `istanza_utility_id` | `anagrafiche.istanze_utilities(id)` | N:1         | CASCADE   | RESTRICT  |
| `utility_id`         | `config.utilities(id)`              | N:1         | CASCADE   | RESTRICT  |
| `tipo_utenza_id`     | `config.tipi_utenze(id)`            | N:1         | CASCADE   | RESTRICT  |
| `classe_utenza_id`   | `config.classi_utenze(id)`          | N:1         | CASCADE   | RESTRICT  |

> **Nota**: le RESTRICT impediscono cancellazioni che lascerebbero orfani i dati pre‑contrattuali.

---

### 🧩 Campi Chiave e Regole

* `stato` → **`RICEVUTO` | `VALIDATO` | `CONSOLIDATO` | `SCARTATO`**
  Workflow di avanzamento tipico: *RICEVUTO → VALIDATO → CONSOLIDATO*.
* `param_1_num` / `param_2_txt` → placeholder **core** per parametri più comuni (es. **potenza impegnata**, **tensione/pressione**).
* `meta JSONB` → estensioni **per‑utility** (chiavi definite dal dominio). Consigli:

  * versionare lo schema (`meta.schema_version`),
  * mantenere **descrizioni** sintetiche (`meta._descr`),
  * usare tipi nativi (numeri, boolean) per abilitare aggregazioni.
* Audit e tracciabilità: `tx_id`, `storicizza` (predefinito **true**), `data_*`, `user_*`.

---

### 🧱 Vincoli & Integrità

* **PK**: `id`.
* **FK**: verso `istanze_utilities`, `utilities`, `tipi_utenze`, `classi_utenze` come da tabella collegamenti.
* **CHECK**: `chk_idp_stato` limita i valori ammessi di `stato`.
* **Immutabilità consigliata**: dopo `stato='CONSOLIDATO'` i campi **sensibili** dovrebbero essere **bloccati** (es. tramite trigger) salvo `meta` per correzioni controllate.

---

### ⚙️ Trigger & Automazioni

* `dbops.trgfn_tx_id_managed` → assegna `tx_id` su INSERT/UPDATE se nullo.
* `script.trgfn_upd_audit_data_user_generic` → aggiorna `data_update`/`user_update` su UPDATE.
* *(Consigliato)* `script.trgfn_upd_dlt_storico_generic('istanza_dati_precontrattuali_id')` → snapshot su UPDATE/DELETE quando `storicizza=true`.
* *(Facoltativo)* `trgfn_lock_when_consolidated` → blocca modifiche a campi core se `stato='CONSOLIDATO'` (eccetto campi note/amministrativi).

---

### 🔎 Query Tipiche

**1) Ultimo snapshot consolidato per istanza**

```sql
SELECT *
FROM anagrafiche.istanze_dati_precontrattuali idp
WHERE idp.istanza_utility_id = :istanza_id
  AND idp.utility_id = :utility_id
  AND idp.stato = 'CONSOLIDATO'
ORDER BY idp.data_update DESC
LIMIT 1;
```

**2) Avanzamento stato (VALIDATO → CONSOLIDATO)**

```sql
UPDATE anagrafiche.istanze_dati_precontrattuali
   SET stato = 'CONSOLIDATO',
       data_update = now()
 WHERE id = :id
   AND stato IN ('VALIDATO','RICEVUTO');
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
  AND idp.stato = 'CONSOLIDATO';
```

---

### 🧪 Esempi d’Uso (flusso)

1. **RICEVUTO**: arrivano dati da CRM/portale/api → popolazione campi base + `meta`.
2. **VALIDATO**: controlli automatici/umani (range, coerenza con `istanze_utilities`, esistenza codifiche).
3. **CONSOLIDATO**: congelamento parametri → disponibili per **contratto** e **fatturazione**.
4. **SCARTATO**: dati errati o incompleti → mantenuti per audit, esclusi dalla catena.

---

### ✅ Best Practice

* Definisci un **mini‑schema per utility** (chiavi JSON standard, es. `elettrico.*`, `gas.*`).
* **Versiona** lo schema (`meta.schema_version`) e mantieni una pagina di mapping in documentazione.
* Valuta una **unique parziale**: una riga consolidata per `(istanza_utility_id, utility_id)`.
* Prevedi funzioni di **validazione** (PL/pgSQL) richiamate da job pgAgent.
* Evita DELETE; preferisci **SCARTATO** oppure storicizzazione.

---

{% include-markdown "signature-core.md" %}

---
