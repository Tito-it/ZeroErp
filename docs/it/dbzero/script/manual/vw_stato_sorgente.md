## 📘 Documentazione Concettuale – Vista `script.vw_stato_sorgente`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.vw_stato_sorgente_preventivo](/dbzero/vendite/views/vw_stato_sorgente_preventivo)
> [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)

---
### 🎯 Scopo Principale
(latest review 01-07-2026)
`script.vw_stato_sorgente` è la **union dei resolver di dominio** della proiezione stato
(brief-db-proiezione-stato-dominio, deliverable D3): è l'**unica superficie di dispatch**
— niente `resolver_key`, niente CASE statico. Un tipo sorgente senza ramo semplicemente
**non ha righe** = non risolto: il wrapper `pratiche.fn_stato_sorgente` degrada a
`UNKNOWN` e il milestone resta manuale come oggi.

Vive in `script` (layer applicativo riusabile) per non costringere a editare l'engine
(`pratiche`) a ogni nuovo dominio: layering `pratiche → script → dominio`.

---

### Rami (resolver di dominio)

| Ramo | Dominio | Registrato |
|------|---------|-----------|
| `vendite.vw_stato_sorgente_preventivo` | PREVENTIVI | 2026-07-01 |
| `vendite.vw_stato_sorgente_offerta` | OFFERTA | 2026-07-02 |
| `vendite.vw_stato_sorgente_ordine` | ORDINE (vendita) | 2026-07-02 |
| `vendite.vw_stato_sorgente_contratto` | CONTRATTO | 2026-07-02 |

Ogni ramo aggancia il proprio `sorgente_tipo_id` via `config.sorgenti.codice_interno`
(mai id letterale) e rispetta il contratto **al più una riga per (tipo, uid)**. La
COMMESSA resta fuori (è un `PIPELINE_MARKER`, non ha `stati_doc_*` a ciclo-vita): un tipo
senza ramo semplicemente non ha righe = non risolto.

---

### 📑 Campi chiave esposti

Il **descrittore universale** (contratto §4 del brief design), tipi normalizzati a `text`:

* **Chiave**: sorgente_tipo_id, sorgente_uid
* **Chiave nel suo tipo** (dal 2026-10-05, in coda): sorgente_chiave_uuid (rami con
  `key_selector = uid`) e sorgente_chiave_id (rami con `key_selector = id`). In ogni riga
  una sola è valorizzata, e coincide con `sorgente_uid`. Servono a **cercare un documento**:
  sotto RLS il confronto sulla forma testuale non può usare l'indice (le conversioni
  `uuid → text` e `bigint → text` non sono `leakproof`), quello sulla chiave nativa sì.
  `pratiche.fn_stato_sorgente` cerca su queste; `sorgente_uid` resta la chiave delle join
  con `pratiche_sorgenti` e del lineage.
* **Risoluzione**: risolto (sempre `true` sulle righe proiettate; il fallback `UNKNOWN`
  con `risolto=false` lo produce solo `fn_stato_sorgente`)
* **Stato nativo**: stato_codice_interno (logica), stato_codice / stato_descrizione (display)
* **Proiezione normalizzata**: fase, esito (verdetto `is_verdetto=true` o NULL), terminale

---

### Esempio d'uso

```sql
-- Liste (niente N+1): descrittore per ogni sorgente di una pratica.
SELECT ps.pratica_id, ps.ruolo_link, v.fase, v.esito, v.terminale, v.risolto
FROM pratiche.pratiche_sorgenti ps
LEFT JOIN script.vw_stato_sorgente v
       ON v.sorgente_tipo_id = ps.sorgente_tipo_id
      AND v.sorgente_uid     = ps.sorgente_uid
WHERE ps.pratica_id = 42;
-- riga v.* NULL = dominio senza resolver (non risolto)
```

---

### Note operative — registrare un nuovo dominio

1. Il dominio dichiara la mappa `fase`/`esito`/`terminale` sulle proprie
   `config.stati_doc_<dominio>` (D1) e crea il resolver `<schema>.vw_stato_sorgente_<tipo>`
   (D2) con le **stesse colonne** e il contratto "al più una riga per (tipo, uid)".
   ⚠️ Comprese le due colonne in coda: il ramo valorizza quella della sua specie di
   chiave (`uid` o `id`) e mette l'altra a `NULL` tipizzato. Un ramo che le lasciasse
   entrambe a `NULL` comparirebbe nella vista ma `fn_stato_sorgente` non lo troverebbe mai.
2. Si aggiunge un ramo con un **nuovo changeset** (mai modificare quello già mergiato):

```sql
CREATE OR REPLACE VIEW script.vw_stato_sorgente AS
SELECT ... FROM vendite.vw_stato_sorgente_preventivo r   -- ramo esistente
UNION ALL
SELECT
    r.sorgente_tipo_id, r.sorgente_uid, true AS risolto,
    (r.stato_codice_interno)::text, (r.stato_codice)::text,
    (r.stato_descrizione)::text, (r.fase)::text, (r.esito)::text, r.terminale,
    r.sorgente_chiave_uuid, r.sorgente_chiave_id
  FROM vendite.vw_stato_sorgente_offerta r;               -- nuovo ramo
```

Nessun'altra modifica al motore: `pratiche.fn_stato_sorgente` e i consumer restano invariati.

* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

{% include-markdown "signature-core.md" %}
