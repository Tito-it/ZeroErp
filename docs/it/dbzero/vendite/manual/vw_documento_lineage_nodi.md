## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage_nodi`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi)
> [vendite.vw_documento_lineage](/dbzero/vendite/views/vw_documento_lineage)
> [config/manual/sorgenti.md — Convenzione chiave sorgente](/dbzero/config/manual/sorgenti)

---

### 🎯 Scopo Principale

`vendite.vw_documento_lineage_nodi` è la **dimensione nodo** del grafo di genealogia
dei documenti vendite (brief-db-lineage-documenti-vendite): **una riga per documento**
delle 8 testate-nodo (preventivo, offerta, ordine, contratto, DDT, fattura, commessa,
reso), con la **chiave nativa polimorfa** e lo **stato/fase normalizzati**.

È il **mattone condiviso** dei tre consumatori del lineage — la vista archi la usa per
decorare i nodi target, la summary `vw_documento_lineage` come base e per la fase
propria, la funzione `fn_documento_lineage` per gli attributi nodo — così la union delle
8 testate è scritta **una volta sola** (no duplicazione).

---

### 🔑 Chiave nodo (polimorfa)

La chiave è `(tipo_id, uid)` **secondo `config.sorgenti.key_selector`** — è la stessa
identità già usata da `pratiche_sorgenti`, `commesse_sorgenti`, `vw_stato_sorgente_*`:

| `key_selector` | Tipi | `uid` esposto |
|---|---|---|
| `uid` | PREVENTIVO, OFFERTA_COMMERCIALE | `(uid)::text` |
| `id` | ORDINE_VENDITA, CONTRATTO, DDT_VENDITA, FATTURA, COMMESSA, RESO_VENDITA | `(id)::text` |

Il `tipo_id` è **sempre risolto per JOIN a `config.sorgenti` su `codice_interno`**
(chiave stabile, linee-guida-sql §6b/§6d) — mai un id numerico letterale.

---

### 📑 Campi chiave esposti

* **Chiave**: `tipo_id`, `uid`
* **Etichetta**: `codice` (display del documento: `numero` per preventivi/ordini/
  contratti/ddt/resi e fattura; `codice` per offerte/commesse)
* **Stato nativo**: `stato_codice_interno` (logica, immutabile), `stato_codice` +
  `stato_descrizione` (display) — alias **fedeli** alla sorgente (§6c)
* **Proiezione**: `fase` (`APERTO`/`IN_ATTESA`/`IN_CORSO`/`CHIUSO`), `is_abortito`
* **`pipeline_rank`**: posizione del tipo nel flusso verso la fattura (crescente = più
  a valle): `1` preventivo/offerta · `2` ordine/contratto · `3` ddt · `4` commessa ·
  `5` fattura · `0` reso. Usato dalla summary come tie-break della frontiera.

---

### Esempio d'uso

```sql
-- Stato normalizzato di un documento per chiave nodo.
SELECT codice, stato_codice_interno, fase, is_abortito
FROM vendite.vw_documento_lineage_nodi
WHERE tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA')
  AND uid = '163';   -- id::text per gli ordini
```

---

### Note operative

* **Una riga per documento**, anche per i nodi isolati (senza lineage): la summary vi si
  appoggia per avere sempre la riga del documento.
* **`LEFT JOIN` allo stato**: difensivo su `fatture.stato_doc_fiscale_id` (nullable).
* **`security_invoker=on`**: la vista applica la RLS emittente del **chiamante** (come la
  famiglia `vw_dash_*`); il backend non passa `auth_user_id`. La reloption **non** è
  visibile in `pg_get_viewdef` e va ri-specificata ad ogni `CREATE OR REPLACE`.
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---

{% include-markdown "signature-core.md" %}
