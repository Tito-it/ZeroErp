## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_ordini`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
>
> Approfondimento funzioni:
>
> [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine)
> [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione)
>
> Pattern correlato (domini gemelli):
>
> [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti)
> [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)

---

### 🎯 Scopo Principale

(rev 2026-06-05)

`config.transizioni_stati_ordini` definisce la **matrice delle transizioni ammesse**
tra gli stati dell'ordine di vendita, con i relativi **metadati UI**. Chiude l'ultimo
outlier documentale: prima di questa rev l'ordine era l'unico documento vendite **senza
matrice transizioni** (preventivi/offerte/contratti la avevano già), con azioni e
capacità calcolate a mano nel backend Python.

La tabella ha **doppio ruolo** (a differenza dei gemelli, dove il grafo è hardcodato nel
trigger):

1. **Fonte metadati UI** per `script.fn_available_actions_ordine`, che la legge per
   costruire `available_actions[]` nel payload del detail endpoint BE.
2. **Grafo di enforcement** per `vendite.trgfn_ordini_guard_transizione`, che valida
   ogni cambio di stato leggendo questa tabella (vero *single source of truth*).

> **Nota architetturale** — Mentre `trgfn_contratti_guard_transizione_stato` e
> `trgfn_offerte_commerciali_guard_transizione` codificano il grafo **dentro** il trigger
> (la tabella serve solo per la UI), per gli ordini il guard **legge la matrice**: una
> sola fonte verità sia per "cosa è ammesso" sia per "come si presenta al FE". Scelta
> coerente con lo scopo SSOT del refactor.

---

### Matrice transizioni configurata

| id | Da stato | A stato | Attivo | Manuale | Descrizione |
|----|----------|---------|:------:|:-------:|-------------|
| 1 | DRAFT (1) | CONFERMATO (2) | Sì | Sì | Conferma ordine; il guard richiede ≥1 riga. Con la stampa documentale, genera anche il documento |
| 2 | DRAFT (1) | ANNULLATO (6) | Sì | Sì | Annullo bozza; ammesso sempre (nessuna evasione su DRAFT) |
| 3 | CONFERMATO (2) | ANNULLATO (6) | **No** | Sì | Riga presente ma **disabilitata**: un ordine confermato non si annulla da interfaccia |

```text
DRAFT ──────> CONFERMATO        (avanzamento a valle: ALLOCATO/SPEDITO/... fuori matrice)
  │
  └──> ANNULLATO                (terminale)

CONFERMATO ┄┄> ANNULLATO        (attivo=false: documenta il grafo, bloccata dal guard)
```

**Decisioni di dominio (ratificate Tid 2026-06-05):**

- **`CONFERMATO → ANNULLATO` con `attivo=false`** — riga in matrice ma disabilitata.
  Riabilitabile in futuro con regola "annullabile se non evaso/fatturato a valle"
  (cross-domain check analogo a `fn_cambia_stato_preventivo`). Per ora un ordine
  confermato non si annulla con un click — pattern coerente con preventivi (annulli a
  valle disattivati) e contratti (l'attivo si cessa, non si annulla).
- **Stati a valle FUORI matrice** — `ALLOCATO / SPEDITO / CONSEGNATO / FATTURATO` esistono
  in `config.stati_doc_ordini` ma **non vengono raggiunti da alcun processo sull'ordine**:
  quelle stringhe vivono solo negli stati DDT e nel `fatturazione_trigger` (che dice
  *quando* fatturare in base allo stato del **DDT**, non dell'ordine). Il push a commessa
  crea entità DDT/commessa separate; l'ordine resta CONFERMATO. Saranno aggiunti alla
  matrice quando magazzino/DDT ne saranno i driver effettivi.

**`push_commessa` non è una transizione di stato:** è un'azione applicativa a sé
(l'ordine resta CONFERMATO), gestita come azione hardcoded in
`fn_available_actions_ordine`, non come riga di questa matrice — come `push_commessa`
dei preventivi e `push_contratto` delle offerte.

---

### Campo `meta` — metadati UI

Il campo `meta jsonb NOT NULL DEFAULT '{}'` porta i metadati letti da
`script.fn_available_actions_ordine`.

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `action_key` | `text` | Chiave semantica dell'azione (es. `conferma`, `annulla`) |
| `label_key` | `text` | Chiave i18n per il label del bottone Vue (`$t(label_key)`) |
| _(icona e colore)_ | — | Non sono dati del DB: il frontend li sceglie dall'`action_key` (mappa verbo → aspetto in `core/`, icona e `severity`). Il colore è uscito dal `meta` il 2026-09-28 |
| `requires_confirm` | `boolean` | `true` → dialog di conferma prima di eseguire |
| `outlined` | `boolean` | `true` → bottone PrimeVue variante outlined (usato su `annulla`) |
| `manuale` | `boolean` | `false` = transizione automatica (job/processo); esclusa dalla lista UI. Default: `true` |

**Valori seed correnti (rev 2026-06-05):**

| id | Transizione | action_key | requires_confirm | outlined | attivo |
|----|-------------|-----------|:---:|:---:|:---:|
| 1 | DRAFT → CONFERMATO | `conferma` | `true` | `false` | `true` |
| 2 | DRAFT → ANNULLATO | `annulla` | `true` | `true` | `true` |
| 3 | CONFERMATO → ANNULLATO | `annulla` | `true` | `true` | `false` |

> Differenza dagli ordini rispetto a contratti: nessuna azione con `requires_date`
> (la cessazione programmata non esiste nel workflow ordine).

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_transizioni_stati_ordini` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola riga per coppia |
| `ck_transizioni_stati_ord_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |
| `ck_transizioni_stati_ord_meta_ui` | CHECK | Ogni transizione **manuale** deve avere `action_key` + `label_key` nel `meta` (le automatiche, `manuale=false`, ne sono esonerate) |
| `fk_tso_da` | FK | `stato_da_id → config.stati_doc_ordini.id` |
| `fk_tso_a` | FK | `stato_a_id → config.stati_doc_ordini.id` |

> A differenza di `transizioni_stati_contratti`, qui è presente il CHECK `meta-ui`
> (allineato a `transizioni_stati_preventivi`): difende dalle righe manuali con metadati
> incompleti, che farebbero crashare il `$t(null)` nel template Vue.

---

### Regole operative

- **Flag `attivo`**: consente di abilitare/disabilitare una transizione senza eliminarla
  (es. `CONFERMATO → ANNULLATO` disabilitata ma documentata). Il guard ammette **solo**
  le righe con `attivo=true`; `fn_available_actions_ordine` espone **solo** quelle attive
  e manuali.
- **Estensione**: per aggiungere una transizione (es. attivare gli stati a valle quando
  arriverà il modulo magazzino), aggiungere la riga al CSV
  `80_data/sql/config/transizioni_stati_ordini.csv` e aggiornare questo documento.
- **Convenzione di naming**: `config.transizioni_stati_ordini` segue la convenzione
  `transizioni_stati_*` di preventivi/contratti (offerte usa `stati_doc_offerte_transizioni`,
  l'outlier — non replicato).

---

### Esempio d'uso

```sql
-- Transizioni UI disponibili per un ordine nel suo stato corrente
SELECT sa.codice AS stato_destinazione,
       t.meta->>'action_key' AS azione,
       t.meta->>'label_key'  AS label_i18n
  FROM config.transizioni_stati_ordini t
  JOIN config.stati_doc_ordini sa ON sa.id = t.stato_a_id
 WHERE t.stato_da_id = (
           SELECT stato_doc_ordine_id
             FROM vendite.ordini
            WHERE id = :ordine_id
       )
   AND t.attivo IS TRUE
   AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
 ORDER BY sa.ordine;
```

---

{% include-markdown "signature-core.md" %}
