# WIP — Refactor: da utility_id a istanza_utility_id su indirizzi, conti bancari e contatti

> Data apertura: 2026-03-25
>
> Stato: **CHIUSO** — DB, documentazione, backend e frontend completati (25-27 marzo 2026)
>
> Priorita: **CRITICA** — difetto architetturale risolto

---

## Contesto e motivazioni della scelta

### Percorso decisionale

Durante lo sprint 8 (gestione clienti) e emerso che indirizzi, conti bancari e contatti
a livello ruolo non avevano un campo per differenziare i dati per utility/istanza.
E stato quindi avviato il refactor `refactor-indirizzi-conti-utility.md` che ha aggiunto
`utility_id` a indirizzi e conti bancari (contatti lo aveva gia).

Il refactor lato DB e stato completato (schema, viste, funzioni, test pgTAP).
Tuttavia, durante la fase di verifica funzionale, l'analisi di uno scenario reale
ha evidenziato un difetto architetturale nel campo scelto come differenziatore.

### Scenario che ha evidenziato il problema

Soggetto Titini, azienda multi-sede:

1. **1 gennaio** — richiesta attivazione GAS per sede Corridonia → cliente 100, utility=GAS
2. **20 gennaio** — attivazione completata, indirizzo fatturazione: Via Roma 1, Corridonia
3. **1 marzo** — richiesta attivazione GAS per sede Civitanova → cliente 200, utility=GAS
4. **Problema**: il vincolo `UNIQUE(soggetto_ruolo_id, utility_id, tipo_indirizzo_id)`
   impedisce un secondo indirizzo fatturazione perche entrambi i clienti condividono
   lo stesso `soggetto_ruolo_id` (CLIENTE) e la stessa `utility_id` (GAS)

**Perche condividono lo stesso `soggetto_ruolo_id`**: il vincolo
`UNIQUE(soggetto_id, tipo_ruolo_id)` su `soggetti_ruoli` garantisce un solo ruolo
CLIENTE per soggetto. La molteplicita sta nella tabella `clienti` (un record per istanza),
non in `soggetti_ruoli`.

Lo stesso problema si replica su conti bancari (IBAN incasso diverso per sede) e
contatti (referente commerciale diverso per sede).

### Perche `utility_id` non e il differenziatore corretto

`utility_id` identifica il **tipo di servizio** (GAS, IDRICO, ELETTRICO), non la
**specifica istanza di servizio**. Un soggetto puo avere piu istanze dello stesso
servizio (due contratti GAS per sedi diverse, due punti di fornitura IDRICO, ecc.).

### Perche `istanza_utility_id` e la scelta corretta

`istanza_utility_id` identifica la **specifica istanza di servizio** e presenta
questi vantaggi:

- **Esiste sempre**: ogni attivazione/pratica parte con una istanza utility
- **Univoco per servizio specifico**: due GAS dello stesso soggetto hanno istanze diverse
- **Implica la utility**: la utility si recupera dal payload cliente che ha gia
  `utility_id` (sincronizzato dal BA via trigger) — non serve derivarla nelle viste
- **Stessa complessita implementativa**: 3 livelli di cascata come prima, stesso numero
  di partial unique index, stesse funzioni di risoluzione — cambia solo il campo

### Nota su `istanze_utilities` e la utility

La tabella `istanze_utilities` **non ha** una colonna `utility_id` diretta.
Ogni istanza appartiene concettualmente a una sola utility, ma il dato e derivato:

- Via `billing_account`: `UNIQUE(istanza_utility_id, utility_id)` — ma e 1:N (parent + sub-account)
- Via `clienti`: `UNIQUE(istanza_utility_id)` + `utility_id` — 1:1, il percorso piu sicuro

Per la UI, il `utility_codice` e gia disponibile nel payload cliente (campo `utility_id`
sincronizzato dal BA via `trgfn_clienti_sync_utility_from_ba`). Le viste DB non devono
derivarlo — basta esporre `istanza_utility_id`.

### Nota su `istanze_utilities.indirizzo_dettaglio_id`

L'istanza ha un riferimento diretto a un indirizzo (`indirizzo_dettaglio_id`), che
rappresenta il **luogo fisico del servizio** (dove si trova il contatore/punto di fornitura).
Gli `indirizzi` con `istanza_utility_id` sono invece indirizzi **operativi del ruolo**
(fatturazione, corrispondenza, ecc.) — dove mandare le cose per quel servizio.
Sono complementari, non in conflitto.

### Come si risale alla utility da un'istanza

La tabella `istanze_utilities` non ha `utility_id` diretto. La utility si ricava dalle
tabelle satellite che la portano con vincolo UNIQUE:

| Tabella | Vincolo | Quando esiste |
|---------|---------|---------------|
| `istanze_dati_precontrattuali` | `UNIQUE(istanza_utility_id, utility_id)` | Fase precontrattuale (creazione da pratica) |
| `billing_account` | `UNIQUE(istanza_utility_id, utility_id)` | Dopo creazione BA (sempre per clienti) |
| `clienti` | `UNIQUE(istanza_utility_id)` + `utility_id` | Dopo creazione cliente |

**Ordine cronologico di disponibilita:**

1. **Pratica aperta** → `istanze_dati_precontrattuali` e il primo punto dove il legame
   istanza → utility viene registrato (prima di BA e cliente)
2. **BA creato** → `billing_account.utility_id` disponibile
3. **Cliente creato** → `clienti.utility_id` disponibile (sincronizzato dal BA via trigger)

**Nota per il motore pratiche:** nella creazione da pratica (utility con `richiede_pdp = true`:
GAS, IDRICO, ENERGIA) e fondamentale che `istanze_dati_precontrattuali` venga popolato
subito alla creazione dell'istanza. Senza questo record, la utility non e reperibile
dall'istanza nella fase precontrattuale (BA e cliente non esistono ancora).

Nella creazione immediata (utility con `richiede_pdp = false`), `istanze_dati_precontrattuali`
non e necessario perche BA e cliente vengono creati atomicamente dal `ClienteService`.

### Decisione

Sostituire `utility_id` con `istanza_utility_id` su tutte e tre le tabelle prima di
procedere con qualsiasi altro sviluppo. Non essendo in produzione, non ci sono vincoli
di retrocompatibilita. Il costo di fare il refactor ora e minimo rispetto al costo di
farlo dopo con dati in produzione.

---

## Soluzione

Sostituire `utility_id` con `istanza_utility_id` (`bigint`, FK → `anagrafiche.istanze_utilities`)
su tutte e tre le tabelle.

### Cascata target (3 livelli)

| Priorita | istanza_utility_id | soggetto_ruolo_id | Significato | Editabile |
|----------|-------------------|-------------------|-------------|-----------|
| 1 | valorizzato | valorizzato | Specifico istanza (Titini GAS Corridonia) | Si |
| 2 | NULL | valorizzato | Generico ruolo CLIENTE | Si |
| 3 | — | — | Soggetto (fallback da tabelle soggetto) | No (readonly) |

**Nota sul tipo `bigint`:** `anagrafiche.istanze_utilities.id` e `bigint` — il campo
`istanza_utility_id` e tutti i parametri funzione (`p_istanza_utility_id`) devono essere
`bigint`, non `integer`.

### Cosa espongono le viste

Le viste espongono **solo `istanza_utility_id`** — niente `istanza_codice` ne
`utility_codice`. Le viste servono per la risoluzione (cascata), non per mostrare
dettagli dell'istanza. Il frontend/backend ha gia `utility_codice` e `istanza_codice`
dal payload cliente. Zero JOIN aggiuntivi, zero rischi di prodotto cartesiano.

### Nessuna retrocompatibilita necessaria

Non siamo in produzione. Si sostituisce direttamente. I changeset del refactor precedente
(02-05 del 2026-03-24) sono nel branch — servono nuovi changeset (regola Liquibase:
mai modificare changeset gia pushati).

---

## Tabelle impattate

| Tabella | Campo attuale | Campo nuovo | Note |
|---------|--------------|-------------|------|
| `anagrafiche.contatti` | `utility_id integer` (FK → config.utilities) | `istanza_utility_id bigint` (FK → anagrafiche.istanze_utilities) | Esistente da sprint precedenti |
| `anagrafiche.indirizzi` | `utility_id integer` (FK → config.utilities) | `istanza_utility_id bigint` (FK → anagrafiche.istanze_utilities) | Aggiunto nel refactor 2026-03-24 |
| `anagrafiche.soggetti_ruoli_conti_bancari` | `utility_id integer` (FK → config.utilities) | `istanza_utility_id bigint` (FK → anagrafiche.istanze_utilities) | Aggiunto nel refactor 2026-03-24 |

---

## STEP 1 — DB: Schema `anagrafiche.contatti` ✅

**Competenza: DBA** — Completato 2026-03-25

### 1.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
-- Rimuovere vecchio campo, vincolo UNIQUE e FK
ALTER TABLE anagrafiche.contatti DROP CONSTRAINT IF EXISTS fk_utilities_config;
DROP INDEX IF EXISTS uq_contatti_multilevel;
ALTER TABLE anagrafiche.contatti DROP COLUMN utility_id;

-- Aggiungere nuovo campo (bigint come istanze_utilities.id)
ALTER TABLE anagrafiche.contatti
  ADD COLUMN istanza_utility_id bigint NULL;

ALTER TABLE anagrafiche.contatti
  ADD CONSTRAINT fk_contatti_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES anagrafiche.istanze_utilities(id);
```

### 1.2 Ricreare vincoli UNIQUE (partial index per gestire NULL)

La tabella contatti ha 3 livelli di contesto (non 4 — il livello "soggetto + utility
senza ruolo" non ha senso con `istanza_utility_id`):

1. **Soggetto puro** — `soggetto_ruolo_id IS NULL`, `istanza_utility_id IS NULL`
2. **Ruolo generico** — `soggetto_ruolo_id IS NOT NULL`, `istanza_utility_id IS NULL`
3. **Ruolo + istanza** — `soggetto_ruolo_id IS NOT NULL`, `istanza_utility_id IS NOT NULL`

```sql
-- Livello soggetto puro: un contatto per (soggetto, tipo)
CREATE UNIQUE INDEX uq_contatti_soggetto_tipo
  ON anagrafiche.contatti (soggetto_id, tipo_contatto_id)
  WHERE soggetto_ruolo_id IS NULL AND istanza_utility_id IS NULL;

-- Livello ruolo generico: un contatto per (soggetto, ruolo, tipo)
CREATE UNIQUE INDEX uq_contatti_ruolo_tipo_no_istanza
  ON anagrafiche.contatti (soggetto_id, soggetto_ruolo_id, tipo_contatto_id)
  WHERE soggetto_ruolo_id IS NOT NULL AND istanza_utility_id IS NULL;

-- Livello ruolo + istanza: un contatto per (soggetto, ruolo, istanza, tipo)
CREATE UNIQUE INDEX uq_contatti_ruolo_istanza_tipo
  ON anagrafiche.contatti (soggetto_id, soggetto_ruolo_id, istanza_utility_id, tipo_contatto_id)
  WHERE soggetto_ruolo_id IS NOT NULL AND istanza_utility_id IS NOT NULL;
```

**Nota:** il vecchio vincolo `uq_contatti_multilevel` era un singolo indice UNIQUE
standard (non partial) su `(soggetto_id, soggetto_ruolo_id, utility_id, tipo_contatto_id)`.
Con `istanza_utility_id` servono 3 partial index per coprire i 3 livelli distinti.

### 1.3 Indice

```sql
CREATE INDEX ix_contatti_istanza_utility_id
  ON anagrafiche.contatti (istanza_utility_id);
```

### 1.4 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/20260325-XX-replace-utility-with-istanza-contatti-mctit.yaml`

---

## STEP 2 — DB: Schema `anagrafiche.indirizzi` ✅

**Competenza: DBA** — Completato 2026-03-25

### 2.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
ALTER TABLE anagrafiche.indirizzi DROP CONSTRAINT IF EXISTS fk_indirizzi_utilities;
DROP INDEX IF EXISTS uq_indirizzi_ruolo_tipo_no_utility;
DROP INDEX IF EXISTS uq_indirizzi_ruolo_utility_tipo;
DROP INDEX IF EXISTS ix_anagrafiche_indirizzi_utility_id;
ALTER TABLE anagrafiche.indirizzi DROP COLUMN utility_id;

-- bigint come istanze_utilities.id
ALTER TABLE anagrafiche.indirizzi
  ADD COLUMN istanza_utility_id bigint NULL;

ALTER TABLE anagrafiche.indirizzi
  ADD CONSTRAINT fk_indirizzi_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES anagrafiche.istanze_utilities(id);
```

### 2.2 Ricreare vincoli UNIQUE

```sql
-- Generico ruolo (istanza NULL)
CREATE UNIQUE INDEX uq_indirizzi_ruolo_tipo_no_istanza
  ON anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id)
  WHERE istanza_utility_id IS NULL;

-- Specifico istanza
CREATE UNIQUE INDEX uq_indirizzi_ruolo_istanza_tipo
  ON anagrafiche.indirizzi (soggetto_ruolo_id, istanza_utility_id, tipo_indirizzo_id)
  WHERE istanza_utility_id IS NOT NULL;
```

### 2.3 Indice

```sql
CREATE INDEX ix_indirizzi_istanza_utility_id
  ON anagrafiche.indirizzi (istanza_utility_id);
```

### 2.4 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/20260325-XX-replace-utility-with-istanza-indirizzi-mctit.yaml`

---

## STEP 3 — DB: Schema `anagrafiche.soggetti_ruoli_conti_bancari` ✅

**Competenza: DBA** — Completato 2026-03-25

### 3.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  DROP CONSTRAINT IF EXISTS fk_soggetti_ruoli_conti_bancari_utilities;
DROP INDEX IF EXISTS uq_src_bancari_ruolo_utility_conto_uso;
DROP INDEX IF EXISTS uq_src_bancari_ruolo_conto_uso_no_utility;
DROP INDEX IF EXISTS uq_src_bancari_predefinito_utility;
DROP INDEX IF EXISTS uq_src_bancari_predefinito_no_utility;
DROP INDEX IF EXISTS ix_soggetti_ruoli_conti_bancari_utility_id;
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  DROP COLUMN utility_id;

-- bigint come istanze_utilities.id
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD COLUMN istanza_utility_id bigint NULL;

ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD CONSTRAINT fk_src_bancari_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES anagrafiche.istanze_utilities(id);
```

### 3.2 Ricreare vincoli UNIQUE

```sql
-- Legame: un conto per combinazione (ruolo, istanza, conto, uso)
CREATE UNIQUE INDEX uq_src_bancari_ruolo_istanza_conto_uso
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, istanza_utility_id, conto_bancario_id, uso)
  WHERE istanza_utility_id IS NOT NULL;

CREATE UNIQUE INDEX uq_src_bancari_ruolo_conto_uso_no_istanza
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso)
  WHERE istanza_utility_id IS NULL;

-- Predefinito: un solo predefinito per (ruolo, istanza, uso)
CREATE UNIQUE INDEX uq_src_bancari_predefinito_istanza
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, istanza_utility_id, uso)
  WHERE predefinito = true AND istanza_utility_id IS NOT NULL;

CREATE UNIQUE INDEX uq_src_bancari_predefinito_no_istanza
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, uso)
  WHERE predefinito = true AND istanza_utility_id IS NULL;
```

### 3.3 Indice

```sql
CREATE INDEX ix_src_bancari_istanza_utility_id
  ON anagrafiche.soggetti_ruoli_conti_bancari (istanza_utility_id);
```

### 3.4 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/20260325-XX-replace-utility-with-istanza-src-bancari-mctit.yaml`

---

## STEP 4 — DB: Aggiornare viste resolved indirizzi ✅

**Competenza: DBA** — Completato 2026-03-25

Le viste espongono **solo `istanza_utility_id`** — niente `istanza_codice`, niente
`utility_codice`. Nessun JOIN aggiuntivo.

### 4.1 `vw_indirizzi_resolved_base`

Sostituire nella SELECT del ramo RUOLO:
```sql
-- DA:
i.utility_id,
-- e il JOIN: LEFT JOIN config.utilities ut ON ut.id = b.utility_id

-- A:
i.istanza_utility_id,
-- rimuovere il JOIN a config.utilities
```

Ramo SOGGETTO: `NULL::bigint AS istanza_utility_id`

### 4.2 `vw_indirizzi_resolved_ruolo` e `vw_indirizzi_resolved_all`

Dipendono dalla base — si aggiornano automaticamente. Solo la lista colonne nella
SELECT esplicita va aggiornata (`utility_id` → `istanza_utility_id`, rimuovere
`utility_codice`).

### 4.3 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/20260325-XX-recreate-indirizzi-chain-istanza-mctit.yaml`
(DROP + CREATE intera catena: viste + funzioni, come fatto per utility_id)

---

## STEP 5 — DB: Aggiornare funzioni di risoluzione indirizzi ✅

**Competenza: DBA** — Completato 2026-03-25

### 5.1 `script.fn_get_indirizzo`

Firma aggiornata (tutti i tipi con `%TYPE`):
```sql
script.fn_get_indirizzo(
  p_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE,
  p_tipo_codice config.tipi_indirizzi.codice_interno%TYPE,
  p_istanza_utility_id anagrafiche.istanze_utilities.id%TYPE DEFAULT NULL
)
```

RETURNS TABLE: `istanza_utility_id` al posto di `utility_id` e `utility_codice`.
Tipo `bigint` (o `%TYPE`).

Cascata:
1. Layer ruolo + istanza → tipo esatto
2. Layer ruolo + istanza → fallback tipo (da matrice)
3. Layer ruolo generico (istanza NULL) → tipo esatto
4. Layer ruolo generico → fallback tipo
5. Layer soggetto → tipo esatto
6. Layer soggetto → fallback tipo

### 5.2 `script.fn_get_indirizzi_by_ruolo`

Firma aggiornata:
```sql
script.fn_get_indirizzi_by_ruolo(
  p_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE,
  p_istanza_utility_id anagrafiche.istanze_utilities.id%TYPE DEFAULT NULL
)
```

RETURNS TABLE: `istanza_utility_id` al posto di `utility_id` e `utility_codice`.

Con `NULL` restituisce TUTTI. Con valore, filtra per istanza + generici (istanza NULL).

### 5.3 Funzioni layer soggetto

`fn_get_indirizzi_by_soggetto` e `fn_get_indirizzo_by_soggetto` operano sul layer
soggetto che non ha `istanza_utility_id`. L'unico adattamento e nel RETURNS TABLE:
il campo `utility_id` / `utility_codice` diventa `istanza_utility_id bigint`
(sempre NULL per il layer soggetto). Necessario per compatibilita con la UNION nella
vista base e con il RETURNS TABLE della funzione principale.

---

## STEP 6 — DB: Aggiornare vista e funzione conti bancari ✅

**Competenza: DBA** — Completato 2026-03-25

### 6.1 `vw_conti_bancari_per_ruolo`

La vista resta **flat** (nessun DISTINCT ON — decisione confermata).
Sostituire `utility_id` e `utility_codice` con `istanza_utility_id` (solo il campo,
nessun JOIN aggiuntivo). Rimuovere il `LEFT JOIN config.utilities`.

Ramo SOGGETTO: `NULL::bigint AS istanza_utility_id`

### 6.2 `script.fn_get_conto_bancario_predefinito`

Firma aggiornata:
```sql
script.fn_get_conto_bancario_predefinito(
  p_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE,
  p_uso anagrafiche.soggetti_ruoli_conti_bancari.uso%TYPE,
  p_istanza_utility_id anagrafiche.istanze_utilities.id%TYPE DEFAULT NULL
)
```

**Nota:** `RETURNS anagrafiche.vw_conti_bancari_per_ruolo` — il tipo di ritorno dipende
dalla struttura della vista. Se la vista cambia colonne (da `utility_id` a
`istanza_utility_id`), la funzione va ricostruita dopo la vista.

Cascata 7 livelli (stessa struttura, `istanza_utility_id` al posto di `utility_id`):
1. Ruolo + istanza + uso specifico
2. Ruolo + istanza NULL + uso specifico
3. Soggetto + uso specifico
4. Ruolo + istanza + uso GENERICO
5. Ruolo + istanza NULL + uso GENERICO
6. Soggetto + uso GENERICO
7. NULL

### 6.3 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/20260325-XX-recreate-conti-bancari-chain-istanza-mctit.yaml`

---

## STEP 7 — DB: Aggiornare funzioni contatti ✅

**Competenza: DBA** — Completato 2026-03-25

### 7.1 `script.fn_get_contatti`

Sostituire `p_utility_id integer` con `p_istanza_utility_id bigint` nella firma.
Nel corpo, sostituire tutti i riferimenti a `utility_id` / `c.utility_id` /
`p_utility_id` con `istanza_utility_id` / `c.istanza_utility_id` /
`p_istanza_utility_id`.

La cascata contatti resta a **3 livelli** (non 4):

| priority | Condizione | Significato |
|----------|-----------|-------------|
| 1 | ruolo + istanza match | Specifico istanza |
| 2 | ruolo match, istanza NULL/generica | Generico ruolo |
| 3 | solo soggetto | Fallback soggetto |

Il vecchio livello 3 ("soggetto + utility") non ha senso con `istanza_utility_id` e
va eliminato. Il CASE nel calcolo priority va semplificato di conseguenza.

### 7.2 `script.fn_get_contatto_default`

Wrapper su `fn_get_contatti` — aggiornare solo la firma del parametro
(`p_utility_id` → `p_istanza_utility_id bigint`).

### 7.3 Chiamanti da aggiornare

Censimento funzioni/viste che chiamano `fn_get_contatti` o `fn_get_contatto_default`
con `p_utility_id`:

- `script.fn_get_search_detail` — chiama `fn_get_contatti` nella sezione CL (clienti).
  Ha gia `p_utility_id` nella firma — va aggiornato a `p_istanza_utility_id`
- Verificare se ci sono altri chiamanti con: `grep -r 'fn_get_contatti\|fn_get_contatto_default'`

### 7.4 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/20260325-XX-recreate-contatti-chain-istanza-mctit.yaml`

---

## STEP 8 — DB: Aggiornare test pgTAP ✅

**Competenza: DBA** — Completato 2026-03-25

| File test | Modifica |
|-----------|----------|
| `test-indirizzi-utility-cascata.sql` | Rinominare: fixture con `istanza_utility_id` (bigint), cascata 3 livelli con istanza. Serve un'istanza reale nel DB di test |
| `test-conti-bancari-utility-cascata.sql` | Stessa logica, cascata con istanza |
| `test-indirizzi-fallback.sql` | Verificare compatibilita DEFAULT NULL sul nuovo parametro |
| `test_fn_get_conto_bancario_predefinito.sql` | Verificare compatibilita DEFAULT NULL |
| `test-contatti-soggetto-cliente.sql` | Se usa `utility_id`, adattare a `istanza_utility_id` |

**Nota:** i test necessitano di un'istanza utility reale nel DB per le fixture.
Verificare se esiste un helper di creazione istanza nei test esistenti
(es. `create-cliente.sql`, `test-istanza-cliente-chain.sql`).

---

## Riepilogo lavoro DB e documentazione completato (2026-03-25)

### Changeset Liquibase applicati

| # | File | Contenuto |
| --- | --- | --- |
| 01 | `00_schema/anagrafiche/20260325-01-replace-utility-with-istanza-contatti-mctit.yaml` | DROP `utility_id` + ADD `istanza_utility_id bigint` + 3 partial unique index su `contatti` (2 changeSet: DDL+pulizia duplicati, poi indici) |
| 02 | `00_schema/anagrafiche/20260325-02-replace-utility-with-istanza-indirizzi-mctit.yaml` | DROP catena viste/funzioni + DROP `utility_id` + ADD `istanza_utility_id bigint` + 2 partial unique index su `indirizzi` |
| 03 | `00_schema/anagrafiche/20260325-03-replace-utility-with-istanza-src-bancari-mctit.yaml` | DROP catena vista/funzione + DROP `utility_id` + ADD `istanza_utility_id bigint` + 4 partial unique index su `soggetti_ruoli_conti_bancari` |
| 04 | `20_code/script/20260325-04-recreate-indirizzi-chain-istanza-mctit.yaml` | CREATE 4 viste resolved + 4 funzioni con `istanza_utility_id`, senza `utility_codice`, `%TYPE` |
| 05 | `20_code/script/20260325-05-recreate-conti-bancari-chain-istanza-mctit.yaml` | CREATE vista flat + funzione cascata 7 livelli con `istanza_utility_id` |
| 06 | `20_code/script/20260325-06-recreate-contatti-chain-istanza-mctit.yaml` | CREATE `fn_get_contatti` (cascata 3 livelli) + `fn_get_contatto_default` + `trgfn_contatti_set_default_contatto` (contesto 'istanza') |

### Scelte architetturali

- **Tipo `bigint`**: `istanze_utilities.id` e `bigint` — tutti i campi e parametri allineati
- **Viste senza JOIN utility**: espongono solo `istanza_utility_id`, niente `utility_codice`. Il frontend lo ha dal payload cliente
- **Contatti 3 livelli**: cascata semplificata da 4 a 3 (rimosso livello "soggetto + utility")
- **Trigger default contesto 'istanza'**: `trgfn_contatti_set_default_contatto` aggiornato da 'utility' a 'istanza'
- **`fn_get_search_detail` non modificata**: il suo `p_utility_id` e un filtro di ricerca, non il differenziatore

### Test pgTAP

| File | Assert | Stato |
| --- | --- | --- |
| `test-indirizzi-istanza-cascata.sql` | 14 | ✅ Nuovo — partial unique, fn_get_indirizzi_by_ruolo con/senza istanza, fn_get_indirizzo cascata 3 livelli, viste con istanza_utility_id |
| `test-conti-bancari-istanza-cascata.sql` | 10 | ✅ Nuovo — partial unique predefinito, fn_get_conto cascata 7 livelli, vista flat con istanza_utility_id |
| `test_vw_conti_bancari_per_ruolo_gestore.sql` | 5 | ✅ Aggiornato — `utility_id` → `istanza_utility_id` nell'ORDER BY |
| `test-contatti-soggetto-cliente.sql` | 12 | ✅ Aggiornato — fix per `tipo_contatto_id NOT NULL` (changeset 20260324-01) |
| `test-indirizzi-fallback.sql` | 14 | ✅ Invariato — funziona con DEFAULT NULL |
| `test_fn_get_conto_bancario_predefinito.sql` | 6 | ✅ Invariato — funziona con DEFAULT NULL |

Test obsoleti eliminati: `test-indirizzi-utility-cascata.sql`, `test-conti-bancari-utility-cascata.sql`

### Documentazione aggiornata

**Guide operative (3):**

- `docs/it/guide/gestione-degli-indirizzi.md` — cascata con `istanza_utility_id`, vincoli, firme funzioni
- `docs/it/guide/gestione-conti-bancari.md` — vista flat, cascata 7 livelli, firma con `p_istanza_utility_id`
- `docs/it/guide/gestione-dei-contatti.md` — cascata da 4 a 3 livelli, 3 partial unique, trigger 'istanza'

**Doc manuali tabelle (3):**

- `contatti.md`, `indirizzi.md`, `soggetti_ruoli_conti_bancari.md`

**Doc manuali funzioni (5):**

- `fn_get_indirizzo.md`, `fn_get_indirizzi_by_ruolo.md`, `fn_get_conto_bancario_predefinito.md`, `fn_get_contatti.md`, `fn_get_contatto_default.md`

**Doc manuali viste (2):**

- `vw_indirizzi_resolved_base.md`, `vw_conti_bancari_per_ruolo.md`

**Guida istanze (1):**

- `gestione-delle-istanze-utility.md` — nota sulla reperibilita utility da istanza (3 percorsi cronologici)

---

## STEP 9 — Backend: API indirizzi ruolo ✅

**Competenza: Backend Python/Django**

### 9.1 `views_indirizzi_ruolo.py` — `backend/apps/anagrafiche/api/views_indirizzi_ruolo.py`

**Nota:** Le query attualmente leggono da viste DB (`vw_indirizzi_resolved_ruolo`,
`vw_indirizzi_resolved_soggetto`) che gia espongono `istanza_utility_id` (STEP 4).
Le colonne `utility_codice` non esistono piu nelle viste — vanno rimosse dalla SELECT.

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L7 | commento | `utility → ruolo` diventa `istanza → ruolo` |
| L34 | `_COLS` | `v.utility_id` → `v.istanza_utility_id`, rimuovere `v.utility_codice` |
| L64 | `@extend_schema` | `OpenApiParameter("utility_id", int)` → `OpenApiParameter("istanza_utility_id", int)` |
| L72 | commento | `utility specifica` → `istanza specifica`, `fonte='utility'` → `fonte='istanza'` |
| L77 | commento | `utility_id` → `istanza_utility_id` |
| L82-83 | query param | `utility_id_str = request.query_params.get("utility_id")` → `...get("istanza_utility_id")` |
| L94 | SQL fonte | `'utility' AS fonte` → `'istanza' AS fonte` |
| L97 | SQL WHERE | `v.utility_id = %s` → `v.istanza_utility_id = %s` |
| L108-113 | SQL L2 | `v.utility_id IS NULL` → `v.istanza_utility_id IS NULL` |
| L140 | fonte filter | `"utility"` → `"istanza"` nel filtro editabili |
| L150 | `@extend_schema` POST | `"utility_id": IntegerField` → `"istanza_utility_id": IntegerField` |
| L168-175 | handler POST | `payload.get("utility_id")` → `payload.get("istanza_utility_id")`, passare `istanza_utility_id=` al repo |
| L182 | messaggio errore | `ruolo/utility` → `ruolo/istanza` |
| L199 | `@extend_schema` PATCH | `"utility_id"` → `"istanza_utility_id"` |

### 9.2 Repository — `backend/apps/anagrafiche/db/soggetti_repository.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L412 | commento | `utility_id` → `istanza_utility_id` |
| L414 | `_IND_RUOLO_ALLOWED` | `"utility_id"` → `"istanza_utility_id"` |
| L418 | `_IND_RUOLO_NULLABLE` | `"utility_id"` → `"istanza_utility_id"` |
| L434 | `crea_indirizzo_ruolo()` | parametro `utility_id=None` → `istanza_utility_id=None` |
| L442-445 | INSERT SQL | colonna `utility_id` → `istanza_utility_id` nel tuple VALUES e RETURNING |
| L462-482 | `update_indirizzo_ruolo()` | i set ammessi gia derivano da `_IND_RUOLO_ALLOWED` — il rename propagato automaticamente |

**Nota tipo:** `istanza_utility_id` e `bigint` nel DB. Il parametro Python puo restare
`int | None` perche Python int gestisce qualsiasi dimensione. Nei `%s` placeholder nessun
cast necessario — psycopg2 gestisce int→bigint.

### 9.3 Smoke test — `backend/scripts/tests/smoke-test-indirizzi-ruolo.sh`

| Sezione | Cambio |
|---------|--------|
| Indice test (commenti) | `utility` → `istanza` nei nomi test |
| L166 | `UTILITY_ID_FROM_CLIENT` → `ISTANZA_UTILITY_ID_FROM_CLIENT` (estrarre `istanza_utility_id` dal dettaglio cliente) |
| L292, L316, L354 | parametro API `utility_id=` → `istanza_utility_id=` |
| L349-371 | Test 7-8: cascata con `istanza_utility_id` |
| Payload POST/PATCH | campo `utility_id` → `istanza_utility_id` |

---

## STEP 10 — Backend: API conti bancari ruolo ✅

**Competenza: Backend Python/Django**

### 10.1 `views_conti_bancari.py` — `backend/apps/anagrafiche/api/views_conti_bancari.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L171 | `@extend_schema` | `OpenApiParameter("utility_id", int)` → `OpenApiParameter("istanza_utility_id", int)` |
| L178 | commento | `utility → ruolo → soggetto` → `istanza → ruolo → soggetto` |
| L181-182 | query param | `get("utility_id")` → `get("istanza_utility_id")` |
| L184 | service call | `utility_id=utility_id` → `istanza_utility_id=istanza_utility_id` |

### 10.2 Service — `backend/apps/anagrafiche/services/conti_bancari_service.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L134-169 | `list_conti_ruolo()` | parametro `utility_id=None` → `istanza_utility_id=None`, commenti cascata L1/L2/L3 aggiornati |
| L142-149 | L1 query | filtro `utility_id` → `istanza_utility_id` nelle condizioni SQL/repo |
| L151-157 | L2 query | filtro `utility_id IS NULL` → `istanza_utility_id IS NULL` |
| L172-194 | `create_conto_ruolo()` | parametro `utility_id` → `istanza_utility_id` nel payload legame |
| L180-183 | payload build | `payload["utility_id"]` → `payload["istanza_utility_id"]` |

### 10.3 Repository — `backend/apps/anagrafiche/db/conti_bancari_repository.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L38 | `_LEGAME_ALLOWED` | `"utility_id"` → `"istanza_utility_id"` |
| L40 | `_LEGAME_NULLABLE` | `"utility_id"` → `"istanza_utility_id"` |
| L241 | SELECT | `srcb.utility_id` → `srcb.istanza_utility_id` |
| L242 | SELECT + JOIN | rimuovere `u.codice AS utility_codice` e il `LEFT JOIN config.utilities u ON u.id = srcb.utility_id` |
| L287 | `create_conto_ruolo()` | parametro `utility_id` → `istanza_utility_id` |
| L290-294 | INSERT | colonna `utility_id` → `istanza_utility_id` |
| L297-298 | RETURNING | `utility_id` → `istanza_utility_id` |

### 10.4 Smoke test — `backend/scripts/tests/smoke-test-conti-bancari.sh`

| Sezione | Cambio |
|---------|--------|
| L15, L22-23 | Indice test: `utility` → `istanza` |
| L348, L371-372 | Estrazione `UTILITY_ID` dal cliente → `ISTANZA_UTILITY_ID` |
| L370-374 | Payload `utility_id` → `istanza_utility_id` |
| L389-390 | GET param `?utility_id=` → `?istanza_utility_id=` |

---

## STEP 11 — Backend: API contatti ruolo ✅

**Competenza: Backend Python/Django**

### 11.1 `views_contatti_ruolo.py` — `backend/apps/anagrafiche/api/views_contatti_ruolo.py`

**Nota:** I contatti usano query dirette sulla tabella `anagrafiche.contatti` (non viste resolved).
Il campo e gia `istanza_utility_id` nella tabella (STEP 1). Le query SQL vanno aggiornate.

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L42 | commento | `utility specifica` → `istanza specifica`, `fonte='utility'` → `fonte='istanza'` |
| L47 | commento | `utility_id` → `istanza_utility_id` |
| L51-52 | query param | `get("utility_id")` → `get("istanza_utility_id")` |
| L58 | `_COLS` | `c.utility_id` → `c.istanza_utility_id`, rimuovere `u.codice AS utility_codice` |
| L60-61 | `_JOIN` | rimuovere `LEFT JOIN config.utilities u ON u.id = c.utility_id` |
| L68 | SQL fonte L1 | `'utility' AS fonte` → `'istanza' AS fonte` |
| L69 | SQL WHERE L1 | `c.utility_id = %s` → `c.istanza_utility_id = %s` |
| L81 | SQL WHERE L2 | `c.utility_id IS NULL` → `c.istanza_utility_id IS NULL` |
| L103 | fonte filter | `'utility'` → `'istanza'` nel filtro editabili |
| L125 | commento POST | `utility_id opzionale` → `istanza_utility_id opzionale` |
| L126-128 | handler POST | `payload.get("utility_id")` → `payload.get("istanza_utility_id")` |
| L141 | repo call | `utility_id=utility_id` → `istanza_utility_id=istanza_utility_id` |
| L143 | messaggio | `ruolo/utility` → `ruolo/istanza` |

### 11.2 Repository contatti — `backend/apps/anagrafiche/db/soggetti_repository.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L272 | `crea_contatto()` | parametro `utility_id=None` → `istanza_utility_id=None` |
| L275-276 | INSERT SQL | colonna `utility_id` → `istanza_utility_id` |
| L281 | RETURNING | `utility_id` → `istanza_utility_id` |

### 11.3 Smoke test contatti

Se esiste `smoke-test-contatti.sh`, aggiornare con la stessa logica degli altri smoke test.
Verificare esistenza: `backend/scripts/tests/smoke-test-contatti*.sh`

---

## STEP 12 — Backend: API clienti ✅

**Competenza: Backend Python/Django**

### 12.1 `clienti_repository.py` — `backend/apps/anagrafiche/db/clienti_repository.py`

**Nota:** `clienti.utility_id` resta invariato — e il tipo di servizio del cliente.
`clienti.istanza_utility_id` e la FK all'istanza. Il repository clienti espone
`istanza_utility_id` nel dettaglio cliente, che il frontend usa per passarlo ai sotto-drawer.

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| Nessuno | Verificare | Che il dettaglio cliente gia esponga `istanza_utility_id` (campo gia presente nella tabella `clienti`) |
| Query list | Verificare | Che `istanza_utility_id` sia nel SELECT della lista/dettaglio cliente |

**Nota importante:** `clienti.utility_id` (integer, FK → config.utilities) **non va toccato**.
Solo i 3 sotto-drawer (contatti, indirizzi, conti) cambiano da `utility_id` a `istanza_utility_id`.
Il record cliente fornisce `istanza_utility_id` che viene passato ai sotto-drawer.

### 12.2 `clienti_service.py` — `backend/apps/anagrafiche/services/clienti_service.py`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| Nessuno | Verificare | Che `ClienteService` non passi `utility_id` ai sotto-servizi contatti/indirizzi/conti. Se lo fa, rinominare in `istanza_utility_id` |

### 12.3 Lista clienti — **INVARIATO**

La `ClientiSearchTable` usa `utility_id` come filtro colonna per tipo servizio.
Questo resta corretto — la utility e il filtro di ricerca, non il differenziatore istanza.
L'`istanza_utility_id` entra in gioco solo nel drawer del singolo cliente.

---

## STEP 13 — Frontend: Drawer indirizzi, conti, contatti ⬜

**Competenza: Frontend Vue.js**

**Principio generale (da frontend-standards.md):** Un solo modo di fare ogni cosa.
La modifica e meccanica (rename prop + rename parametro API) su componenti riutilizzabili
in `core/components/`. I componenti dominio (`anagrafiche/`) passano solo il valore.

### 13.1 Drawer Indirizzi — `frontend/src/core/components/IndirizziSoggettoDrawer.vue`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L34 | commento | `utilityId` → `istanzaUtilityId` |
| L40 | prop | `utilityId: { type: Number, default: null }` → `istanzaUtilityId: { type: Number, default: null }` |
| L66 | load params | `props.utilityId ? { utility_id: props.utilityId }` → `props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId }` |
| L214-215 | save payload | `props.utilityId → payload.utility_id` → `props.istanzaUtilityId → payload.istanza_utility_id` |

### 13.2 Drawer Contatti — `frontend/src/core/components/ContattiSoggettoDrawer.vue`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L33 | commento | `utilityId` → `istanzaUtilityId` |
| L38 | prop | `utilityId: { type: Number, default: null }` → `istanzaUtilityId: { type: Number, default: null }` |
| L68-69 | load params | `props.utilityId ? { utility_id: props.utilityId }` → `props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId }` |
| L138 | save payload | `props.utilityId ? { utility_id: props.utilityId }` → `props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId }` |

### 13.3 Drawer Conti Bancari — `frontend/src/core/components/ContiBancariDrawer.vue`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L41 | prop | `utilityId: { type: Number, default: null }` → `istanzaUtilityId: { type: Number, default: null }` |
| L71-72 | load params | `props.utilityId ? { utility_id: props.utilityId }` → `props.istanzaUtilityId ? { istanza_utility_id: props.istanzaUtilityId }` |
| L136-138 | save payload | `props.utilityId → payload.utility_id` → `props.istanzaUtilityId → payload.istanza_utility_id` |

### 13.4 ClienteDrawer — `frontend/src/anagrafiche/components/ClienteDrawer.vue`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L444 | sub-drawer contatti | `:utility-id="detail.utility_id"` → `:istanza-utility-id="detail.istanza_utility_id"` |
| L454 | sub-drawer indirizzi | `:utility-id="detail.utility_id"` → `:istanza-utility-id="detail.istanza_utility_id"` |
| L465 | sub-drawer conti | `:utility-id="detail.utility_id"` → `:istanza-utility-id="detail.istanza_utility_id"` |

**Nota:** `detail.utility_id` va cambiato con `detail.istanza_utility_id`. Il campo
`istanza_utility_id` deve essere presente nel payload di dettaglio del cliente restituito
dal backend (STEP 12.1). `form.utility_id` per la creazione cliente **resta invariato**
(e il tipo di servizio, non l'istanza).

### 13.5 ClientiView — `frontend/src/anagrafiche/views/ClientiView.vue`

| Riga attuale | Cambio | Dettaglio |
|---|---|---|
| L32 | ref contatti | `utilityId: null` → `istanzaUtilityId: null` |
| L33 | ref indirizzi | `utilityId: null` → `istanzaUtilityId: null` |
| L37 | handler contatti | `utilityId: data.utility_id` → `istanzaUtilityId: data.istanza_utility_id` |
| L41 | handler indirizzi | `utilityId: data.utility_id` → `istanzaUtilityId: data.istanza_utility_id` |
| L49 | handler conti | `utilityId: data.utility_id` → `istanzaUtilityId: data.istanza_utility_id` |
| L88 | template contatti | `:utility-id="contattiDrawer.utilityId"` → `:istanza-utility-id="contattiDrawer.istanzaUtilityId"` |
| L96 | template indirizzi | `:utility-id="indirizziDrawer.utilityId"` → `:istanza-utility-id="indirizziDrawer.istanzaUtilityId"` |
| L105 | template conti | `:utility-id="contiBancariDrawer.utilityId"` → `:istanza-utility-id="contiBancariDrawer.istanzaUtilityId"` |

**Nota:** `data.utility_id` (dal record riga della tabella clienti) diventa
`data.istanza_utility_id`. Il campo deve essere esposto dalla API lista clienti
oppure dal dettaglio. Verificare che la query lista clienti nel backend includa
`istanza_utility_id`.

### 13.6 ClientiSearchTable — **INVARIATO**

`store.filters.utility_id` resta invariato — filtra per tipo servizio (utility),
non per istanza. Corretto cosi.

### 13.7 API client — `frontend/src/anagrafiche/api/anagrafiche.js`

Le funzioni `listRuoloContatti`, `listRuoloContiBancari`, `listRuoloIndirizzi` ricevono
`params` generico — non serve modificarle. Il rename del parametro e gia gestito
dai drawer (13.1–13.3) che costruiscono `{ istanza_utility_id: X }` invece di
`{ utility_id: X }`.

### 13.8 Badge fonte nei card

Il badge `utility_codice` nei card resta — viene dal payload cliente che ha
`utility_id` sincronizzato dal BA. Non dipende dalla vista (che non espone piu
`utility_codice`). Nessuna modifica.

---

## STEP 14 — Test (backend ✅, frontend ⬜)

**Competenza: Tutti**

### 14.1 Test unitari Django

| File | Cambio |
|------|--------|
| `apps/anagrafiche/tests/api/test_indirizzi_ruolo_api.py` | `utility_id` → `istanza_utility_id` in fixture, assertion, payload (L43-44, L59, L63-74) |
| `apps/anagrafiche/tests/services/test_conti_bancari_service.py` | `utility_id` → `istanza_utility_id` in mock, fixture, nome test (L32-34) |
| `apps/anagrafiche/tests/services/test_clienti_service.py` | Verificare se i mock passano `utility_id` ai sotto-servizi. `utility_id` nel payload creazione cliente **resta** (e il tipo servizio), ma se il service crea contatti/indirizzi con `utility_id` va cambiato in `istanza_utility_id` |

### 14.2 Smoke test (3 script)

| Script | Note |
|--------|------|
| `smoke-test-indirizzi-ruolo.sh` | Dettaglio in STEP 9.3 |
| `smoke-test-conti-bancari.sh` | Dettaglio in STEP 10.4 |
| `smoke-test-clienti.sh` | L178, L188: se usa `utility_id` per cascata sotto-drawer, aggiornare. Il filtro lista clienti per `utility_id` **resta** |

### 14.3 Test manuali UI (post-frontend)

- [ ] Creare contatto per istanza specifica → verificare salvataggio con `istanza_utility_id`
- [ ] Creare indirizzo per istanza specifica → idem
- [ ] Creare conto bancario per istanza specifica → idem
- [ ] Verificare cascata: istanza → ruolo generico → soggetto (3 livelli visibili nel drawer)
- [ ] Verificare scenario critico: due clienti stessa utility (GAS), istanze diverse,
  possano avere indirizzi/contatti/conti diversi senza collisione UNIQUE
- [ ] Verificare che il badge utility_codice resti visibile nei card

### 14.4 Esecuzione test Django

```bash
# Test singola app
./manage-test.sh apps.anagrafiche.tests.api -v 2
./manage-test.sh apps.anagrafiche.tests.services -v 2

# Tutti i test
./manage-test.sh -v 2
```

---

## STEP 15 — Documentazione ✅

**Competenza: Tutti** — Completato 2026-03-25

### 15.1 Guide operative

- `gestione-degli-indirizzi.md` — cascata con istanza_utility_id
- `gestione-conti-bancari.md` — idem
- `gestione-dei-contatti.md` — cascata a 3 livelli (non piu 4)

### 15.2 Doc funzioni DB (auto-generata, aggiornata dopo apply)

- `fn_get_indirizzo.md` — nuovo parametro `p_istanza_utility_id`
- `fn_get_indirizzi_by_ruolo.md` — idem
- `fn_get_conto_bancario_predefinito.md` — idem
- `fn_get_contatti.md` — `p_istanza_utility_id`, cascata 3 livelli
- `fn_get_contatto_default.md` — idem

### 15.3 Doc manuali funzioni

Aggiornare i file in `docs/it/dbzero/script/manual/` per le funzioni modificate.

### 15.4 Aggiornare il WIP precedente

`refactor-indirizzi-conti-utility.md` — aggiungere nota che il refactor DB con `utility_id`
e stato superato da questo refactor con `istanza_utility_id`.

---

## Riepilogo impatto (aggiornato dopo analisi codice)

| Area | File impattati | Complessita |
|------|---------------|-------------|
| DB schema | 3 tabelle (DROP utility_id + ADD istanza_utility_id bigint + vincoli) | ✅ media |
| DB viste | 4 (resolved base/ruolo/soggetto/all) + 1 (conti flat) | ✅ media |
| DB funzioni indirizzi | 4 (fn_get_indirizzo, by_ruolo, by_soggetto, indirizzo_by_soggetto) | ✅ media |
| DB funzioni conti | 1 (fn_get_conto_bancario_predefinito) | ✅ bassa |
| DB funzioni contatti | 2 (fn_get_contatti, fn_get_contatto_default) + trigger | ✅ media |
| DB test pgTAP | 6 file (2 nuovi + 4 aggiornati) | ✅ bassa |
| **Backend views** | **3 file** (`views_indirizzi_ruolo.py`, `views_contatti_ruolo.py`, `views_conti_bancari.py`) | **media** |
| **Backend repository** | **2 file** (`soggetti_repository.py` indirizzi+contatti, `conti_bancari_repository.py`) | **media** |
| **Backend service** | **1 file** (`conti_bancari_service.py`) | **bassa** |
| **Backend clienti** | **2 file** (`clienti_repository.py` verifica, `clienti_service.py` verifica) | **bassa** |
| **Backend test** | **3 file** (`test_indirizzi_ruolo_api.py`, `test_conti_bancari_service.py`, `test_clienti_service.py`) | **bassa** |
| **Smoke test** | **3 script** (`smoke-test-indirizzi-ruolo.sh`, `smoke-test-conti-bancari.sh`, `smoke-test-clienti.sh`) | **bassa** |
| **Frontend drawer core** | **3 file** (`IndirizziSoggettoDrawer.vue`, `ContattiSoggettoDrawer.vue`, `ContiBancariDrawer.vue`) | **bassa** |
| **Frontend clienti** | **2 file** (`ClienteDrawer.vue`, `ClientiView.vue`) | **bassa** |
| **Frontend API/store** | **0 file** (nessuna modifica necessaria — params sono dinamici) | **nessuna** |
| Documentazione | 13 file (guide + funzioni + manuali + viste) | ✅ bassa |

**Totale file da modificare: Backend 14, Frontend 5**

---

## Ordine di esecuzione

```
STEP 1-3   → DB: schema (3 tabelle) .............. DBA       ✅ 2026-03-25
STEP 4-7   → DB: viste + funzioni (indirizzi,
             conti, contatti) ..................... DBA       ✅ 2026-03-25
STEP 8     → DB: test pgTAP ...................... DBA       ✅ 2026-03-25
STEP 15    → Documentazione DB ................... DBA       ✅ 2026-03-25
─── FASE BACKEND ──────────────────────────────────────────────────────
STEP 9     → Backend: API indirizzi ruolo ........ Backend   ✅ 2026-03-25
STEP 10    → Backend: API conti bancari ruolo .... Backend   ✅ 2026-03-25
STEP 11    → Backend: API contatti ruolo ......... Backend   ✅ 2026-03-25
STEP 12    → Backend: API clienti (verifica) ..... Backend   ✅ 2026-03-25
STEP 14.1  → Backend: test unitari Django ........ Backend   ✅ 2026-03-25
STEP 14.2  → Backend: smoke test (3 script) ...... Backend   ✅ 2026-03-25
─── FASE FRONTEND (dopo) ──────────────────────────────────────────────
STEP 13.1  → Frontend: 3 drawer core ............ Frontend  ✅ 2026-03-25
STEP 13.4  → Frontend: ClienteDrawer ............ Frontend  ✅ 2026-03-25
STEP 13.5  → Frontend: ClientiView .............. Frontend  ✅ 2026-03-25
STEP 14.3  → Frontend: test manuali UI .......... Frontend  ⬜ DA FARE
```

---

*ZeroERP Refactor istanza_utility — aperto 25 marzo 2026*
*Aggiornato: 25 marzo 2026 — piano dettagliato backend/frontend con analisi file reali*
*Priorita CRITICA — prerequisito architetturale per gestione clienti multi-istanza*
