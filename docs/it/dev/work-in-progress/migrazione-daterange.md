# Migrazione a `daterange` nativo PostgreSQL — Analisi di impatto

> Stato: **WIP — IN ANALISI**
>
> Ultima revisione: aprile 2026
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
| 11 | `config.tipi_ruoli_nature_ammesse` | No | DB + BE | CHECK validita`. Backend: lookup `list_tipi_ruoli_per_natura()` filtrato per data |
| 12 | `config.ruoli_tipi_indirizzo` | No | DB only | CHECK `chk_ruoli_tipi_indirizzo_validita`. Nessun codice applicativo diretto |
| 13 | `config.tipi_soggetto_dettaglio_tipi_indirizzo` | No | DB only | CHECK `chk_tsd_tipi_indirizzo_validita`. Nessun codice applicativo |
| 14 | `config.user_override_aree` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |
| 15 | `config.user_override_oggetti` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |
| 16 | `config.user_override_azioni` | No | DB + BE | CHECK validita`. Backend: risoluzione permessi |

#### Tabelle con date di validita` gestite da form dedicato (conti bancari / matrice indirizzi / operatori)

| # | Schema.Tabella | GIST | Stack | Note |
|---|---|---|---|---|
| 17 | `anagrafiche.conti_bancari` (legami soggetto/ruolo) | No | FULL | Backend: `views_conti_bancari.py`, service, repository. Frontend: `ContoBancarioForm.vue`, composable `useContoBancarioForm.js` con validazione `valido_al >= valido_dal` |
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

## 3) Analisi di impatto — Modifiche DB

Questa sezione descrive le modifiche da apportare **esclusivamente lato database** (DDL, funzioni, trigger, vincoli).
Il DB ha la proprieta` del modello dati: tutte le modifiche partono da qui.

### 3.1 Strategia di migrazione per tabella

Per ogni tabella la sequenza e`:

1. **Aggiungere colonna** `validita daterange` (o nome specifico per dominio)
2. **Popolare** la nuova colonna da `valido_dal` / `valido_al` esistenti:
   ```sql
   UPDATE schema.tabella
   SET validita = daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]');
   ```
3. **Creare trigger** (modello `trgfn_clienti_set_periodo`) che mantiene sincronizzata la colonna `validita` ad ogni INSERT/UPDATE sulle colonne `valido_dal` / `valido_al`
4. **Ricreare vincoli GIST** sulla colonna nativa (dove gia` esistono):
   - Drop vecchio EXCLUDE su espressione `daterange(valido_dal, ...)`
   - Create nuovo EXCLUDE su colonna `validita WITH &&`
5. **Aggiornare funzioni** che costruiscono `daterange()` al volo → usare la colonna `validita` direttamente
6. **Aggiornare query** nelle funzioni/trigger che filtrano con `x >= valido_dal AND (valido_al IS NULL OR x <= valido_al)` → `validita @> x::date`
7. **(Fase futura, opzionale)** Drop delle colonne `valido_dal` / `valido_al` se non piu` necessarie come input utente

### 3.2 Decisione aperta: drop colonne o mantenere entrambe?

Due approcci possibili:

| Approccio | Pro | Contro |
|---|---|---|
| **A — Mantieni colonne + aggiungi `validita`** (modello clienti) | Retrocompatibile, l'utente continua a inserire date separate, il trigger calcola il range | Colonne ridondanti, rischio disallineamento se il trigger salta |
| **B — Sostituisci con sola colonna `validita`** | Modello pulito, zero ridondanza | Richiede modifiche a tutti i layer (API, frontend) che oggi inviano `valido_dal`/`valido_al` come campi separati |

**Raccomandazione**: approccio **A** per le tabelle con stack FULL (backend + frontend gia` sviluppati) — minimizza l'impatto applicativo. Approccio **B** per le tabelle DB only — non c'e` codice da cambiare.

### 3.3 Impatto per gruppo di tabelle

#### Gruppo 1 — Tabelle con GIST gia` esistente (priorita` ALTA)

Queste gia` pagano il costo del GIST ma ricostruiscono il range ad ogni valutazione. Il beneficio e` immediato.

**`vendite.listini_versioni`** (#1)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync da `valido_dal` / `valido_al`
* Ricreare `ex_listini_versioni_no_overlap` sulla colonna nativa (filtro `stato = 'ATTIVA' AND attivo`)
* **Funzioni da aggiornare**:
  - `vendite.fn_resolve_prezzo_listino` — CTE `versioni_candidate`: sostituire filtro date con `v.validita @> p_data_riferimento`
  - ORDER BY: `COALESCE(v.valido_al, 'infinity')` → `upper(v.validita)`
* Indice `ix_listini_versioni_listino_valido_dal` → valutare sostituzione con indice GiST su `validita`

**`vendite.listini_associazioni`** (#2)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync
* Ricreare vincolo automazione_overlap sulla colonna nativa
* **Funzioni da aggiornare**:
  - `vendite.fn_resolve_prezzo_listino` — CTE `associazioni_candidate`: stesso pattern
* Aggiornare record in `dbops.automazione_overlap` per puntare alla colonna `validita`

**`catalogo.unita_misura_conversioni`** (#3)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync
* Ricreare `ex_uom_conv_no_overlap` sulla colonna nativa
* **Funzioni da aggiornare**: eventuali query di risoluzione UoM

**`vendite.contratti`** (#4)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync
* Ricreare vincolo automazione_overlap sulla colonna nativa
* Nessuna funzione applicativa da aggiornare (DB only)

**`catalogo.articoli_componenti`** (#5)

* Aggiungere colonna `validita daterange NOT NULL`
* Trigger sync
* Ricreare vincolo automazione_overlap sulla colonna nativa

#### Gruppo 2 — Tabelle con solo CHECK (priorita` MEDIA)

Queste non hanno GIST ma beneficiano comunque degli operatori nativi nelle query.

**Tabelle config (permessi)**: `user_override_aree` (#14), `user_override_oggetti` (#15), `user_override_azioni` (#16)

* Aggiungere colonna `validita daterange`
* Trigger sync
* Le funzioni di risoluzione permessi (`script.fn_risolvi_permesso_*`) possono usare `@>` invece dei doppi confronti
* CHECK constraint sulle date puo` essere sostituito dal range type (range invalido = errore nativo)

**Tabelle config (lookup)**: `utilities_tipi_ruolo` (#10), `tipi_ruoli_nature_ammesse` (#11), `ruoli_tipi_indirizzo` (#12), `tipi_soggetto_dettaglio_tipi_indirizzo` (#13)

* Aggiungere colonna `validita daterange`
* Trigger sync
* Le query lookup in `lookup_repository.py` usano il pattern `(valido_dal IS NULL OR valido_dal <= CURRENT_DATE) AND (valido_al IS NULL OR valido_al >= CURRENT_DATE)` → sostituibile con `validita @> CURRENT_DATE` ma questo va fatto nel backend (vedi §4)

**Tabelle anagrafiche**: `billing_account` (#7), `risorse_umane` (#8), `resellers_billing_account` (#9)

* Aggiungere colonna `validita daterange`
* Trigger sync

**Tabelle catalogo**: `articoli_uom_operativa` (#6)

* Aggiungere colonna `validita daterange`
* Trigger sync

**Tabelle anagrafiche (form)**: conti bancari (#17), matrice indirizzi (#18), operatori (#19)

* Aggiungere colonna `validita daterange`
* Trigger sync

#### Gruppo 3 — Tabelle con TIMESTAMP → `tstzrange` (priorita` BASSA)

**`pratiche.sospensioni`** (#20), **`pratiche.calcoli_tempo`** (#21)

* Tipo diverso: `tstzrange` invece di `daterange`
* Stessa logica: aggiungere colonna range, trigger sync, aggiornare vincoli
* Da valutare separatamente perche` la semantica timestamp e` diversa (istanti vs giorni)

### 3.4 Aggiornamento infrastruttura `dbops.automazione_overlap`

La funzione `dbops.fn_apply_automazione_overlap` costruisce vincoli GIST usando:

```sql
daterange(%I, COALESCE(%I, 'infinity'::date), %L) WITH &&
```

Dopo la migrazione, per le tabelle migrate dovra` puntare direttamente alla colonna `validita`:

* Aggiungere colonna `range_col` alla tabella `dbops.automazione_overlap` (nome colonna daterange nativa, default NULL)
* Se `range_col IS NOT NULL` → usare `%I WITH &&` diretto
* Se `range_col IS NULL` → mantenere il comportamento attuale (retrocompatibile per tabelle non ancora migrate)

### 3.5 Naming convention colonna range

| Dominio | Nome colonna suggerito | Bounds |
|---|---|---|
| Validita` generica | `validita` | `[]` (inclusivo) o `[)` (da valutare per coerenza) |
| Pratiche (timestamp) | `periodo_sospensione` / `periodo_calcolo` | `[)` |

**Decisione aperta**: scegliere bounds `[]` (inclusivo-inclusivo, come oggi con `valido_al` incluso) oppure `[)` (inclusivo-esclusivo, come il modello `clienti.periodo`). Il `[)` e` lo standard PostgreSQL per i range e semplifica i calcoli di adiacenza (`upper(r1) = lower(r2)` senza -1 giorno).

---

## 4) Analisi di impatto — Modifiche Backend e Frontend

Questa sezione descrive le modifiche necessarie **solo per le tabelle che hanno codice applicativo sviluppato**.
Le tabelle DB only non richiedono interventi in questa sezione.

### 4.1 Approccio generale

Con l'approccio A (mantenere colonne separate + colonna range calcolata dal trigger):

* **L'API non cambia**: il frontend continua a inviare `valido_dal` e `valido_al` come campi separati
* **Il trigger DB** si occupa di popolare la colonna `validita`
* **Le query backend** che filtrano per data possono essere semplificate usando `validita @> data`
* **Le SELECT** che restituiscono `valido_dal` / `valido_al` continuano a funzionare (le colonne restano)

Con l'approccio B (solo colonna range):

* **L'API cambia**: il payload diventa `validita: {dal: "...", al: "..."}` oppure il backend converte
* **Il frontend** deve adattare form e display
* **Le query** usano direttamente la colonna range

### 4.2 Impatto per tabella con stack FULL

#### `vendite.listini_versioni` (#1) + `vendite.listini_associazioni` (#2)

**Backend** (approccio A — impatto BASSO):

| File | Modifica |
|---|---|
| `apps/vendite/db/listini_repository.py` | Query SELECT: nessuna modifica (le colonne restano). Query di filtro per data in eventuali list/search: sostituire doppio confronto con `validita @> %(data)s` |
| `apps/vendite/services/listini_service.py` | Validazione payload `valido_dal` / `valido_al`: nessuna modifica (il trigger gestisce il range). `fn_change_versione_state` con auto-close D3: il PATCH su `valido_al` resta invariato |
| `apps/vendite/api/views_listini.py` | Serializer: nessuna modifica (campi restano `valido_dal`, `valido_al`) |

**Frontend** (approccio A — impatto ZERO):

Nessuna modifica. I componenti continuano a usare `valido_dal` / `valido_al` come campi form.

#### `catalogo.unita_misura_conversioni` (#3) + `catalogo.articoli_componenti` (#5) + `catalogo.articoli_uom_operativa` (#6)

**Backend** (approccio A — impatto BASSO):

| File | Modifica |
|---|---|
| `apps/catalogo/db/catalogo_repository.py` | Query di filtro per data: sostituire con `@>` dove presente |
| `apps/catalogo/api/views.py` | Serializer: nessuna modifica |

**Frontend** (approccio A — impatto ZERO):

Nessuna modifica per ArticoloUomDrawer, ArticoloBomDrawer, UomConversioniDrawer.

#### Conti bancari (#17)

**Backend** (approccio A — impatto BASSO):

| File | Modifica |
|---|---|
| `apps/anagrafiche/db/conti_bancari_repository.py` | Query filtro: eventuale uso `@>` |
| `apps/anagrafiche/api/views_conti_bancari.py` | Nessuna modifica serializer |
| `apps/anagrafiche/services/conti_bancari_service.py` | Nessuna modifica |

**Frontend** (approccio A — impatto ZERO):

`ContoBancarioForm.vue` e `useContoBancarioForm.js`: nessuna modifica.

#### Matrice indirizzi (#18)

**Backend** (approccio A — impatto BASSO):

| File | Modifica |
|---|---|
| `apps/anagrafiche/db/matrice_indirizzi_repository.py` | SELECT con valido_dal, valido_al: nessuna modifica. Filtro attivi per data: eventuale `@>` |
| `apps/anagrafiche/services/matrice_indirizzi_service.py` | Logica "valido_dal = oggi": nessuna modifica (il trigger sync la colonna range) |

**Frontend** (approccio A — impatto ZERO):

`MatriceIndirizziDrawer.vue`, `MatriceIndirizziSearchTable.vue`: nessuna modifica.

#### Operatori (#19)

**Backend** (approccio A — impatto BASSO):

| File | Modifica |
|---|---|
| `apps/amm_software/db/amm_software_repository.py` | Logica disattivazione `valido_al = CURRENT_DATE` e riattivazione `valido_dal = CURRENT_DATE`: nessuna modifica (il trigger sync) |
| `apps/amm_software/services/amm_software_service.py` | Nessuna modifica |

**Frontend** (approccio A — impatto ZERO):

`OperatoriListView.vue`: nessuna modifica.

### 4.3 Impatto per tabelle con stack DB + BE (no frontend)

#### Lookup config (#10, #11, #14, #15, #16)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/core/db/lookup_repository.py` | Metodi `list_tipi_ruoli_per_natura()`, `list_utilities_per_ruolo()`, `list_utilities_per_emittente()`: sostituire `(m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE) AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)` con `(m.validita IS NULL OR m.validita @> CURRENT_DATE)` |
| Funzioni permessi (`script.fn_risolvi_permesso_*`) | Stesso pattern di semplificazione sui filtri temporali — questo e` nel DB, non nel backend Python |

#### Pratiche (#20, #21)

**Backend** (impatto BASSO):

| File | Modifica |
|---|---|
| `apps/pratiche/services/pratiche_service.py` | Chiusura sospensione `data_fine = NOW()`: nessuna modifica (trigger sync) |
| `apps/pratiche/types.py` | TypedDict: nessuna modifica (campi restano per serializzazione) |

---

## 5) Piano di esecuzione proposto

### Fase 1 — Infrastruttura (prerequisito)

1. Decidere bounds standard: `[]` o `[)` (vedi §3.5)
2. Aggiornare `dbops.automazione_overlap` con supporto colonna range nativa (§3.4)
3. Definire template trigger sync (basato su `trgfn_clienti_set_periodo`)

### Fase 2 — Tabelle con GIST esistente (massimo beneficio)

4. `vendite.listini_versioni` — DDL + trigger + ricreazione GIST + aggiornamento `fn_resolve_prezzo_listino`
5. `vendite.listini_associazioni` — DDL + trigger + ricreazione GIST + aggiornamento `fn_resolve_prezzo_listino`
6. `catalogo.unita_misura_conversioni` — DDL + trigger + ricreazione GIST
7. `vendite.contratti` — DDL + trigger + ricreazione GIST
8. `catalogo.articoli_componenti` — DDL + trigger + ricreazione GIST
9. Aggiornamento backend listini (query `@>`) + test

### Fase 3 — Tabelle config/anagrafiche (beneficio query)

10. Tabelle config permessi (#14-#16) — DDL + trigger + aggiornamento funzioni permessi
11. Tabelle config lookup (#10-#13) — DDL + trigger + aggiornamento `lookup_repository.py`
12. Tabelle anagrafiche (#6-#9, #17-#19) — DDL + trigger
13. Aggiornamento backend lookup e permessi + test

### Fase 4 — Tabelle pratiche con timestamp (separato)

14. `pratiche.sospensioni` — DDL `tstzrange` + trigger
15. `pratiche.calcoli_tempo` — DDL `tstzrange` + trigger
16. Aggiornamento backend pratiche + test

---

## 6) Decisioni aperte

| # | Domanda | Opzioni | Stato |
|---|---|---|---|
| D1 | Bounds standard per i range | `[]` inclusivo-inclusivo (coerente con oggi) vs `[)` inclusivo-esclusivo (standard PG, coerente con `clienti.periodo`) | DA DECIDERE |
| D2 | Approccio A o B per tabelle con stack FULL | A = mantieni colonne + range calcolato (minimo impatto) vs B = solo range (modello pulito) | DA DECIDERE |
| D3 | Nome colonna range | `validita` generico vs nome specifico per dominio | DA DECIDERE |
| D4 | Drop colonne originali in futuro? | Si` (fase successiva dopo stabilizzazione) vs No (mantieni per retrocompatibilita`) | DA DECIDERE |
| D5 | Tabelle pratiche: `daterange` o `tstzrange`? | Le colonne sono TIMESTAMPTZ → `tstzrange` naturale, ma se la granularita` e` giornaliera `daterange` basta | DA DECIDERE |

---

*Migrazione daterange — ZeroERP (aprile 2026, WIP analisi di impatto)*
