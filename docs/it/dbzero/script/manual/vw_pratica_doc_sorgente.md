## 📘 Documentazione Concettuale – Vista `script.vw_pratica_doc_sorgente`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
> [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente)

---
### 🎯 Scopo Principale
(latest review 2026-07-02)
`script.vw_pratica_doc_sorgente` risolve, **per ogni pratica**, *quale documento*
rappresenta lo stato vivo della pratica, e ne proietta il descrittore normalizzato
(brief-db-proiezione-stato-dominio roll-out, deliverable D3b). Restituisce **una riga per
`pratica_id`**: il documento **più vivo** tra tutti i link della pratica (ROOT + COLLEGATO)
in `pratiche.pratiche_sorgenti`, con il descrittore letto da `script.vw_stato_sorgente`.

Promuove a livello DB la **regola d'ancora** che prima viveva solo nel frammento Python
`pratiche_repository._doc_sorgente_lateral`: sede **unica**, riusabile anche dalla futura
fase GUIDA (D4, "avanza-su-esito-proiettato").

---

### La regola d'ancora (priorità)

Tra i link della pratica si sceglie il primo per questo ordinamento:

| # | Criterio | SQL |
|---|----------|-----|
| 1 | **risolto** batte non-risolto | `COALESCE(ss.risolto, false) DESC` |
| 2 | **vivo** (non-terminale) batte terminale | `(NOT COALESCE(ss.terminale, false)) DESC` |
| 3 | **ROOT** come tiebreak | `(ps.ruolo_link = 'ROOT') DESC` |
| 4 | link **più recente** | `ps.id DESC` |

Perché serve (e perché la naive `ORDER BY (NOT terminale) DESC` è **sbagliata**):

* Una pratica evoluta **preventivo → ordine** ha il preventivo ROOT spesso già terminale
  (es. `EVASO`): con la sola àncora ROOT non si vedrebbe mai l'**ordine** `COLLEGATO` vivo.
  Il criterio 2 fa vincere l'ordine vivo (entrambi risolti, l'ordine non-terminale).
* Una pratica **preventivo → commessa** ha la commessa `COLLEGATO` **non risolta**
  (`PIPELINE_MARKER`, nessun resolver): il suo `terminale` è **NULL** e sotto `DESC` i NULL
  ordinano *per primi* → con la naive vincerebbe la commessa (**regressione**). Il criterio
  1 (risolto-first) e i `COALESCE` NULL-safe chiudono il buco: la commessa non risolta
  perde, il preventivo resta proiettato.

---

### 📑 Campi chiave esposti

* **Chiave**: pratica_id
* **Link scelto**: sorgente_tipo_id, sorgente_uid, ruolo_link, sorgente_descrizione
* **Risoluzione**: risolto (`false` se il documento scelto è di un dominio senza resolver)
* **Descrittore** (NULL se il link scelto non è risolto): stato_codice_interno,
  stato_codice, stato_descrizione, fase, esito, terminale

**Fallback**: coerente con il consumo BE odierno (non la sentinella `UNKNOWN` dello scalare
`fn_stato_sorgente`). Link scelto non risolto → `risolto=false` e campi `stato_*` NULL (il
FE mostra il milestone come oggi). Pratica **senza link** → nessuna riga (il consumer in
LEFT JOIN ottiene NULL).

---

### Esempio d'uso

```sql
-- Dettaglio/lista pratiche: descrittore del documento vivo, una riga per pratica.
SELECT p.id, d.stato_descrizione, d.fase, d.esito, d.terminale, d.risolto
FROM pratiche.pratiche p
LEFT JOIN script.vw_pratica_doc_sorgente d ON d.pratica_id = p.id
WHERE p.id = 42;
```

---

### Note operative

* Il **percorso/coda** per-flusso continua ad ancorare per `flusso_id` (invariato): questa
  vista serve l'àncora **a livello pratica** (dettaglio/lista), dove un ordine/commessa
  `COLLEGATO` senza `flusso_id` altrimenti non si vedrebbe.
* Placement `script` (layer applicativo cross-dominio), coerente con `vw_stato_sorgente`.
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql` (casi 25-28, incl. la
  regressione preventivo→commessa).

---

{% include-markdown "signature-core.md" %}
