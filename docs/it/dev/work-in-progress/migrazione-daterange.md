# Migrazione a `daterange` nativo PostgreSQL — Analisi di impatto e piano DB

> Stato: **COMPLETATA — Fase 1, 2, 3 applicate**
>
> Ultima revisione: 12 aprile 2026
>
> Scopo: censimento di tutte le tabelle sviluppate che usano il pattern `valido_dal / valido_al`
> (o `data_inizio / data_fine`) con due colonne DATE separate, e analisi di impatto per la
> migrazione al tipo nativo `daterange` di PostgreSQL.
>
> Riferimenti:
>
> * [linee-guida-sql.md](/linee-guida-sql) — convenzioni SQL di progetto
> * [dbops/automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — infrastruttura GIST exclusion corrente
> * [anagrafiche/trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — modello di riferimento gia` in produzione

---

## 1) Contesto

PostgreSQL supporta nativamente il tipo `daterange` (e `tstzrange` per timestamp).
Oggi nel progetto tutte le tabelle con validita` temporale usano **due colonne separate**
(`valido_dal DATE`, `valido_al DATE`) e ricostruiscono il range al volo nei vincoli GIST e nelle query:

```sql
daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]')
```

Esiste gia` un **precedente funzionante**: la tabella `anagrafiche.clienti` mantiene le colonne
`data_attivazione` e `data_chiusura` come input, e un trigger (`trgfn_clienti_set_periodo`)
popola una colonna calcolata `periodo daterange`. Questo e` il modello di riferimento.

### Vantaggi della migrazione

| Aspetto | Due colonne separate | Colonna `daterange` nativa |
|---|---|---|
| Vincoli anti-overlap | `daterange(col1, COALESCE(col2, 'infinity'))` al volo | `EXCLUDE USING GIST (col WITH &&)` diretto |
| Query "data X e` nel periodo?" | `x >= valido_dal AND (valido_al IS NULL OR x <= valido_al)` | `col @> x::date` |
| Indici GiST | Su espressione calcolata | Sulla colonna nativa |
| Gestione infinity (aperto) | `COALESCE` ovunque | Nativo nel bound superiore |
| Operatori set (overlap, intersezione, differenza) | Non disponibili | `&&`, `*`, `-` nativi |
| Estrazione bound | Gia` disponibile | `lower(col)`, `upper(col)` |

---

## 2) Censimento tabelle con validita` temporale

### Legenda colonna "Stack sviluppato"

* **FULL** = DB + Backend (repository, service, API) + Frontend (componenti Vue)
* **DB + BE** = DB + Backend sviluppato, nessun componente frontend
* **DB only** = Solo DDL e seed, nessun codice applicativo Python/Vue

### Legenda colonna "GIST"

* **Si** = Ha gia` un vincolo EXCLUDE USING GIST con daterange costruito al volo
* **No** = Solo CHECK constraint sulle date

---

### 2.1 Tabelle con `valido_dal` / `valido_al` (DATE)

| # | Schema.Tabella | GIST | Stack | Note |
|---|---|---|---|---|
| 1 | `vendite.listini_versioni` | Si | FULL | Vincolo `ex_listini_versioni_no_overlap`. Resolver `fn_resolve_prezzo_listino` usa le colonne. 5+ componenti Vue (VersioneDrawer, CloneVersioneDrawer, AttivaVersioneDialog, ListiniSearchTable, VersioneFormDrawer) |
| 2 | `vendite.listini_associazioni` | Si | FULL | Vincolo via `dbops.automazione_overlap`. Resolver le usa per filtro candidati. Componente ListinoAssociazioniDrawer |
| 3 | `catalogo.unita_misura_conversioni` | Si | FULL | Vincolo `ex_uom_conv_no_overlap`. Componenti UomConversioniDrawer, ConversioneUomDrawer |
| 4 | `vendite.contratti` | Si | DB only | Vincolo via `dbops.automazione_overlap` su chiave `(billing_account_id, istanza_utility_id, utility_id, ambito)`. Nessun backend/frontend sviluppato |
| 5 | `catalogo.articoli_componenti` | Si | FULL | Vincolo via `dbops.automazione_overlap` su `(prodotto_id, componente_id)`. Componente ArticoloBomDrawer |
| 6 | `catalogo.articoli_uom_operativa` | No | FULL | CHECK su date. Componente ArticoloUomDrawer |
| 7 | `anagrafiche.billing_account` | No | DB only | CHECK `chk_billing_account_validita`. Nessun frontend dedicato per le date |
| 8 | `anagrafiche.risorse_umane` | No | DB + BE | CHECK `chk_risorse_umane_date`. Backend: `risorse_umane_core_repository.py` (create). Usata indirettamente da operatori |
| 9 | `anagrafiche.resellers_billing_account` | No | DB only | CHECK `chk_resellers_ba_validita`. Nessun codice applicativo |
| 10 | `config.utilities_tipi_ruolo` | No | DB + BE | CHECK `chk_utilities_tipi_ruolo_validita`. Backend: lookup filtrato per data corrente in `lookup_repository.py` |
| 11 | `config.tipi_ruoli_nature_ammesse` | No | DB + BE | CHECK `chk_tipi_ruoli_nature_ammesse_validita`. Backend: lookup `list_tipi_ruoli_per_natura()` filtrato per data |
| ~~12~~ | ~~`config.ruoli_tipi_indirizzo`~~ | — | — | **RIMOSSA**: tabella non esiste, e` `config.tipi_ruolo_tipi_indirizzo` (#18) |
| 13 | `config.tipi_soggetto_dettaglio_tipi_indirizzo` | No | DB only | CHECK `chk_tsd_tipi_indirizzo_validita`. Nessun codice applicativo |
| 14 | `config.user_override_aree` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |
| 15 | `config.user_override_oggetti` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |
| 16 | `config.user_override_azioni` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |

#### Tabelle con date di validita` gestite da form dedicato (conti bancari / matrice indirizzi / operatori)

| # | Schema.Tabella | GIST | Stack | Note |
|---|---|---|---|---|
| ~~17~~ | ~~`anagrafiche.conti_bancari`~~ | — | — | **RIMOSSA**: la tabella non ha colonne `valido_dal`/`valido_al` |
| 18 | `config.tipi_ruolo_tipi_indirizzo` (matrice indirizzi) | No | FULL | Backend: `matrice_indirizzi_repository.py`, service, API. Frontend: `MatriceIndirizziDrawer.vue`, `MatriceIndirizziSearchTable.vue` con toggle attivo/valido_al |
| 19 | `anagrafiche.risorse_umane` (via operatori) | No | FULL | Backend: `amm_software_repository.py` con logica disattivazione (`valido_al = CURRENT_DATE`) e riattivazione (`valido_dal = CURRENT_DATE, valido_al = NULL`). Frontend: `OperatoriListView.vue` |

### 2.2 Tabelle con `data_inizio` / `data_fine` (TIMESTAMP WITH TIME ZONE)

Queste sono candidate a `tstzrange` (non `daterange`).

| # | Schema.Tabella | GIST | Stack | Note |
|---|---|---|---|---|
| 20 | `pratiche.sospensioni` | No | DB + BE | CHECK `chk_sospensioni_data_fine`. Unique parziali per sospensione attiva. Backend: `pratiche_service.py` (chiusura `data_fine = NOW()`) |
| 21 | `pratiche.calcoli_tempo` | No | DB + BE | CHECK `chk_calcoli_tempo_data_fine`. Backend: types + repository |

### 2.3 Modello di riferimento gia` implementato

La tabella `anagrafiche.clienti` usa gia` il pattern target:

* Colonne input: `data_attivazione`, `data_chiusura` (DATE)
* Colonna calcolata: `periodo` (daterange, bounds `[)`)
* Trigger: `trgfn_clienti_set_periodo` popola `periodo` ad ogni INSERT/UPDATE
* Vincoli GIST sulla colonna `periodo`

Questo dimostra che il pattern e` gia` validato nel progetto.

---

## 3) Decisioni architetturali — RISOLTE

Questa sezione documenta le decisioni prese dopo l'analisi critica di aprile 2026.
Ogni decisione ha la motivazione esplicita per consentire valutazioni future.

### D1 — Bounds standard: `[]` nel trigger (PG canonicalizza in `[)`)

**Decisione**: usare `'[]'` nella costruzione del daterange nei trigger sync.

**Motivazione**: le colonne `valido_dal` / `valido_al` hanno semantica **inclusiva-inclusiva**
nel dominio (es. "valido dal 1 gennaio al 31 dicembre" = entrambi i giorni inclusi).
Scrivere `daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]')` riflette
esattamente questa semantica.

**Comportamento PG**: PostgreSQL canonicalizza automaticamente i daterange `[]` in `[)` internamente
perche` le date sono un tipo discreto. Quindi `daterange('2026-01-01', '2026-12-31', '[]')` viene
memorizzato come `[2026-01-01, 2027-01-01)`. Questo e` corretto e trasparente.

**Invariante da documentare**: `upper(validita)` restituisce `valido_al + 1` (non `valido_al`).
Per estrarre il bound originale usare `upper(validita) - 1` oppure continuare a leggere `valido_al`.

**Coerenza con `clienti.periodo`**: il trigger di clienti usa `[)` esplicitamente, ma il risultato
e` identico quando si parte da `[]` — PG produce lo stesso range. Nessuna incoerenza reale.

### D2 — Approccio: SEMPRE A (mantieni colonne + range calcolato) per tutte le tabelle

**Decisione**: approccio A anche per le tabelle DB only, senza eccezioni.

**Motivazione**:

* **Coerenza**: un solo pattern in tutto il progetto, zero ambiguita` nelle convenzioni
* **Preparazione futura**: quando backend/frontend verranno sviluppati per le tabelle DB only,
  il contratto API (`valido_dal` / `valido_al` come campi separati) e` gia` pronto
* **Costo marginale**: una colonna in piu` + trigger per tabella — trascurabile
* **Rischio evitato**: due modelli diversi nello stesso progetto complicano le convenzioni
  e aumentano il carico cognitivo

### D3 — Nome colonna range: `validita` standard

**Decisione**: `validita` come nome standard per tutte le tabelle con pattern `valido_dal` / `valido_al`.
Nomi dominio-specifici solo dove le colonne sorgente non si chiamano `valido_dal` / `valido_al`.

| Dominio | Colonne sorgente | Nome colonna range |
|---|---|---|
| Validita` generica | `valido_dal` / `valido_al` | `validita` |
| Pratiche (timestamp) | `data_inizio` / `data_fine` | `periodo_sospensione` / `periodo_calcolo` |
| Clienti (esistente) | `data_attivazione` / `data_chiusura` | `periodo` (gia` in uso) |

### D4 — Drop colonne originali: NO in questa fase

**Decisione**: le colonne `valido_dal` / `valido_al` restano. Non si droppano.

**Motivazione**: servono come interfaccia di input (API, frontend, INSERT diretti).
Valutare il drop solo dopo che tutto il codice (DB, backend, frontend) usa esclusivamente
`validita` per le letture — oggi non e` il caso e non e` l'obiettivo di questa migrazione.

### D5 — Pratiche: `tstzrange`

**Decisione**: usare `tstzrange` per `pratiche.sospensioni` e `pratiche.calcoli_tempo`.

**Motivazione**: le colonne sorgente sono `TIMESTAMP WITH TIME ZONE` e la chiusura usa
`data_fine = NOW()` — la granularita` e` sub-giornaliera. Usare `daterange` perderebbe
informazione temporale.

### D6 — Semantica di `valido_dal IS NULL`: usa `-infinity` (RIVISTA)

**Decisione**: `valido_dal IS NULL` → `validita` usa `-infinity` come lower bound.
`validita` non e` **mai** NULL. Il trigger calcola sempre:

```sql
daterange(COALESCE(valido_dal, '-infinity'), COALESCE(valido_al, 'infinity'), '[]')
```

**Motivazione** (revisione post-analisi critica):

La decisione originale (`validita = NULL` quando `valido_dal IS NULL`) aveva un **bug semantico**:
se `valido_dal IS NULL` e `valido_al = '2025-12-31'`, il range NULL veniva trattato come
"sempre valido" nelle query (`validita IS NULL OR validita @> CURRENT_DATE`), ignorando
la scadenza `valido_al`. Con `-infinity` il range diventa `[-infinity, 2026-01-01)` e
l'operatore `@>` rispetta correttamente la scadenza.

**Vantaggi**:

* `validita` e` NOT NULL su **tutte** le tabelle (uniforme con Fase 1)
* Le query usano sempre e solo `validita @> CURRENT_DATE` — nessun check NULL
* Semantica corretta per tutti i casi: entrambi NULL, uno solo NULL, nessuno NULL

---

## 4) Analisi di impatto — Modifiche DB

Questa sezione descrive le modifiche da apportare **esclusivamente lato database** (DDL, funzioni, trigger, vincoli).
Il DB ha la proprieta` del modello dati: tutte le modifiche partono da qui.

### 4.1 Strategia di migrazione per tabella

Per ogni tabella la sequenza Liquibase e`:

1. **Aggiungere colonna** `validita daterange` (nullable inizialmente)
2. **Creare trigger sync** (modello template §4.3) — BEFORE INSERT OR UPDATE
3. **Popolare** la colonna per le righe esistenti:
   ```sql
   UPDATE schema.tabella
   SET validita = daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]')
   WHERE valido_dal IS NOT NULL;
   ```
   (il trigger si attiva sull'UPDATE e ricalcola — ma l'UPDATE esplicito e` piu` chiaro)
4. **Impostare NOT NULL** sulla colonna `validita` (dove `valido_dal` e` NOT NULL)
5. **Drop vecchio vincolo GIST** (dove esiste)
6. **Creare nuovo vincolo GIST** sulla colonna `validita` nativa
7. **Aggiornare funzioni** che costruiscono `daterange()` al volo → usare `validita` direttamente
8. **Aggiornare query** nelle funzioni/trigger che filtrano con doppio confronto → `validita @> x::date`

**Nota sui dati esistenti**: non c'e` produzione. Se i dati esistenti in sviluppo causano
problemi durante la migrazione (es. righe con date incoerenti), si cancellano e si reinseriscono.
Non servono script di migrazione dati difensivi.

### 4.2 Invariante del trigger sync: sovrascrittura incondizionata

Il trigger sync deve **sempre sovrascrivere** la colonna `validita` ad ogni INSERT/UPDATE,
ignorando eventuali valori passati dall'utente. Questo previene il disallineamento tra
`valido_dal`/`valido_al` e `validita`.

PostgreSQL non supporta `GENERATED ALWAYS STORED` per espressioni con `COALESCE` su range,
quindi il trigger e` l'unico meccanismo disponibile. L'invariante e`:

> `validita` e` SEMPRE una funzione deterministica di `valido_dal` e `valido_al`.
> Nessun codice applicativo deve mai scrivere direttamente su `validita`.

### 4.3 Template trigger sync

Trigger function riutilizzabile, da istanziare per ogni tabella.
Basata sul modello `trgfn_clienti_set_periodo` gia` in produzione.

```sql
-- Template: trigger sync validita` per tabelle con valido_dal / valido_al
-- Adattare: schema, nome funzione, gestione NULL su valido_dal

CREATE OR REPLACE FUNCTION <schema>.trgfn_<tabella>_set_validita()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    -- Calcola validita` daterange da valido_dal / valido_al
    -- Bounds '[]' (PG canonicalizza in '[)' per date)
    IF NEW.valido_dal IS NOT NULL THEN
        NEW.validita := daterange(
            NEW.valido_dal,
            COALESCE(NEW.valido_al, 'infinity'::date),
            '[]'
        );
    ELSE
        NEW.validita := NULL;
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_<tabella>_a20_set_validita_ins_upd
    BEFORE INSERT OR UPDATE OF valido_dal, valido_al
    ON <schema>.<tabella>
    FOR EACH ROW
    EXECUTE FUNCTION <schema>.trgfn_<tabella>_set_validita();
```

**Note sul template**:

* Fase `_a20_`: dopo i guard (`_a10_`) ma prima della logica applicativa
* `UPDATE OF valido_dal, valido_al`: il trigger si attiva solo quando cambiano le colonne sorgente,
  non su ogni UPDATE della riga (performance)
* Per tabelle dove `valido_dal` e` NOT NULL, il ramo `ELSE` non si raggiunge mai —
  mantenerlo comunque per robustezza
* Per tabelle con colonne diverse (es. `data_inizio`/`data_fine`): adattare i nomi
* Per `tstzrange` (pratiche): sostituire `daterange` con `tstzrange` e i cast di tipo

### 4.4 Aggiornamento infrastruttura `dbops.automazione_overlap`

La funzione `dbops.fn_apply_automazione_overlap` costruisce vincoli GIST usando:

```sql
daterange(%I, COALESCE(%I, 'infinity'::date), %L) WITH &&
```

Dopo la migrazione, per le tabelle migrate dovra` puntare direttamente alla colonna `validita`.

**Modifiche alla tabella `dbops.automazione_overlap`**:

* Aggiungere colonna `range_col TEXT DEFAULT NULL` — nome della colonna daterange nativa
* Se `range_col IS NOT NULL` → la funzione genera `%I WITH &&` (colonna diretta)
* Se `range_col IS NULL` → comportamento attuale (espressione calcolata, retrocompatibile)

**Modifiche a `dbops.fn_apply_automazione_overlap`**:

```sql
-- Nuovo codepath per colonna range nativa
IF rconf.range_col IS NOT NULL THEN
    v_range_expr := format('%I WITH &&', rconf.range_col);
ELSE
    v_range_expr := format(
        'daterange(%I, COALESCE(%I, ''infinity''::date), %L) WITH &&',
        rconf.valido_dal_col,
        rconf.valido_al_col,
        v_bounds
    );
END IF;
```

**Modifiche a `dbops.fn_seed_automazione_overlap`**:

* Aggiungere detection: se la tabella ha una colonna `validita` di tipo `daterange`,
  popolare automaticamente `range_col = 'validita'`

**Vincoli con WHERE personalizzate** (#1 `listini_versioni`, #2 `listini_associazioni`):

Dall'analisi risulta che questi vincoli sono stati creati **manualmente** (non via automazione)
perche` hanno clausole WHERE filtrate (`attivo IS TRUE AND stato = 'ATTIVA'`).
L'infrastruttura `automazione_overlap` non gestisce filtri WHERE.

Questi vincoli **restano manuali** anche dopo la migrazione: la migration Liquibase li ricrea
esplicitamente con la colonna `validita` nativa. L'automazione si occupa solo dei casi standard
(#2, #4, #5 tramite `automazione_overlap`).

**Correzione**: `listini_associazioni` (#2) e` gestito sia manualmente che via automazione.
Verificare quale dei due e` autorevole e consolidare.

### 4.5 Impatto per gruppo di tabelle

#### Gruppo 1 — Tabelle con GIST gia` esistente (priorita` ALTA)

Queste gia` pagano il costo del GIST ma ricostruiscono il range ad ogni valutazione. Il beneficio e` immediato.

**`vendite.listini_versioni`** (#1)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger `trgfn_listini_versioni_set_validita`
* Ricreare `ex_listini_versioni_no_overlap` sulla colonna nativa:
  ```sql
  EXCLUDE USING gist (listino_id WITH =, validita WITH &&)
  WHERE (attivo IS TRUE AND stato = 'ATTIVA')
  ```
* **Funzioni da aggiornare**:
  - `vendite.fn_resolve_prezzo_listino` — CTE `versioni_candidate`:
    sostituire `p_data_riferimento >= v.valido_dal AND (v.valido_al IS NULL OR p_data_riferimento <= v.valido_al)`
    con `v.validita @> p_data_riferimento`
  - ORDER BY: `COALESCE(v.valido_al, 'infinity')` → `upper(v.validita)`
* Indice `ix_listini_versioni_listino_valido_dal` → valutare sostituzione con indice GiST su `validita`

**`vendite.listini_associazioni`** (#2)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger `trgfn_listini_associazioni_set_validita`
* Ricreare vincolo sulla colonna nativa:
  ```sql
  EXCLUDE USING gist (
      COALESCE(billing_account_id, -1::bigint) WITH =,
      COALESCE(utility_id, -1::integer) WITH =,
      COALESCE(emittente_soggetto_ruolo_id, -1::bigint) WITH =,
      validita WITH &&
  ) WHERE (attivo IS TRUE)
  ```
* **Funzioni da aggiornare**:
  - `vendite.fn_resolve_prezzo_listino` — CTE `associazioni_candidate`: stesso pattern
* Aggiornare record in `dbops.automazione_overlap`: set `range_col = 'validita'`

**`catalogo.unita_misura_conversioni`** (#3)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger `trgfn_unita_misura_conversioni_set_validita`
* Ricreare `ex_uom_conv_no_overlap` sulla colonna nativa:
  ```sql
  EXCLUDE USING gist (uom_from_id WITH =, uom_to_id WITH =, validita WITH &&)
  ```
* **Funzioni da aggiornare**: eventuali query di risoluzione UoM

**`vendite.contratti`** (#4)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger `trgfn_contratti_set_validita`
* Aggiornare record in `dbops.automazione_overlap`: set `range_col = 'validita'`
* Nessuna funzione applicativa da aggiornare (DB only)

**`catalogo.articoli_componenti`** (#5)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger `trgfn_articoli_componenti_set_validita`
* Aggiornare record in `dbops.automazione_overlap`: set `range_col = 'validita'`

#### Gruppo 2 — Tabelle con solo CHECK (priorita` MEDIA)

Queste non hanno GIST ma beneficiano comunque degli operatori nativi nelle query.

**Tabelle config (permessi)**: `user_override_aree` (#14), `user_override_oggetti` (#15), `user_override_azioni` (#16)

* Aggiungere colonna `validita daterange NOT NULL` (trigger usa `-infinity` per NULL, vedi D6 rivista)
* Trigger sync via `script.trgfn_set_validita()`
* Le funzioni di risoluzione permessi usano `validita @> CURRENT_DATE`
* CHECK constraint sulle date **resta** (validazione input utente), il range e` derivato

**Tabelle config (lookup)**: `utilities_tipi_ruolo` (#10), `tipi_ruoli_nature_ammesse` (#11), `tipi_soggetto_dettaglio_tipi_indirizzo` (#13)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync via `script.trgfn_set_validita()`
* Le query lookup in `lookup_repository.py` usano `validita @> CURRENT_DATE`

**Tabelle anagrafiche**: `billing_account` (#7), `risorse_umane` (#8), `resellers_billing_account` (#9)

* Aggiungere colonna `validita daterange` (nullable dove `valido_dal` e` nullable)
* Trigger sync

**Tabelle catalogo**: `articoli_uom_operativa` (#6)

* Aggiungere colonna `validita daterange`
* Trigger sync

**Tabelle anagrafiche (form)**: conti bancari (#17), matrice indirizzi (#18), operatori (#19)

* Aggiungere colonna `validita daterange`
* Trigger sync

#### Gruppo 3 — Tabelle con TIMESTAMP → `tstzrange` (priorita` BASSA)

**`pratiche.sospensioni`** (#20), **`pratiche.calcoli_tempo`** (#21)

* Tipo: `tstzrange` (non `daterange`)
* Stessa logica: aggiungere colonna range, trigger sync, aggiornare vincoli
* I trigger usano `tstzrange` e `COALESCE(data_fine, 'infinity'::timestamptz)`
* Da eseguire separatamente perche` la semantica timestamp e` diversa (istanti vs giorni)

---

## 5) Analisi di impatto — Modifiche Backend e Frontend

Questa sezione descrive le modifiche necessarie **solo per le tabelle che hanno codice applicativo sviluppato**.
Le tabelle DB only non richiedono interventi in questa sezione.

### 5.1 Approccio generale

Con l'approccio A (mantenere colonne separate + colonna range calcolata dal trigger):

* **L'API non cambia**: il frontend continua a inviare `valido_dal` e `valido_al` come campi separati
* **Il trigger DB** si occupa di popolare la colonna `validita`
* **Le query backend** che filtrano per data possono essere semplificate usando `validita @> data`
* **Le SELECT** che restituiscono `valido_dal` / `valido_al` continuano a funzionare (le colonne restano)

### 5.2 Impatto per tabella con stack FULL

#### `vendite.listini_versioni` (#1) + `vendite.listini_associazioni` (#2)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/vendite/db/listini_repository.py` | Query SELECT: nessuna modifica (le colonne restano). Query di filtro per data in eventuali list/search: sostituire doppio confronto con `validita @> %(data)s` |
| `apps/vendite/services/listini_service.py` | Validazione payload `valido_dal` / `valido_al`: nessuna modifica (il trigger gestisce il range). `fn_change_versione_state` con auto-close D3: il PATCH su `valido_al` resta invariato |
| `apps/vendite/api/views_listini.py` | Serializer: nessuna modifica (campi restano `valido_dal`, `valido_al`) |

**Frontend** (impatto ZERO): nessuna modifica.

#### `catalogo.unita_misura_conversioni` (#3) + `catalogo.articoli_componenti` (#5) + `catalogo.articoli_uom_operativa` (#6)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/catalogo/db/catalogo_repository.py` | Query di filtro per data: sostituire con `@>` dove presente |
| `apps/catalogo/api/views.py` | Serializer: nessuna modifica |

**Frontend** (impatto ZERO): nessuna modifica.

#### Conti bancari (#17)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/anagrafiche/db/conti_bancari_repository.py` | Query filtro: eventuale uso `@>` |
| `apps/anagrafiche/api/views_conti_bancari.py` | Nessuna modifica serializer |
| `apps/anagrafiche/services/conti_bancari_service.py` | Nessuna modifica |

**Frontend** (impatto ZERO): nessuna modifica.

#### Matrice indirizzi (#18)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/anagrafiche/db/matrice_indirizzi_repository.py` | Filtro attivi per data: eventuale `@>` |
| `apps/anagrafiche/services/matrice_indirizzi_service.py` | Logica "valido_dal = oggi": nessuna modifica (il trigger sync) |

**Frontend** (impatto ZERO): nessuna modifica.

#### Operatori (#19)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/amm_software/db/amm_software_repository.py` | Logica disattivazione/riattivazione su `valido_dal`/`valido_al`: nessuna modifica (il trigger sync) |

**Frontend** (impatto ZERO): nessuna modifica.

### 5.3 Impatto per tabelle con stack DB + BE (no frontend)

#### Lookup config (#10, #11, #14, #15, #16)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/core/db/lookup_repository.py` | Metodi `list_tipi_ruoli_per_natura()`, `list_utilities_per_ruolo()`, `list_utilities_per_emittente()`: sostituire doppio confronto con `(m.validita IS NULL OR m.validita @> CURRENT_DATE)` |
| Funzioni permessi (`script.fn_risolvi_permesso_*`) | Stesso pattern di semplificazione — questo e` nel DB, non nel backend Python |

#### Pratiche (#20, #21)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/pratiche/services/pratiche_service.py` | Chiusura sospensione `data_fine = NOW()`: nessuna modifica (trigger sync) |
| `apps/pratiche/types.py` | TypedDict: nessuna modifica (campi restano per serializzazione) |

---

## 6) Piano di esecuzione DB — Dettaglio Liquibase

> **Premessa dati**: non c'e` produzione. I dati di sviluppo sono sacrificabili —
> se una riga causa errore durante la migrazione si cancella e si reinserisce.
> Non servono script di migrazione dati difensivi.

### Fase 0 — Infrastruttura (prerequisito per tutte le fasi successive)

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 0.1 | `YYYYMMDD-01-schema-dbops-automazione_overlap-add-range_col.yaml` | DDL | `ALTER TABLE dbops.automazione_overlap ADD COLUMN range_col TEXT DEFAULT NULL` |
| 0.2 | `YYYYMMDD-02-code-dbops-fn_apply_automazione_overlap.yaml` | Code | Aggiornare funzione con doppio codepath (§4.4). `runOnChange: true` |
| 0.3 | `YYYYMMDD-03-code-dbops-fn_seed_automazione_overlap.yaml` | Code | Aggiornare seed per detection colonna `validita`. `runOnChange: true` |

### Fase 1 — Tabelle con GIST esistente (massimo beneficio)

Per ogni tabella la sequenza e` sempre: DDL add column → trigger → populate → NOT NULL → drop old GIST → new GIST.

**`vendite.listini_versioni`** (#1):

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 1.1 | `...-schema-vendite-listini_versioni-add-validita.yaml` | DDL | `ADD COLUMN validita daterange` |
| 1.2 | `...-code-vendite-trgfn_listini_versioni_set_validita.yaml` | Code | Trigger function + trigger. `runOnChange: true` |
| 1.3 | `...-data-vendite-listini_versioni-populate-validita.yaml` | Data | UPDATE populate + `ALTER COLUMN validita SET NOT NULL` |
| 1.4 | `...-schema-vendite-listini_versioni-recreate-gist.yaml` | DDL | DROP `ex_listini_versioni_no_overlap` + CREATE nuovo su `validita` |
| 1.5 | `...-code-vendite-fn_resolve_prezzo_listino.yaml` | Code | Aggiornare CTE versioni_candidate. `runOnChange: true` |

**`vendite.listini_associazioni`** (#2):

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 2.1 | `...-schema-vendite-listini_associazioni-add-validita.yaml` | DDL | `ADD COLUMN validita daterange` |
| 2.2 | `...-code-vendite-trgfn_listini_associazioni_set_validita.yaml` | Code | Trigger function + trigger. `runOnChange: true` |
| 2.3 | `...-data-vendite-listini_associazioni-populate-validita.yaml` | Data | UPDATE populate + NOT NULL |
| 2.4 | `...-schema-vendite-listini_associazioni-recreate-gist.yaml` | DDL | DROP + CREATE nuovo EXCLUDE su `validita` |
| 2.5 | `...-data-dbops-automazione_overlap-set-range_col-listini_assoc.yaml` | Data | UPDATE `automazione_overlap` SET `range_col = 'validita'` per questa tabella |
| 2.6 | Accorpare in 1.5 | Code | Aggiornare CTE associazioni_candidate in `fn_resolve_prezzo_listino` |

**`catalogo.unita_misura_conversioni`** (#3):

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 3.1 | `...-schema-catalogo-unita_misura_conversioni-add-validita.yaml` | DDL | `ADD COLUMN validita daterange` |
| 3.2 | `...-code-catalogo-trgfn_uom_conversioni_set_validita.yaml` | Code | Trigger + trigger function. `runOnChange: true` |
| 3.3 | `...-data-catalogo-uom_conversioni-populate-validita.yaml` | Data | UPDATE + NOT NULL |
| 3.4 | `...-schema-catalogo-uom_conversioni-recreate-gist.yaml` | DDL | DROP + CREATE `ex_uom_conv_no_overlap` su `validita` |

**`vendite.contratti`** (#4):

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 4.1 | `...-schema-vendite-contratti-add-validita.yaml` | DDL | `ADD COLUMN validita daterange` |
| 4.2 | `...-code-vendite-trgfn_contratti_set_validita.yaml` | Code | Trigger. `runOnChange: true` |
| 4.3 | `...-data-vendite-contratti-populate-validita.yaml` | Data | UPDATE + NOT NULL |
| 4.4 | `...-data-dbops-automazione_overlap-set-range_col-contratti.yaml` | Data | UPDATE `automazione_overlap` SET `range_col` |

**`catalogo.articoli_componenti`** (#5):

| Step | File Liquibase | Tipo | Contenuto |
|---|---|---|---|
| 5.1 | `...-schema-catalogo-articoli_componenti-add-validita.yaml` | DDL | `ADD COLUMN validita daterange` |
| 5.2 | `...-code-catalogo-trgfn_articoli_componenti_set_validita.yaml` | Code | Trigger. `runOnChange: true` |
| 5.3 | `...-data-catalogo-articoli_componenti-populate-validita.yaml` | Data | UPDATE + NOT NULL |
| 5.4 | `...-data-dbops-automazione_overlap-set-range_col-art_comp.yaml` | Data | UPDATE `automazione_overlap` SET `range_col` |

### Fase 2 — Tabelle config/anagrafiche (beneficio query)

Queste seguono lo stesso pattern ma `validita` e` **nullable** (perche` `valido_dal` e` nullable).
Non c'e` ricreazione GIST (non ne hanno).

**Tabelle config permessi** (#14, #15, #16): un file DDL + trigger per ciascuna.
Poi un unico file code per aggiornare le funzioni `script.fn_risolvi_permesso_*` e
`script.fn_get_user_permissions_map` / `fn_get_user_object_permissions_map`.

**Tabelle config lookup** (#10, #11, #12, #13): un file DDL + trigger per ciascuna.
Nessuna funzione DB da aggiornare (le query sono nel backend Python).

**Tabelle anagrafiche** (#6, #7, #8, #9, #17, #18, #19): un file DDL + trigger per ciascuna.

### Fase 3 — Tabelle pratiche con timestamp (separato)

**`pratiche.sospensioni`** (#20) e **`pratiche.calcoli_tempo`** (#21):

* Colonna `tstzrange` invece di `daterange`
* Trigger sync con `tstzrange(data_inizio, COALESCE(data_fine, 'infinity'::timestamptz), '[)')`
* Bounds `[)` per i timestamp (standard PG per range continui)

### Riepilogo numerazione file Liquibase

| Fase | File stimati | Cartella |
|---|---|---|
| 0 (infrastruttura) | 3 | `00_schema` + `20_code` |
| 1 (GIST) | ~20 | `00_schema` + `20_code` + `80_data` |
| 2 (config/anagrafiche) | ~20 | `00_schema` + `20_code` |
| 3 (pratiche) | ~5 | `00_schema` + `20_code` |
| **Totale** | **~48** | |

---

## 7) Piano test pgTAP

Ogni fase della migrazione deve includere test che verificano:

### Test per ogni tabella migrata

1. **Trigger sync — casi base**:
   - INSERT con `valido_dal` e `valido_al` → `validita` calcolata correttamente
   - INSERT con `valido_al IS NULL` → `validita` con upper bound infinity
   - UPDATE di `valido_al` → `validita` ricalcolata
   - UPDATE di campo non-date → `validita` non cambia (trigger `UPDATE OF`)

2. **Trigger sync — edge cases**:
   - `valido_dal IS NULL` (tabelle nullable) → `validita IS NULL`
   - `valido_dal = valido_al` (range di un giorno) → range valido
   - INSERT con `validita` esplicitamente valorizzata → sovrascritta dal trigger

3. **Vincoli GIST** (solo tabelle Gruppo 1):
   - Due righe con overlap sulla stessa chiave → errore
   - Due righe senza overlap sulla stessa chiave → OK
   - Due righe con overlap su chiavi diverse → OK
   - Riga con `valido_al IS NULL` (infinito) → corretto blocking

4. **Funzioni aggiornate**:
   - `fn_resolve_prezzo_listino`: stessi risultati di prima con operatore `@>`
   - Funzioni permessi: stessi risultati con `validita @> CURRENT_DATE`

### Organizzazione file test

```
db/pgtap/
├── daterange/
│   ├── test_trigger_sync_template.sql      -- test generici applicabili a tutte le tabelle
│   ├── test_listini_versioni_validita.sql   -- test specifici listini
│   ├── test_listini_associazioni_validita.sql
│   ├── test_uom_conversioni_validita.sql
│   ├── test_permessi_validita.sql           -- test funzioni permessi con range
│   └── test_resolve_prezzo_validita.sql     -- test fn_resolve_prezzo_listino con range
```

---

## 8) Strategia di rollback

Con l'approccio A il rollback e` semplice perche` le colonne originali restano intatte:

1. Drop colonna `validita`
2. Drop trigger sync
3. Ricrea vecchi vincoli GIST (con espressione `daterange(valido_dal, COALESCE(...))`)
4. Ripristina funzioni alle versioni precedenti (Liquibase `runOnChange` con il codice precedente)

Non e` necessario uno script di rollback automatico — in sviluppo il rollback Liquibase
standard (`liquibase rollback`) e` sufficiente se i changeset hanno `rollback` definito.

---

## 9) Checklist pre-implementazione

- [x] **D1 bounds**: confermato `[]` (PG canonicalizza in `[)`) — §3
- [x] **D2 approccio**: confermato sempre A — §3
- [x] **D3 naming**: confermato `validita` standard — §3
- [x] **D6 NULL semantics**: RIVISTA — usa `-infinity`/`infinity`, `validita` mai NULL — §3
- [x] Verificare che `listini_associazioni` vincolo GIST e` manuale (confermato, WHERE custom)
- [x] Confermare naming trigger: funzione generica `script.trgfn_set_validita()` + trigger `trg_<tabella>_a20_set_validita_ins_upd`
- [x] Censimento corretto: rimossa #12 (non esiste) e #17 (no colonne valido)
- [x] Verificare funzioni DB con `daterange(valido_dal, ...)` al volo — **nessuna trovata**, tutte migrate
- [x] Aggiornare `linee-guida-sql.md` con la convenzione `validita daterange` — sezione 7b aggiunta

---

## 10) Riepilogo esecuzione — File Liquibase creati

### Fase 0 — Infrastruttura (4 file)

| # | File | Contenuto |
|---|---|---|
| -01 | `00_schema/dbops/...add-range-col` | ADD COLUMN `range_col` a `automazione_overlap` |
| -02 | `20_code/dbops/...fn-apply-automazione-overlap` | Dual codepath (range nativo / espressione calcolata) |
| -03 | `20_code/dbops/...fn-seed-automazione-overlap` | Detection colonna `validita` |
| -05 | `20_code/script/...trgfn-set-validita` | Funzione generica `script.trgfn_set_validita()` — COALESCE `-infinity`/`infinity` |

### Fase 1 — Tabelle con GIST (12 file)

| # | Tabella | File |
|---|---|---|
| -04, -17, -06, -07 | `vendite.listini_versioni` | DDL + trigger + backfill + GIST |
| -08, -09, -10, -11 | `vendite.listini_associazioni` | DDL + trigger + backfill + GIST |
| -12 | — | `fn_resolve_prezzo_listino` aggiornata con `@>` |
| -13 | `catalogo.unita_misura_conversioni` | All-in-one |
| -14 | `vendite.contratti` | All-in-one |
| -15 | `catalogo.articoli_componenti` | All-in-one (+ drop indice duplicato) |

### Fase 2 — Tabelle config/anagrafiche (16 file)

| # | Tabella | Note |
|---|---|---|
| -18...-20 | `config.user_override_aree/oggetti/azioni` | NOT NULL, trigger generico |
| -21...-24 | `config.utilities_tipi_ruolo`, `tipi_ruoli_nature_ammesse`, `tsd_tipi_indirizzo`, `tipi_ruolo_tipi_indirizzo` | NOT NULL, trigger generico |
| -25 | `catalogo.articoli_uom_operativa` | NOT NULL, trigger generico |
| -26 | `anagrafiche.billing_account` | NOT NULL, trigger generico |
| -27 | `anagrafiche.risorse_umane` | NOT NULL, trigger generico |
| -28 | `anagrafiche.resellers_billing_account` | NOT NULL, trigger generico |
| -29...-33 | Funzioni permessi | `fn_resolve_livello_area/oggetto`, `fn_get_user_permissions/object/actions_map` — `validita @> CURRENT_DATE` |

### Fase 3 — Pratiche tstzrange (2 file)

| # | Tabella | Colonna | Tipo |
|---|---|---|---|
| -34 | `pratiche.sospensioni` | `periodo_sospensione` | `tstzrange` |
| -35 | `pratiche.calcoli_tempo` | `periodo_calcolo` | `tstzrange` |

### Ottimizzazioni applicate

* **Funzione generica** `script.trgfn_set_validita()`: 1 sola funzione per 19 tabelle (Fase 1 + 2), elimina duplicazione
* **`-infinity`/`infinity`**: `validita` mai NULL, query semplificate a `validita @> data`
* **Backfill esplicito**: `SET validita = daterange(...)` indipendente dall'ordine trigger
* **DROP CONSTRAINT** (non DROP INDEX) per vincoli EXCLUDE con backing index

---

*Migrazione daterange — ZeroERP (12 aprile 2026, Fase 1-2-3 completate)*
