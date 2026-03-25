# WIP — Refactor Indirizzi e Conti Bancari: aggiunta livello Utility

> Data apertura: 2026-03-24
>
> Stato: **COMPLETATO (sviluppo)** — DB, backend, frontend, smoke test, PATCH cliente, doc API — test UI manuali pendenti
>
> Priorità: alta (prerequisito per gestione clienti multi-utility completa)

---

## Obiettivo

Aggiungere la colonna `utility_id` a:
- `anagrafiche.indirizzi` — indirizzi a livello ruolo
- `anagrafiche.soggetti_ruoli_conti_bancari` — conti bancari a livello ruolo

per supportare indirizzi e conti bancari specifici per utility (es. fatturazione GAS diversa
da fatturazione IDRICO), allineando il modello a quello già implementato su `anagrafiche.contatti`.

### Scenario di riferimento

Soggetto Titini ha due clienti per utility diverse:
- Cliente COR → utility GAS → indirizzo fatturazione: Corridonia
- Cliente CIV → utility IDRICO → indirizzo fatturazione: Civitanova

Senza `utility_id` è impossibile differenziare: il vincolo UNIQUE `(soggetto_ruolo_id, tipo_indirizzo_id)`
permette un solo indirizzo di fatturazione per ruolo CLIENTE.

### Cascata di risoluzione target (3 livelli)

| Priorità | utility_id | soggetto_ruolo_id | Significato | Editabile |
|----------|-----------|-------------------|-------------|-----------|
| 1 | valorizzato | valorizzato | Indirizzo specifico utility | Sì |
| 2 | NULL | valorizzato | Indirizzo generico ruolo | Sì |
| 3 | — | — | Indirizzo soggetto (tabella `indirizzi_soggetti`) | No (readonly) |

### Pattern di riferimento

Già implementato su:
- `anagrafiche.contatti` → `utility_id` nullable, UNIQUE `(soggetto_id, soggetto_ruolo_id, utility_id, tipo_contatto_id)`

**Nota sulla differenza strutturale contatti vs indirizzi/conti bancari:**

Il modello contatti usa **una sola tabella** con contesto determinato dai campi nullable
(`soggetto_id` sempre presente, `soggetto_ruolo_id` e `utility_id` opzionali).
Il modello indirizzi usa **due tabelle** separate (`indirizzi` per ruolo, `indirizzi_soggetti`
per soggetto). Il modello conti bancari analogamente usa due tabelle di legame
(`soggetti_conti_bancari` per soggetto, `soggetti_ruoli_conti_bancari` per ruolo).

Conseguenza: `utility_id` va aggiunto **solo** sulle tabelle layer ruolo (`anagrafiche.indirizzi`
e `anagrafiche.soggetti_ruoli_conti_bancari`). Le tabelle layer soggetto non sono impattate.
La cascata contatti (4 livelli: utility → ruolo → soggetto+utility → soggetto) non si replica
integralmente — il livello "soggetto + utility" non esiste perché le tabelle soggetto non hanno
`utility_id`. La cascata target è a **3 livelli** (utility → ruolo generico → soggetto).

---

## Prerequisiti

Prima di iniziare il refactor verificare che:

1. **DB stabile** — nessuna migrazione Liquibase in pending
2. **Test verdi** — tutti i 744+ test passano
3. **Sprint 8 clienti** — lo STEP 4 (frontend) deve essere funzionante con il modello a 2 livelli
4. **Backup** — dump del DB prima delle migrazioni schema

---

## STEP 1 — DB: Modifica schema tabella `anagrafiche.indirizzi` ✅

**Competenza: DBA** — Completato 2026-03-24

### 1.1 Aggiungere colonna `utility_id`

```sql
ALTER TABLE anagrafiche.indirizzi
  ADD COLUMN utility_id integer NULL;

ALTER TABLE anagrafiche.indirizzi
  ADD CONSTRAINT fk_indirizzi_utilities
  FOREIGN KEY (utility_id) REFERENCES config.utilities(id);
```

- Nullable: sì (NULL = indirizzo generico ruolo, come per contatti)
- FK verso `config.utilities(id)`

### 1.2 Modificare vincolo UNIQUE

```sql
-- Rimuovere il vecchio
ALTER TABLE anagrafiche.indirizzi
  DROP CONSTRAINT uq_indirizzi_ruolo_tipo;

-- Creare il nuovo (3 colonne)
ALTER TABLE anagrafiche.indirizzi
  ADD CONSTRAINT uq_indirizzi_ruolo_utility_tipo
  UNIQUE (soggetto_ruolo_id, utility_id, tipo_indirizzo_id);
```

**ATTENZIONE**: PostgreSQL tratta NULL come valori distinti in UNIQUE.
Questo significa che `(64, NULL, 1)` e `(64, NULL, 1)` sarebbero entrambi ammessi.
Per impedire duplicati a livello ruolo generico, servono due vincoli:

```sql
-- Per righe con utility_id NULL (un solo indirizzo generico per tipo per ruolo)
CREATE UNIQUE INDEX uq_indirizzi_ruolo_tipo_no_utility
  ON anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id)
  WHERE utility_id IS NULL;

-- Per righe con utility_id valorizzato
CREATE UNIQUE INDEX uq_indirizzi_ruolo_utility_tipo
  ON anagrafiche.indirizzi (soggetto_ruolo_id, utility_id, tipo_indirizzo_id)
  WHERE utility_id IS NOT NULL;
```

Stessa strategia usata per `contatti.uq_contatti_multilevel`.

### 1.3 Aggiungere indice

```sql
CREATE INDEX ix_anagrafiche_indirizzi_utility_id
  ON anagrafiche.indirizzi (utility_id);
```

### 1.4 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/20260324-02-add-utility-id-indirizzi-mctit.yaml`

---

## STEP 2 — DB: Aggiornare trigger guard ✅

**Competenza: DBA** — Completato 2026-03-24 (verifica: nessuna modifica necessaria)

### 2.1 `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

Il trigger valida `tipo_indirizzo_id` contro la matrice `config.tipi_ruolo_tipi_indirizzo`.
Attualmente non conosce `utility_id` — non serve modificarlo perché la validazione è
su `(tipo_ruolo_id, tipo_indirizzo_id)` che resta invariata. Il tipo di indirizzo ammesso
non dipende dall'utility.

**Azione**: verificare che il trigger non faccia assunzioni sulla unicità
`(soggetto_ruolo_id, tipo_indirizzo_id)`. Se sì, aggiornare.

### 2.2 Altri trigger da verificare

| Trigger | Impatto atteso | Azione |
| --- | --- | --- |
| `trgfn_indirizzi_base_normalize` | Opera su `anagrafiche.indirizzi` — deve gestire/ignorare `utility_id` senza interferenze | Verificare che non azzeri colonne extra non previste |
| `trgfn_indirizzi_sync_geoloc` | Sincronizza geolocalizzazione da `indirizzi_dettaglio` — non dipende da utility | Nessuna modifica attesa, verifica sola |
| `trgfn_child_requires_active_parent` | Verifica che soggetto/indirizzi_dettaglio siano attivi | Valutare se aggiungere check su `config.utilities.attivo` quando `utility_id IS NOT NULL` |
| `trgfn_prevent_deactivate_if_children` | Su `indirizzi_dettaglio`, blocca disattivazione con figli attivi | Non impattato |

### 2.3 Trigger storicizzazione

`trgfn_storico_generic` salva la riga come **snapshot JSONB** — il nuovo campo `utility_id`
viene automaticamente incluso nello snapshot senza modifiche alla tabella `storico.indirizzi`.
**Nessuna migrazione necessaria sullo schema storico.**

---

## STEP 3 — DB: Aggiornare viste resolved ✅

**Competenza: DBA** — Completato 2026-03-24

Le 4 viste devono esporre `utility_id` e il codice utility per la UI.

### 3.1 `vw_indirizzi_resolved_base`

Aggiungere nella SELECT:
```sql
i.utility_id,
u.codice AS utility_codice
```

E il JOIN:
```sql
LEFT JOIN config.utilities u ON u.id = i.utility_id
```

### 3.2 `vw_indirizzi_resolved_ruolo`

Eredita dalla base — se è una vista su `vw_indirizzi_resolved_base`, basta aggiornare la base.
Altrimenti aggiungere le stesse colonne.

### 3.3 `vw_indirizzi_resolved_soggetto`

Non impattata (tabella `indirizzi_soggetti` non ha `utility_id`).

### 3.4 `vw_indirizzi_resolved_all`

Se è UNION di ruolo + soggetto, aggiungere `NULL AS utility_id, NULL AS utility_codice`
sul ramo soggetto per compatibilità.

### 3.5 `vw_indirizzi_dettaglio`

Non impattata (vista sul dettaglio civico, non ha contesto ruolo/utility).

**Changeset**: `db/changelog/migrations_v2/20_code/script/20260324-04-recreate-indirizzi-chain-utility-mctit.yaml`
(contiene DROP + CREATE dell'intera catena: 4 viste + 4 funzioni, in ordine di dipendenza)

---

## STEP 4 — DB: Aggiornare funzioni di risoluzione ✅

**Competenza: DBA** — Completato 2026-03-24

### 4.1 `script.fn_get_indirizzo(p_soggetto_ruolo_id, p_tipo_codice)`

La funzione principale con fallback. Attualmente la catena è:
1. Layer ruolo → tipo esatto
2. Layer ruolo → fallback tipo (da matrice)
3. Layer soggetto → tipo esatto
4. Layer soggetto → fallback tipo

Deve diventare:
1. Layer ruolo + utility → tipo esatto
2. Layer ruolo + utility → fallback tipo
3. Layer ruolo generico (utility NULL) → tipo esatto
4. Layer ruolo generico → fallback tipo
5. Layer soggetto → tipo esatto
6. Layer soggetto → fallback tipo

**Firma aggiornata**:
```sql
script.fn_get_indirizzo(
  p_soggetto_ruolo_id BIGINT,
  p_tipo_codice TEXT,
  p_utility_id INTEGER DEFAULT NULL  -- nuovo parametro opzionale
)
```

Il default NULL mantiene retrocompatibilità: i chiamanti esistenti continuano a funzionare
senza modifiche (ricevono il fallback ruolo generico).

### 4.2 `script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)`

Attualmente restituisce tutti gli indirizzi del layer ruolo. Aggiungere parametro opzionale:

```sql
script.fn_get_indirizzi_by_ruolo(
  p_soggetto_ruolo_id BIGINT,
  p_utility_id INTEGER DEFAULT NULL  -- se valorizzato, filtra per utility
)
```

Con `p_utility_id = NULL` restituisce TUTTI gli indirizzi del ruolo (comportamento attuale).
Con `p_utility_id = 5` restituisce solo quelli dell'utility 5 + quelli generici (utility NULL).

### 4.3 Funzioni non impattate

Le seguenti funzioni operano sul layer soggetto, che non ha `utility_id`:

- `script.fn_get_indirizzi_by_soggetto(p_soggetto_id)` — tutti gli indirizzi del layer soggetto → **nessuna modifica**
- `script.fn_get_indirizzo_by_soggetto(p_soggetto_id, p_tipo_codice)` — indirizzo soggetto con fallback tra tipi → **nessuna modifica**

**Changeset**: incluso in `20260324-04-recreate-indirizzi-chain-utility-mctit.yaml` (unico file per tutta la catena)

---

## Riepilogo lavoro DB completato (2026-03-24)

### Changeset Liquibase applicati

| # | File | Contenuto |
| --- | --- | --- |
| 02 | `00_schema/anagrafiche/20260324-02-add-utility-id-indirizzi-mctit.yaml` | Colonna `utility_id` + FK + 2 partial unique index su `anagrafiche.indirizzi` |
| 03 | `00_schema/anagrafiche/20260324-03-add-utility-id-src-bancari-mctit.yaml` | Colonna `utility_id` + FK + 4 partial unique index su `anagrafiche.soggetti_ruoli_conti_bancari` |
| 04 | `20_code/script/20260324-04-recreate-indirizzi-chain-utility-mctit.yaml` | DROP + CREATE intera catena indirizzi: 4 viste resolved + 4 funzioni (by_ruolo, by_soggetto, indirizzo_by_soggetto, indirizzo) con `%TYPE`, `p_utility_id` e `utility_id`/`utility_codice` in output |
| 05 | `20_code/script/20260324-05-recreate-conti-bancari-chain-utility-mctit.yaml` | DROP + CREATE vista flat `vw_conti_bancari_per_ruolo` (senza DISTINCT ON) + funzione `fn_get_conto_bancario_predefinito` con cascata 7 livelli |

### Scelte architetturali

- **Storicizzazione**: le tabelle `storico.*` usano snapshot JSONB — `utility_id` incluso automaticamente, nessuna migrazione storico
- **Vista conti bancari flat**: rimosso `DISTINCT ON`, la selezione singola e nella funzione `fn_get_conto_bancario_predefinito` (coerenza con pattern indirizzi: vista espone, funzione decide)
- **Catena dipendenze**: changeset 04 e 05 usano `splitStatements: false` con DROP in ordine inverso di dipendenza e CREATE in ordine corretto (pattern da `20260311-02-repair`)
- **`%TYPE`**: usato in tutti i parametri, RETURNS TABLE e DECLARE delle funzioni ricreate
- **`config.utilities` non ha campo `attivo`**: i trigger `trgfn_child_requires_active_parent` non necessitano check su utility

### Test pgTAP

| File | Assert | Stato |
| --- | --- | --- |
| `db/pgtap/anagrafiche/test-indirizzi-utility-cascata.sql` | 14 | ✅ Nuovo — partial unique, fn_get_indirizzi_by_ruolo con/senza utility, fn_get_indirizzo cascata 3 livelli, viste con utility_id/utility_codice |
| `db/pgtap/anagrafiche/test-conti-bancari-utility-cascata.sql` | 10 | ✅ Nuovo — partial unique predefinito, fn_get_conto cascata 7 livelli, vista flat con utility_codice |
| `db/pgtap/anagrafiche/test_vw_conti_bancari_per_ruolo_gestore.sql` | 5 | ✅ Aggiornato — test 5 adattato per vista flat (LIMIT 1 + ORDER BY priorita) |
| `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` | 14 | ✅ Invariato — funziona con DEFAULT sui nuovi parametri |
| `db/pgtap/anagrafiche/test_fn_get_conto_bancario_predefinito.sql` | 6 | ✅ Invariato — funziona con DEFAULT sul terzo parametro |

### Documentazione manuale aggiornata

- `docs/it/dbzero/script/manual/fn_get_indirizzo.md` — scopo, firma, parametri, logica 3 livelli, esempi
- `docs/it/dbzero/script/manual/fn_get_indirizzi_by_ruolo.md` — scopo, firma con `p_utility_id`, logica filtro
- `docs/it/dbzero/script/manual/fn_get_conto_bancario_predefinito.md` — scopo, `p_utility_id`, cascata 7 livelli
- `docs/it/dbzero/anagrafiche/manual/vw_conti_bancari_per_ruolo.md` — scopo flat, utility_id/utility_codice, ordinamento
- `docs/it/dbzero/anagrafiche/manual/vw_indirizzi_resolved_base.md` — utility_id/utility_codice nella tabella campi

---

## STEP 5 — Backend: Repository e Service ✅

**Competenza: Backend Python/Django** — Completato 2026-03-24

**Prerequisiti**: STEP 1-4 completati e migrati

### 5.1 Creare endpoint API indirizzi a livello ruolo

File: `backend/apps/anagrafiche/api/views_indirizzi_ruolo.py`

Seguire il pattern di `views_contatti_ruolo.py`:

- `GET /api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/?utility_id=X`
  - Cascata 3 livelli: utility → ruolo → soggetto (per tipo_indirizzo_id)
  - Response: `{ indirizzi_ruolo: [...], indirizzi_soggetto: [...] }` (stessa struttura contatti)
- `POST /api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/`
  - Crea indirizzo con `utility_id` opzionale
- `PATCH /api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{id}/`
  - Ownership check su `soggetto_ruolo_id`
- `DELETE /api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/{id}/`
  - Ownership check su `soggetto_ruolo_id`

### 5.2 Aggiungere rotte in `urls.py`

```python
path("ruoli/<int:soggetto_ruolo_id>/indirizzi/", RuoloIndirizziView.as_view()),
path("ruoli/<int:soggetto_ruolo_id>/indirizzi/<int:indirizzo_id>/", RuoloIndirizziDetailView.as_view()),
```

### 5.3 Repository

Aggiungere metodi a `SoggettiRepository` o creare `IndirizziRuoloRepository`:
- `list_indirizzi_ruolo(soggetto_ruolo_id, utility_id=None)` — con cascata
- `crea_indirizzo_ruolo(soggetto_ruolo_id, tipo_indirizzo_id, ..., utility_id=None)`
- `update_indirizzo_ruolo(indirizzo_id, data, soggetto_ruolo_id)`
- `delete_indirizzo_ruolo(indirizzo_id, soggetto_ruolo_id)`

### 5.4 Test

- Test unitari per ciascuna operazione CRUD
- Test cascata 3 livelli: utility presente nasconde ruolo, ruolo nasconde soggetto
- Test retrocompatibilità: senza utility_id funziona come prima
- Smoke test script: `backend/scripts/tests/smoke-test-indirizzi-ruolo.sh`

---

## STEP 6 — Frontend: Drawer indirizzi ruolo ✅

**Competenza: Frontend Vue.js** — Completato 2026-03-25

**Prerequisiti**: STEP 5 completato

### 6.1 Creare `IndirizziRuoloDrawer.vue`

Seguire il pattern del `ContattiSoggettoDrawer.vue` con context ruolo:
- Riceve props: `soggetto-id`, `soggetto-ruolo-id`, `utility-id` (opzionale)
- Lista indirizzi con badge fonte (Utility/Ruolo/Soggetto)
- Codice utility visibile accanto al tipo indirizzo (come per contatti: "Fatturazione · GAS")
- Indirizzi soggetto → readonly (no edit/delete)
- Indirizzi ruolo/utility → editabili
- Form creazione: scelta tipo indirizzo (da matrice ammessi), modalità normalizzata/libera

### 6.2 API client

File: `frontend/src/anagrafiche/api/anagrafiche.js`

```javascript
export const listRuoloIndirizzi = (ruoloId, params) =>
  api.get(`/anagrafiche/ruoli/${ruoloId}/indirizzi/`, { params })
export const createRuoloIndirizzo = (ruoloId, data) =>
  api.post(`/anagrafiche/ruoli/${ruoloId}/indirizzi/`, data)
export const updateRuoloIndirizzo = (ruoloId, id, data) =>
  api.patch(`/anagrafiche/ruoli/${ruoloId}/indirizzi/${id}/`, data)
export const deleteRuoloIndirizzo = (ruoloId, id) =>
  api.delete(`/anagrafiche/ruoli/${ruoloId}/indirizzi/${id}/`)
```

### 6.3 Integrare nel ClienteDrawer

Sostituire l'attuale `IndirizziSoggettoDrawer` nel drawer cliente con `IndirizziRuoloDrawer`
che supporta la cascata a 3 livelli.

### 6.4 Integrare nella lista ClientiSearchTable

Aggiornare il pulsante indirizzi nella colonna azioni per aprire `IndirizziRuoloDrawer`
passando `utility_id` del cliente.

---

## STEP 7 — Documentazione (parziale)

**Competenza: Tutti** — Doc API backend completate, guide operative da aggiornare

### 7.1 Aggiornare guida indirizzi

File: `docs/it/guide/gestione-degli-indirizzi.md`

- Sezione "Policy di risoluzione" → aggiungere livello utility
- Aggiornare diagramma ER con `utility_id`
- Aggiornare tabella regole R2 (unicità per tipo) con nuova logica
- Aggiungere esempio pratico: cliente multi-utility con indirizzi diversi

### 7.2 Aggiornare documentazione tabella

File: `docs/it/dbzero/anagrafiche/tabelle/indirizzi.md` — aggiungere colonna utility_id

### 7.3 Aggiornare documentazione funzioni

- `fn_get_indirizzo` → nuovo parametro `p_utility_id`
- `fn_get_indirizzi_by_ruolo` → nuovo parametro `p_utility_id`

### 7.4 Aggiornare guida generazione cliente

File: `docs/it/guide/generazione-cliente.md` — nota su indirizzi per utility

---

## Stima impatto

| Area | File impattati | Complessità |
|------|---------------|-------------|
| DB schema | 1 (indirizzi — storico usa JSONB, nessuna modifica) | bassa |
| DB viste | 3-4 (resolved_*) | media |
| DB funzioni | 2 (fn_get_indirizzo, fn_get_indirizzi_by_ruolo) | media-alta |
| DB trigger | 4 (guard tipo + normalize + sync_geoloc + child_requires_active_parent — verifica) | bassa |
| Backend API | 2-3 (views, urls, repository) | media |
| Frontend | 2-3 (drawer, api, integrazione) | media |
| Documentazione | 5-6 guide/tabelle | bassa |
| Test | 1 smoke + unitari | media |

---

## Rischi e mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Dati esistenti senza utility_id | Colonna nullable, dati esistenti restano con NULL (livello ruolo generico) |
| Retrocompatibilità funzioni DB | Parametro `p_utility_id DEFAULT NULL` — chiamanti esistenti invariati |
| Vincolo UNIQUE con NULL PostgreSQL | Due partial unique index (WHERE IS NULL / IS NOT NULL) |
| Storicizzazione | Tabelle storico usano JSONB snapshot — utility_id incluso automaticamente, nessuna modifica |

---

---

## PARTE B — Conti Bancari: aggiunta livello Utility

---

## Stato attuale

La tabella di legame `anagrafiche.soggetti_ruoli_conti_bancari` associa conti a livello
**ruolo** con vincoli:

- `UNIQUE (soggetto_ruolo_id, conto_bancario_id, uso)` — un legame per combinazione
- `UNIQUE PARTIAL (soggetto_ruolo_id, uso) WHERE predefinito=true` — un solo predefinito per uso

**Non esiste `utility_id`** — lo stesso scenario indirizzi si ripete: il soggetto Titini non
può avere un conto INCASSO per GAS (Banca A) e un conto INCASSO per IDRICO (Banca B) perché
il predefinito è unico per `(soggetto_ruolo_id, uso)`.

### Cascata attuale (via `vw_conti_bancari_per_ruolo`)

1. Ruolo + uso specifico
2. Soggetto + uso specifico
3. Ruolo + uso GENERICO
4. Soggetto + uso GENERICO

### Cascata target (con utility)

1. Ruolo + utility + uso specifico
2. Ruolo + uso specifico (utility NULL — generico)
3. Soggetto + uso specifico (fallback)
4. Ruolo + utility + uso GENERICO
5. Ruolo + uso GENERICO (utility NULL)
6. Soggetto + uso GENERICO (fallback finale)

### Integrazione con mandati SEPA — catena di risoluzione

La tabella `pagamenti.sepa_mandati` ha i campi `istanza_utility_id` e `billing_account_id`
per il perimetro, più `soggetto_ruolo_conto_id` che punta al legame ruolo ↔ conto selezionato.

**Catena di risoluzione utility per un mandato SEPA:**

```text
sepa_mandati.billing_account_id
    → billing_account.utility_id     → config.utilities(id)
```

`istanze_utilities` **non ha** `utility_id` direttamente — la utility si ricava sempre
tramite `billing_account.utility_id`. Il vincolo `UNIQUE(istanza_utility_id, utility_id)`
su `billing_account` garantisce la coerenza.

**Flusso operativo per creazione/rinnovo mandato dopo il refactor:**

1. Dal mandato → `billing_account_id` → `billing_account.utility_id` = conosco la utility
2. `fn_get_conto_bancario_predefinito(ruolo, 'INCASSO', utility_id)` → seleziona il conto migliore
3. Il conto trovato diventa `soggetto_ruolo_conto_id` del mandato
4. `iban_snapshot` = snapshot dell'IBAN al momento della creazione

**Fallback per mandati senza utility specifica (aziende non-utility):**

Per aziende non-utility l'istanza è fittizia e il BA ha una utility "generica/default".
Il conto si risolve con `utility_id = NULL` (generico ruolo) come fallback naturale della
cascata. Non serve un mandato "senza perimetro" — il vincolo `chk_sepa_mandati_perimetro`
(`billing_account_id IS NOT NULL OR istanza_utility_id IS NOT NULL`) resta valido.

**Per aziende utility con unico IBAN per tutti i servizi:**

Il conto a livello `(ruolo, NULL, INCASSO)` — senza utility — fa da fallback per tutte
le utility. Ogni mandato resta legato al suo BA specifico, ma il conto che "vince" nella
cascata è lo stesso per tutti perché non ci sono override per utility.

---

## STEP 8 — DB: Modifica schema `soggetti_ruoli_conti_bancari` ✅

**Competenza: DBA** — Completato 2026-03-24

### 8.1 Aggiungere colonna `utility_id`

```sql
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD COLUMN utility_id integer NULL;

ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  ADD CONSTRAINT fk_soggetti_ruoli_conti_bancari_utilities
  FOREIGN KEY (utility_id) REFERENCES config.utilities(id);
```

- Nullable: sì (NULL = conto generico del ruolo, come per contatti e indirizzi)
- FK verso `config.utilities(id)`

### 8.2 Modificare vincoli UNIQUE

```sql
-- Rimuovere i vecchi vincoli
ALTER TABLE anagrafiche.soggetti_ruoli_conti_bancari
  DROP CONSTRAINT uq_soggetti_ruoli_conti_bancari_ruolo_conto_uso;

-- NOTA: verificare il nome esatto del vincolo UNIQUE parziale predefinito
-- prima di dropparlo

-- Nuovi vincoli con utility_id (partial index per gestire NULL)

-- Legame: un conto per combinazione (ruolo, utility, conto, uso)
CREATE UNIQUE INDEX uq_src_bancari_ruolo_utility_conto_uso
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, utility_id, conto_bancario_id, uso)
  WHERE utility_id IS NOT NULL;

CREATE UNIQUE INDEX uq_src_bancari_ruolo_conto_uso_no_utility
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, conto_bancario_id, uso)
  WHERE utility_id IS NULL;

-- Predefinito: un solo predefinito per (ruolo, utility, uso)
CREATE UNIQUE INDEX uq_src_bancari_predefinito_utility
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, utility_id, uso)
  WHERE predefinito = true AND utility_id IS NOT NULL;

CREATE UNIQUE INDEX uq_src_bancari_predefinito_no_utility
  ON anagrafiche.soggetti_ruoli_conti_bancari (soggetto_ruolo_id, uso)
  WHERE predefinito = true AND utility_id IS NULL;
```

### 8.3 Aggiungere indice

```sql
CREATE INDEX ix_soggetti_ruoli_conti_bancari_utility_id
  ON anagrafiche.soggetti_ruoli_conti_bancari (utility_id);
```

### 8.4 Trigger storicizzazione

`trgfn_storico_generic` salva la riga come **snapshot JSONB** — il nuovo campo `utility_id`
viene automaticamente incluso nello snapshot senza modifiche alla tabella storico.
**Nessuna migrazione necessaria sullo schema storico.**

### 8.5 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/20260324-03-add-utility-id-src-bancari-mctit.yaml`

---

## STEP 9 — DB: Aggiornare vista e funzione di selezione ✅

**Competenza: DBA** — Completato 2026-03-24

### 9.1 `vw_conti_bancari_per_ruolo`

**Cambio architetturale**: la vista attuale restituisce **una sola riga per `(ruolo, uso)`**
tramite `ROW_NUMBER() OVER (PARTITION BY soggetto_ruolo_id, uso)`. Con `utility_id` questo
approccio non funziona più — il PARTITION dovrebbe cambiare, ma la logica di cascata
(utility → generico → soggetto) richiede un filtering dinamico che non si esprime in una vista.

**Decisione: la vista diventa flat (espone tutte le righe), la funzione fa la logica.**

La vista aggiornata:

- Espone `utility_id` e `utility_codice` (JOIN su `config.utilities`)
- **Rimuove** il `ROW_NUMBER()` / `DISTINCT ON` — restituisce tutte le candidate
- Mantiene i filtri esistenti: `valido_dal <= oggi`, `valido_al >= oggi`, `bloccato = false`, `conto attivo = true`
- Espone `fonte` (`RUOLO` / `SOGGETTO`) come oggi

```sql
-- Colonne aggiunte alla SELECT
srcb.utility_id,
u.codice AS utility_codice

-- JOIN aggiunto
LEFT JOIN config.utilities u ON u.id = srcb.utility_id
```

Questo è lo stesso pattern degli indirizzi: le viste `vw_indirizzi_resolved_*` espongono
tutto, `fn_get_indirizzo` fa il fallback. Coerenza architetturale.

**Nota retrocompatibilità**: i chiamanti che oggi fanno `SELECT * FROM vw_conti_bancari_per_ruolo
WHERE soggetto_ruolo_id = X AND uso = 'INCASSO'` riceveranno più righe dopo il refactor.
Devono migrare a `fn_get_conto_bancario_predefinito` per la selezione singola.
Verificare che nessun chiamante dipenda dal comportamento "1 riga per (ruolo, uso)".

### 9.2 `script.fn_get_conto_bancario_predefinito`

**Firma aggiornata**:

```sql
script.fn_get_conto_bancario_predefinito(
  p_soggetto_ruolo_id BIGINT,
  p_uso VARCHAR,
  p_utility_id INTEGER DEFAULT NULL  -- nuovo parametro opzionale
)
```

Catena completa:
1. Ruolo + utility specifica + uso richiesto
2. Ruolo + utility NULL + uso richiesto
3. Soggetto + uso richiesto
4. Ruolo + utility specifica + uso GENERICO
5. Ruolo + utility NULL + uso GENERICO
6. Soggetto + uso GENERICO
7. NULL

Il default `p_utility_id = NULL` mantiene retrocompatibilità.

**Changeset**: `db/changelog/migrations_v2/20_code/script/20260324-05-recreate-conti-bancari-chain-utility-mctit.yaml`
(contiene DROP + CREATE della vista flat e della funzione con cascata 7 livelli)

---

## STEP 10 — Backend: API conti bancari con utility ✅

**Competenza: Backend Python/Django** — Completato 2026-03-24

**Prerequisiti**: STEP 8-9 completati e migrati

### 10.1 Aggiornare `views_contatti_ruolo.py` / creare `views_conti_bancari_ruolo.py`

L'endpoint `RuoloContiBancariView` esistente deve accettare `?utility_id=X` come query param
e applicare la cascata 3 livelli (utility → ruolo → soggetto) nel GET, identica alla logica contatti.

Nel POST, accettare `utility_id` opzionale nel payload per creare il legame a livello utility.

### 10.2 Aggiornare `conti_bancari_service.py`

Il metodo `list_conti_ruolo` deve implementare la cascata per `uso`:
- L1: conti con `utility_id = X` (se passato)
- L2: conti con `utility_id IS NULL` (usi non coperti da L1)
- L3: conti soggetto (usi non coperti da L1 e L2)

Il metodo `crea_conto_ruolo` deve accettare `utility_id` opzionale.

### 10.3 Test

- Test unitari cascata 3 livelli per uso
- Test predefinito per utility: GAS ha predefinito INCASSO diverso da IDRICO
- Test retrocompatibilità senza utility_id
- Smoke test: `backend/scripts/tests/smoke-test-conti-bancari-ruolo.sh`

---

## STEP 11 — Frontend: Drawer conti bancari con utility ✅

**Competenza: Frontend Vue.js** — Completato 2026-03-25

**Prerequisiti**: STEP 10 completato

### 11.1 Aggiornare `ContiBancariDrawer.vue`

Il drawer in `context="ruolo"` deve:
- Passare `utility_id` come query param nel GET
- Mostrare badge fonte (Utility/Ruolo/Soggetto) come per contatti
- Codice utility visibile accanto all'uso (es. "Incasso · GAS")
- Readonly per conti soggetto e ruolo generico quando esiste override utility
- Nel POST, passare `utility_id` dal contesto cliente

### 11.2 API client

Aggiornare `listRuoloContiBancari` per passare `utility_id` come param.

---

## STEP 12 — Documentazione conti bancari

**Competenza: Tutti**

### 12.1 Aggiornare guida conti bancari

File: `docs/it/guide/gestione-conti-bancari.md`

- Sezione "Il modello in sintesi" → aggiungere livello utility nel diagramma
- Aggiornare regola R2 (predefinito per uso) con utility
- Aggiornare `fn_get_conto_bancario_predefinito` con nuovo parametro
- Aggiungere esempio: cliente multi-utility con conti diversi

### 12.2 Aggiornare documentazione tabella

File: `docs/it/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari.md`

### 12.3 Aggiornare documentazione vista e funzione

- `vw_conti_bancari_per_ruolo` → nuova colonna utility_id
- `fn_get_conto_bancario_predefinito` → nuovo parametro p_utility_id

---

## Stima impatto complessiva (Indirizzi + Conti Bancari)

| Area | File impattati | Complessità |
|------|---------------|-------------|
| DB schema indirizzi | 1 (indirizzi — storico usa JSONB, nessuna modifica) | bassa |
| DB schema conti | 1 (soggetti_ruoli_conti_bancari — storico usa JSONB, nessuna modifica) | bassa |
| DB viste indirizzi | 3-4 (resolved_*) | media |
| DB vista conti | 1 (vw_conti_bancari_per_ruolo) | media |
| DB funzioni indirizzi | 2 (fn_get_indirizzo, fn_get_indirizzi_by_ruolo) | media-alta |
| DB funzioni conti | 1 (fn_get_conto_bancario_predefinito) | media |
| DB trigger | 5 (guard tipo + normalize + sync_geoloc + child_active indirizzi, guard conti) | bassa |
| Backend indirizzi | 3 (views, urls, repository) | media |
| Backend conti | 2 (service, views aggiornamento) | media |
| Frontend indirizzi | 3 (drawer, api, integrazione) | media |
| Frontend conti | 2 (drawer aggiornamento, api) | bassa |
| Documentazione | 8-10 guide/tabelle | bassa |
| Test | 2 smoke + unitari per area | media |

---

## Rischi e mitigazioni (aggiornati)

| Rischio | Mitigazione |
|---------|-------------|
| Dati esistenti senza utility_id | Colonna nullable su entrambe le tabelle, dati esistenti = livello ruolo generico |
| Retrocompatibilità funzioni DB | Parametro `p_utility_id DEFAULT NULL` su tutte le funzioni |
| Vincolo UNIQUE con NULL PostgreSQL | Partial unique index (WHERE IS NULL / IS NOT NULL) su entrambe le tabelle |
| Storicizzazione | Tabelle storico usano JSONB snapshot — utility_id incluso automaticamente, nessuna modifica |
| Vincolo predefinito conti | 4 partial index (2 per utility valorizzata, 2 per NULL) — più complesso di indirizzi |
| Mandati SEPA | La utility si ricava da `billing_account.utility_id`, non da `istanza_utility_id` (che non ha utility_id). Il flusso di creazione/rinnovo mandato deve chiamare `fn_get_conto_bancario_predefinito` con il nuovo parametro `p_utility_id` derivato dal BA |
| Vista conti flat | La vista `vw_conti_bancari_per_ruolo` non restituisce più 1 riga per (ruolo, uso) — verificare che tutti i chiamanti usino la funzione per la selezione singola |

---

## Test UI manuali da completare

Lo sviluppo e` completo. Prima di chiudere il WIP, eseguire i seguenti test manuali
sulla UI per verificare il corretto funzionamento end-to-end in tutti gli scenari.

### Indirizzi ruolo

| # | Scenario | Dove | Verifica |
| --- | --- | --- | --- |
| 1 | Lista indirizzi senza utility | ClienteDrawer edit → Gestisci indirizzi | Mostra indirizzi ruolo (editabili) + soggetto (readonly grigio) |
| 2 | Lista indirizzi con utility | ClientiView lista → pulsante indirizzi | Cascata: utility vince su ruolo per stesso tipo, soggetto fallback |
| 3 | Crea indirizzo normalizzato | Drawer indirizzi → Aggiungi | Seleziona tipo, cerca indirizzo dettaglio, salva OK |
| 4 | Crea indirizzo libero | Drawer indirizzi → Aggiungi → modalita` libera | Testo libero + stato estero, salva OK |
| 5 | Crea duplicato | Stesso tipo + utility gia` presente | Errore E_ANAG_DUPLICATO con messaggio chiaro |
| 6 | Elimina indirizzo ruolo | Drawer indirizzi → icona cestino | Conferma, lista aggiornata |
| 7 | Indirizzo soggetto readonly | Drawer indirizzi → card grigia | Nessun pulsante azione visibile |

### Conti bancari ruolo

| # | Scenario | Dove | Verifica |
| --- | --- | --- | --- |
| 8 | Lista conti con utility | ClienteDrawer edit → Gestisci conti | Cascata: utility > ruolo > soggetto, badge fonte corretto |
| 9 | Crea conto con utility | Drawer conti → Aggiungi | IBAN autocomplete, filiale, uso, salva con utility_id |
| 10 | Predefinito spunta verde | Conto con predefinito=true | Spunta verde prima dell'IBAN, tooltip "Predefinito" |
| 11 | Verificato badge blu | Conto con verificato=true (non bloccato) | Tag "Verificato" blu visibile |
| 12 | Bloccato badge rosso | Conto con bloccato=true | Tag "Bloccato" rosso, verificato nascosto |
| 13 | Predefinito/bloccato mutuo esclusivo | Attiva predefinito poi bloccato | Predefinito si spegne; e viceversa |
| 14 | IBAN maxlength | Digita piu` di 34 caratteri | Input bloccato a 34 |
| 15 | Crea duplicato | Stesso IBAN + uso + ruolo + utility | Errore E_ANAG_DUPLICATO |

### Contatti ruolo

| # | Scenario | Dove | Verifica |
| --- | --- | --- | --- |
| 16 | Lista contatti con utility | ClienteDrawer edit → Gestisci contatti | Cascata: utility > ruolo > soggetto |
| 17 | Crea contatto | Drawer contatti → Aggiungi | Tipo obbligatorio, nominativo, salva OK |
| 18 | Crea duplicato tipo+utility | Stesso tipo_contatto + utility | Errore E_ANAG_DUPLICATO con messaggio chiaro |
| 19 | Modifica contatto ruolo | Click matita su contatto editabile | Form pre-popolato, salva OK |
| 20 | Elimina contatto ruolo | Click cestino | Conferma, lista aggiornata |
| 21 | Contatto soggetto readonly | Card grigia senza azioni | Nessun pulsante visibile |

### Cliente drawer (PATCH)

| # | Scenario | Dove | Verifica |
| --- | --- | --- | --- |
| 22 | Modifica pagamento | ClienteDrawer edit → cambia IVA/modalita` | Salva OK, ricarica mostra nuovo valore |
| 23 | Modifica PA | ClienteDrawer edit → cliente_pa=Si` | Appaiono campi CIG/CUP/Commessa, salva OK |
| 24 | Modifica garanzia | ClienteDrawer edit → cambia importo | Salva OK |
| 25 | Campi protetti | ClienteDrawer edit → utility, BA, istanza, date | Tutti disabled/readonly, non modificabili |
| 26 | Stato inline | ClienteDrawer edit → riga utility | Tag stato visibile accanto a utility + servizio |

---

{% include-markdown "signature-core.md" %}
