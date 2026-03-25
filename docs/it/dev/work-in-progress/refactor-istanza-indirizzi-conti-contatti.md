# WIP — Refactor: da utility_id a istanza_utility_id su indirizzi, conti bancari e contatti

> Data apertura: 2026-03-25
>
> Stato: **DA FARE** — priorita alta, bloccante
>
> Priorita: **CRITICA** — difetto architetturale, va risolto prima di proseguire

---

## Contesto e motivazioni della scelta

### Percorso decisionale

Durante lo sprint 8 (gestione clienti) e emerso che indirizzi, conti bancari e contatti
a livello ruolo non avevano un campo per differenziare i dati per utility, a differenza
del modello contatti che gia aveva `utility_id`. E stato quindi avviato il refactor
`refactor-indirizzi-conti-utility.md` che ha aggiunto `utility_id` a tutte e tre le tabelle.

Il refactor e stato completato end-to-end (DB, backend, frontend, test, documentazione).
Tuttavia, durante la fase di test e verifica funzionale, l'analisi di uno scenario reale
ha evidenziato un difetto architetturale nel campo scelto come differenziatore.

### Scenario che ha evidenziato il problema

Soggetto Titini, azienda multi-sede:

1. **1 gennaio** — richiesta attivazione GAS per sede Corridonia → cliente 100, utility=GAS
2. **20 gennaio** — attivazione completata, indirizzo fatturazione: Via Roma 1, Corridonia
3. **1 marzo** — richiesta attivazione GAS per sede Civitanova → cliente 200, utility=GAS
4. **Problema**: il vincolo `UNIQUE(soggetto_ruolo_id, utility_id, tipo_indirizzo_id)`
   impedisce un secondo indirizzo fatturazione perche entrambi i clienti condividono
   lo stesso `soggetto_ruolo_id` (CLIENTE) e la stessa `utility_id` (GAS)

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
- **Implica la utility**: `istanza_utility → billing_account → utility`, quindi
  `utility_codice` e sempre derivabile per la UI senza campo ridondante
- **Elimina un livello di cascata**: il livello "generico utility" (utility valorizzata,
  istanza NULL) non ha senso pratico — o il dato e specifico dell'istanza, o e generico
  del ruolo. Non esiste un caso d'uso per "generico della utility ma non dell'istanza"
- **Stessa complessita implementativa**: 3 livelli di cascata come prima, stesso numero
  di partial unique index, stesse funzioni di risoluzione — cambia solo il campo

### Decisione

Sostituire `utility_id` con `istanza_utility_id` su tutte e tre le tabelle prima di
procedere con qualsiasi altro sviluppo. Non essendo in produzione, non ci sono vincoli
di retrocompatibilita. Il costo di fare il refactor ora e minimo rispetto al costo di
farlo dopo con dati in produzione.

---

## Problema tecnico

Il refactor precedente ha aggiunto `utility_id` a indirizzi, conti bancari e contatti
per differenziare i dati per utility (GAS, IDRICO, ecc.). Ma `utility_id` non e il
differenziatore corretto per i motivi descritti sopra.

**Il vero differenziatore e `istanza_utility_id`**, che:
- Esiste sempre (ogni attivazione ha una istanza utility)
- E unico per combinazione soggetto + servizio specifico
- Implica gia la utility (derivabile con JOIN)
- Elimina la necessita del livello intermedio "generico utility"

## Soluzione

Sostituire `utility_id` con `istanza_utility_id` su tutte e tre le tabelle.

### Cascata target (3 livelli — stessa di prima, campo diverso)

| Priorita | istanza_utility_id | soggetto_ruolo_id | Significato | Editabile |
|----------|-------------------|-------------------|-------------|-----------|
| 1 | valorizzato | valorizzato | Specifico istanza (Titini GAS Corridonia) | Si |
| 2 | NULL | valorizzato | Generico ruolo CLIENTE | Si |
| 3 | — | — | Soggetto (fallback da tabelle soggetto) | No (readonly) |

**Vantaggi rispetto al modello con `utility_id`:**
- Nessuna collisione: due GAS dello stesso soggetto hanno istanze diverse
- Livello "generico utility" eliminato — non ha senso pratico
- Cascata piu semplice e corretta
- `utility_codice` per la UI si deriva sempre da istanza → BA → utility

### Nota: nessuna retrocompatibilita necessaria

Non siamo in produzione. Possiamo sostituire direttamente senza migrazioni di transizione.

---

## Tabelle impattate

| Tabella | Campo attuale | Campo nuovo | Note |
|---------|--------------|-------------|------|
| `anagrafiche.contatti` | `utility_id` (FK → config.utilities) | `istanza_utility_id` (FK → config.istanze_utilities) | Gia esistente da sprint precedenti |
| `anagrafiche.indirizzi` | `utility_id` (FK → config.utilities) | `istanza_utility_id` (FK → config.istanze_utilities) | Aggiunto nel refactor 2026-03-24 |
| `anagrafiche.soggetti_ruoli_conti_bancari` | `utility_id` (FK → config.utilities) | `istanza_utility_id` (FK → config.istanze_utilities) | Aggiunto nel refactor 2026-03-24 |

---

## STEP 1 — DB: Schema `anagrafiche.contatti`

**Competenza: DBA**

### 1.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
-- Rimuovere vecchio campo e FK
ALTER TABLE anagrafiche.contatti DROP CONSTRAINT IF EXISTS fk_contatti_utilities;
ALTER TABLE anagrafiche.contatti DROP COLUMN utility_id;

-- Aggiungere nuovo campo
ALTER TABLE anagrafiche.contatti
  ADD COLUMN istanza_utility_id integer NULL;

ALTER TABLE anagrafiche.contatti
  ADD CONSTRAINT fk_contatti_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES config.istanze_utilities(id);
```

### 1.2 Ricreare vincoli UNIQUE

Rimuovere i vecchi vincoli basati su `utility_id` e creare i nuovi:

```sql
-- Per righe con istanza_utility_id NULL (generico ruolo)
CREATE UNIQUE INDEX uq_contatti_ruolo_tipo_no_istanza
  ON anagrafiche.contatti (soggetto_id, soggetto_ruolo_id, tipo_contatto_id)
  WHERE istanza_utility_id IS NULL AND soggetto_ruolo_id IS NOT NULL;

-- Per righe con istanza_utility_id valorizzato
CREATE UNIQUE INDEX uq_contatti_ruolo_istanza_tipo
  ON anagrafiche.contatti (soggetto_id, soggetto_ruolo_id, istanza_utility_id, tipo_contatto_id)
  WHERE istanza_utility_id IS NOT NULL;
```

**Nota:** verificare i nomi esatti dei vincoli esistenti da droppare. La tabella contatti
ha una struttura multilevel (soggetto/ruolo/utility) — i vincoli partial index vanno
ricreati tutti sostituendo `utility_id` con `istanza_utility_id`.

### 1.3 Indice

```sql
CREATE INDEX ix_contatti_istanza_utility_id
  ON anagrafiche.contatti (istanza_utility_id);
```

### 1.4 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-XX-replace-utility-with-istanza-contatti-mctit.yaml`

---

## STEP 2 — DB: Schema `anagrafiche.indirizzi`

**Competenza: DBA**

### 2.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
ALTER TABLE anagrafiche.indirizzi DROP CONSTRAINT IF EXISTS fk_indirizzi_utilities;
ALTER TABLE anagrafiche.indirizzi DROP COLUMN utility_id;

ALTER TABLE anagrafiche.indirizzi
  ADD COLUMN istanza_utility_id integer NULL;

ALTER TABLE anagrafiche.indirizzi
  ADD CONSTRAINT fk_indirizzi_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES config.istanze_utilities(id);
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

File: `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-XX-replace-utility-with-istanza-indirizzi-mctit.yaml`

---

## STEP 3 — DB: Schema `anagrafiche.soggetti_ruoli_conti_bancari`

**Competenza: DBA**

### 3.1 Rimuovere `utility_id`, aggiungere `istanza_utility_id`

```sql
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  DROP CONSTRAINT IF EXISTS fk_soggetti_ruoli_conti_bancari_utilities;
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  DROP COLUMN utility_id;

ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD COLUMN istanza_utility_id integer NULL;

ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD CONSTRAINT fk_src_bancari_istanze_utilities
  FOREIGN KEY (istanza_utility_id) REFERENCES config.istanze_utilities(id);
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

File: `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-XX-replace-utility-with-istanza-src-bancari-mctit.yaml`

---

## STEP 4 — DB: Aggiornare viste resolved indirizzi

**Competenza: DBA**

### 4.1 `vw_indirizzi_resolved_base`

Sostituire nella SELECT:
```sql
-- DA:
i.utility_id,
u.codice AS utility_codice
LEFT JOIN config.utilities u ON u.id = i.utility_id

-- A:
i.istanza_utility_id,
iu.codice AS istanza_codice,
ut.codice AS utility_codice
LEFT JOIN config.istanze_utilities iu ON iu.id = i.istanza_utility_id
LEFT JOIN vendite.billing_account ba ON ba.istanza_utility_id = iu.id
LEFT JOIN config.utilities ut ON ut.id = ba.utility_id
```

**Nota:** verificare il percorso corretto per derivare `utility_codice` da
`istanza_utility_id`. Potrebbe essere diretto (`istanze_utilities.utility_id`)
o tramite `billing_account`. Controllare lo schema.

### 4.2 `vw_indirizzi_resolved_ruolo`

Se dipende dalla base, aggiornamento automatico. Altrimenti stesse modifiche.

### 4.3 `vw_indirizzi_resolved_all`

Ramo soggetto: `NULL AS istanza_utility_id, NULL AS istanza_codice, NULL AS utility_codice`

### 4.4 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/YYYYMMDD-XX-recreate-indirizzi-chain-istanza-mctit.yaml`
(DROP + CREATE intera catena: viste + funzioni, come fatto per utility_id)

---

## STEP 5 — DB: Aggiornare funzioni di risoluzione indirizzi

**Competenza: DBA**

### 5.1 `script.fn_get_indirizzo`

Firma aggiornata:
```sql
script.fn_get_indirizzo(
  p_soggetto_ruolo_id BIGINT,
  p_tipo_codice TEXT,
  p_istanza_utility_id INTEGER DEFAULT NULL  -- sostituisce p_utility_id
)
```

Cascata:
1. Layer ruolo + istanza → tipo esatto
2. Layer ruolo + istanza → fallback tipo
3. Layer ruolo generico (istanza NULL) → tipo esatto
4. Layer ruolo generico → fallback tipo
5. Layer soggetto → tipo esatto
6. Layer soggetto → fallback tipo

### 5.2 `script.fn_get_indirizzi_by_ruolo`

Firma aggiornata:
```sql
script.fn_get_indirizzi_by_ruolo(
  p_soggetto_ruolo_id BIGINT,
  p_istanza_utility_id INTEGER DEFAULT NULL
)
```

Con `NULL` restituisce TUTTI. Con valore, filtra per istanza + generici.

---

## STEP 6 — DB: Aggiornare vista e funzione conti bancari

**Competenza: DBA**

### 6.1 `vw_conti_bancari_per_ruolo`

Sostituire `utility_id` / `utility_codice` con `istanza_utility_id` / `istanza_codice` / `utility_codice`
(derivato tramite JOIN).

### 6.2 `script.fn_get_conto_bancario_predefinito`

Firma aggiornata:
```sql
script.fn_get_conto_bancario_predefinito(
  p_soggetto_ruolo_id BIGINT,
  p_uso VARCHAR,
  p_istanza_utility_id INTEGER DEFAULT NULL
)
```

Cascata 7 livelli (stessa struttura, `istanza_utility_id` al posto di `utility_id`):
1. Ruolo + istanza + uso specifico
2. Ruolo + istanza NULL + uso specifico
3. Soggetto + uso specifico
4. Ruolo + istanza + uso GENERICO
5. Ruolo + istanza NULL + uso GENERICO
6. Soggetto + uso GENERICO
7. NULL

### 6.3 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/YYYYMMDD-XX-recreate-conti-bancari-chain-istanza-mctit.yaml`

---

## STEP 7 — DB: Aggiornare funzioni/viste contatti

**Competenza: DBA**

Stessa logica degli STEP 4-6 applicata alle viste e funzioni contatti.
Verificare quali viste/funzioni usano `utility_id` su `anagrafiche.contatti` e aggiornarle.

### 7.1 Changeset Liquibase

File: `db/changelog/migrations_v2/20_code/script/YYYYMMDD-XX-recreate-contatti-chain-istanza-mctit.yaml`

---

## STEP 8 — DB: Aggiornare test pgTAP

**Competenza: DBA**

| File test | Modifica |
|-----------|----------|
| `test-indirizzi-utility-cascata.sql` | Rinominare/adattare: fixture con `istanza_utility_id`, cascata 3 livelli con istanza |
| `test-conti-bancari-utility-cascata.sql` | Stessa logica, cascata con istanza |
| `test-indirizzi-fallback.sql` | Verificare compatibilita DEFAULT NULL |
| `test_fn_get_conto_bancario_predefinito.sql` | Verificare compatibilita DEFAULT NULL |
| Eventuali test contatti | Adattare se presenti |

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
  allo stesso soggetto (tramite `istanze_utilities → soggetto_id`)
- `create_with_dedup`: messaggio errore aggiornato

### 9.4 Smoke test

- `smoke-test-indirizzi-ruolo.sh` — aggiornare parametri `utility_id` → `istanza_utility_id`

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

Il ClienteDrawer attualmente passa `utility_id` ai sotto-drawer (contatti, indirizzi, conti).
Deve passare `istanza_utility_id` — derivato dal record cliente:

```
cliente → billing_account → istanza_utility_id
```

Verificare che il GET cliente ritorni `istanza_utility_id` nel payload.

### 12.2 Lista clienti

La ClientiSearchTable usa `utility_id` come filtro. Valutare se aggiungere
anche `istanza_utility_id` come filtro o se la utility basta per la lista
(la utility si mostra nella colonna, l'istanza e un livello sotto).

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
// DA:
export const listRuoloIndirizzi = (ruoloId, params) =>
  api.get(`/anagrafiche/ruoli/${ruoloId}/indirizzi/`, { params })
// Il params conteneva { utility_id: X }, ora conterra { istanza_utility_id: X }
```

### 13.3 Badge fonte

Il badge "utility_codice" nei card deve derivare da istanza → utility.
Il backend dovrebbe gia restituire `utility_codice` nel payload (derivato via JOIN).
Se non lo fa, aggiungere nel serializer/repository.

### 13.4 ClienteDrawer e ClientiView

- `ClienteDrawer.vue`: passa `istanza-utility-id` ai sotto-drawer
- `ClientiView.vue`: `onContatti/onIndirizzi/onContiBancari` passa `istanza_utility_id`
  dal record cliente (non piu `utility_id`)

### 13.5 ClientiSearchTable

Valutare se la colonna filtro resta `utility_id` (per filtrare per utility nella lista)
o se serve anche `istanza_utility_id`.

---

## STEP 14 — Test

**Competenza: Tutti**

### 14.1 Backend

- Aggiornare tutti i test unitari che usano `utility_id` → `istanza_utility_id`
- `test_clienti_service.py`, `test_conti_bancari_service.py`, test contatti/indirizzi
- Smoke test: tutti i 3 script

### 14.2 Frontend

- Test manuali UI: creare contatti/indirizzi/conti per istanza specifica
- Verificare cascata: istanza → ruolo generico → soggetto
- Verificare che due clienti stessa utility, istanze diverse, possano avere dati diversi

---

## STEP 15 — Documentazione

**Competenza: Tutti**

### 15.1 Guide operative

- `gestione-degli-indirizzi.md` — cascata con istanza_utility_id
- `gestione-conti-bancari.md` — idem
- Guide contatti — idem

### 15.2 Doc API manuali

- `api_indirizzi_ruolo.md` — parametro istanza_utility_id
- `api_conti_bancari_ruolo.md` — idem
- `api_contatti_ruolo.md` — idem

### 15.3 Doc funzioni DB

- `fn_get_indirizzo.md` — nuovo parametro
- `fn_get_indirizzi_by_ruolo.md` — idem
- `fn_get_conto_bancario_predefinito.md` — idem

### 15.4 Aggiornare il WIP precedente

- `refactor-indirizzi-conti-utility.md` — aggiungere nota che e stato superato da questo refactor

---

## Riepilogo impatto

| Area | File impattati | Complessita |
|------|---------------|-------------|
| DB schema | 3 tabelle (DROP utility_id + ADD istanza_utility_id + vincoli) | media |
| DB viste | 4-6 (resolved indirizzi + flat conti + eventuali contatti) | media |
| DB funzioni | 4-5 (fn_get_indirizzo, fn_get_indirizzi_by_ruolo, fn_get_conto_predefinito, contatti) | media |
| DB test pgTAP | 4-5 file | bassa |
| Backend API | 6-8 file (views, repository, service per 3 entita) | media |
| Backend test | 4-5 file | bassa |
| Frontend drawer | 3 drawer + ClienteDrawer + ClientiView | bassa (rename prop) |
| Frontend API | 1 file (anagrafiche.js) | bassa |
| Documentazione | 8-10 file | bassa |

**Stima complessiva:** il lavoro e speculare al refactor utility_id appena completato.
La struttura e identica, cambia solo il campo. Il grosso del lavoro e DB (schema + viste + funzioni).
Backend e frontend sono rename meccanici.

---

## Ordine di esecuzione

```
STEP 1-3   → DB: schema (3 tabelle) .............. DBA
STEP 4-7   → DB: viste + funzioni + contatti ...... DBA
STEP 8     → DB: test pgTAP ...................... DBA
STEP 9-12  → Backend: API 3 entita + clienti ...... Backend
STEP 13    → Frontend: prop rename + API .......... Frontend
STEP 14    → Test integrazione ................... Tutti
STEP 15    → Documentazione ...................... Tutti
```

---

*ZeroERP Refactor istanza_utility — aperto 25 marzo 2026*
*Priorita CRITICA — prerequisito architetturale per gestione clienti multi-istanza*
