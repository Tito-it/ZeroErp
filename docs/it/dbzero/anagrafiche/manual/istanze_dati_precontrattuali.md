## 📘 Documentazione Concettuale – Tabella `anagrafiche.istanze_dati_precontrattuali`

> 👀 **Vedi anche**
>
Guide generali:
>
[Generazione di un cliente](/guide/generazione-cliente)
>
Approfondimento tabelle:
>
[anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
> [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze)
> [config.classi_utenze](/dbzero/config/tabelle/classi_utenze)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> [vendite.regole_fatturazione_articolo](/dbzero/vendite/tabelle/articolo_regole_fatturazione)
>
### 🎯 Scopo Principale
(latest review 09-01-26)
La tabella `anagrafiche.istanze_dati_precontrattuali` raccoglie **tutte le informazioni pre‑contrattuali** relative ad una specifica **istanza utility** (fornitura/utenza). Il campo **`meta` (JSONB)** consente di archiviare attributi **specifici per tipo di utility** (es. potenza impegnata, pressione, soglie tecniche, parametri di profilazione).

Tali informazioni, una volta **caricate**, sono considerate **definitive** e:

* propagate al **contratto** (per la configurazione tecnica e commerciale),
* riutilizzate in **fatturazione** per i **calcoli di prezzo/consumi** quando rappresentano parametri tariffari.
* eventuali comunicazioni da sistemi esterni sono tracciate in tabelle dedicate, separate dal dato definitivo.

---

### Collegamenti con Altre Tabelle

| Campo                | Riferimento                         | Cardinalità | ON UPDATE | ON DELETE |
| -------------------- | ----------------------------------- | ----------- | --------- | --------- |
| `istanza_utility_id` | `anagrafiche.istanze_utilities(id)` | N:1         | CASCADE   | RESTRICT  |
| `utility_id`         | `config.utilities(id)`              | N:1         | CASCADE   | RESTRICT  |
| `classe_utenza_id`   | `config.classi_utenze(id)`          | N:1         | CASCADE   | RESTRICT  |

> **Nota**: le RESTRICT impediscono cancellazioni che lascerebbero orfani i dati pre‑contrattuali.
> Il **tipo utenza** è reperito tramite la classe (`config.classi_utenze.tipo_utenza_id`).

---

### Campi Chiave e Regole

* `param_1_num` / `param_2_txt` → placeholder **core** per parametri più comuni (es. **potenza impegnata**, **tensione/pressione**).
* `classe_utenza_id` → determina il **tipo utenza** tramite la relazione con `config.classi_utenze`.
* `meta JSONB` → estensioni **per‑utility** (chiavi definite dal dominio). Consigli:

  * versionare lo schema (`meta.schema_version`),
  * mantenere **descrizioni** sintetiche (`meta._descr`),
  * usare tipi nativi (numeri, boolean) per abilitare aggregazioni.
* Audit e tracciabilità: `tx_id`, `storicizza` (predefinito **true**), `data_*`, `user_*`.

---

### Vincoli & Integrità

* **PK**: `id`.
* **FK**: verso `istanze_utilities`, `utilities`, `tipi_utenze`, `classi_utenze` come da tabella collegamenti.
* **Solo col billing account della coppia** (dal 2026-10-08, `fk_idp_billing_account_coppia`): una riga per la coppia (istanza, utility) esiste solo se quella coppia ha il suo billing account. I dati precontrattuali sono **dati**, non dichiarano la utility dell'istanza: lo fa il billing account, che nasce con l'istanza. Fino a quel giorno una riga qui bastava a far nascere un'istanza senza BA. Vedi [Ogni istanza nasce col suo billing account](/it/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account).
* **Visibilità per azienda** (dal 2026-10-08, RLS `rls_istanze_dati_precontrattuali_ef_whitelist`): un operatore vede e scrive i dati precontrattuali solo se vede il billing account della loro coppia: la policy trova il BA con [`fn_get_ba_id_da_coppia`](/dbzero/script/manual/fn_get_ba_id_da_coppia) e calcola il perimetro dell'operatore una volta per istruzione (dal 2026-10-21). La vista `vw_istanze_dati_precontrattuali_dettaglio` è `security_invoker`, così non scavalca la regola.
* **Immutabilità consigliata**: i campi **sensibili** dovrebbero essere **bloccati** dopo il consolidamento applicativo (es. tramite trigger), salvo `meta` per correzioni controllate.

---


### Query Tipiche

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

### Esempi d’Uso (flusso)

1. **Inserimento**: arrivano dati da CRM/portale/api → popolazione campi base + `meta`.
2. **Validazione**: controlli automatici/umani (range, coerenza con `istanze_utilities`, esistenza codifiche).
3. **Consolidamento applicativo**: dati definitivi → disponibili per **contratto** e **fatturazione**.

---

### Best Practice

* Definisci un **mini‑schema per utility** (chiavi JSON standard, es. `elettrico.*`, `gas.*`).
* **Versiona** lo schema (`meta.schema_version`) e mantieni una pagina di mapping in documentazione.
* Valuta una **unique parziale** per `(istanza_utility_id, utility_id)` se serve vincolare una sola riga definitiva.
* Prevedi funzioni di **validazione** (PL/pgSQL) richiamate da job pgAgent.
* Evita DELETE; preferisci storicizzazione.

---

{% include-markdown "signature-core.md" %}

---
