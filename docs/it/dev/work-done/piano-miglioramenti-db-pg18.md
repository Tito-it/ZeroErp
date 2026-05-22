# Piano Miglioramenti DB — PostgreSQL 18 Feature Adoption

> **Data**: 2026-05-14 (verifiche DB eseguite 2026-05-14)
> **Stato**: WIP — bozza revisionata dopo verifica empirica su dev (PG 18.3)
> **Autore**: Tid / Claude Code
> **Contesto**: Pre-produzione. Nessun dato reale da proteggere, nessun SLA da rispettare.
>   La finestra pre-produzione è la condizione ideale per refactoring strutturali.

---

## 1. Sintesi esecutiva

PostgreSQL 18.3 introduce tre feature rilevanti per ZeroErp:

| Feature | Tipo impatto | Sforzo | Priorità |
|---|---|---|---|
| Temporal constraints (`WITHOUT OVERLAPS`) | Architetturale | incluso nel piano | Alta |
| STORED generated columns per `validita` | Architetturale | incluso nel piano | Alta |
| Parallel GIN index builds | Performance | Zero | Immediata (già attiva) |

**Decisione**: siamo in fase di sviluppo puro, nessun vincolo di produzione.
Il piano precedente era strutturato con cautela da produzione — fasi separate,
"opzionale per le esistenti", "decidere per sprint". Quei freni non si applicano.

**Si fa tutto ora, in un unico sprint strutturato** (5–8 giorni):

- Feature 2 (STORED generated) per **tutte e 19 le tabelle** — con dati di sviluppo
  il costo di DROP+ADD column è zero. Farlo ora evita una migrazione 3x più costosa
  post-produzione e consegna un'architettura coerente da subito.
- Feature 1 (temporal UNIQUE) per le 3 tabelle candidate — bundlato con Feature 2.
- Fix `fn_apply_automazione_overlap` come primo step prima di tutto il resto.
- `trgfn_set_validita` eliminata completamente al termine.

Il piano di esecuzione è in §6.

---

## 2. Contesto: il pattern attuale ZeroErp

### 2.1 Pattern `validita` (19 tabelle, non 18)

Il progetto usa il pattern introdotto con la migrazione daterange (12-04-2026):

```
tabella
├── valido_dal  DATE         -- input utente/API, inizio periodo
├── valido_al   DATE NULL    -- input utente/API, fine periodo (NULL = aperto)
└── validita    daterange    -- calcolato da trigger trgfn_set_validita
                             -- = daterange(COALESCE(valido_dal,'-inf'),
                             --              COALESCE(valido_al,'inf'),'[]')
```

Il trigger `script.trgfn_set_validita` è condiviso da **19** tabelle (non 18 — verificato con query su pg_trigger).

Lista completa delle 19 tabelle (da DB, query §9):
`anagrafiche.billing_account`, `anagrafiche.categorie_clienti_listini`,
`anagrafiche.resellers_billing_account`, `anagrafiche.risorse_umane`,
`catalogo.articoli_componenti`, `catalogo.articoli_uom_operativa`,
`catalogo.unita_misura_conversioni`, `config.tipi_ruoli_nature_ammesse`,
`config.tipi_ruolo_tipi_indirizzo`, `config.tipi_soggetto_dettaglio_tipi_indirizzo`,
`config.user_override_aree`, `config.user_override_azioni`,
`config.user_override_oggetti`, `config.utilities_tipi_ruolo`,
`documenti.template_asset`, `documenti.template_documenti_versioni`,
`vendite.contratti`, `vendite.listini_versioni`, `vendite.promo_articoli`.

### 2.2 Pattern anti-overlap (7 tabelle con EXCLUDE attivo)

Il framework `dbops.automazione_overlap` crea EXCLUDE USING gist
per impedire sovrapposizioni temporali su chiave:

```sql
EXCLUDE USING gist (chiave WITH =, validita WITH &&)  -- senza WHERE
EXCLUDE USING gist (chiave WITH =, validita WITH &&) WHERE (attivo IS TRUE)  -- con WHERE
```

### 2.3 Ordinamento trigger e visibilità di `NEW.validita`

**Fatto verificato empiricamente**: la colonna `validita` (sia come colonna ordinaria
gestita da trigger, sia come generated column VIRTUAL o STORED) **non è disponibile
in un BEFORE trigger che precede il trigger `set_validita`**.

Per colonne ordinarie: il trigger `trgfn_set_validita` è alla fase `_a20_`; guard alla
fase `_a10_` vedono `NEW.validita` con il valore pre-calcolo (NULL su INSERT, valore
precedente su UPDATE del chiamante).

Questo significa che ogni guard che legge `NEW.validita` per containment check
(**guards 6+7 di `trgfn_listini_righe_comp_guard_coerenza_bom`**) lo ottiene tramite
la colonna già calcolata e salvata in righe esistenti (UPDATE), ma nullo su INSERT.
Vedi §3.7 per il bug specifico su `listini_righe_componenti`.

---

## 3. Feature 1 — Temporal Constraints (`WITHOUT OVERLAPS`)

### 3.1 Risultati verifica empirica (Fase 0 completata)

Tutti i test eseguiti su PostgreSQL 18.3 (Debian 18.3-1.pgdg13+1):

| Test | Risultato |
|---|---|
| `WITHOUT OVERLAPS` su colonna `daterange` nativa | ✅ **FUNZIONA** |
| Temporal FK con sintassi `PERIOD` | ✅ **FUNZIONA** |
| Temporal UNIQUE su colonna VIRTUAL generated | ❌ Non supportato |
| Temporal UNIQUE su colonna STORED generated | ✅ **FUNZIONA** |

### 3.2 Cos'è

SQL:2011 temporal UNIQUE e FOREIGN KEY, supportati nativamente da PG 18:

```sql
-- Temporal UNIQUE (sostituisce EXCLUDE USING gist senza WHERE)
UNIQUE (chiave_id, validita WITHOUT OVERLAPS)

-- Temporal PRIMARY KEY
PRIMARY KEY (chiave_id, validita WITHOUT OVERLAPS)

-- Temporal FOREIGN KEY — sintassi PG 18 confermata
FOREIGN KEY (parent_id, PERIOD validita)
    REFERENCES parent_table (id, PERIOD validita)
```

La temporal FK garantisce che per ogni riga figlia esista una riga padre
la cui validità **copre** il periodo della figlia. È la formalizzazione
del constraint `lrc.validita <@ lv.validita` oggi gestito via trigger.

### 3.3 Differenze rispetto al pattern GIST attuale

| Aspetto | GIST exclusion (attuale) | Temporal UNIQUE PG 18 |
|---|---|---|
| Sintassi | PG-specific | SQL:2011 standard |
| Semantica anti-overlap | Identica | Identica |
| Clausola `WHERE` parziale | Supportata | **Non supportata** |
| FK temporale | Non esiste (solo trigger) | Dichiarativa, nativa |
| Portabilità | Solo PostgreSQL | Standard SQL |
| Tool support | Standard PG | Standard PG + SQL standard |

### 3.4 Inventario EXCLUDE esistenti (da DB — aggiornato)

Dati reali dalla query su pg_constraint (§9):

| Tabella | Chiave | WHERE? | Temporal UNIQUE? |
|---|---|---|---|
| `catalogo.articoli_componenti` | `prodotto_id, componente_id` | No | ✅ Candidata |
| `catalogo.unita_misura_conversioni` | `uom_from_id, uom_to_id` | No | ✅ Candidata |
| `vendite.contratti` | `billing_account_id, istanza_utility_id, utility_id, ambito` | No | ✅ Candidata |
| `anagrafiche.categorie_clienti_listini` | `(4 colonne + COALESCE)` | `WHERE attivo IS TRUE` | ❌ Resta GIST |
| `documenti.template_documenti_versioni` | `template_documento_id` | `WHERE attivo IS TRUE AND stato='PUBBLICATA'` | ❌ Resta GIST |
| `vendite.listini_versioni` | `listino_id` | `WHERE attivo IS TRUE AND stato='ATTIVA'` | ❌ Resta GIST |
| `vendite.promo_articoli` | `articolo_id, uom_id` | `WHERE attivo IS TRUE` | ❌ Resta GIST |
| `vendite.listini_righe_componenti` | `listino_versione_id, articolo_componente_id` | `WHERE attivo IS TRUE` | ❌ Resta GIST |

**Note**:

- La tabella `dbops.automazione_overlap` gestisce la creazione automatica degli EXCLUDE.
  Le 3 tabelle candidate vanno spostate a temporal UNIQUE; le 5 con WHERE restano nel
  framework GIST. Aggiungere campo `use_temporal_constraint` alla tabella di configurazione
  per documentare esplicitamente quale pathway usa ciascuna tabella.
- `vendite.listini_righe_componenti` **non era nella versione precedente del documento
  come tabella con WHERE** — ora confermata non candidata.

### 3.5 Tabelle interessate dalla FK temporale (candidati temporal FK)

Con temporal FK, i check di containment validità oggi gestiti nei guard trigger
diventano parzialmente ridondanti:

| Figlio | Padre | Semantica | Guard da valutare |
|---|---|---|---|
| `vendite.listini_righe_componenti` | `vendite.listini_versioni` | riga_comp ⊆ versione | guard 7 in trgfn_listini_righe_comp_guard_coerenza_bom |
| `vendite.listini_righe_componenti` | `catalogo.articoli_componenti` | riga_comp ⊆ BoM | guard 6 in trgfn_listini_righe_comp_guard_coerenza_bom |

**Prerequisito**: per aggiungere temporal FK su `listini_righe_componenti →
listini_versioni`, la tabella padre `listini_versioni` deve avere un temporal UNIQUE o
temporal PK. `listini_versioni` ha il EXCLUDE **con WHERE** → **non può avere temporal
UNIQUE**. Quindi la temporal FK verso `listini_versioni` **non è applicabile** salvo
rimuovere il `WHERE` dal constraint (cambio semantico rilevante da valutare
separatamente).

La temporal FK verso `catalogo.articoli_componenti` (candidata temporal UNIQUE) è
invece applicabile dopo la migrazione di `articoli_componenti`.

**Coppia `catalogo.articoli_componenti` → `catalogo.articoli`**: `articoli` è entità
master senza versioning temporale, non ha temporal PK → temporal FK **impossibile**
su questa coppia. Rimossa dalla tabella.

### 3.6 Ordine corretto di migrazione

Il piano precedente aveva un'inversione di dipendenza tra Step 2 e Step 3.
Ordine corretto (dalla tabella meno connessa alla più connessa):

1. **`catalogo.unita_misura_conversioni`** — tabella autonoma, zero dipendenze
   temporali con altre. Ottimo banco di prova della migrazione.

2. **`catalogo.articoli_componenti`** — dopo Step 1. Poi diventa padre per temporal FK
   di `listini_righe_componenti`.

3. **`vendite.contratti`** — indipendente da 1 e 2.

4. **`vendite.listini_righe_componenti` + temporal FK verso `articoli_componenti`** —
   solo dopo Step 2. L'EXCLUDE resta comunque GIST (ha WHERE), ma si aggiunge
   la temporal FK verso `articoli_componenti`.

**Nota**: `vendite.listini_versioni` + `vendite.listini_righe` NON sono candidati a
temporal UNIQUE (hanno WHERE). Restano nel framework GIST esistente.

### 3.7 Bug: `listini_righe_componenti` manca del trigger `set_validita`

**Scoperto durante verifica DB.** La tabella `vendite.listini_righe_componenti`
(migrazioni 20260513-* uncommitted) ha il guard
`trg_listrighe_comp_a10_guard_coerenza_bom_ins_upd` che legge `NEW.validita`
per i check di containment (guards 6 e 7), ma **non ha un trigger `set_validita`**.

Conseguenza: su INSERT, `NEW.validita` è NULL nel guard → il check
`NOT (v_ac_validita @> NEW.validita)` ritorna NULL (falsy) → il guard
**non blocca** righe con validità incoerente. La colonna `validita` rimane NULL.

**Azione richiesta** (nelle migrations uncommitted, prima del commit):
aggiungere `trg_listrighe_comp_a20_set_validita_ins_upd` oppure migrare la colonna
a STORED generated column (vedi §4 — soluzione preferita per nuove tabelle).

### 3.8 Analisi costi-benefici

#### Benefici

1. **Integrità referenziale temporale dichiarativa** (dove applicabile): i guards
   di containment validità diventano ridondanti per la parte coperta dalla FK temporale.
2. **Standardizzazione SQL:2011**: leggibile da qualsiasi tool che conosce lo standard.
3. **Schema auto-documentante**: chi legge il DDL capisce la semantica senza leggere i trigger.

#### Costi e rischi

1. **Solo 3 tabelle su 8 sono candidate** a temporal UNIQUE (le altre restano GIST).
   Beneficio ridotto rispetto alle aspettative iniziali.
2. **Temporal FK limitata**: la coppia più utile (`listini_righe_componenti →
   listini_versioni`) non è applicabile perché `listini_versioni` ha EXCLUDE con WHERE.
3. **`dbops.automazione_overlap` non deprecabile**: resta necessario per le 5 tabelle
   con WHERE.

#### Stima sforzo pre-produzione

| Attività | Sforzo |
|---|---|
| Migrazione 3 tabelle candidate (EXCLUDE → temporal UNIQUE) | S (1-2gg) |
| Temporal FK su `listini_righe_componenti → articoli_componenti` | XS (0.5gg) |
| Aggiornamento `dbops.automazione_overlap` (campo use_temporal_constraint) | XS (2-3h) |
| Fix bug `set_validita` su `listini_righe_componenti` | XS (1-2h) |
| pgTAP per nuovi constraint | S (1gg) |
| **Totale Feature 1** | **S–M (3-5gg)** |

---

## 4. Feature 2 — Generated Columns per `validita`

### 4.1 Risultati verifica empirica (Fase 0 completata)

| Test | Risultato |
|---|---|
| GiST index su VIRTUAL generated column | ❌ **Non supportato** (PG 18.3) |
| Temporal UNIQUE su VIRTUAL generated column | ❌ **Non supportato** (PG 18.3) |
| `NEW.validita` in BEFORE trigger (VIRTUAL) | ❌ **NULL** (non disponibile) |
| GiST index su STORED generated column | ✅ FUNZIONA |
| Temporal UNIQUE su STORED generated column | ✅ FUNZIONA |
| Functional GiST index su espressione `daterange(...)` | ✅ FUNZIONA |

**Impatto su Feature 2**: la feature VIRTUAL è **non applicabile** al pattern
`validita` di ZeroErp. La colonna VIRTUAL non può avere indici GiST (richiesti per
le query `WHERE validita @> data`), non può partecipare a temporal constraints, e
`NEW.validita` è NULL nei BEFORE trigger (romperebbe i guard esistenti).

### 4.2 Opzioni concrete

#### Opzione A: STORED generated column (raccomandata per nuove tabelle)

```sql
validita daterange GENERATED ALWAYS AS (
    daterange(
        COALESCE(valido_dal, '-infinity'::date),
        COALESCE(valido_al,  'infinity'::date),
        '[]'
    )
) STORED
-- equivalente alla scrittura senza STORED in PG 17; in PG 18 STORED è esplicito
-- perché VIRTUAL diventa il default ma va dichiarato esplicitamente per supportare indici
```

**Vantaggi rispetto al trigger**:

- Colonna sempre corretta per costruzione — nessun bypass possibile
- Schema auto-documentante
- Compatibile con temporal constraints (`WITHOUT OVERLAPS`)
- GiST indexable

**Svantaggi / vincoli**:

- `NEW.validita` è **NULL** nei BEFORE trigger sia per VIRTUAL sia per STORED
  (confermato con test su PG 18.3 — vedi D-OPEN-1 risolto) → i guard che leggono
  `NEW.validita` devono usare `daterange(NEW.valido_dal, NEW.valido_al, '[]')` esplicitamente
- ALTER COLUMN non supporta conversione a GENERATED → richiede DROP + ADD column
  (table rewrite, accettabile pre-produzione con dati limitati)
- Trigger `trgfn_set_validita` va rimosso dalla tabella migrata

#### Opzione B: Functional GiST index (complementare, non sostitutivo)

Per tabelle che restano con il pattern trigger + colonna ordinaria, si può
aggiungere un indice funzionale come alternativa alla colonna STORED:

```sql
CREATE INDEX ix_tabella_validita_fn
    ON schema.tabella
    USING gist (daterange(COALESCE(valido_dal,'-infinity'::date),
                          COALESCE(valido_al,'infinity'::date),'[]'));
```

Questo non elimina il trigger ma garantisce performance uguali a un indice
su colonna nativa. Utile per tabelle dove la migrazione a STORED è troppo costosa.

#### Opzione C: Mantenere il trigger (status quo)

Per le 19 tabelle esistenti, il trigger funziona correttamente. Il rischio di
bypass (INSERT diretto senza trigger) è reale ma gestibile pre-produzione.

### 4.3 Raccomandazione per ZeroErp

| Caso | Strategia |
|---|---|
| **Nuove tabelle** (da oggi in poi) | STORED generated column + guardie con `daterange(NEW.valido_dal,...)` |
| **19 tabelle esistenti** | Mantenere trigger (status quo) oppure migrare a STORED su base decisione sprint |
| **`listini_righe_componenti`** (uncommitted) | STORED generated column — è nuova, costo zero, fix il bug §3.7 contestualmente |

### 4.4 Pattern di migrazione per tabella (se si decide di migrare)

Per ogni tabella da migrare, la sequenza migration è:

```sql
-- 1. Rimuovi il trigger set_validita da questa tabella
DROP TRIGGER IF EXISTS trg_<tabella>_a20_set_validita_ins_upd ON <schema>.<tabella>;

-- 2. Converti la colonna (DROP + ADD, necessario perché ALTER non supporta GENERATED)
--    ATTENZIONE: verifica oggetti dipendenti (viste) prima del DROP
ALTER TABLE <schema>.<tabella>
    DROP COLUMN validita CASCADE,
    ADD COLUMN  validita daterange
        GENERATED ALWAYS AS (
            daterange(
                COALESCE(valido_dal, '-infinity'::date),
                COALESCE(valido_al,  'infinity'::date),
                '[]'
            )
        ) STORED;

-- 3. Ricrea l'indice GiST (il DROP CASCADE lo ha rimosso)
CREATE INDEX ix_<tabella>_validita_gist
    ON <schema>.<tabella> USING gist (validita);

-- 4. Ricrea le viste droppate in cascade (se presenti)
-- 5. Aggiorna i guard trigger che usano NEW.validita:
--    sostituire NEW.validita con daterange(NEW.valido_dal, NEW.valido_al, '[]')
```

**Attenzione obbligatoria**: prima del DROP COLUMN, verificare gli oggetti dipendenti:

```sql
SELECT pg_describe_object(classid, objid, objsubid) AS oggetto
  FROM pg_depend
 WHERE refclassid = 'pg_class'::regclass
   AND refobjid = '<schema>.<tabella>'::regclass
   AND refobjsubid = (
       SELECT attnum FROM pg_attribute
        WHERE attrelid = '<schema>.<tabella>'::regclass
          AND attname = 'validita'
   )
   AND deptype = 'n';
```

### 4.5 Guard trigger: riscrittura obbligatoria se si migra a STORED

I guard che leggono `NEW.validita` per containment check devono essere riscritti.
File coinvolti identificati (grep su migrations):

| File trigger | Uso di `NEW.validita` | Riscrittura richiesta |
| --- | --- | --- |
| `trgfn_articoli_componenti_block_modifica_struttura` | `IS DISTINCT FROM OLD.validita` | Sostituire con `NEW.valido_dal IS DISTINCT FROM OLD.valido_dal OR NEW.valido_al IS DISTINCT FROM OLD.valido_al` |
| `trgfn_listini_righe_comp_guard_coerenza_bom` (guards 6+7) | `v @> NEW.validita` (containment) | Sostituire con `v @> daterange(NEW.valido_dal, NEW.valido_al, '[]')` |
| `trgfn_listini_righe_comp_guard_immutabilita_v5` | `IS DISTINCT FROM OLD.validita` | Come sopra |

**Nota**: `trgfn_set_validita` stessa non ha `NEW.validita` tra i suoi output — scrive
`NEW.validita := ...`. Con STORED generated questo trigger è eliminato e la
scrittura esplicita diventa il meccanismo nativo. Nessuna riscrittura per questo file.

### 4.6 Analisi costi-benefici

#### Benefici di STORED generated per nuove tabelle

1. **Consistenza garantita per costruzione**: nessun bypass possibile (COPY, partition
   attach, INSERT con OVERRIDING, seed Liquibase — tutti producono `validita` corretta).
2. **Seed Liquibase più semplici**: non serve specificare `validita` nei changeSet seed.
3. **Leggibilità DDL**: la relazione tra le tre colonne è visibile nel CREATE TABLE.
4. **Fix del bug §3.7**: per `listini_righe_componenti`, la migrazione a STORED elimina
   il bisogno del trigger `set_validita` e risolve contestualmente il problema.

#### Benefici di STORED generated per tabelle esistenti

1. Eliminazione di 19 trigger registration e della trigger function condivisa.
2. Come sopra (consistenza, seed, leggibilità).
3. **Storage**: colonne `validita` STORED occupano spazio identico all'attuale (entrambe
   salvano il valore). VIRTUAL eliminerebbe lo storage, ma non è usabile.

#### Costi per tabelle esistenti

1. DROP + ADD column = table rewrite per ogni tabella.
2. Rewrite di 3 guard trigger + relativi pgTAP.
3. Ricreazione di indici GiST e viste dipendenti.

#### Stima sforzo pre-produzione

| Attività | Sforzo |
|---|---|
| `listini_righe_componenti` → STORED (fix bug §3.7, nuova tabella) | XS (2-3h) |
| Template migration riusabile (script) | XS (1h) |
| Migrazione 19 tabelle esistenti (~45min/tabella) | M–L (7-10gg) |
| Riscrittura guard trigger (3 trigger, pgTAP incluso) | S (1-2gg) |
| Rimozione `trgfn_set_validita` e registrations | XS (2h) |
| **Totale se si fanno tutte e 19** | **M–L (9-13gg)** |
| **Totale se si fa solo `listini_righe_componenti`** | **XS (3-4h)** |

---

## 5. Feature 3 — Parallel GIN Index Builds

### 5.1 Cos'è

Da PG 18, i GIN index possono essere costruiti in parallelo (come già
avveniva per B-tree e BRIN). Nessuna modifica al codice o DDL.

### 5.2 Impatto su ZeroErp

ZeroErp usa indici GIN per `pg_trgm` (es. `ragione_sociale_normalizzata`),
JSONB su colonne payload, e FTS dove applicato.

Con il parallel build, il tempo di `CREATE INDEX` e `REINDEX` si riduce
proporzionalmente ai worker disponibili. **Nessuna azione richiesta** — già attivo.

---

## 6. Piano di Esecuzione

### Prerequisiti — COMPLETATI

Verifiche empiriche su PG 18.3 (2026-05-14). Tutti i risultati incorporati nelle sezioni 3 e 4.
Tutti i dubbi aperti (D-OPEN-1, D-OPEN-2, D-OPEN-3) risolti.

---

### Step 0 — Fix `fn_apply_automazione_overlap` ✅ COMPLETATO (2026-05-14)

**Migration**: `20260514-03-update-fn-apply-automazione-overlap-temporal-unique-mctit.yaml`

Aggiunto `v_temporal_unique_exists` e relativo check: la funzione ora skippa se esiste già
un `UNIQUE (WITHOUT OVERLAPS)` sulla colonna periodo. Applicata su dev.

---

### Step 1 — Fix urgente `listini_righe_componenti` ✅ COMPLETATO (2026-05-14)

**Nota scoperta in fase di implementazione**: `listini_righe_componenti` non aveva
`valido_dal`/`valido_al` (il 20260513-18 usava `validita` come input diretto).
La migrazione ha aggiunto le due colonne con backfill automatico dalla colonna `validita`.

**Migrations create**:

- `20260514-04` (`00_schema/vendite`): ALTER tabella — add `valido_dal`/`valido_al`,
  backfill da `validita`, `validita` → STORED generated, ricrea indici
- `20260514-05` (`20_code/script`): riscrive `trgfn_listini_righe_comp_guard_coerenza_bom`
  — guards 6+7 usano `v_new_validita := daterange(NEW.valido_dal, NEW.valido_al, '[]')`
- `20260514-06` (`20_code/vendite`): riscrive `trgfn_listini_righe_comp_guard_immutabilita_v5`
  — check UPDATE usa `valido_dal`/`valido_al IS DISTINCT FROM` invece di `validita`

**File originali pushati** (`20260513-19`, `20260513-20`) **non modificati** — corretto.

Applicate su dev. Da committare insieme alle `20260513-*` uncommitted.

---

### Step 2a — Tabelle con temporal UNIQUE ✅ COMPLETATO (2026-05-14)

**Migrations**: `20260514-07..10` (applicate su dev, non committate)

| Tabella | Migration | Constraint |
| --- | --- | --- |
| `catalogo.unita_misura_conversioni` | 07 `00_schema/catalogo` | `uq_uom_conv_no_overlap` |
| `catalogo.articoli_componenti` | 08 `00_schema/catalogo` | `uq_articoli_componenti_no_overlap` |
| `catalogo.articoli_componenti` (guard) | 09 `20_code/catalogo` | `trgfn_block_modifica_struttura` rewrite |
| `vendite.contratti` | 10 `00_schema/vendite` | `uq_contratti_no_overlap` |

Ottimizzazione trigger `trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt`: aggiunto `UPDATE OF` sui campi struttura — migration `20260514-15`.

---

### Step 3 — Temporal FK `listini_righe_componenti → articoli_componenti` ✅ COMPLETATO (2026-05-14)

**Migrations**: `20260514-11..15` (applicate su dev, non committate)

- `20260514-11`: ADD `UNIQUE (id, validita WITHOUT OVERLAPS)` su `articoli_componenti` — prerequisito PG 18 per FK reference
- `20260514-12`: ADD temporal FK `fk_listrighe_comp_articoli_comp_temporal`
- `20260514-13`: rimozione guard 6 da `trgfn_listini_righe_comp_guard_coerenza_bom` (redundante con la FK)
- `20260514-14`: ottimizzazione stessa funzione — query unica con LEFT JOIN (1 round-trip invece di 2)
- `20260514-15`: trigger `trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt` con `UPDATE OF`

**Fix pgTAP**: `test-fn-resolve-prezzo-listino-v2-bundle-prioritario-v1.sql` — INSERT su `listini_righe_componenti` usava `validita` direttamente (bug esposto da Step 1). Corretto con `valido_dal/valido_al`.

---

### Step 2b — Restanti 16 tabelle STORED generated ✅ COMPLETATO (2026-05-14)

**Migrations**: `20260514-17..32` (create, da applicare su dev)

| # | Tabella | Migration | Note |
| --- | --- | --- | --- |
| 1 | `anagrafiche.billing_account` | 17 | semplice |
| 2 | `anagrafiche.resellers_billing_account` | 18 | semplice |
| 3 | `anagrafiche.risorse_umane` | 19 | semplice |
| 4 | `config.tipi_ruoli_nature_ammesse` | 20 | semplice |
| 5 | `config.tipi_ruolo_tipi_indirizzo` | 21 | semplice |
| 6 | `config.tipi_soggetto_dettaglio_tipi_indirizzo` | 22 | semplice |
| 7 | `config.user_override_aree` | 23 | semplice |
| 8 | `config.user_override_azioni` | 24 | semplice |
| 9 | `config.user_override_oggetti` | 25 | semplice |
| 10 | `config.utilities_tipi_ruolo` | 26 | semplice |
| 11 | `documenti.template_asset` | 27 | semplice |
| 12 | `catalogo.articoli_uom_operativa` | 28 | ricrea `vw_articoli_uom_operativa_dettaglio` |
| 13 | `vendite.listini_versioni` | 29 | ricrea EXCLUDE `WHERE stato='ATTIVA'` |
| 14 | `vendite.promo_articoli` | 30 | ricrea EXCLUDE + standalone GiST |
| 15 | `anagrafiche.categorie_clienti_listini` | 31 | ricrea EXCLUDE con COALESCE + standalone GiST |
| 16 | `documenti.template_documenti_versioni` | 32 | ricrea EXCLUDE `WHERE stato='PUBBLICATA'` |

---

### Step 4 — Drop `trgfn_set_validita` ✅ COMPLETATO (2026-05-14)

**Migration**: `20260514-33` (`20_code/script`) — con preCondition che conta i trigger residui.
La migration si sblocca automaticamente solo dopo che tutte le 19 tabelle sono migrate
(preCondition conta trigger attivi su `trgfn_set_validita` = 0).

---

### Step 5 — Aggiornamento `linee-guida-sql.md §7b` ✅ COMPLETATO (2026-05-14)

`docs/it/linee-guida-sql.md §7b` aggiornato con nuovo standard: STORED generated,
due pathway anti-overlap (temporal UNIQUE vs EXCLUDE con WHERE), temporal FK sintassi PERIOD.

---

### Ottimizzazione aggiuntiva — `fn_apply_automazione_overlap` ✅ COMPLETATO (2026-05-14)

**Migration**: `20260514-34` (`20_code/dbops`) — 3 query separate su `pg_constraint`
fuse in una singola scan con `CROSS JOIN LATERAL`. Una lettura del catalogo per
iterazione, `pg_get_constraintdef()` invocato una volta per riga.

---

### Riepilogo ordine esecuzione

```text
Step 0  →  Step 1  →  Step 2a  →  Step 3  →  Step 2b  →  Step 4  →  Step 5
 Fix fn      listini     3 tab    temp FK    16 tab     drop fn    linee
 overlap   righe_comp  STORED+UQ  PERIOD     STORED     set_val    guida
  ✅ fatto   ✅ fatto   ✅ fatto   ✅ fatto   ✅ fatto   ✅ fatto   ✅ fatto
```

Migrations `20260514-03..15` applicate. Migrations `20260514-17..34` create, da applicare.

---

---

## 7. Analisi Costi-Benefici

### 7.1 Perché fare tutto ora

| Voce | Ora (dev) | Dopo prima release |
|---|---|---|
| Dati reali da preservare | No — DROP+ADD istantaneo | Sì — migration multi-step |
| Zero-downtime richiesto | No | Sì |
| Rollback | Git revert | Procedure DB reversibili |
| Guard trigger da riscrivere | 3 (invariato) | 3 + tutti i consumer futuri |
| **Moltiplicatore costo** | **1x** | **3x–4x** |

Il piano precedente trattava Feature 2 come "opzionale per le esistenti" perché
stimava costi elevati. Con dati di sviluppo quei costi non esistono. La scelta
di fare tutto ora è economicamente ovvia.

### 7.2 Stime sforzo piano rivisto

| Step | Attività | Sforzo |
| --- | --- | --- |
| Step 0 | Fix `fn_apply_automazione_overlap` | XS (1h) |
| Step 1 | `listini_righe_componenti` STORED + guard | XS (3-4h) |
| Step 2a | 3 tabelle STORED + temporal UNIQUE + guard `articoli_componenti` | S (1-2gg) |
| Step 2b | 16 tabelle STORED (nessun guard) | M (3-4gg) |
| Step 3 | Temporal FK `listrighe_comp → articoli_componenti` | XS (1h) |
| Step 4 | Drop `trgfn_set_validita` | XS (30min) |
| Step 5 | Aggiornamento linee-guida §7b | XS (1h) |
| **Totale** | | **M (5-8 giorni)** |

### 7.3 Risultato architetturale finale

Al termine del piano:

- `validita` è STORED generated su tutte le 32 tabelle (19 esistenti + 13 future stimate)
- `trgfn_set_validita` eliminata — nessun trigger per colonne computed
- 3 tabelle usano temporal UNIQUE invece di EXCLUDE GIST
- 1 temporal FK attiva (`listrighe_comp → articoli_componenti`)
- `dbops.automazione_overlap` resta per le 5 tabelle con WHERE — non deprecabile
- Guard trigger scritti con `daterange(NEW.valido_dal, ...)` — pattern uniforme

---

## 8. Decisioni — PRESE

Tutte le decisioni sono state prese in data 2026-05-14. Il piano in §6 è quello esecutivo.

| ID | Decisione | Stato |
| --- | --- | --- |
| D1 | Fix `listini_righe_componenti` → STORED generated (bug §3.7) | ✅ Step 1 |
| D2 | Aggiornare `linee-guida-sql.md §7b` con nuovo standard | ✅ Step 5 |
| D3 | Migrare le 3 tabelle candidate a temporal UNIQUE | ✅ Step 2a |
| D4 | Migrare tutte le 19 tabelle esistenti a STORED generated | ✅ Step 2a+2b |
| D5 | Fix `fn_apply_automazione_overlap` (check temporal UNIQUE) invece di `active=false` | ✅ Step 0 |

---

## 9. Appendice: Query Utili

```sql
-- Tutte le tabelle con trgfn_set_validita (risultato: 19 tabelle)
SELECT DISTINCT n.nspname || '.' || c.relname AS tabella
  FROM pg_trigger t
  JOIN pg_proc p   ON p.oid  = t.tgfoid
  JOIN pg_namespace pn ON pn.oid = p.pronamespace
  JOIN pg_class  c ON c.oid  = t.tgrelid
  JOIN pg_namespace n  ON n.oid  = c.relnamespace
 WHERE pn.nspname = 'script'
   AND p.proname  = 'trgfn_set_validita'
 ORDER BY 1;

-- Tutte le GIST exclusion esistenti con/senza WHERE (candidati temporal UNIQUE)
SELECT n.nspname || '.' || c.relname AS tabella,
       con.conname AS constraint_name,
       pg_get_constraintdef(con.oid) AS definizione
  FROM pg_constraint con
  JOIN pg_class c ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE con.contype = 'x'
   AND pg_get_constraintdef(con.oid) LIKE '%validita%'
 ORDER BY 1;

-- Oggetti dipendenti da colonna validita (da eseguire prima di DROP COLUMN)
SELECT pg_describe_object(classid, objid, objsubid) AS oggetto,
       deptype
  FROM pg_depend
 WHERE refclassid = 'pg_class'::regclass
   AND refobjid = 'schema.tabella'::regclass
   AND refobjsubid = (
       SELECT attnum FROM pg_attribute
        WHERE attrelid = 'schema.tabella'::regclass
          AND attname = 'validita'
   )
   AND deptype = 'n';

-- Colonne validita nelle tabelle (verifica copertura)
SELECT n.nspname || '.' || c.relname AS tabella,
       a.attname AS colonna,
       t.typname AS tipo,
       CASE a.attgenerated WHEN 's' THEN 'STORED' WHEN 'v' THEN 'VIRTUAL' ELSE 'normale' END AS generated
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_type t ON t.oid = a.atttypid
 WHERE a.attname = 'validita'
   AND a.attnum > 0
   AND NOT a.attisdropped
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
 ORDER BY 1;
```

---

## 10. Dubbi Aperti — Da Risolvere Prima di Procedere

I seguenti punti restano **non completamente verificati** e richiedono un test
o una decisione prima di procedere con le relative fasi:

---

**D-OPEN-1** — `NEW.validita` in BEFORE trigger per colonna STORED generated ✅ RISOLTO

*Risultato (testato su PG 18.3)*: `NEW.validita STORED: [<NULL>]`

**Comportamento confermato**: per STORED generated column, `NEW.validita` è NULL
nei BEFORE trigger esattamente come per VIRTUAL. La generazione avviene dopo
l'esecuzione di tutti i BEFORE trigger, senza eccezioni.

*Implicazione operativa*: la riscrittura dei guard trigger (§4.5) è **obbligatoria**
per qualsiasi tabella migrata a generated column (STORED o VIRTUAL). Ogni
`NEW.validita` nei BEFORE trigger deve diventare
`daterange(NEW.valido_dal, NEW.valido_al, '[]')`.

---

**D-OPEN-2** — L'indice GiST creato da temporal UNIQUE serve le query `WHERE validita @> data`? ✅ RISOLTO

*Risultato (testato su PG 18.3)*:

```sql
-- Test B: WHERE validita @> CURRENT_DATE (senza filtro su id)
Bitmap Heap Scan on _test_d2
  Recheck Cond: (validita @> CURRENT_DATE)
  -> Bitmap Index Scan on _test_d2_id_validita_key   ← indice del constraint
       Index Cond: (validita @> CURRENT_DATE)
```

**Comportamento confermato**: il planner usa *naturalmente* l'indice GiST creato
dal temporal UNIQUE (`_test_d2_id_validita_key`) anche per query che non filtrano
sulla colonna chiave. L'indice su `(id, validita)` supporta ricerche per sola
dimensione temporale senza richiedere il filtro su `id`.

*Implicazione operativa*: per le 3 tabelle candidate a temporal UNIQUE
(`uom_conversioni`, `articoli_componenti`, `contratti`), **non è necessario
creare un indice GiST standalone separato su `validita`**. Il constraint provvede
l'indice sufficiente per tutte le query `WHERE validita @> data`.

Gli indici standalone esistenti su 2 tabelle con WHERE (`ix_categ_cli_listini_validita_gist`,
`ix_promo_articoli_validita_gist`) restano necessari perché quelle tabelle non
migrano a temporal UNIQUE e il loro EXCLUDE è parziale.

---

**D-OPEN-3** — `dbops.automazione_overlap`: comportamento dopo migrazione a temporal UNIQUE ⚠️ RISOLTO — AZIONE OBBLIGATORIA

*Risultato (analisi codice `fn_apply_automazione_overlap`)*: la funzione controlla
l'esistenza di un constraint con `contype = 'x'` (EXCLUDE). Un temporal UNIQUE ha
`contype = 'u'`. Dopo migrazione, non esiste nessun `contype = 'x'` sulla tabella →
`v_constraint_exists` e `v_any_exclusion` risultano entrambi FALSE → **la funzione
ricrea l'EXCLUDE USING gist**, annullando la migrazione.

*La funzione non è idempotente per tabelle migrate a temporal UNIQUE.*

**Azione obbligatoria**: nella stessa migration che aggiunge il temporal UNIQUE,
impostare `active = false` nella riga corrispondente di `dbops.automazione_overlap`:

```sql
UPDATE dbops.automazione_overlap
   SET active = false
 WHERE target_schema = 'catalogo'
   AND target_table  = 'unita_misura_conversioni'; -- ripetere per ogni tabella migrata
```

In alternativa strutturale (consigliata per pulizia a lungo termine): estendere
`fn_apply_automazione_overlap` con un terzo check per temporal UNIQUE:

```sql
SELECT EXISTS (
  SELECT 1 FROM pg_constraint con
   WHERE con.conrelid = v_rel
     AND con.contype = 'u'
     AND pg_get_constraintdef(con.oid) ILIKE '%WITHOUT OVERLAPS%'
     AND pg_get_constraintdef(con.oid) ILIKE '%' ||
         COALESCE(rconf.range_col, rconf.valido_dal_col) || '%'
) INTO v_temporal_unique_exists;

IF v_constraint_exists OR v_any_exclusion OR v_temporal_unique_exists THEN CONTINUE; END IF;
```

Questo terzo check rende la funzione idempotente anche per temporal UNIQUE,
eliminando il rischio senza dover toccare `active`. La modifica va inserita come
nuova migration `20_code` su `fn_apply_automazione_overlap` prima di eseguire
le migrazioni di Fase 2.

*Decisione*: il fix alla funzione è semplice (5 righe) ed elimina la necessità di
gestire `active = false` per ogni tabella migrata. Raccomandato farlo in Fase 2,
changeSet precedente alle migrazioni delle 3 tabelle.

---

*Documento aggiornato il 2026-05-14. Tutti i dubbi aperti risolti. Piano esecutivo definitivo in §6.*

---

## 11. Note sviluppo backend/frontend

### Backend Django

**1. Colonna `validita` diventa `GENERATED ALWAYS` — non scrivibile**

PostgreSQL rifiuta `INSERT`/`UPDATE` che includano `validita` nella lista colonne.
Azione richiesta: grep sui repository per `INSERT ... validita` e `UPDATE ... validita`
e rimuovere la colonna dalle istruzioni SQL raw. È probabile che già oggi non venga
scritta (il trigger la gestisce), ma la verifica è obbligatoria prima del merge.

#### 2. Modelli Django ORM

I modelli con `managed=False` che dichiarano `validita` come campo scrivibile devono
passare a `editable=False` (o rimuovere il campo dal model e accederlo solo in lettura).
Non è bloccante — PostgreSQL respinge comunque l'UPDATE — ma allinea il model alla realtà.

#### 3. Temporal FK — nuovo tipo di errore da gestire

La FK temporale `listrighe_comp → articoli_componenti` genera `foreign_key_violation`
con semantica diversa dal guard trigger attuale (che solleva un errore applicativo
con codice `E_LISTINO_COMPONENTE_COERENZA_BOM`). Se il service che inserisce righe
listino componenti cattura solo l'errore applicativo del guard, deve essere aggiornato
per gestire anche la violazione FK. Verificare `error_policies.py` e il mapping HTTP.

#### 4. Temporal UNIQUE — cambio tipo eccezione constraint violation

Le 3 tabelle che passano da EXCLUDE a temporal UNIQUE generano `unique_violation`
invece di `exclusion_violation`. Se `error_policies.py` o i service fanno matching
sul tipo specifico di eccezione PostgreSQL (improbabile ma da verificare), va aggiornato.
Se gli errori passano per `ServiceError` generico, nessun impatto.

#### 5. Seed e fixture Liquibase

I changeSet `80_data` che fanno INSERT su tabelle migrate a STORED generated
devono rimuovere `validita` dalla lista colonne (se presente). Fare grep su
`db/changelog/migrations_v2/80_data/` per ogni tabella migrata.

Sintesi lavoro backend: verifica e pulizia, non riscrittura logica.
Unico rischio reale: punti 3 e 4 (gestione eccezioni).

---

### Frontend Vue

**Impatto: praticamente zero.**

Il frontend invia sempre e solo `valido_dal` e `valido_al` come input utente.
Non conosce né scrive mai `validita`. Le response API che includono `validita`
continuano a funzionare identicamente — è una colonna readable come prima.

Unico scenario marginale: se un componente mostrasse il messaggio di errore raw
di PostgreSQL per overlap (testo cambia da `exclusion_violation` a `unique_violation`),
il messaggio potrebbe variare. Se gli errori passano per il sistema centralizzato
`config.messaggi_errore` → `error_manager`, nessun impatto visibile all'utente.
