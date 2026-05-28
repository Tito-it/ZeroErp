## 📘 Documentazione Concettuale – Tabella `config.stati_doc_offerte_transizioni`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte)
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
>
> Approfondimento funzioni:
>
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)

---

### 🎯 Scopo Principale

(latest review 2026-05-24)

`config.stati_doc_offerte_transizioni` definisce la **matrice delle transizioni ammesse**
tra gli stati del ciclo di vita delle offerte commerciali. Pattern identico a
`config.transizioni_stati_preventivi`.

Il trigger `vendite.trgfn_offerte_commerciali_guard_transizione` consulta questa tabella
(BEFORE UPDATE OF `stato_doc_offerta_id`) per validare ogni passaggio di stato,
rendendo le regole configurabili senza rilasciare codice.

---

### Matrice transizioni configurata

(addendum A2 — `BOZZA→RIFIUTATA` rimossa perche' semanticamente incongrua:
`RIFIUTATA` e' il "no del cliente", non un ritiro interno)

| id | Da stato | A stato | Manuale | Descrizione |
|----|----------|---------|:-------:|-------------|
| 1 | BOZZA (1) | EMESSA (2) | Si' | Emissione al cliente; congela `listino_versione_id` |
| 2 | BOZZA (1) | ANNULLATA (6) | Si' | Ritiro interno prima o durante bozza (A2) |
| 3 | EMESSA (2) | ACCETTATA (3) | Si' | Accettazione cliente; innesca push a contratto |
| 4 | EMESSA (2) | RIFIUTATA (4) | Si' | Rifiuto cliente |
| 5 | EMESSA (2) | SUPERATA (5) | No | Automatico: trigger revisione (Step 6) |

```text
BOZZA ──────> EMESSA ──────> ACCETTATA ──> (push → contratto DRAFT)
  │              │
  │              ├──> RIFIUTATA   (no del cliente)
  │              └──> SUPERATA    (automatico, trigger revisione)
  └──> ANNULLATA  (ritiro interno)
```

**Stati terminali senza transizioni uscenti**: ACCETTATA, RIFIUTATA, SUPERATA, ANNULLATA.

---

### Guard aggiuntivi del trigger (non delegabili alla matrice)

Il trigger `trgfn_offerte_commerciali_guard_transizione` applica guard supplementari
che richiedono lettura di altre tabelle:

| Transizione | Guard | Errore |
|-------------|-------|--------|
| BOZZA → EMESSA | `listino_versione_id IS NOT NULL` | `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` |
| BOZZA → EMESSA | `vendite.listini_versioni.stato = 'ATTIVA'` | `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` |
| qualsiasi non ammessa | non in matrice | `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` |

Il trigger valorizza automaticamente anche i timestamp di passaggio:

| Passaggio | Colonna valorizzata |
|-----------|---------------------|
| → EMESSA | `data_emissione = NOW()` |
| → ACCETTATA | `data_accettazione = NOW()` |
| → RIFIUTATA | `data_rifiuto = NOW()` |
| → ANNULLATA | `data_annullamento = NOW()` |

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_stati_doc_offerte_transizioni` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola regola per coppia |
| `ck_sdot_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |
| `fk_sdot_da` | FK | `stato_da_id → config.stati_doc_offerte.id` |
| `fk_sdot_a` | FK | `stato_a_id → config.stati_doc_offerte.id` |

---

### Campo `meta` — metadati UI

Il campo `meta jsonb NOT NULL DEFAULT '{}'` porta i metadati letti dal backend
per costruire i bottoni azione nella UI.

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `action_key` | `text` | Chiave semantica dell'azione (es. `emetti`, `annulla`, `accetta`, `rifiuta`) |
| `label_key` | `text` | Chiave i18n per il label del bottone Vue (`$t(label_key)`) |
| `severity` | `text` | Severity PrimeVue: `info` / `success` / `danger` |
| `icon` | `text` | Classe PrimeIcons (es. `pi pi-send`, `pi pi-times`) |
| `requires_confirm` | `boolean` | `true` → mostra dialog di conferma prima di eseguire |
| `manuale` | `boolean` | `false` = transizione automatica (trigger); esclusa dalla lista UI |

Le transizioni automatiche (id 5, EMESSA → SUPERATA) hanno `meta = {"manuale": false}`.

**Valori `severity` correnti** (rev 28-05-2026):

| id | Transizione | severity |
|----|-------------|----------|
| 1 | BOZZA → EMESSA | `info` (era `success` fino al 27-05-2026, allineata a preventivi con migration 20260528-03) |
| 2 | BOZZA → ANNULLATA | `danger` |
| 3 | EMESSA → ACCETTATA | `success` |
| 4 | EMESSA → RIFIUTATA | `danger` |

---

### Regole operative

- **Flag `attivo`**: consente di disabilitare temporaneamente una transizione senza eliminarla.
- **Estensione**: per aggiungere una nuova transizione, aggiungere la riga al CSV
  `80_data/sql/config/stati_doc_offerte_transizioni.csv` e aggiornare questo documento.
- **Nessun guard-meta CHECK**: a differenza di `transizioni_stati_preventivi`, questa tabella
  non ha un CHECK sul contenuto di `meta`. La correttezza del meta e' garantita dal seed CSV.

---

### Esempio d'uso

```sql
-- Transizioni manuali disponibili per un'offerta nel suo stato corrente
SELECT sdo_a.codice AS stato_destinazione,
       t.meta->>'action_key' AS azione,
       t.meta->>'label_key'  AS label_i18n
  FROM config.stati_doc_offerte_transizioni t
  JOIN config.stati_doc_offerte sdo_a ON sdo_a.id = t.stato_a_id
 WHERE t.stato_da_id = (
           SELECT stato_doc_offerta_id
             FROM vendite.offerte_commerciali
            WHERE id = :offerta_id
       )
   AND t.attivo IS TRUE
   AND (t.meta->>'manuale')::boolean IS NOT FALSE
 ORDER BY sdo_a.ordine;
```

---

{% include-markdown "signature-core.md" %}
