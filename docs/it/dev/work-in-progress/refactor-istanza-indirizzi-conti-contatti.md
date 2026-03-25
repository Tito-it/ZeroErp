# WIP — Refactor: da utility_id a istanza_utility_id su indirizzi, conti bancari e contatti

> Data apertura: 2026-03-25
>
> Stato: **IN CORSO** — DB e documentazione completati, backend/frontend da fare
>
> Priorita: **CRITICA** — difetto architetturale, va risolto prima di proseguire

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

## STEP 9 — Backend: API indirizzi ruolo

**Competenza: Backend Python/Django**

### 9.1 `views_indirizzi_ruolo.py`

- `GET /ruoli/{id}/indirizzi/?istanza_utility_id=X` — sostituisce `?utility_id=X`
- `POST` — campo `istanza_utility_id` nel payload (sostituisce `utility_id`)
- `PATCH` — idem

### 9.2 Repository

- `list_indirizzi_ruolo(soggetto_ruolo_id, istanza_utility_id=None)`
- `crea_indirizzo_ruolo(..., istanza_utility_id=None)`
- Tutti i metodi: rinominare parametro `utility_id` → `istanza_utility_id`

### 9.3 Service

- Validazione: se `istanza_utility_id` fornito, verificare che esista e appartenga
  allo stesso soggetto (tramite `istanze_utilities.soggetto_id`)

### 9.4 Smoke test

- `smoke-test-indirizzi-ruolo.sh` — aggiornare parametri

---

## STEP 10 — Backend: API conti bancari ruolo

**Competenza: Backend Python/Django**

Stessa logica dello STEP 9 applicata a:

- `views_conti_bancari.py` (o view dedicata ruolo)
- `conti_bancari_repository.py`
- `conti_bancari_service.py`
- `smoke-test-conti-bancari.sh`

Rinominare `utility_id` → `istanza_utility_id` ovunque.

---

## STEP 11 — Backend: API contatti ruolo

**Competenza: Backend Python/Django**

Stessa logica applicata a:

- `views_contatti_ruolo.py`
- Repository/service contatti
- Smoke test contatti

---

## STEP 12 — Backend: API clienti

**Competenza: Backend Python/Django**

### 12.1 Drawer cliente

Il ClienteDrawer passa il contesto ai sotto-drawer (contatti, indirizzi, conti).
Deve passare `istanza_utility_id` — disponibile direttamente dal record cliente
(`clienti.istanza_utility_id`).

### 12.2 Lista clienti

La ClientiSearchTable usa `utility_id` come filtro colonna. Questo resta invariato —
la utility e il filtro corretto per la lista (mostra il tipo di servizio).
L'`istanza_utility_id` entra in gioco solo quando si apre il drawer del singolo cliente.

---

## STEP 13 — Frontend: Drawer indirizzi, conti, contatti

**Competenza: Frontend Vue.js**

### 13.1 Prop rename

Tutti e tre i drawer:
- Prop `utility-id` → `istanza-utility-id`
- Parametro API: `utility_id` → `istanza_utility_id`

### 13.2 API client

File: `frontend/src/anagrafiche/api/anagrafiche.js`

```javascript
// Il params conteneva { utility_id: X }, ora conterra { istanza_utility_id: X }
```

### 13.3 Badge fonte

Il badge "utility_codice" nei card viene dal payload cliente (che ha gia `utility_id`
sincronizzato dal BA). Non serve derivarlo dalla vista — il frontend lo ha gia
nel contesto del drawer.

### 13.4 ClienteDrawer e ClientiView

- `ClienteDrawer.vue`: passa `istanza-utility-id` ai sotto-drawer (dal record cliente)
- `ClientiView.vue`: `onContatti/onIndirizzi/onContiBancari` passa `istanza_utility_id`
  dal record cliente

---

## STEP 14 — Test

**Competenza: Tutti**

### 14.1 Backend

- Aggiornare tutti i test unitari che usano `utility_id` → `istanza_utility_id`
- Smoke test: tutti i 3 script

### 14.2 Frontend

- Test manuali UI: creare contatti/indirizzi/conti per istanza specifica
- Verificare cascata: istanza → ruolo generico → soggetto
- Verificare che due clienti stessa utility, istanze diverse, possano avere dati diversi

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

## Riepilogo impatto

| Area | File impattati | Complessita |
|------|---------------|-------------|
| DB schema | 3 tabelle (DROP utility_id + ADD istanza_utility_id bigint + vincoli) | media |
| DB viste | 4 (resolved base/ruolo/soggetto/all) + 1 (conti flat) | media |
| DB funzioni indirizzi | 4 (fn_get_indirizzo, by_ruolo, by_soggetto, indirizzo_by_soggetto) | media |
| DB funzioni conti | 1 (fn_get_conto_bancario_predefinito) | bassa |
| DB funzioni contatti | 2 (fn_get_contatti, fn_get_contatto_default) + chiamanti (fn_get_search_detail) | media |
| DB test pgTAP | 4-5 file | bassa |
| Backend API | 6-8 file (views, repository, service per 3 entita) | media |
| Backend test | 4-5 file | bassa |
| Frontend drawer | 3 drawer + ClienteDrawer + ClientiView | bassa (rename prop) |
| Frontend API | 1 file (anagrafiche.js) | bassa |
| Documentazione | 8-10 file | bassa |

---

## Ordine di esecuzione

```
STEP 1-3   → DB: schema (3 tabelle) .............. DBA       ✅ 2026-03-25
STEP 4-7   → DB: viste + funzioni (indirizzi,
             conti, contatti) ..................... DBA       ✅ 2026-03-25
STEP 8     → DB: test pgTAP ...................... DBA       ✅ 2026-03-25
STEP 9-12  → Backend: API 3 entita + clienti ...... Backend  ⬜ DA FARE
STEP 13    → Frontend: prop rename + API .......... Frontend ⬜ DA FARE
STEP 14    → Test integrazione ................... Tutti     ⬜ DA FARE
STEP 15    → Documentazione ...................... Tutti     ✅ 2026-03-25
```

---

*ZeroERP Refactor istanza_utility — aperto 25 marzo 2026*
*Priorita CRITICA — prerequisito architetturale per gestione clienti multi-istanza*
