
## Sprint 3 — Piano di implementazione dettagliato

> Data: 2026-03-13
> Stato: **DA IMPLEMENTARE**
> Prerequisiti globali: Sprint 2 completato (52 test OK, building block backend/DB)
> Guida di riferimento: [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

### Obiettivi Sprint 3

1. **SoggettoForm universale** — un unico componente Vue che si adatta a PF/PG/ENTE guidato dalla matrice `tipi_soggetto_dettaglio`
2. **Refactoring lookup** — eliminare i lookup duplicati da `amm-software`, usare `core/lookup-codici` per tabelle config standard
3. **Gestione indirizzi completa** — risolvere il trigger DEFERRED `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` con supporto a tutta la catena indirizzi normalizzati
4. **Autocomplete comuni e stradario** — ricerca server-side su comuni (8098 record) e stradario

---

### Matrice dati dal DB (riferimento per lo sviluppo)

**Tipi soggetto dettaglio:**

| id  | codice | natura | CF obbl. | PIVA obbl. | Dati societari | Campi visibili                                                    |
| --- | ------ | ------ | :------: | :--------: | -------------- | ----------------------------------------------------------------- |
| 1   | PR     | PF     |    si    |     no     | NONE           | cognome, nome, sesso, data_nascita, comune_nascita, CF            |
| 2   | DI     | PF     |    si    |     si     | OPTIONAL       | cognome, nome, sesso, data_nascita, comune_nascita, CF, **P.IVA** |
| 3   | SC     | PG     |    si    |     si     | REQUIRED       | ragione_sociale, CF, P.IVA, **dati societari obbl.**              |
| 4   | SP     | PG     |    si    |     si     | OPTIONAL       | ragione_sociale, CF, P.IVA, dati societari opz.                   |
| 5   | ENC    | ENTE   |    si    |     si     | OPTIONAL       | ragione_sociale, CF, P.IVA, dati societari opz.                   |

**Indirizzi obbligatori per tipo:**

| Tipo               | Obbligatori                               | Opzionali ammessi                                                                                                                        |
| ------------------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| PR (Privato)       | RESID, DOM-FISC, FATT (fallback→DOM-FISC) | CONS (fallback→RESID), POSTALE (fallback→RESID), SPED                                                                                    |
| DI (Ditta Ind.)    | DOM-FISC                                  | RESID, SEDE-LEG (fallback→DOM-FISC), SEDE-OP, CONS, FATT (fallback→DOM-FISC), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED |
| SC (Soc. Capitali) | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |
| SP (Soc. Persone)  | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |
| ENC (Ente)         | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |

**Tabella comuni**: `config.comuni` — 8098 record (id, descrizione, provincia_id).

**Tabella indirizzi**: `anagrafiche.indirizzi_soggetti` — soggetto_id, tipo_indirizzo_id, indirizzo_dettaglio_id (normalizzato) o indirizzo_libero (eccezione), stato_id, ecc.

---

### Architettura indirizzi — catena completa

> Riferimento: [Guida Gestione degli Indirizzi](/guide/gestione-degli-indirizzi)

L'indirizzo in ZeroERP **non e' un campo di testo**: e' un dato strutturato normalizzato.
La modalita' **normalizzata** (via `indirizzo_dettaglio_id`) e' **sempre preferita**.
L'`indirizzo_libero` e' riservato a eccezioni (migrazioni, indirizzi esteri non normalizzabili).

**Catena di normalizzazione (dal basso verso l'alto):**

```
config.toponomastica          (Via, Piazza, Corso, Largo...)
       ↓
config.stradario_generale     (toponimo + denominazione via)
       ↓
config.stradario              (via locale = stradario_generale + comune + CAP)
       ↓
anagrafiche.indirizzi_dettaglio  (civico normalizzato: stradario + civico + estensione + palazzina + scala + piano + interno)
       ↓
anagrafiche.indirizzi_soggetti   (soggetto_id + tipo_indirizzo_id + indirizzo_dettaglio_id)
```

**Gerarchia geografica:**
```
config.stati → config.regioni → config.province → config.comuni → config.codici_postali
                                                        ↓
                                                  config.stradario
```

**Regole chiave (dalla guida):**
- **R1 — XOR**: o normalizzato (`indirizzo_dettaglio_id`) o libero (`indirizzo_libero`), mai entrambi
- **R2 — Unicita'**: un solo indirizzo per tipo per soggetto (`UNIQUE soggetto_id, tipo_indirizzo_id`)
- **R3 — Completezza libero**: se libero, obbligatori `indirizzo_libero` + `stato_id` + (`comune_id` + `codice_postale_id`) oppure (`locality` + `postal_box`)
- **R6 — Guard tipo**: trigger verifica tipo_indirizzo contro matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`
- **R7 — Unicita' civico**: vincolo `uq_indirizzi_dettaglio_norm` su (stradario_id, civico, estensione, palazzina, scala, piano, interno)

**Funzioni di ricerca gia' esistenti:**
- `anagrafiche.fn_search_indirizzi_dettaglio(...)` — ricerca per stradario+civico o fuzzy su indirizzo_normalizzato
- `script.fn_get_indirizzo(p_soggetto_ruolo_id, p_tipo_codice)` — risoluzione master/fallback
- `script.fn_get_indirizzo_by_soggetto(p_soggetto_id, p_tipo_codice)` — layer soggetto con fallback

---

### TRACK DB (competenza server DB)

> **Nota**: DB-1 e' stato riscritto completamente rispetto alla versione iniziale.
> La gestione indirizzi richiede building block dedicati per tutta la catena di normalizzazione,
> non un semplice parametro JSONB con `indirizzo_libero`.

#### DB-1 — Building block `fn_get_or_create_indirizzo_dettaglio` ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: nessuno
**Schema**: `anagrafiche`
**Tipo**: building block riusabile

Funzione upsert: cerca un civico esistente per chiave naturale, se non esiste lo crea.
Il vincolo `uq_indirizzi_dettaglio_norm` garantisce la deduplicazione.

**Implementato in:**
- Changeset: `db/changelog/migrations_v2/20_code/anagrafiche/20260313-12-create-fn-get-or-create-indirizzo-dettaglio-mctit.yaml`
- Doc manuale: `docs/it/dbzero/anagrafiche/manual/fn_get_or_create_indirizzo_dettaglio.md`
- Test pgTAP: `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` (9 test)

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    p_stradario_id        config.stradario.id%TYPE,
    p_civico              anagrafiche.indirizzi_dettaglio.civico%TYPE         DEFAULT NULL,
    p_estensione_civico   anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE DEFAULT NULL,
    p_palazzina           anagrafiche.indirizzi_dettaglio.palazzina%TYPE      DEFAULT NULL,
    p_scala               anagrafiche.indirizzi_dettaglio.scala%TYPE          DEFAULT NULL,
    p_piano               anagrafiche.indirizzi_dettaglio.piano%TYPE          DEFAULT NULL,
    p_interno             anagrafiche.indirizzi_dettaglio.interno%TYPE        DEFAULT NULL
)
RETURNS anagrafiche.indirizzi_dettaglio.id%TYPE
```

**Logica:**
1. Guard: `p_stradario_id` obbligatorio, verificare che esista e sia attivo in `config.stradario`
2. Cercare per chiave naturale (stradario_id, civico, estensione, palazzina, scala, piano, interno) con COALESCE su nullable
3. Se trovato → RETURN id esistente
4. Se non trovato → INSERT + RETURNING id (il trigger `trgfn_indirizzi_dettaglio_normalize` calcola `indirizzo_normalizzato`, `via_norm`, `civico_norm`)
5. Gestire `unique_violation` (race condition) con retry

**Nota**: questa funzione NON gestisce la creazione dello stradario. Se lo stradario non esiste, il chiamante (o il frontend) deve prima crearlo o selezionarlo. Vedi DB-1b.

#### DB-1b — `fn_get_or_create_stradario`: NON SERVE (stradario chiuso)

**Stato**: CHIUSO — nessun changeset necessario.

Lo stradario e' **chiuso**: la gestione di `config.toponomastica`, `config.stradario_generale`
e `config.stradario` e' riservata all'admin. L'utente operativo seleziona da stradari esistenti
tramite autocomplete (vedi DB-7). Non serve nessuna funzione di creazione on-the-fly.

#### DB-2 — Building block `fn_crea_indirizzo_soggetto` ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: DB-1 (se normalizzato) oppure nessuno (se libero)
**Schema**: `anagrafiche`

**Implementato in:**
- Changeset: `db/changelog/migrations_v2/20_code/anagrafiche/20260313-14-create-fn-crea-indirizzo-soggetto-mctit.yaml`
- Doc manuale: `docs/it/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto.md`
- Test pgTAP: `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` (11 test)
**Tipo**: building block riusabile

Crea un record in `anagrafiche.indirizzi_soggetti`. Supporta entrambe le modalita':
- **Normalizzata** (standard): riceve `p_indirizzo_dettaglio_id`
- **Libera** (eccezione): riceve `p_indirizzo_libero` + campi geografici

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(
    -- Obbligatori
    p_soggetto_id             anagrafiche.soggetti.id%TYPE,
    p_tipo_indirizzo_codice   config.tipi_indirizzi.codice_interno%TYPE,
    -- Modalita' normalizzata (preferita)
    p_indirizzo_dettaglio_id  anagrafiche.indirizzi_dettaglio.id%TYPE   DEFAULT NULL,
    -- Modalita' libera (eccezione)
    p_indirizzo_libero        text                                     DEFAULT NULL,
    p_stato_id                config.stati.id%TYPE                     DEFAULT NULL,
    p_comune_id               config.comuni.id%TYPE                    DEFAULT NULL,
    p_codice_postale_id       config.codici_postali.id%TYPE            DEFAULT NULL
)
RETURNS anagrafiche.indirizzi_soggetti.id%TYPE
```

**Logica:**
1. Guard XOR: o `p_indirizzo_dettaglio_id` o `p_indirizzo_libero`, mai entrambi (R1)
2. Lookup `tipo_indirizzo_id` da `p_tipo_indirizzo_codice` in `config.tipi_indirizzi`
3. Se modalita' libera: guard completezza (R3) — `stato_id` + (`comune_id` + `codice_postale_id`)
4. INSERT in `anagrafiche.indirizzi_soggetti`
5. I trigger si occupano di: guard tipo (R6), normalizzazione (R8), sync geoloc, audit, tx_id

**Nota**: il trigger `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` verifica automaticamente
che il tipo indirizzo sia ammesso per il tipo_soggetto_dettaglio del soggetto (matrice config).

#### DB-3 — Aggiornare `fn_crea_soggetto_pf`: aggiungere `p_comune_nascita_id` ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: nessuno
**File**: nuovo changeset per `anagrafiche.fn_crea_soggetto_pf` (runOnChange)

* Nuovo parametro `p_comune_nascita_id anagrafiche.soggetti.comune_id%TYPE DEFAULT NULL`
* Aggiungere `comune_id` nell'INSERT di `anagrafiche.soggetti` (colonna gia' esistente, FK `fk_comuni_config`)
* La FK verifica automaticamente l'esistenza del comune — nessun guard aggiuntivo necessario
* Propagare il parametro anche in `fn_crea_operatore`
* DROP vecchia firma (7 params) per evitare ambiguita' overload

**Implementato in:**
- Changeset: `db/changelog/migrations_v2/20_code/anagrafiche/20260313-13-update-fn-crea-soggetto-pf-comune-nascita-mctit.yaml`
- Doc manuale aggiornata: `docs/it/dbzero/anagrafiche/manual/fn_crea_soggetto_pf.md`
- Test pgTAP aggiornato: `db/pgtap/anagrafiche/test-fn-crea-soggetto-pf.sql` (9 test, inclusi test 8-9 per comune_nascita_id)

#### DB-4 — `risorse_umane.valido_dal`: nessun intervento (opzione B)

**Stato**: CHIUSO — nessun changeset necessario.

La funzione `fn_crea_risorsa_umana` gestisce gia' `p_valido_dal DEFAULT CURRENT_DATE` nel parametro.
Non si aggiunge DEFAULT sulla colonna: tutti gli INSERT passano dalla funzione building block.

#### DB-5 — Aggiornare `fn_crea_operatore`: indirizzi tramite building block ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: DB-1, DB-2, DB-3
**File**: nuovo changeset per `anagrafiche.fn_crea_operatore` (runOnChange)

**Implementato in:**
- Changeset: `db/changelog/migrations_v2/20_code/anagrafiche/20260313-15-update-fn-crea-operatore-indirizzi-mctit.yaml`
- Doc manuale aggiornata: `docs/it/dbzero/anagrafiche/manual/fn_crea_operatore.md`
- DROP vecchia firma (13 params) per evitare ambiguita' overload

Aggiungere alla firma dell'orchestratore i parametri per gli indirizzi obbligatori PR:

**Nuovi parametri (modalita' normalizzata):**
```sql
-- Indirizzo residenza (RESID) — normalizzato
p_indirizzo_resid_dettaglio_id   anagrafiche.indirizzi_dettaglio.id%TYPE DEFAULT NULL,
-- Indirizzo domicilio fiscale (DOM-FISC) — se NULL, usa stesso di RESID
p_indirizzo_domfisc_dettaglio_id anagrafiche.indirizzi_dettaglio.id%TYPE DEFAULT NULL,
-- Comune nascita
p_comune_nascita_id              anagrafiche.soggetti.comune_id%TYPE     DEFAULT NULL
```

**Logica aggiuntiva nel body:**
1. Dopo `fn_crea_soggetto_pf` (che ora accetta `p_comune_nascita_id`)
2. Se `p_indirizzo_resid_dettaglio_id` IS NOT NULL:
   - `PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_soggetto_id, 'RESID', p_indirizzo_resid_dettaglio_id)`
   - Se `p_indirizzo_domfisc_dettaglio_id` IS NULL → usa lo stesso di RESID per DOM-FISC
   - `PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_soggetto_id, 'DOMFISC', COALESCE(p_indirizzo_domfisc_dettaglio_id, p_indirizzo_resid_dettaglio_id))`
3. Se `p_indirizzo_resid_dettaglio_id` IS NULL → nessun indirizzo creato (il trigger DEFERRED potrebbe
   bloccare al COMMIT se la matrice richiede RESID per PR — questo e' voluto: il chiamante deve fornire
   gli indirizzi obbligatori)

**Nota sul trigger DEFERRED**: `trgfn_soggetti_guard_indirizzi_required` scatta al COMMIT.
Se gli indirizzi obbligatori non sono presenti, il COMMIT fallisce con errore chiaro.
L'orchestratore non deve duplicare questo check — il trigger fa da rete di sicurezza.

#### DB-6 — Aggiornare test pgTAP ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: DB-1..DB-5

**Test implementati (tutti verificati OK):**

* `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` — 9 test (DB-1)
* `db/pgtap/anagrafiche/test-fn-crea-soggetto-pf.sql` — 9 test (DB-3, inclusi test 8-9 comune_nascita_id)
* `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` — 11 test (DB-2: normalizzato, DOMFISC, XOR, guard)
* `db/pgtap/script/test-fn-search-stradario.sql` — 8 test (DB-7)
* `db/pgtap/anagrafiche/test-fn-crea-operatore.sql` — 12 test (aggiornato: CF validi, match errori reali)
* `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana.sql` — 9 test (aggiornato: CF validi, match errori reali)

**Fix applicati ai test preesistenti:**
* Sostituiti CF casuali invalidi con CF validi (`PNZFDN78A01L219Y`, `LCCRLD80A01L736X`, `PRAFNC80A01F205N`)
* Corretti match errore: `E_ADMIN_CF_DUPLICATO` → `Codice fiscale gia`, `E_ADMIN_UO_NON_TROVATA` → `non trovata o non attiva`
* Corretti lookup cognome/nome: `UPPER` → case originale (fn_crea_soggetto_pf usa TRIM, non UPPER)

**Nota**: test DB-5 (fn_crea_operatore con indirizzi) non ancora aggiunto — richiede test specifici per RESID+DOMFISC nell'orchestratore

#### DB-7 — Funzione `fn_search_stradario` (ricerca vie per autocomplete) ✅ COMPLETATO

**Stato**: COMPLETATO (2026-03-13)
**Prerequisiti**: nessuno
**Schema**: `script` (funzione di lettura cross-dominio, come le altre `fn_search_*`)
**Tipo**: funzione STABLE di lettura ottimizzata

**Implementato in:**
- Changeset: `db/changelog/migrations_v2/20_code/script/20260313-11-create-fn-search-stradario-mctit.yaml`
- Doc manuale: `docs/it/dbzero/script/manual/fn_search_stradario.md`
- Test pgTAP: `db/pgtap/script/test-fn-search-stradario.sql` (8 test)

Il frontend cerca VIE (stradario) per comune, non civici. L'utente:
1. Seleziona un comune (autocomplete comuni, BE-3)
2. Cerca una via nel comune selezionato (autocomplete stradario, questa funzione)
3. Inserisce il civico manualmente (campo numerico + dettagli)
4. Il backend chiama `fn_get_or_create_indirizzo_dettaglio` (DB-1) per ottenere/creare il civico

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION script.fn_search_stradario(
    p_comune_id    config.comuni.id%TYPE        DEFAULT NULL,
    p_search       text                         DEFAULT NULL,
    p_limit        integer                      DEFAULT 30
)
RETURNS TABLE (
    stradario_id           config.stradario.id%TYPE,
    toponimo               config.toponomastica.descrizione%TYPE,
    denominazione          config.stradario_generale.denominazione_norm%TYPE,
    via_completa           text,    -- es. "Via Roma"
    comune_id              config.comuni.id%TYPE,
    comune_descrizione     config.comuni.denominazione%TYPE,
    provincia_sigla        config.province.sigla%TYPE,
    codice_postale_id      config.codici_postali.id%TYPE,
    cap                    config.codici_postali.cap%TYPE
)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
```

**Logica:**
1. Guard: almeno `p_comune_id` o `p_search` deve essere valorizzato
2. Se `p_comune_id` fornito: filtra per comune (caso principale — autocomplete dopo selezione comune)
3. Se `p_search` fornito: ricerca ILIKE su `toponimo || ' ' || denominazione_norm`
4. JOIN: `stradario` → `stradario_generale` → `toponomastica` + `comuni` → `province` + `codici_postali`
5. Filtro `stradario.attivo = true` (se presente), ORDER BY `via_completa`, LIMIT `p_limit`
6. Campo calcolato `via_completa` = `toponimo || ' ' || denominazione_norm` (es. "Via Roma", "Piazza Garibaldi")

**Nota sulle performance**: con `p_comune_id` + `p_search` il numero di righe e' contenuto
(un comune ha mediamente poche centinaia di vie). Se necessario, aggiungere indice trigram
su `stradario_generale.denominazione_norm`.

**Pattern coerente con il progetto**: stessa struttura di `fn_search_soggetti_universale`
e `fn_search_indirizzi_dettaglio` — funzione STABLE in `script`, usata dal backend come entry point.

---

### TRACK BACKEND

#### BE-1 — Refactoring lookup: eliminare duplicati da `amm-software`

**Prerequisiti**: nessuno
**Principio**: le tabelle config sono trasversali, i lookup vanno in `core`

**Tabelle compatibili con `lookup-codici` (struttura id/codice/descrizione/attivo)**:

Verificare e registrare nella whitelist di `dbops.fn_get_lookup_codici`:
* `config.qualifiche`
* `config.unita_organizzative`
* `script.aree_funzionali`
* `script.azioni_processo`
* `config.emittenti_fiscali` (potrebbe avere campi extra — verificare)

**Azioni**:

1. Verificare quali tabelle sono gia' nella whitelist di `fn_get_lookup_codici`
2. Aggiungere le mancanti (se la struttura e' compatibile)
3. Aggiungere in `fn_get_lookup_codici` il supporto per le tabelle che hanno `codice_interno` invece di `codice` (tipi_soggetto_dettaglio)
4. Eliminare da `amm_software/api/views.py` le 5 view Lookup* (QualificheView, AreeView, AzioniView, EmittentiView, UOView)
5. Eliminare da `amm_software/api/urls_v1.py` le 5 URL lookup
6. Eliminare da `amm_software/db/amm_software_repository.py` i metodi `list_qualifiche()`, `list_unita_organizzative()`, `list_aree_funzionali()`, `list_azioni_processo()`, `list_emittenti_fiscali()`
7. Aggiornare i test (rimuovere test lookup da amm_software, verificare test lookup-codici copra le nuove tabelle)

#### BE-2 — Endpoint matrice indirizzi per tipo soggetto

**Prerequisiti**: nessuno
**File**: `apps/core/api/views.py` + `apps/core/db/lookup_repository.py` (nuovo)

```
GET /api/v1/core/lookup/tipi-soggetto-dettaglio/<id>/indirizzi/
→ [{ "tipo_indirizzo_id": 1, "codice": "RESID", "descrizione": "Residenza",
     "obbligatorio": true, "fallback_tipo_indirizzo_id": null }, ...]
```

* Query su `config.tipi_soggetto_dettaglio_tipi_indirizzo` JOIN `config.tipi_indirizzi`
* Filtro `attivo=true` e date validita'
* Permission: `ZeroERPPermission` (qualsiasi utente autenticato)

#### BE-3 — Endpoint autocomplete comuni

**Prerequisiti**: nessuno
**File**: `apps/core/api/views.py` + `apps/core/db/lookup_repository.py`

```
GET /api/v1/core/lookup/comuni/?search=ROM&limit=20
→ { "results": [{ "id": 4517, "descrizione": "ROMA", "provincia_id": 69 }, ...] }
```

* Query `config.comuni WHERE descrizione ILIKE '%search%' LIMIT 20`
* Ottimizzare con indice GIN/trigram se necessario (8098 record, ILIKE gestibile)
* Permission: `ZeroERPPermission`

#### BE-4 — Endpoint lookup tipi soggetto dettaglio

**Prerequisiti**: nessuno
**File**: `apps/core/api/views.py` + `apps/core/db/lookup_repository.py`

```
GET /api/v1/core/lookup/tipi-soggetto-dettaglio/
→ [{ "id": 1, "codice_interno": "PR", "descrizione": "...", "natura_soggetto": "PF",
     "cf_obbligatorio": true, "piva_obbligatoria": false, "dati_societari_policy": "NONE" }, ...]
```

* JOIN con `config.tipi_soggetto` per avere `natura_soggetto`
* Il frontend usa questo per guidare la visibilita' dei campi

#### BE-5 — Aggiornare POST creazione operatore

**Prerequisiti**: DB-1 (fn_crea_operatore con indirizzi), BE-1 (refactoring lookup)
**File**: `apps/amm_software/api/views.py`, `apps/amm_software/db/amm_software_repository.py`

* Aggiungere al payload POST: `comune_nascita_id`, `indirizzo_residenza` (oggetto), `indirizzo_dom_fiscale` (oggetto, opzionale)
* `amm_software_repository.crea_operatore()` passa i nuovi parametri JSONB alla funzione DB
* Aggiornare test `test_crea_utente.py`

#### BE-6 — Test

**Prerequisiti**: BE-1..BE-5
**File**: `apps/core/tests/api/`, `apps/amm_software/tests/api/`

* Test `lookup_repository` (mock cursor): tipi_soggetto_dettaglio, matrice indirizzi, comuni
* Test endpoint API: autocomplete comuni, matrice indirizzi
* Aggiornare `test_crea_utente.py` con nuovi campi (indirizzo, comune_nascita)
* Smoke test: aggiornare `smoke-test-amm-software.sh` con i nuovi endpoint

---

### TRACK FRONTEND

#### FE-1 — API client core per lookup

**Prerequisiti**: BE-2, BE-3, BE-4
**File**: `src/core/api/core.js` (esistente o nuovo)

Aggiungere funzioni:
* `lookupCodici(rel, params)` → chiama `GET /api/v1/core/lookup-codici/?rel=...`
* `lookupTipiSoggettoDettaglio()` → chiama BE-4
* `lookupMatriceIndirizzi(tipoSoggettoDettaglioId)` → chiama BE-2
* `searchComuni(search, limit)` → chiama BE-3

#### FE-2 — Composable `useLookup`

**Prerequisiti**: FE-1
**File**: `src/core/composables/useLookup.js`

```js
export function useLookup(fetchFn, options = {}) {
  // Cache, loading, load(), reload()
  // immediate: true per caricare subito
}
```

#### FE-3 — Refactoring store `utenti.js` e API `amministrazione.js`

**Prerequisiti**: BE-1, FE-1
**File**: `src/amministrazione/stores/utenti.js`, `src/amministrazione/api/amministrazione.js`

* Rimuovere da `amministrazione.js`: `listQualifiche()`, `listUnitaOrganizzative()`, `listAreeFunzionali()`, `listAzioniProcesso()`, `listEmittentiFiscali()`
* Rimuovere da `utenti.js`: i ref e le action corrispondenti (qualifiche, unitaOrganizzative, areeFunzionali, ecc.)
* Sostituire con `useLookup(() => lookupCodici('config.qualifiche'))` nei componenti che li usano
* Aggiornare tutti i componenti che importano queste funzioni

#### FE-4 — Composable `useSoggettoForm`

**Prerequisiti**: FE-1, FE-2
**File**: `src/core/composables/useSoggettoForm.js`

Un **unico composable** che gestisce PF + PG + ENTE (non separare PF e PG):

```js
export function useSoggettoForm(options = {}) {
  const { tipoForzato = null } = options
  // tipoForzato: se impostato (es. 1 per PR), il select tipo non appare

  const form = reactive({
    tipo_soggetto_dettaglio_id: tipoForzato || null,
    // PF
    cognome: '', nome: '', sesso: 'M', data_nascita: null, comune_nascita_id: null,
    // PG
    ragione_sociale: '',
    // Comuni
    codice_fiscale: '', partita_iva: '',
    // Contatto default
    email: '',
    // Indirizzo obbligatorio (il primo della matrice)
    indirizzo: { indirizzo_libero: '', comune_id: null, codice_postale_id: null }
  })

  // Computed guidati dalla matrice DB
  const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio)
  const tipoCorrente = computed(() => tipiSoggetto.find(t => t.id === form.tipo_soggetto_dettaglio_id))
  const isPF = computed(() => ['PF'].includes(tipoCorrente.natura_soggetto))
  const showPartitaIva = computed(() => tipoCorrente.piva_obbligatoria)
  const showDatiSocietari = computed(() => tipoCorrente.dati_societari_policy !== 'NONE')
  const requireDatiSocietari = computed(() => tipoCorrente.dati_societari_policy === 'REQUIRED')

  // Matrice indirizzi: ricaricata quando cambia tipo
  const matriceIndirizzi = ref([])
  const indirizziObbligatori = computed(() => matriceIndirizzi.filter(m => m.obbligatorio))

  watch(() => form.tipo_soggetto_dettaglio_id, async (id) => {
    if (id) matriceIndirizzi.value = await lookupMatriceIndirizzi(id)
  })

  function validate() { /* validazione campi in base al tipo corrente */ }
  function reset() { /* reset form */ }

  return { form, isPF, showPartitaIva, showDatiSocietari, requireDatiSocietari,
           indirizziObbligatori, matriceIndirizzi, tipiSoggetto, validate, reset }
}
```

#### FE-5 — Componente `SoggettoForm.vue`

**Prerequisiti**: FE-4
**File**: `src/core/components/SoggettoForm.vue`

Un **unico componente** che si adatta al tipo selezionato:

```vue
<template>
  <!-- Select tipo soggetto (nascosto se tipoForzato) -->
  <Select v-if="!tipoForzato" v-model="model.tipo_soggetto_dettaglio_id"
    :options="tipiSoggetto" option-label="descrizione" option-value="id" />

  <!-- Sezione PF (PR, DI) -->
  <template v-if="isPF">
    cognome*, nome*, sesso, data_nascita, ComuneAutocomplete(comune_nascita)
  </template>

  <!-- Sezione PG (SC, SP, ENC) -->
  <template v-else>
    ragione_sociale*
  </template>

  <!-- Sempre visibili -->
  codice_fiscale*
  partita_iva* (v-if="showPartitaIva")
  email* (contatto default)

  <!-- Indirizzi obbligatori dalla matrice -->
  <div v-for="ind in indirizziObbligatori" :key="ind.tipo_indirizzo_id">
    <h4>{{ ind.descrizione }} *</h4>
    <IndirizzoSubForm v-model="indirizzi[ind.codice]" />
  </div>

  <!-- Dati societari (se richiesti) -->
  <DatiSocietariSection v-if="showDatiSocietari" :required="requireDatiSocietari" />
</template>
```

**Props**:
```js
defineProps({
  modelValue: Object,       // binding bidirezionale
  tipoForzato: Number,      // null = mostra select, 1 = forza PR
  readonly: Boolean,
  showIndirizzi: { type: Boolean, default: true }  // per operatori: true (serve RESID)
})
```

#### FE-6 — Componente `ComuneAutocomplete.vue`

**Prerequisiti**: FE-1 (endpoint BE-3)
**File**: `src/core/components/ComuneAutocomplete.vue`

* PrimeVue `AutoComplete` con `completeMethod` che chiama `searchComuni(query)`
* Mostra `descrizione` + provincia
* Emette `id` via v-model

#### FE-7 — Composable `useAuthUser` + componente `AuthUserForm.vue`

**Prerequisiti**: FE-2
**File**: `src/core/composables/useAuthUser.js`, `src/core/components/AuthUserForm.vue`

Come da catalogo componenti gia' documentato sopra. Campi: username, email, password, password_confirm.

#### FE-8 — Refactor `UtenteDrawer.vue`

**Prerequisiti**: FE-5, FE-7, BE-5
**File**: `src/amministrazione/components/UtenteDrawer.vue`

Sostituire il form monolitico con building block:

```vue
<template>
  <Drawer ...>
    <template v-if="!isEdit">
      <!-- Building block soggetto: tipo forzato PR, include indirizzi -->
      <SoggettoForm v-model="soggetto.form" :tipo-forzato="1" />

      <!-- Building block auth -->
      <AuthUserForm v-model="auth.form" />

      <!-- Specifico operatore (non building block) -->
      <h4>{{ t('amm.section_collocazione') }}</h4>
      <Select v-model="collocazione.ruolo_sistema" ... />
      <Select v-model="collocazione.qualifica_id" ... />  <!-- via useLookup -->
      <Select v-model="collocazione.unita_organizzativa_id" ... />  <!-- via useLookup -->

      <Button @click="onSave" />
    </template>
  </Drawer>
</template>
```

Il payload POST assembla: `{ ...soggetto.form, ...auth.form, ...collocazione }`.

#### FE-9 — Aggiornare `UtentiListView.vue` e `UtentePermessiTab.vue`

**Prerequisiti**: FE-3 (refactoring store)
**File**: `src/amministrazione/views/UtentiListView.vue`, `src/amministrazione/components/UtentePermessiTab.vue`

* Sostituire i riferimenti a `store.unitaOrganizzative` e altri lookup rimossi
* Usare `useLookup` direttamente nei componenti che ne hanno bisogno

#### FE-10 — i18n

**Prerequisiti**: nessuno (puo' procedere in parallelo)
**File**: `src/locales/it.json`, `src/locales/en.json`

Aggiungere chiavi nel namespace `common` per i campi dei building block:
* `common.cognome`, `common.nome`, `common.codice_fiscale`, `common.partita_iva`
* `common.ragione_sociale`, `common.sesso`, `common.data_nascita`, `common.comune_nascita`
* `common.indirizzo`, `common.comune`, `common.cap`, `common.provincia`
* `common.email`, `common.telefono`, `common.pec`
* `common.username`, `common.password`, `common.password_confirm`
* `common.tipo_soggetto`, `common.select_tipo_soggetto`

#### FE-11 — Build e verifica

**Prerequisiti**: FE-8, FE-9
**File**: nessuno

* `vite build` — zero errori
* Test manuale: creare operatore con tutti i campi (CF valido, indirizzo, comune nascita)
* Verificare che il trigger DEFERRED non blocchi piu' la creazione

---

### Diagramma dipendenze

```text
DB TRACK                              BACKEND TRACK                    FRONTEND TRACK
────────                              ─────────────                    ──────────────

DB-4 (valido_dal) ─ CHIUSO            BE-1 (refactor lookup)  ─────→  FE-3 (refactor store)
                                           │                               │
DB-3 (comune_nascita fn_crea_soggetto_pf)  BE-2 (matrice indirizzi)     FE-1 (API client)
     │                                     BE-3 (autocomplete comuni)      │
DB-1 (fn_get_or_create_indirizzo_dettaglio)BE-4 (tipi soggetto dett.)  FE-2 (useLookup)
     │                                          │                          │
DB-2 (fn_crea_indirizzo_soggetto) ←── DB-1 BE-7 (search stradario)    FE-4 (useSoggettoForm)
     │                                          │                          │
DB-7 (search stradario) — parallelo        BE-5 (POST operatore)      FE-5 (SoggettoForm.vue)
     │                                       ←── DB-5                  FE-6 (ComuneAutocomplete)
DB-5 (fn_crea_operatore + indirizzi)            │                      FE-6b (StradarioAutocomplete)
   ←── DB-1, DB-2, DB-3                   BE-6 (test)                  FE-7 (AuthUserForm)
     │                                                                      │
DB-6 (test pgTAP) ←── DB-1..DB-5                                      FE-8 (refactor drawer)
                                                                       FE-9 (aggiorna views)
                                                                       FE-10 (i18n) — parallelo
                                                                       FE-11 (build + verifica)
```

### Decisioni prese

1. **DB-1b — Stradario chiuso**: toponomastica / stradario_generale / stradario sono gestiti solo da admin.
   L'utente operativo seleziona da vie esistenti via autocomplete. Nessuna funzione di creazione on-the-fly.

2. **DB-7 — Funzione DB**: `script.fn_search_stradario(p_comune_id, p_search, p_limit)` — coerente
   col pattern del progetto (lettura ottimizzata in DB, Django orchestra e espone API).

3. **DB-4 — `valido_dal` opzione B**: nessun ALTER TABLE, il COALESCE nella funzione basta.

### Ordine di esecuzione consigliato

**Parallelo 1** (indipendenti, nessuna dipendenza) — ✅ TRACK DB COMPLETATO (2026-03-13):

* ✅ DB-1 (`fn_get_or_create_indirizzo_dettaglio`)
* ✅ DB-3 (`fn_crea_soggetto_pf` + `p_comune_nascita_id`)
* ✅ DB-7 (search stradario)
* BE-1 (refactoring lookup — nessuna dipendenza DB)
* FE-10 (i18n — nessuna dipendenza)

**Parallelo 2** (dopo Parallelo 1) — ✅ TRACK DB COMPLETATO (2026-03-13):

* ✅ DB-2 (`fn_crea_indirizzo_soggetto`)
* BE-2, BE-3, BE-4, BE-7 (endpoint lookup/search — nessuna dipendenza DB)
* FE-1, FE-2, FE-3 (API client, useLookup, refactoring store — dipende da BE-1..BE-4)

**Sequenziale 3** (dopo Parallelo 2) — ✅ TRACK DB COMPLETATO (2026-03-13):

* ✅ DB-5 (aggiornare `fn_crea_operatore` — con indirizzi RESID/DOMFISC + comune_nascita_id)
* BE-5 (POST operatore — dipende da DB-5)
* FE-4, FE-5, FE-6, FE-6b, FE-7 (composable + componenti — dipende da FE-1..FE-3)

**Sequenziale 4** (dopo tutto):

* DB-6 (test pgTAP — dipende da DB-1..DB-5)
* FE-8 (refactor drawer — dipende da FE-5, FE-7, BE-5)
* FE-9 (aggiorna views)
* BE-6 (test completi)
* FE-11 (build + verifica finale)
