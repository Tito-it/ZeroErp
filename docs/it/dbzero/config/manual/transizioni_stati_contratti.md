## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_contratti`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
>
> Approfondimento funzioni:
>
> [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto)
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)

---

### 🎯 Scopo Principale

(rev 2026-05-28)

`config.transizioni_stati_contratti` definisce la **matrice dei metadati UI** per le
transizioni tra gli stati del contratto di fornitura. Fonte dati per
`script.fn_available_actions_contratto`, che la legge per costruire `available_actions[]`
nel payload del detail endpoint BE.

Pattern identico a `config.transizioni_stati_preventivi` e `config.stati_doc_offerte_transizioni`:
stessa struttura, stesso meccanismo di lettura nella capability function.

> **Nota architetturale** — La **regola di business** (quali transizioni sono ammesse)
> continua a risiedere nel trigger
> `vendite.trgfn_contratti_guard_transizione_stato`. Questa tabella serve
> esclusivamente come fonte dei metadati UI (label, icona, severity, ecc.): la separazione
> tra "cosa è ammesso" (trigger) e "come si presenta al FE" (tabella) è intenzionale e
> allineata al pattern dei due domini fratelli.

---

### Matrice transizioni configurata

| id | Da stato | A stato | Manuale | Descrizione |
|----|----------|---------|:-------:|-------------|
| 1 | DRAFT (1) | ATTIVO (2) | Sì | Attivazione contratto; il trigger blocca se componenti BoM in PENDING |
| 2 | DRAFT (1) | ANNULLATO (8) | Sì | Ritiro bozza; ammessa sempre (nessuna fatturazione su DRAFT) |
| 3 | ATTIVO (2) | CESSATO (5) | Sì | Cessazione; richiede data (`requires_date=true`) |

```text
DRAFT ──────> ATTIVO ──────> CESSATO   (terminale)
  │
  └──> ANNULLATO             (terminale, is_abortito=true)
```

**Transizioni non presenti (bloccate dal trigger, mai in tabella)**:
- `ATTIVO → ANNULLATO` — un contratto attivo deve essere cessato ordinariamente.
- Qualsiasi transizione uscente da `CESSATO` e `ANNULLATO` (terminali).

---

### Campo `meta` — metadati UI

Il campo `meta jsonb NOT NULL DEFAULT '{}'` porta i metadati letti da
`script.fn_available_actions_contratto`.

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `action_key` | `text` | Chiave semantica dell'azione (es. `attiva`, `annulla`, `cessa`) |
| `label_key` | `text` | Chiave i18n per il label del bottone Vue (`$t(label_key)`) |
| `severity` | `text` | Severity PrimeVue: `info` / `success` / `danger` |
| `icon` | `text` | Classe PrimeIcons (es. `pi pi-play`, `pi pi-times`, `pi pi-stop`) |
| `requires_confirm` | `boolean` | `true` → dialog di conferma prima di eseguire |
| `requires_date` | `boolean` | `true` → la UI deve raccogliere una data (ex: cessazione). La funzione arricchisce l'azione con `default_date` e `min_date` contestuali |
| `outlined` | `boolean` | `true` → bottone PrimeVue variante outlined (usato su `annulla` per ridurne il peso visivo) |
| `manuale` | `boolean` | `false` = transizione automatica (job/trigger); esclusa dalla lista UI. Default: `true` |

**Valori seed correnti (rev 2026-05-28)**:

| id | Transizione | severity | requires_date | outlined |
|----|-------------|----------|:---:|:---:|
| 1 | DRAFT → ATTIVO | `info` | `false` | `false` |
| 2 | DRAFT → ANNULLATO | `danger` | `false` | `true` |
| 3 | ATTIVO → CESSATO | `danger` | `true` | `false` |

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_transizioni_stati_contratti` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola riga per coppia |
| `ck_tsc_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |
| `fk_tsc_da` | FK | `stato_da_id → config.stati_doc_contratti.id` |
| `fk_tsc_a` | FK | `stato_a_id → config.stati_doc_contratti.id` |

---

### Arricchimento contestuale `requires_date`

Le azioni con `requires_date=true` ricevono due campi aggiuntivi a runtime dalla
funzione (non presenti in tabella, dipendono dal contratto specifico):

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| `default_date` | `CURRENT_DATE::text` | Data suggerita dalla UI (cessazione programmata per oggi via job pgAgent) |
| `min_date` | `contratto.valido_dal::text` | Data minima accettabile (non si cessa prima dell'inizio contratto) |

La regola del trigger per `ATTIVO → CESSATO`:
- `valido_al < CURRENT_DATE` → il job pgAgent porta in CESSATO automaticamente.
- `valido_al >= CURRENT_DATE` → il BE esegue solo `PATCH valido_al`; il job pgAgent chiuderà alla scadenza.

---

### Regole operative

- **Flag `attivo`**: consente di disabilitare temporaneamente una transizione senza eliminarla.
- **Estensione**: per aggiungere una nuova transizione, aggiungere la riga al CSV
  `80_data/sql/config/transizioni_stati_contratti.csv` e aggiornare questo documento.
- **Nessun CHECK meta-UI**: a differenza di `transizioni_stati_preventivi`,
  questa tabella non ha un CHECK sul contenuto di `meta`. La correttezza è garantita
  dal seed CSV.
- **`stati_doc_contratti.meta.outgoing_action`**: campo storico presente su DRAFT e ATTIVO,
  non più letto dalla funzione dalla rev 2026-05-28. Dato morto da rimuovere nella prossima
  PR che tocca `stati_doc_contratti`.

---

### Esempio d'uso

```sql
-- Transizioni UI disponibili per un contratto nel suo stato corrente
SELECT sdc_a.codice AS stato_destinazione,
       t.meta->>'action_key' AS azione,
       t.meta->>'label_key'  AS label_i18n,
       t.meta->>'severity'   AS severity
  FROM config.transizioni_stati_contratti t
  JOIN config.stati_doc_contratti sdc_a ON sdc_a.id = t.stato_a_id
 WHERE t.stato_da_id = (
           SELECT stato_doc_contratto_id
             FROM vendite.contratti
            WHERE id = :contratto_id
       )
   AND t.attivo IS TRUE
   AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
 ORDER BY sdc_a.ordine;
```

---

{% include-markdown "signature-core.md" %}
