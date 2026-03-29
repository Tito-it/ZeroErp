# Anagrafica Fornitori — Piano di Completamento

> **Modulo:** Ciclo Passivo / Acquisti
> **Area:** Anagrafiche
> **Versione:** 2.0 — basata su analisi struttura esistente
> **Stato:** **CHIUSO** — sviluppo completato end-to-end (backend, frontend, test UI) — 25-27 marzo 2026
> **Data:** 2026-03-24

---

## Panoramica

Il **fornitore** e un ruolo specializzato del soggetto base, gestito tramite il pattern standard `soggetti → soggetti_ruoli → fornitori` (relazione 1:1 via `soggetto_ruolo_id`).

La tabella `anagrafiche.fornitori` **esiste gia** con struttura base funzionante: identita, fiscale, pagamento, FE/SDI, rating, audit. Questo documento elenca le **modifiche incrementali** necessarie per allinearla al pattern standard dei ruoli e prepararla per il ciclo passivo.

---

## Analisi di simmetria — Il fornitore come ruolo del sistema

### Principio architetturale

In ZeroErp **tutti i ruoli seguono lo stesso pattern strutturale**. Un ruolo e un'estensione 1:1 di `soggetti_ruoli` che aggiunge campi specifici del dominio. Il pattern base comprende:

- Indirizzi, contatti e conti bancari **sono gia gestiti** a livello di soggetto/ruolo dalla infrastruttura trasversale (cascata risoluzione multi-livello)
- Ogni tabella ruolo si aggancia a `soggetti_ruoli.id` con UNIQUE 1:1
- La validazione del ruolo e delegata a `script.fn_guard_soggetto_ruolo`

### Pattern standard dei ruoli (confronto tra tutti)

| Elemento | Clienti | Fornitori | Vettori | Emittenti F. | Pattern comune |
|----------|---------|-----------|---------|--------------|----------------|
| `id` BIGINT PK | si | si | si | si | **standard** |
| `soggetto_ruolo_id` FK UNIQUE | si | si | si | si | **standard** |
| `uid` UUID uuidv7() | no | **no** | si | si | presente nei ruoli piu recenti |
| `codice` UNIQUE | no (via BA) | si | si | si | **standard** (escluso clienti) |
| `attivo` BOOLEAN | no (via stato) | si | si | si | **standard** (escluso clienti) |
| `meta` JSONB | no | si | si | si | **standard** (escluso clienti) |
| `tx_id` + `storicizza` | si | si | si | si | **standard** |
| Audit 4 campi | si | si | si | si | **standard** |
| Guard ruolo | si (CL) | si (FO) | si (VT) | si (EF) | **standard** |
| Normalize | no | si | si | si | **standard** |
| Lock codice | no | si | si | si | **standard** |
| Delete block GUC | si | si | si | si | **standard** |
| Storicizzazione | si | si | si | si | **standard** |

### Cosa e SPECIFICO del cliente (dominio utility) — NON da replicare sui fornitori

Il cliente ha logica **esclusiva del ciclo attivo utility** che non ha senso nel ciclo passivo:

| Elemento cliente | Perche esiste | Applicabile a fornitori |
|-----------------|---------------|------------------------|
| `istanza_utility_id` FK | Lega il cliente a un ciclo servizio su indirizzo | **NO** — i fornitori non hanno istanze |
| `billing_account_id` FK | Account di fatturazione (a chi fatturare) | **NO** — il fornitore fattura a noi, non il contrario |
| `pdp_id` FK + GIST exclusion | Punto di prelievo (contatore fisico) | **NO** — concetto utility |
| `utility_id` FK | Servizio specifico (gas, idrico, ecc.) | **NO** — concetto utility |
| `periodo` DATERANGE | Range temporale cliente attivo su PDP | **NO** — non c'e esclusivita temporale per i fornitori |
| Trigger `sync_pdp`, `sync_utility_from_ba`, `set_parent_istanza`, `set_periodo` | Sincronizzazione catena istanza→BA→cliente→PDP | **NO** — catena che non esiste |
| `codice_cig/cup/commessa` | Codici tracciabilita PA per appalti | **DA VALUTARE** — potrebbe servire anche lato acquisti |
| `garanzia_tipo/importo` | Depositi cauzionali clienti | **NO** — concetto diverso lato fornitori |

### Cosa e SIMMETRICO tra clienti e fornitori (stessa logica, adattata al dominio)

| Concetto | Clienti | Fornitori (attuale) | Gap |
|----------|---------|---------------------|-----|
| Stato gestito | FK → `config.stati_cliente` | VARCHAR libero `stato_operativo` | **DA CORREGGERE** |
| Termini pagamento | FK → `config.termini_pagamento` | `giorni_pagamento` + `fine_mese` manuali | **DA AGGIUNGERE FK** |
| Modalita pagamento | FK → `config.modalita_pagamento` | FK → `config.modalita_pagamento` | OK |
| Require attivo su FK | su IVA, PDP, termini | nessuno | **DA AGGIUNGERE** |
| Vista dettaglio | `vw_clienti_codice_ba` | nessuna | **DA CREARE** |
| Guard attivo per ciclo doc | implicito via stato cliente | nessuno | **DA CREARE** |

### Cosa MANCA rispetto al pattern ruoli recenti (vettori, emittenti)

| Elemento | Vettori | Emittenti F. | Fornitori (attuale) | Gap |
|----------|---------|--------------|---------------------|-----|
| `uid` UUID uuidv7() | si | si | **no** | **DA AGGIUNGERE** |
| `descrizione` | si | si | no (usa ragione_sociale del soggetto) | Non necessaria — il fornitore si identifica con la ragione sociale del soggetto |

---

## Stato attuale — Cosa esiste gia

### Tabella `anagrafiche.fornitori`

| Area | Campi | Stato |
|------|-------|-------|
| Identita | `id` (BIGINT PK), `soggetto_ruolo_id` (FK UNIQUE 1:1), `codice` (VARCHAR UNIQUE) | OK |
| Stato | `attivo` (BOOLEAN), `stato_operativo` (VARCHAR libero) | DA MIGRARE |
| Pagamento | `valuta_id` → config.valute, `modalita_pagamento_id` → config.modalita_pagamento, `giorni_pagamento`, `fine_mese` | PARZIALE |
| Fiscale | `split_payment`, `ritenuta_acconto`, `ritenuta_aliquota` (NUMERIC), `regime_fiscale` (codice RF SdI), `bollo_esente` | OK |
| FE/SDI | `canale_fe` (VARCHAR 7, check lunghezza), `pec_email` | OK |
| Rating | `rating` (SMALLINT 0-100, check), `qualifica_scadenza` (DATE) | OK base |
| Audit | `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`, `storicizza` | OK |
| Estensioni | `note` (TEXT), `meta` (JSONB) | OK |

### Trigger esistenti su `anagrafiche.fornitori`

| Trigger | Fase | Funzione | Stato |
|---------|------|----------|-------|
| `trg_fornitori_guard_ruolo_fornitore_ins_upd` | BEFORE INS/UPD | `trgfn_fornitori_guard_ruolo_fornitore()` — valida ruolo FO via `script.fn_guard_soggetto_ruolo` | OK |
| `trg_fornitori_guard_normalize_ins_upd` | BEFORE INS/UPD | `trgfn_fornitori_guard_normalize()` — normalizza `canale_fe` uppercase no spazi | OK |
| `trg_fornitori_a10_lock_columns_upd` | BEFORE UPD | `script.trgfn_lock_columns('codice')` — blocca modifica codice | OK |
| `trg_fornitori_a10_delete_block_dlt` | AFTER DEL | `script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` | OK |
| `trg_fornitori_audit_data_user_upd` | BEFORE INS/UPD | `script.trgfn_audit_data_user_generic()` | OK |
| `trg_fornitori_gen_tx_id_ins_upd` | BEFORE INS/UPD | `dbops.trgfn_tx_id_managed()` | OK |
| `trg_fornitori_z90_storico_upd_dlt` | BEFORE UPD/DEL | `script.trgfn_storico_generic('fornitori_id')` | OK |

### Funzioni trigger esistenti

| Funzione | Scopo | Stato |
|----------|-------|-------|
| `anagrafiche.trgfn_fornitori_guard_ruolo_fornitore()` | Valida ruolo FO | OK |
| `anagrafiche.trgfn_fornitori_guard_normalize()` | Normalizza canale_fe | OK |

### Vincoli esistenti

| Vincolo | Tipo | Stato |
|---------|------|-------|
| `pk_fornitori` | PK su `id` | OK |
| `uq_fornitori_soggetto_ruolo_id` | UNIQUE 1:1 | OK |
| `uq_fornitori_codice` | UNIQUE codice | OK |
| `fk_fornitori_soggetti_ruoli` | FK → soggetti_ruoli | OK |
| `fk_fornitori_valute` | FK → config.valute | OK |
| `fk_fornitori_modalita_pagamento` | FK → config.modalita_pagamento | OK |
| `chk_fornitori_canale_fe_len` | CHECK char_length = 7 | OK |
| `chk_fornitori_rating` | CHECK 0..100 | OK |
| `chk_fornitori_ritenuta_aliquota` | CHECK range valido | OK |

### Indici esistenti

| Indice | Tipo | Stato |
|--------|------|-------|
| `ix_fornitori_attivo_stato` | B-Tree su (attivo, stato_operativo) | OK |
| `ix_fornitori_codice_trgm` | GIN trgm su codice | OK |

### Infrastruttura trasversale gia disponibile (layer soggetto/ruolo)

Queste tabelle funzionano **gia** per il ruolo FORNITORE senza modifiche:

- **Indirizzi**: `indirizzi_soggetti` (livello soggetto) + `indirizzi` (livello ruolo) — cascata risoluzione attiva
- **Contatti**: `contatti` — multi-livello (soggetto, ruolo, utility)
- **Conti bancari**: `soggetti_conti_bancari` (livello soggetto) + `soggetti_ruoli_conti_bancari` (livello ruolo) — cascata risoluzione via `vw_conti_bancari_per_ruolo`

---

## Modifiche da implementare

### STEP 1 — Tabella `config.stati_fornitore` (nuova)

**Motivazione:** `stato_operativo` e attualmente VARCHAR libero. Va normalizzato con una tabella di riferimento come `config.stati_cliente`.

**DDL:**

```sql
CREATE TABLE config.stati_fornitore (
    id              INTEGER         NOT NULL GENERATED BY DEFAULT AS IDENTITY,
    codice_interno  VARCHAR(4)      NOT NULL,   -- AT, SO, CE, BL, VE
    codice          VARCHAR(4)      NOT NULL,
    descrizione     VARCHAR(100)    NOT NULL DEFAULT '',
    descrizione_breve VARCHAR(20)   NOT NULL,
    attivo          BOOLEAN         NOT NULL DEFAULT true,
    blocca_ordini   BOOLEAN         NOT NULL DEFAULT false,
    -- audit
    data_insert     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    user_insert     TEXT            NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    user_update     TEXT            NOT NULL DEFAULT CURRENT_USER,

    CONSTRAINT pk_stati_fornitore PRIMARY KEY (id),
    CONSTRAINT uq_stati_fornitore_codice_interno UNIQUE (codice_interno)
);

COMMENT ON TABLE config.stati_fornitore
IS 'Tabella di riferimento per gli stati operativi dei fornitori.';
```

**Trigger:**

| Trigger | Funzione | Evento |
|---------|----------|--------|
| `trg_stati_fornitore_a10_lock_columns_upd` | `script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` | BEFORE UPDATE |
| `trg_stati_fornitore_audit_data_user_upd` | `script.trgfn_audit_data_user_generic()` | BEFORE INSERT/UPDATE |

**Seed dati:**

| codice_interno | descrizione | descrizione_breve | blocca_ordini |
|----------------|-------------|-------------------|---------------|
| `VE` | In verifica/valutazione | In verifica | true |
| `AT` | Attivo / Qualificato | Attivo | false |
| `SO` | Sospeso | Sospeso | true |
| `CE` | Cessato | Cessato | true |
| `BL` | Blacklist | Blacklist | true |

**File migration:**

- `db/changelog/migrations_v2/00_schema/config/YYYYMMDD-NN-table-stati_fornitore.yaml`
- `db/changelog/migrations_v2/20_code/config/YYYYMMDD-NN-trigger-stati_fornitore.yaml`
- `db/changelog/migrations_v2/80_data/config/YYYYMMDD-NN-seed-stati_fornitore.yaml`

---

### STEP 2 — ALTER TABLE `anagrafiche.fornitori`: aggiunta `uid` UUID

**Motivazione:** i ruoli piu recenti (vettori, emittenti_fiscali) hanno `uid UUID NOT NULL DEFAULT uuidv7()` con UNIQUE. I fornitori non ce l'hanno. L'`uid` serve per:

- Esporre un identificatore stabile nelle API senza rivelare il BIGINT sequenziale
- Allineamento al pattern standard dei ruoli

**Azioni:**

1. Aggiungere colonna `uid UUID NOT NULL DEFAULT uuidv7()`
2. Aggiungere vincolo `uq_fornitori_uid UNIQUE (uid)`
3. Aggiungere indice (creato automaticamente dal UNIQUE)

**File migration:**

- `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-NN-alter-fornitori-uid.yaml`

**Nota:** per i record esistenti, l'`DEFAULT uuidv7()` assegnera automaticamente un uid al momento della ALTER.

---

### STEP 3 — ALTER TABLE `anagrafiche.fornitori`: migrazione `stato_operativo` → FK

**Azioni:**

1. Aggiungere colonna `stato_fornitore_id INTEGER` (nullable inizialmente)
2. Popolare `stato_fornitore_id` da mapping `stato_operativo` → `config.stati_fornitore.codice_interno`
3. Aggiungere FK `fk_fornitori_stati_fornitore` → `config.stati_fornitore(id)`
4. Impostare NOT NULL + DEFAULT (stato `VE` = in verifica)
5. Droppare colonna `stato_operativo`
6. Aggiornare indice `ix_fornitori_attivo_stato` → `ix_fornitori_attivo_stato_fornitore` su `(attivo, stato_fornitore_id)`

**Trigger nuovi:**

| Trigger | Funzione | Evento | Scopo |
|---------|----------|--------|-------|
| `trg_fornitori_a10_stato_fornitore_require_attivo_ins_upd` | `dbops.trgfn_child_requires_active_parent('config', 'stati_fornitore', 'attivo', 'stato_fornitore_id')` | AFTER INS/UPD | Impedisce uso di stato disattivato |

**File migration:**

- `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-NN-alter-fornitori-stato_fornitore_id.yaml`
- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-trigger-fornitori-require-stato-attivo.yaml`

---

### STEP 4 — ALTER TABLE `anagrafiche.fornitori`: aggiunta `termine_pagamento_id`

**Motivazione:** i clienti hanno gia `termine_pagamento_id` → `config.termini_pagamento`. I fornitori gestiscono i termini tramite `giorni_pagamento` + `fine_mese` ma manca il collegamento formale alla tabella `termini_pagamento` che gestisce rate, offset e calcolo scadenze strutturato.

**Azioni:**

1. Aggiungere colonna `termine_pagamento_id BIGINT` (nullable)
2. Aggiungere FK `fk_fornitori_termini_pagamento` → `config.termini_pagamento(id)`
3. Valutare se mantenere `giorni_pagamento` e `fine_mese` come override/fallback o deprecarli

**Trigger nuovi:**

| Trigger | Funzione | Evento | Scopo |
|---------|----------|--------|-------|
| `trg_fornitori_a10_termini_pagamento_require_attivo_ins_upd` | `dbops.trgfn_child_requires_active_parent('config', 'termini_pagamento', 'attivo', 'termine_pagamento_id')` | AFTER INS/UPD | Impedisce uso di termini disattivati |

**File migration:**

- `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-NN-alter-fornitori-termine_pagamento_id.yaml`
- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-trigger-fornitori-require-termine-attivo.yaml`

---

### ~~STEP 5~~ — RIMOSSO: Trigger `require_attivo` su valuta e modalita pagamento

> **Non applicabile**: `config.valute` e `config.modalita_pagamento` non hanno colonna `attivo`
> e non e previsto aggiungerla. I trigger require_attivo su queste FK non si faranno.
> I trigger require_attivo su `stato_fornitore_id` e `termine_pagamento_id` sono gia
> implementati nello STEP 5b (migration 20260324-28).

---

### ~~STEP 6~~ — RIMOSSO: auto-generazione codice fornitore

> **Non necessario**: il codice fornitore e gestito dall'automatismo esistente
> `config.sistema_codici` + `script.fn_generate_codice` (pattern centralizzato).
> Non serve sequenza dedicata ne trigger specifico.

---

### STEP 6 — Aggiornamento `trgfn_fornitori_guard_normalize`

**Motivazione:** la funzione attuale normalizza solo `canale_fe`. Va estesa per normalizzare anche `pec_email` (lowercase trim) e validare coerenza ritenuta (`ritenuta_aliquota` obbligatoria se `ritenuta_acconto = true`).

**Logica da aggiungere:**

```sql
-- Normalizza pec_email
IF NEW.pec_email IS NOT NULL THEN
    NEW.pec_email := lower(btrim(NEW.pec_email));
END IF;

-- Guard: ritenuta coerente
IF NEW.ritenuta_acconto = true AND (NEW.ritenuta_aliquota IS NULL OR NEW.ritenuta_aliquota <= 0) THEN
    PERFORM script.fn_log_and_raise_error(
        'E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA',
        'Se ritenuta_acconto = true, ritenuta_aliquota deve essere > 0'
    );
END IF;

IF NEW.ritenuta_acconto IS DISTINCT FROM true THEN
    NEW.ritenuta_aliquota := NULL;
END IF;
```

**File migration:**

- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-update-trgfn-fornitori-guard-normalize.yaml` (runOnChange: true)

---

### STEP 7 — Vista `anagrafiche.vw_fornitori_dettaglio`

**Motivazione:** i clienti hanno `vw_clienti_codice_ba`. I fornitori non hanno nessuna vista di dettaglio. Serve per API list/search.

**Definizione:**

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_fornitori_dettaglio AS
SELECT
    f.id,
    f.codice,
    f.attivo,
    sf.codice_interno      AS stato_codice,
    sf.descrizione         AS stato_descrizione,
    sf.blocca_ordini,
    -- soggetto
    s.id                   AS soggetto_id,
    s.ragione_sociale_completa,
    s.codice_fiscale,
    s.partita_iva,
    -- pagamento
    v.iso_code             AS valuta_iso,
    mp.codice              AS modalita_pagamento_codice,
    mp.descrizione         AS modalita_pagamento_desc,
    tp.codice              AS termine_pagamento_codice,
    f.giorni_pagamento,
    f.fine_mese,
    -- fiscale
    f.split_payment,
    f.ritenuta_acconto,
    f.ritenuta_aliquota,
    f.regime_fiscale,
    f.bollo_esente,
    -- FE
    f.canale_fe,
    f.pec_email,
    -- rating
    f.rating,
    f.qualifica_scadenza,
    -- audit
    f.data_insert,
    f.data_update
FROM anagrafiche.fornitori f
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
LEFT JOIN config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
LEFT JOIN config.valute v           ON v.id  = f.valuta_id
LEFT JOIN config.modalita_pagamento mp ON mp.id = f.modalita_pagamento_id
LEFT JOIN config.termini_pagamento tp  ON tp.id = f.termine_pagamento_id;

COMMENT ON VIEW anagrafiche.vw_fornitori_dettaglio
IS 'Vista consolidata fornitori con dati soggetto, stato, pagamento e fiscale.';
```

**File migration:**

- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-view-vw_fornitori_dettaglio.yaml`

---

### STEP 8 — Funzione `fn_guard_fornitore_attivo`

**Motivazione:** serve una funzione guard riusabile per verificare che un fornitore sia attivo e non bloccato prima di creare ordini/DDT nel ciclo passivo.

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_fornitore_attivo(
    p_fornitore_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_attivo            BOOLEAN;
    v_blocca_ordini     BOOLEAN;
    v_stato_desc        VARCHAR;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_fornitore_id IS NULL OR p_fornitore_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'E_FORNITORE_ID_INVALIDO',
            'p_fornitore_id deve essere NOT NULL e > 0'
        );
    END IF;

    SELECT f.attivo, sf.blocca_ordini, sf.descrizione
    INTO   v_attivo, v_blocca_ordini, v_stato_desc
    FROM   anagrafiche.fornitori f
    LEFT JOIN config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
    WHERE  f.id = p_fornitore_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'E_FORNITORE_NON_TROVATO',
            format('Fornitore id=%s non trovato', p_fornitore_id)
        );
    END IF;

    IF v_attivo IS DISTINCT FROM true THEN
        PERFORM script.fn_log_and_raise_error(
            'E_FORNITORE_NON_ATTIVO',
            format('Fornitore id=%s non attivo', p_fornitore_id)
        );
    END IF;

    IF v_blocca_ordini = true THEN
        PERFORM script.fn_log_and_raise_error(
            'E_FORNITORE_BLOCCATO',
            format('Fornitore id=%s in stato "%s" — ordini bloccati', p_fornitore_id, v_stato_desc)
        );
    END IF;
END;
$$;
```

**Funzione check corrispondente:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_fornitore_attivo(
    p_fornitore_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    -- Puro boolean, no raise
    RETURN EXISTS (
        SELECT 1
        FROM   anagrafiche.fornitori f
        JOIN   config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
        WHERE  f.id = p_fornitore_id
          AND  f.attivo = true
          AND  sf.blocca_ordini = false
    );
END;
$$;
```

**File migration:**

- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-fn-guard-fornitore-attivo.yaml`
- `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-NN-fn-check-fornitore-attivo.yaml`

---

### STEP 9 — Integrazione con ciclo passivo (`acquisti`)

**Motivazione:** le tabelle `acquisti.ordini` e `acquisti.ddt` devono validare il fornitore. Servono:

**Trigger su `acquisti.ordini`:**

| Trigger | Scopo |
|---------|-------|
| `trg_ordini_a10_guard_fornitore_attivo_ins_upd` | Chiama `anagrafiche.fn_guard_fornitore_attivo(NEW.fornitore_id)` per impedire ordini verso fornitori bloccati |

**Trigger su `acquisti.ddt`:**

| Trigger | Scopo |
|---------|-------|
| `trg_ddt_a10_guard_fornitore_attivo_ins` | Chiama `anagrafiche.fn_guard_fornitore_attivo(NEW.fornitore_id)` per impedire DDT da fornitori bloccati |

**Nota:** verificare che `acquisti.ordini` e `acquisti.ddt` abbiano colonna `fornitore_id` con FK verso `anagrafiche.fornitori`. Se manca, aggiungerla.

**File migration:**

- `db/changelog/migrations_v2/20_code/acquisti/YYYYMMDD-NN-trigger-ordini-guard-fornitore-attivo.yaml`
- `db/changelog/migrations_v2/20_code/acquisti/YYYYMMDD-NN-trigger-ddt-guard-fornitore-attivo.yaml`

---

## Elementi futuri (non in questo sprint)

### A. Tabella `fornitore_documenti_compliance`

Documenti legali con scadenze (DURC, antimafia, ISO, SOA). Richiede:
- Tabella `anagrafiche.fornitore_documenti_compliance`
- Tabella config `config.tipi_documento_compliance` (catalogo tipi)
- Vista `vw_fornitori_documenti_in_scadenza`
- Funzione alert `fn_check_documenti_compliance_scaduti`
- Job pgAgent per notifica scadenze

**Dipendenza:** sistema notifiche/alert non ancora implementato.

### B. Vendor rating strutturato

Attualmente `rating` e un SMALLINT 0-100 manuale. Evoluzione possibile:
- Tabella `anagrafiche.fornitori_valutazioni` (storico valutazioni periodiche)
- Calcolo automatico da: rispetto lead time, contestazioni, puntualita pagamenti

**Dipendenza:** ciclo passivo operativo (ordini, DDT, fatture passive).

### C. Categorie merceologiche

La tabella `config.categorie_merceologiche` non esiste. Se necessaria:
- Creare tabella config con struttura gerarchica (parent_id)
- Aggiungere FK su `anagrafiche.fornitori`

**Dipendenza:** definire tassonomia (livelli, collegamento ATECO).

### D. Macchina a stati con transizioni

Transizioni formalizzate `config.transizioni_stati_fornitore` (come `transizioni_stati_flussi_pratiche`):
- VE → AT (qualificazione)
- AT → SO (sospensione)
- SO → AT (riattivazione)
- AT → CE (cessazione)
- CE → BL (blacklist, terminale)

**Dipendenza:** valutare se servono subito o se basta il campo stato_fornitore_id senza vincolo di transizione.

---

## Riepilogo file migration da generare

### Ordine di esecuzione (dipendenze)

```
STEP 1: config.stati_fornitore (tabella + seed)                          ✅ FATTO (DDL + CSV + YAML seed)
    ↓
STEP 2: ALTER fornitori — uid UUID (allineamento pattern ruoli recenti)  ✅ FATTO
    ↓
STEP 3: ALTER fornitori — stato_fornitore_id + FK + NOT NULL + drop      ✅ FATTO (completo)
    ↓
STEP 4: ALTER fornitori — termine_pagamento_id + FK                      ✅ FATTO
    ↓
STEP 5: ~~Trigger require_attivo valuta/modalita~~ RIMOSSO (no colonna attivo)
    ↓
STEP 5b: Trigger require_attivo su FK (stato_fornitore, termini)         ✅ FATTO
    ↓
STEP 5c: Trigger su config.stati_fornitore (lock + audit)                ✅ FATTO
    ↓
STEP 6: Update trgfn_fornitori_guard_normalize (pec, ritenuta)           ✅ FATTO
    ↓
STEP 7: Vista vw_fornitori_dettaglio                                     ✅ FATTO
    ↓
STEP 8: fn_guard_fornitore_attivo + fn_check_fornitore_attivo            ✅ FATTO
    ↓
STEP 9: Trigger guard su acquisti.ordini e acquisti.ddt                   FUTURO (ciclo passivo)
```

> **Nota:** STEP 6 originale (gen_codice_fornitore) rimosso — il codice e gestito
> dall'automatismo centralizzato `config.sistema_codici` + `script.fn_generate_codice`.

### Lista file stimata

| N. | STEP | Percorso | Tipo | Stato |
|----|------|----------|------|-------|
| 1 | 1 | `00_schema/config/20260324-21-create-stati-fornitore-mctit.yaml` | DDL | ✅ |
| 2 | 1 | `80_data/changelog/20260324-26-upsert-config-stati-fornitore-mctit.yaml` | Seed CSV | ✅ |
| 3 | 2 | `00_schema/anagrafiche/20260324-22-alter-fornitori-add-uid-mctit.yaml` | DDL | ✅ |
| 4 | 3 | `00_schema/anagrafiche/20260324-23-alter-fornitori-add-stato-fornitore-id-mctit.yaml` | DDL | ✅ |
| 5 | 3 | `00_schema/anagrafiche/20260324-32-alter-fornitori-finalize-stato-fornitore-id-mctit.yaml` | DDL | ✅ |
| 7 | 4 | `00_schema/anagrafiche/20260324-24-alter-fornitori-add-termine-pagamento-id-mctit.yaml` | DDL | ✅ |
| 8 | 5 | `20_code/config/20260324-27-trigger-stati-fornitore-mctit.yaml` | Trigger | ✅ |
| 9 | 5b | `20_code/anagrafiche/20260324-28-trigger-fornitori-require-attivo-fk-mctit.yaml` | Trigger | ✅ |
| 10 | 6 | `20_code/anagrafiche/20260324-29-update-trgfn-fornitori-guard-normalize-mctit.yaml` | Trigger fn | ✅ |
| 11 | 7 | `20_code/anagrafiche/20260324-30-create-view-vw-fornitori-dettaglio-mctit.yaml` | View | ✅ |
| 12 | 8 | `20_code/anagrafiche/20260324-31-create-fn-guard-check-fornitore-attivo-mctit.yaml` | Function | ✅ |
| 13 | 9 | Trigger guard fornitore su acquisti.ordini e acquisti.ddt | Trigger | futuro |

---

## Test pgTAP previsti

| File test | Copertura |
|-----------|-----------|
| `db/pgtap/anagrafiche/test_fornitori_stati.sql` | Insert/update stati, transizioni, blocca_ordini |
| `db/pgtap/anagrafiche/test_fornitori_gen_codice.sql` | Auto-generazione codice, unicita, codice manuale |
| `db/pgtap/anagrafiche/test_fornitori_guard_normalize.sql` | Normalizzazione pec, coerenza ritenuta |
| `db/pgtap/anagrafiche/test_fornitori_guard_attivo.sql` | fn_guard_fornitore_attivo, fn_check_fornitore_attivo |
| `db/pgtap/anagrafiche/test_fornitori_require_attivo_fk.sql` | FK require_attivo su valuta, modalita, termini, stato |
| `db/pgtap/acquisti/test_ordini_guard_fornitore.sql` | Blocco ordini per fornitore inattivo/bloccato |

---

## Confronto pattern clienti vs fornitori (post-implementazione)

| Elemento | Clienti | Fornitori (post) |
|----------|---------|------------------|
| Tabella master | `anagrafiche.clienti` | `anagrafiche.fornitori` |
| FK ruolo | `soggetto_ruolo_id` UNIQUE | `soggetto_ruolo_id` UNIQUE |
| Stato | FK → `config.stati_cliente` | FK → `config.stati_fornitore` |
| Codice | Auto via istanza/BA | Auto via `fn_gen_codice_fornitore` |
| Modalita pagamento | FK → `config.modalita_pagamento` | FK → `config.modalita_pagamento` |
| Termini pagamento | FK → `config.termini_pagamento` | FK → `config.termini_pagamento` |
| Valuta | via BA | FK → `config.valute` |
| Guard ruolo | `trgfn_clienti_guard_ruolo_cliente` | `trgfn_fornitori_guard_ruolo_fornitore` |
| Guard attivo | via stato cliente | `fn_guard_fornitore_attivo` |
| Require attivo FK | IVA, PDP, termini | termini, stato (valuta e modalita non hanno `attivo`) |
| Lock codice | n/a | `trgfn_lock_columns('codice')` |
| Delete block | GUC maintenance | GUC maintenance |
| Audit | standard | standard |
| Storicizzazione | standard | standard |
| Vista dettaglio | `vw_clienti_codice_ba` | `vw_fornitori_dettaglio` |
| Indirizzi | cascata soggetto/ruolo | cascata soggetto/ruolo (gia funzionante) |
| Contatti | cascata multi-livello | cascata multi-livello (gia funzionante) |
| Conti bancari | cascata soggetto/ruolo | cascata soggetto/ruolo (gia funzionante) |

---

## Analisi completezza DB — Segnalazioni

### Conferme positive

Il lavoro DB e solido: tutti gli STEP 1-8 risultano FATTO. Il pattern ruoli e rispettato (guard, normalize, lock, delete block, audit, storicizzazione, require_attivo su FK config).

### Gap identificati

| # | Area | Problema | Priorita | Azione suggerita |
|---|------|----------|----------|------------------|
| G1 | Lookup whitelist | `config.stati_fornitore` **non e nella whitelist** del lookup generico (`core/db/dbops_repository.py`) | Alta | Aggiungere `"config.stati_fornitore"` alla lista in `dbops_repository.py` — serve per i filtri/dropdown frontend |
| G2 | STEP 9 — Acquisti | `acquisti.ordini` e `acquisti.ddt` **non hanno** colonna `fornitore_id` FK verso `anagrafiche.fornitori` | Bassa (futuro) | Le tabelle acquisti esistono con struttura completa ma il collegamento FK fornitore va aggiunto quando si sviluppa il ciclo passivo. Non blocca lo sviluppo fornitori |
| G3 | Navigation frontend | Fornitori **non presente** in `core/navigation.js` ne nelle rotte Vue Router | Alta | Da aggiungere durante lo sviluppo frontend (FE-1) |

**Nota su valute e modalita pagamento**: `config.valute` e `config.modalita_pagamento` non hanno colonna `attivo` e non e previsto aggiungerla. I trigger require_attivo su queste FK non si faranno. I due trigger require_attivo effettivi (su `stato_fornitore_id` e `termine_pagamento_id`) sono gia implementati.

### Raccomandazioni

1. **G1** e bloccante per il frontend: senza il lookup, il dropdown stati fornitore non funziona
2. **G2** e correttamente marcato FUTURO nel documento
3. **G3** si risolve naturalmente durante lo step FE-1

---

## Piano di sviluppo Backend + Frontend

> **Metodologia**: Sviluppo concentrico — ogni anello chiude un percorso end-to-end verificabile.
> **Posizione**: Anello 1 (Dati Base) — i fornitori sono un ruolo anagrafico, stessa natura di clienti/vettori/emittenti.
> **Base di riferimento**: pattern clienti (`views_clienti.py`, `clienti_service.py`, `clienti_repository.py`, `ClienteDrawer.vue`, `ClientiSearchTable.vue`, `ClientiView.vue`) con **semplificazione significativa** — nessuna cascata istanza/BA.

### Differenze chiave clienti vs fornitori

| Aspetto | Clienti | Fornitori |
|---------|---------|-----------|
| Cascata creazione | Complessa: ruolo CL → istanza_utility → billing_account → cliente | **Semplice**: ruolo FO → insert fornitore |
| Dipendenza utility | Si (FK istanza, BA, utility, PDP) | **No** — nessun concetto utility |
| Stato | FK → `config.stati_cliente` | FK → `config.stati_fornitore` |
| Campi specifici | PA (CIG/CUP/commessa), garanzia, servizio da fatturare | Ritenuta acconto, rating, qualifica, canale FE, PEC, bollo |
| Vista DB | `vw_clienti_codice_ba` (JOIN BA + istanza) | `vw_fornitori_dettaglio` (JOIN diretto soggetto + config) |
| Complessita service | Alta (~200 righe, validazione multi-entita) | **Media** (~100 righe, CRUD diretto) |

---

### FASE 1 — Backend: Repository + Service + API

> Anello concentrico: **chiude il percorso dati** dal DB all'endpoint REST.

#### BE-1: Repository (`fornitori_repository.py`)

**File**: `backend/apps/anagrafiche/db/fornitori_repository.py`

**Classe**: `FornitoriRepository`

**Metodi da implementare:**

| Metodo | Tipo | SQL | Note |
|--------|------|-----|------|
| `list_fornitori(search, stato_fornitore_id, attivo, limit, offset, order_by, order_dir)` | Read | SELECT su `vw_fornitori_dettaglio` con filtri, ILIKE su codice/ragione_sociale/partita_iva/codice_fiscale, paginazione | Tiebreaker `f.id` obbligatorio |
| `get_fornitore(fornitore_id)` | Read | SELECT su `vw_fornitori_dettaglio` WHERE id = %s | Riga completa con decodifiche FK |
| `create_fornitore(**kwargs)` | Write | INSERT INTO `anagrafiche.fornitori` con colonne ammesse | Colonne: soggetto_ruolo_id, codice, stato_fornitore_id, attivo, valuta_id, modalita_pagamento_id, termine_pagamento_id, giorni_pagamento, fine_mese, split_payment, ritenuta_acconto, ritenuta_aliquota, regime_fiscale, bollo_esente, canale_fe, pec_email, rating, qualifica_scadenza, note, meta |
| `update_fornitore(fornitore_id, data)` | Write | UPDATE delta con normalizzazione nullable (stringhe vuote → NULL) | `_UPDATE_ALLOWED` e `_UPDATE_NULLABLE` come in clienti |
| `get_or_create_ruolo_fornitore(soggetto_id)` | Write | Chiama `script.fn_get_or_create_soggetto_ruolo(soggetto_id, 'FO')` | Pattern identico a clienti |
| `exists(fornitore_id)` | Read | SELECT EXISTS WHERE id = %s | Per guard service |

**Pattern**: cursor.execute + parameterized queries, `row_to_dict()` + `rows_to_list()` helper da `_helpers.py`.

#### BE-2: Service (`fornitori_service.py`)

**File**: `backend/apps/anagrafiche/services/fornitori_service.py`

**Classe**: `FornitoriService`

**Metodi:**

| Metodo | Scopo | Logica |
|--------|-------|--------|
| `list_fornitori(**params)` | Lista paginata | Delega a repository, restituisce dict con count + results |
| `get_fornitore(fornitore_id)` | Dettaglio singolo | Guard esistenza, restituisce dict completo |
| `crea_fornitore(payload)` | Creazione end-to-end | 1) `_require_str(payload, "soggetto_id")` 2) `get_or_create_ruolo_fornitore(soggetto_id)` 3) INSERT fornitore in `transaction.atomic()` |
| `update_fornitore(fornitore_id, payload)` | Aggiornamento parziale | Guard esistenza, delta update con normalizzazione |

**Validazioni service:**
- `soggetto_id` obbligatorio (POST)
- Campi opzionali con tipizzazione: `optional_int`, `optional_bool`, `optional_iso_date`
- Coerenza ritenuta: se `ritenuta_acconto=true` allora `ritenuta_aliquota` obbligatoria (nota: gia validato dal trigger DB, ma il service puo dare errore user-friendly prima)
- Duplicato: catch `IntegrityError` su `uq_fornitori_soggetto_ruolo_id` → `E_ANAG_DUPLICATO`

**Error codes** (gia registrati in `error_policies.py`):
- `E_ANAG_VALIDAZIONE` (400) — input invalido
- `E_ANAG_NOT_FOUND` (404) — fornitore non trovato
- `E_ANAG_DUPLICATO` (409) — soggetto ha gia ruolo FO

#### BE-3: Views (`views_fornitori.py`)

**File**: `backend/apps/anagrafiche/api/views_fornitori.py`

**Endpoint:**

| Classe | Metodo | Path | Scopo |
|--------|--------|------|-------|
| `FornitoriView` | GET | `/api/v1/anagrafiche/fornitori/` | Lista paginata con search + filtri |
| `FornitoriView` | POST | `/api/v1/anagrafiche/fornitori/` | Crea fornitore |
| `FornitoriDetailView` | GET | `/api/v1/anagrafiche/fornitori/<id>/` | Dettaglio |
| `FornitoriDetailView` | PATCH | `/api/v1/anagrafiche/fornitori/<id>/` | Aggiorna campi editabili |

**Pattern:**
- Eredita da `DomainAPIView` con `area_funzionale = "anagrafiche"`
- `is_search_endpoint = True` su `FornitoriView`
- POST usa `handle_post_json` con `require_idempotency_key=True`
- PATCH usa `request.data` diretto (pattern adottato)
- `@extend_schema` con `inline_serializer` per ogni metodo

#### BE-4: Routing (`urls.py`)

**File**: `backend/apps/anagrafiche/api/urls.py` — aggiungere:

```python
# Fornitori
path("fornitori/", FornitoriView.as_view(), name="anagrafiche-fornitori-list"),
path("fornitori/<int:fornitore_id>/", FornitoriDetailView.as_view(), name="anagrafiche-fornitori-detail"),
```

#### BE-5: Lookup whitelist

**File**: `backend/apps/core/db/dbops_repository.py` — aggiungere `"config.stati_fornitore"` alla whitelist lookup generico.

#### BE-6: Test

**File test API**: `backend/apps/anagrafiche/tests/api/test_fornitori_api.py`

| Test | Cosa verifica |
|------|---------------|
| `test_list_fornitori_ok` | GET lista con mock service |
| `test_get_fornitore_ok` | GET dettaglio |
| `test_get_fornitore_not_found` | 404 |
| `test_create_fornitore_ok` | POST con payload valido |
| `test_update_fornitore_ok` | PATCH con payload parziale |
| `test_update_fornitore_not_found` | PATCH 404 |

**File test service**: `backend/apps/anagrafiche/tests/services/test_fornitori_service.py`

| Test | Cosa verifica |
|------|---------------|
| `test_list_ok` | Delega a repository |
| `test_get_ok` | Restituisce dettaglio |
| `test_get_not_found` | Raise ServiceError E_ANAG_NOT_FOUND |
| `test_create_ok` | get_or_create ruolo + insert + transaction |
| `test_create_soggetto_missing` | Validazione soggetto_id obbligatorio |
| `test_create_duplicate` | IntegrityError → E_ANAG_DUPLICATO |
| `test_update_ok` | Delta update |
| `test_update_not_found` | Raise E_ANAG_NOT_FOUND |
| `test_update_no_valid_fields` | Nessun campo valido → E_ANAG_VALIDAZIONE |

**Pattern test**: `unittest.TestCase` con mock repository (no DB reale), compatibile CI.

---

### FASE 2 — Frontend: Store + API + Componenti

> Anello concentrico: **chiude il percorso visivo** dall'API al browser.

#### FE-1: API client + Store + Rotta + Navigazione

**File API**: `frontend/src/anagrafiche/api/anagrafiche.js` — aggiungere:

```javascript
// --- Fornitori ---
export function listFornitori(params = {}) { ... }
export function getFornitore(id) { ... }
export function createFornitore(payload) { ... }
export function updateFornitore(fornitoreId, payload) { ... }
```

**File Store**: `frontend/src/anagrafiche/stores/fornitori.js`

Store Pinia `useFornitoriStore()` con:
- State: `items`, `totalRecords`, `loading`, `filters` (search, stato_fornitore_id, attivo, limit, offset, order_by, order_dir)
- Actions: `fetchList()`, `fetchDetail(id)`, `create(payload)`, `update(fornitoreId, payload)`
- Integrazione `useTabEvents()` per `emitDataChanged('fornitore', id)`

**Rotta**: `frontend/src/router/` — aggiungere:

```javascript
{
  path: '/anagrafiche/fornitori',
  name: 'fornitori',
  component: () => import('@/anagrafiche/views/FornitoriView.vue'),
  meta: { requiresAuth: true, area: 'anagrafiche', title: 'Fornitori' }
}
```

**Navigazione**: `frontend/src/core/navigation.js` — aggiungere voce Fornitori nel dominio Anagrafiche con icona appropriata (es. `pi-truck` o `pi-building`).

#### FE-2: `FornitoriSearchTable.vue`

**File**: `frontend/src/anagrafiche/components/FornitoriSearchTable.vue`

**Colonne DataTable:**

| Colonna | Campo | Sortable | Note |
|---------|-------|----------|------|
| Codice | `codice` | Si | |
| Ragione sociale | `ragione_sociale_completa` | Si | Da soggetto via vista |
| P.IVA | `partita_iva` | No | |
| C.F. | `codice_fiscale` | No | |
| Mod. pagamento | `modalita_pagamento_desc` | No | |
| Stato | `stato_descrizione` | Si | Tag con severity (AT=success, SO=warn, CE/BL=danger, VE=info) |
| Attivo | `attivo` | Si | Badge si/no |

**Toolbar:**
- Search input (debounce 400ms via `useSearchTable`)
- Filtro Stato fornitore (Select via `useLookup('config.stati_fornitore')`)
- Filtro Attivo (Select boolean)
- Reload button
- NewButton

**Click riga** → emit `@row-click` per apertura drawer edit.

**Pulsanti riga** (come clienti): Contatti, Indirizzi, Conti bancari (3 icone).

#### FE-3: `FornitoreDrawer.vue`

**File**: `frontend/src/anagrafiche/components/FornitoreDrawer.vue`

**Larghezza**: `DRAWER_WIDTH.STANDARD` (640px) — form non complesso come pratiche.

**Modalita CREATE:**

| Sezione | Campi | Componente |
|---------|-------|------------|
| Soggetto | SoggettoResolver (search/create soggetto) | Componente esistente riutilizzabile |
| Pagamento | `modalita_pagamento_id` (Select lookup), `termine_pagamento_id` (Select lookup), `valuta_id` (Select lookup), `giorni_pagamento` (InputNumber), `fine_mese` (Checkbox) | |
| Fiscale | `split_payment` (Checkbox), `ritenuta_acconto` (Checkbox), `ritenuta_aliquota` (InputNumber, visibile se ritenuta_acconto), `regime_fiscale` (InputText), `bollo_esente` (Checkbox) | |
| FE/SDI | `canale_fe` (InputText, maxlength 7), `pec_email` (InputText) | |
| Rating | `rating` (InputNumber 0-100), `qualifica_scadenza` (Calendar) | |
| Note | `note` (Textarea) | |

**Modalita EDIT:**
- Header: codice fornitore (readonly) + stato (Tag)
- Tutti i campi editabili tranne `soggetto_ruolo_id` e `codice`
- Sezione info: data_insert, data_update (readonly)
- Pulsanti gestione: Contatti, Indirizzi, Conti bancari (come clienti)

**Sub-drawer**: ContattiSoggettoDrawer, IndirizziSoggettoDrawer, ContiBancariDrawer — gia esistenti, riutilizzabili tramite `soggetto_id` e `soggetto_ruolo_id`.

#### FE-4: `FornitoriView.vue`

**File**: `frontend/src/anagrafiche/views/FornitoriView.vue`

Orchestrator della pagina — pattern identico a `ClientiView.vue`:
- `FornitoriSearchTable` + `FornitoreDrawer` + 3 sub-drawer
- Composable: `useDrawerState()`, `useReadonlyMode()`, `useFornitoriStore()`
- Event flow: `@new` → `openCreate()`, `@row-click` → `editRow()`, sub-drawer per contatti/indirizzi/conti

#### FE-5: Traduzioni i18n

**File**: `frontend/src/locales/it.json` — aggiungere sezione `fornitori`:

```json
{
  "fornitori": {
    "titolo": "Fornitori",
    "search_placeholder": "Cerca per codice, ragione sociale, P.IVA...",
    "filtro_stato": "Stato",
    "filtro_attivo": "Attivo",
    "nuovo_fornitore": "Nuovo fornitore",
    "fornitore_creato": "Fornitore creato con successo",
    "fornitore_salvato": "Fornitore salvato con successo",
    "col_codice": "Codice",
    "col_ragione_sociale": "Ragione sociale",
    "col_partita_iva": "Partita IVA",
    "col_codice_fiscale": "Codice fiscale",
    "col_modalita_pagamento": "Mod. pagamento",
    "col_stato": "Stato",
    "col_attivo": "Attivo",
    "sez_pagamento": "Pagamento",
    "sez_fiscale": "Fiscale",
    "sez_fe_sdi": "Fattura elettronica / SDI",
    "sez_rating": "Rating e qualifica",
    "sez_note": "Note"
  }
}
```

---

### FASE 3 — Test end-to-end e rifinitura

> Anello concentrico: **verifica coerenza** tra tutti gli strati.

#### T-1: Test backend CI

- Eseguire `./manage-test.sh apps.anagrafiche.tests -v 2` — tutti i test nuovi + regressione esistenti
- Verificare che i nuovi test funzionino senza DB (mock completi)

#### T-2: Smoke test curl

**File**: `backend/scripts/tests/smoke-test-fornitori.sh`

| # | Test | Metodo | Path | Verifica |
|---|------|--------|------|----------|
| 1 | Lista vuota/paginata | GET | `/api/v1/anagrafiche/fornitori/` | 200 + envelope |
| 2 | Crea fornitore | POST | `/api/v1/anagrafiche/fornitori/` | 201 + id |
| 3 | Dettaglio | GET | `/api/v1/anagrafiche/fornitori/{id}/` | 200 + dati completi |
| 4 | Aggiorna | PATCH | `/api/v1/anagrafiche/fornitori/{id}/` | 200 |
| 5 | Dettaglio not found | GET | `/api/v1/anagrafiche/fornitori/99999/` | 404 |
| 6 | Crea duplicato | POST | `/api/v1/anagrafiche/fornitori/` (stesso soggetto) | 409 |
| 7 | Lookup stati | GET | `/api/v1/core/lookup/codici/?rel=config.stati_fornitore` | 200 + lista stati |

#### T-3: Test UI browser

- Navigazione sidebar → Anagrafiche → Fornitori
- Lista con paginazione, search, filtri stato/attivo
- Crea fornitore: seleziona soggetto → compila form → salva
- Edit fornitore: click riga → modifica campi → salva
- Sub-drawer: contatti, indirizzi, conti bancari
- Modalita sola lettura (utente senza permessi scrittura anagrafiche)

---

### Ordine di esecuzione (sviluppo concentrico)

```
FASE 1 — Backend (anello dati)
  │
  ├── BE-1: fornitori_repository.py         ← primo: accesso DB
  ├── BE-2: fornitori_service.py            ← orchestra il repository
  ├── BE-3: views_fornitori.py              ← espone via REST
  ├── BE-4: urls.py (aggiunta rotte)        ← registra endpoint
  ├── BE-5: lookup whitelist                ← abilita dropdown
  └── BE-6: test (API + service)            ← verifica anello
  │
FASE 2 — Frontend (anello presentazione)
  │
  ├── FE-1: API client + store + rotta + nav ← connessione al backend
  ├── FE-2: FornitoriSearchTable.vue         ← lista
  ├── FE-3: FornitoreDrawer.vue              ← form crea/modifica
  ├── FE-4: FornitoriView.vue                ← orchestrator pagina
  └── FE-5: Traduzioni i18n                  ← testi
  │
FASE 3 — Verifica (coerenza tra anelli)
  │
  ├── T-1: Test backend CI                   ← regressione
  ├── T-2: Smoke test curl                   ← end-to-end reale
  └── T-3: Test UI browser                   ← validazione visiva
```

### Stima file da creare/modificare

| Tipo | File | Azione |
|------|------|--------|
| Backend | `apps/anagrafiche/db/fornitori_repository.py` | **Nuovo** |
| Backend | `apps/anagrafiche/services/fornitori_service.py` | **Nuovo** |
| Backend | `apps/anagrafiche/api/views_fornitori.py` | **Nuovo** |
| Backend | `apps/anagrafiche/api/urls.py` | **Modifica** (aggiunta 2 path) |
| Backend | `apps/core/db/dbops_repository.py` | **Modifica** (aggiunta whitelist) |
| Backend | `apps/anagrafiche/tests/api/test_fornitori_api.py` | **Nuovo** |
| Backend | `apps/anagrafiche/tests/services/test_fornitori_service.py` | **Nuovo** |
| Backend | `backend/scripts/tests/smoke-test-fornitori.sh` | **Nuovo** |
| Frontend | `src/anagrafiche/api/anagrafiche.js` | **Modifica** (aggiunta 4 funzioni) |
| Frontend | `src/anagrafiche/stores/fornitori.js` | **Nuovo** |
| Frontend | `src/anagrafiche/components/FornitoriSearchTable.vue` | **Nuovo** |
| Frontend | `src/anagrafiche/components/FornitoreDrawer.vue` | **Nuovo** |
| Frontend | `src/anagrafiche/views/FornitoriView.vue` | **Nuovo** |
| Frontend | `src/router/` (file rotte) | **Modifica** (aggiunta rotta) |
| Frontend | `src/core/navigation.js` | **Modifica** (aggiunta voce) |
| Frontend | `src/locales/it.json` | **Modifica** (aggiunta sezione) |
| Doc | `docs/it/dev/api.md` | **Modifica** (aggiunta tabella endpoint fornitori) |

**Totale**: 8 file nuovi, 9 file modificati

---

*Piano aggiornato il 2026-03-25 — sviluppo concentrico, base pattern clienti semplificato*
*Da revisionare e approvare prima dell'implementazione*
