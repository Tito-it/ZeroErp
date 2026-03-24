# WIP — Refactor Indirizzi e Conti Bancari: aggiunta livello Utility

> Data apertura: 2026-03-24
>
> Stato: **DA FARE**
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
- `anagrafiche.conti_bancari` → `utility_id` nullable, UNIQUE con utility

---

## Prerequisiti

Prima di iniziare il refactor verificare che:

1. **DB stabile** — nessuna migrazione Liquibase in pending
2. **Test verdi** — tutti i 744+ test passano
3. **Sprint 8 clienti** — lo STEP 4 (frontend) deve essere funzionante con il modello a 2 livelli
4. **Backup** — dump del DB prima delle migrazioni schema

---

## STEP 1 — DB: Modifica schema tabella `anagrafiche.indirizzi`

**Competenza: DBA**

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

File: `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-XX-add-utility-id-indirizzi-mctit.yaml`

---

## STEP 2 — DB: Aggiornare trigger guard

**Competenza: DBA**

### 2.1 `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

Il trigger valida `tipo_indirizzo_id` contro la matrice `config.tipi_ruolo_tipi_indirizzo`.
Attualmente non conosce `utility_id` — non serve modificarlo perché la validazione è
su `(tipo_ruolo_id, tipo_indirizzo_id)` che resta invariata. Il tipo di indirizzo ammesso
non dipende dall'utility.

**Azione**: verificare che il trigger non faccia assunzioni sulla unicità
`(soggetto_ruolo_id, tipo_indirizzo_id)`. Se sì, aggiornare.

### 2.2 Trigger storicizzazione

`trgfn_storico_generic` copia la riga completa in `storico.indirizzi_id` — se la tabella
storico non ha `utility_id`, aggiungere la colonna anche lì.

```sql
ALTER TABLE storico.indirizzi_id
  ADD COLUMN utility_id integer NULL;
```

**Changeset**: `db/changelog/migrations_v2/00_schema/storico/YYYYMMDD-XX-add-utility-id-storico-indirizzi-mctit.yaml`

---

## STEP 3 — DB: Aggiornare viste resolved

**Competenza: DBA**

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

**Changeset**: `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-XX-recreate-indirizzi-views-utility-mctit.yaml`

---

## STEP 4 — DB: Aggiornare funzioni di risoluzione

**Competenza: DBA**

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

**Changeset**: `db/changelog/migrations_v2/20_code/script/YYYYMMDD-XX-update-fn-get-indirizzo-utility-mctit.yaml`

---

## STEP 5 — Backend: Repository e Service

**Competenza: Backend Python/Django**

**Prerequisiti**: STEP 1-4 completati e migrati

### 5.1 Creare endpoint API indirizzi a livello ruolo

File: `backend/apps/anagrafiche/api/views_indirizzi_ruolo.py`

Seguire il pattern di `views_contatti_ruolo.py`:

- `GET /api/v1/anagrafiche/ruoli/{soggetto_ruolo_id}/indirizzi/?utility_id=X`
  - Cascata 3 livelli: utility → ruolo → soggetto (per tipo_indirizzo_id)
  - Response: `{ contatti_ruolo: [...], contatti_soggetto: [...] }` (stessa struttura contatti)
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

## STEP 6 — Frontend: Drawer indirizzi ruolo

**Competenza: Frontend Vue.js**

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

## STEP 7 — Documentazione

**Competenza: Tutti**

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
| DB schema | 2 (indirizzi + storico) | bassa |
| DB viste | 3-4 (resolved_*) | media |
| DB funzioni | 2 (fn_get_indirizzo, fn_get_indirizzi_by_ruolo) | media-alta |
| DB trigger | 1 (guard, verifica sola) | bassa |
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
| Storicizzazione | Aggiungere utility_id anche alla tabella storico prima della migrazione dati |

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

### Nota: `sepa_mandati` già usa `istanza_utility_id`

La tabella `pagamenti.sepa_mandati` ha già i campi `istanza_utility_id` e `billing_account_id`
per il perimetro — il modello pagamenti è già predisposto per la distinzione per utility.
Manca solo il livello di selezione del conto.

---

## STEP 8 — DB: Modifica schema `soggetti_ruoli_conti_bancari`

**Competenza: DBA**

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

Verificare se esiste tabella storico per `soggetti_ruoli_conti_bancari` — se sì,
aggiungere `utility_id` anche lì.

### 8.5 Changeset Liquibase

File: `db/changelog/migrations_v2/00_schema/anagrafiche/YYYYMMDD-XX-add-utility-id-src-bancari-mctit.yaml`

---

## STEP 9 — DB: Aggiornare vista e funzione di selezione

**Competenza: DBA**

### 9.1 `vw_conti_bancari_per_ruolo`

La vista deve esporre `utility_id` e `utility_codice`. La logica di priorità diventa:

```sql
ORDER BY
  CASE WHEN fonte = 'RUOLO' AND utility_id IS NOT NULL THEN 1   -- utility specifica
       WHEN fonte = 'RUOLO' AND utility_id IS NULL     THEN 2   -- ruolo generico
       WHEN fonte = 'SOGGETTO'                         THEN 3   -- fallback soggetto
  END,
  predefinito DESC,
  data_update DESC
```

Con `ROW_NUMBER() OVER (PARTITION BY soggetto_ruolo_id, uso)` la vista restituisce
una riga per combinazione `(ruolo, uso)`. Per supportare utility, il PARTITION deve
includere utility_id oppure la vista deve essere parametrizzata.

**Opzione consigliata**: la vista espone tutte le righe con fonte e utility_id;
la funzione `fn_get_conto_bancario_predefinito` fa il filtering con cascata.

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

**Changeset**: `db/changelog/migrations_v2/20_code/anagrafiche/YYYYMMDD-XX-recreate-vw-conti-bancari-utility-mctit.yaml`

---

## STEP 10 — Backend: API conti bancari con utility

**Competenza: Backend Python/Django**

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

## STEP 11 — Frontend: Drawer conti bancari con utility

**Competenza: Frontend Vue.js**

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
| DB schema indirizzi | 2 (indirizzi + storico) | bassa |
| DB schema conti | 2 (soggetti_ruoli_conti_bancari + storico) | bassa |
| DB viste indirizzi | 3-4 (resolved_*) | media |
| DB vista conti | 1 (vw_conti_bancari_per_ruolo) | media |
| DB funzioni indirizzi | 2 (fn_get_indirizzo, fn_get_indirizzi_by_ruolo) | media-alta |
| DB funzioni conti | 1 (fn_get_conto_bancario_predefinito) | media |
| DB trigger | 2 (guard indirizzi verifica, guard conti verifica) | bassa |
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
| Storicizzazione | Aggiungere utility_id alle tabelle storico prima delle migrazioni dati |
| Vincolo predefinito conti | 4 partial index (2 per utility valorizzata, 2 per NULL) — più complesso di indirizzi |
| Mandati SEPA | Già predisposti con `istanza_utility_id` — nessun impatto |

---

{% include-markdown "signature-core.md" %}
