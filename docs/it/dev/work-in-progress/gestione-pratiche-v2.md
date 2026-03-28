# Gestione Pratiche v2 — Piano di completamento

> **Stato**: Pianificazione
> **Prerequisiti**: Pratiche v1 (DB+BE completi, FE stub)
> **Approccio**: refactor diretto, nessuna retrocompatibilita', nessuna produzione attiva
>
> Questo documento completa il modulo pratiche. I documenti v1
> (`sviluppo-gestione-pratiche.md`, `piano-gestione-pratiche.md`) sono spostati in work-done
> come riferimento storico.

---

## Recap stato v1

| Area | Stato | Gap |
|------|-------|-----|
| DB Schema | 20 migrazioni, 15+ tabelle | Manca collegamento ruolo/istanza, codice prefisso |
| DB Trigger/Funzioni | 34 migrazioni, tutte operative | OK |
| Backend Repository | 2 file | list/get ritornano solo ID, mancano JOIN display |
| Backend Service | 31 metodi | Manca guard pre/post-attivazione |
| Backend API | 20 view, 19 endpoint | Dati incompleti per la UI |
| Backend Test | 94 test OK | Coprono logica, non display fields |
| Frontend | Store + SearchTable + Drawer + Flussi + Giornale | Non funzionante: mancano dati display dal backend |

---

## Gap da colmare (ordine di sviluppo)

### Priorita' ALTA — Senza questi il frontend non funziona

| # | Area | Descrizione |
|---|------|-------------|
| **G1** | DB | Aggiungere `soggetto_ruolo_id` e `istanza_utility_id` a `pratiche.pratiche` |
| **G2** | DB | Repository: JOIN display fields su list/get (soggetto, stato, priorita', tipo, risorsa, UO) |
| **G3** | BE | Aggiornare `PraticaRow` TypedDict con nuovi campi display |
| **G4** | BE | Aggiornare `crea_pratica` per accettare soggetto_ruolo_id e istanza_utility_id |
| **G5** | BE | Guard pre/post-attivazione nel service (verifica BA del soggetto) |
| **G6** | FE | Aggiornare store/drawer/searchTable per i nuovi campi |

### Priorita' MEDIA — Funzionalita' di dominio

| # | Area | Descrizione |
|---|------|-------------|
| **G7** | DB | Codice pratica con prefisso dominio (CLI/SOG/FOR/INT) |
| **G8** | DB+BE | Note pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) |
| **G9** | DB+BE | Allegati pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) |
| **G10** | FE | Tab Note nel drawer pratica |
| **G11** | FE | Tab Allegati nel drawer pratica |

### Priorita' BASSA — Automazioni e estensioni

| # | Area | Descrizione |
|---|------|-------------|
| **G12** | BE | pgAgent job riattivazione automatica sospensioni |
| **G13** | BE | SLA alert (WARNING/CRITICO da calcoli_tempo) |
| **G14** | DB | Tabelle estensione ext_* (Anello 3, quando servono) |
| **G15** | BE | Handler concreti nel registry (quando i domini li usano) |

---

## Fase 1 — DB: Collegamento anagrafico + display fields

### 1.1 ALTER pratiche.pratiche — nuovi campi opzionali

**Migration**: `00_schema/pratiche/YYYYMMDD-NN-alter-pratiche-add-ruolo-istanza-mctit.yaml`

```sql
ALTER TABLE pratiche.pratiche
  ADD COLUMN soggetto_ruolo_id BIGINT
    REFERENCES anagrafiche.soggetti_ruoli(id),
  ADD COLUMN istanza_utility_id BIGINT
    REFERENCES anagrafiche.istanze_dati_precontrattuali(istanza_utility_id);

COMMENT ON COLUMN pratiche.pratiche.soggetto_ruolo_id IS
  'FK opzionale a soggetti_ruoli — quando la pratica e'' nel contesto di un ruolo (cliente, fornitore)';
COMMENT ON COLUMN pratiche.pratiche.istanza_utility_id IS
  'FK opzionale a istanze_dati_precontrattuali — quando la pratica e'' nel contesto di una istanza/utility';
```

**Vincoli logici** (non FK constraint ma validazione service):

- `istanza_utility_id` richiede `soggetto_ruolo_id` (non puo' avere istanza senza ruolo)
- `soggetto_ruolo_id` richiede `soggetto_id` (il ruolo deve appartenere al soggetto)
- Tutti e tre opzionali (pratica interna: tutti NULL)

**Catena collegamento**:

```text
pratiche.pratiche
  └── soggetto_id (UUID)              → anagrafiche.soggetti
  └── soggetto_ruolo_id (BIGINT)      → anagrafiche.soggetti_ruoli
  └── istanza_utility_id (BIGINT)     → anagrafiche.istanze_dati_precontrattuali
                                            └── → billing_account → utility
```

### 1.2 Funzione DB helper: fn_resolve_contesto_pratica

**Migration**: `20_code/pratiche/YYYYMMDD-NN-create-fn-resolve-contesto-pratica-mctit.yaml`

Funzione utile per il prefisso codice e per validazione:

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_resolve_contesto_pratica(
  p_soggetto_id UUID,
  p_soggetto_ruolo_id BIGINT,
  p_emittente_fiscale_id BIGINT
) RETURNS TEXT AS $$
-- Ritorna il contesto: 'INT', 'SOG', 'CLI', 'FOR'
-- Basato su: soggetto NULL → INT, ruolo cliente attivo → CLI, ruolo fornitore → FOR, else → SOG
$$;
```

Questa funzione:

- Centralizza la logica "che tipo di pratica e'?" nel DB
- Usata dal trigger codice (G7) e dal service per validazione
- Evita duplicazione della logica in Python

### 1.3 Trigger codice pratica con prefisso dominio (G7)

**Migration**: `20_code/pratiche/YYYYMMDD-NN-create-trgfn-pratiche-codice-prefisso-mctit.yaml`

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_codice_prefisso()
RETURNS TRIGGER AS $$
-- BEFORE INSERT: genera codice con prefisso
-- Usa fn_resolve_contesto_pratica per il prefisso
-- Formato: <PREFISSO>-<ANNO>-<SEQUENZA 6 cifre>
-- Sequenza per (prefisso, anno, emittente_fiscale_id)
$$;
```

**Richiede**: tabella sequenze per contatore (o usa `config.sistema_codici` esistente).

### 1.4 Trigger guard coerenza soggetto-ruolo-istanza

**Migration**: `20_code/pratiche/YYYYMMDD-NN-create-trgfn-pratiche-guard-contesto-mctit.yaml`

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
RETURNS TRIGGER AS $$
-- BEFORE INSERT/UPDATE:
-- Se istanza_utility_id NOT NULL → soggetto_ruolo_id deve essere NOT NULL
-- Se soggetto_ruolo_id NOT NULL → soggetto_id deve essere NOT NULL
-- Se soggetto_ruolo_id NOT NULL → deve appartenere a soggetto_id
$$;
```

---

## Fase 2 — Backend: Repository con JOIN display + nuovi campi

### 2.1 Aggiornare PraticaRow TypedDict

**File**: `backend/apps/pratiche/types.py`

Aggiungere campi display:

```python
class PraticaRow(TypedDict):
    # Campi esistenti...
    id: int
    emittente_fiscale_id: int
    tipo_prestazione_id: int
    soggetto_id: str | None
    soggetto_ruolo_id: int | None        # NUOVO
    istanza_utility_id: int | None        # NUOVO
    stato_id: int
    priorita_id: int
    # ... altri campi esistenti ...

    # Campi display da JOIN (NUOVI)
    tipo_prestazione_codice: str
    tipo_prestazione_descrizione: str
    stato_codice_interno: str
    stato_descrizione: str
    priorita_codice_interno: str
    priorita_descrizione: str
    soggetto_display: str | None          # ragione_sociale_completa
    risorsa_umana_display: str | None     # nome + cognome
    unita_organizzativa_descrizione: str | None
    utility_codice: str | None            # dalla catena istanza → BA → utility
```

### 2.2 Riscrivere SQL list_pratiche e get_pratica

**File**: `backend/apps/pratiche/db/pratiche_repository.py`

Il SELECT deve fare JOIN su:

```sql
SELECT
    p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
    p.soggetto_id, p.soggetto_ruolo_id, p.istanza_utility_id,
    p.stato_id, p.priorita_id,
    p.risorsa_umana_id, p.unita_organizzativa_id,
    p.pratica_padre_id, p.flusso_origine_id, p.canale_origine_id,
    p.codice, p.descrizione, p.data_scadenza,
    p.meta, p.data_insert, p.user_insert,
    -- Display fields
    tp.codice AS tipo_prestazione_codice,
    tp.descrizione AS tipo_prestazione_descrizione,
    sp.codice_interno AS stato_codice_interno,
    sp.descrizione AS stato_descrizione,
    pp.codice_interno AS priorita_codice_interno,
    pp.descrizione AS priorita_descrizione,
    s.ragione_sociale_completa AS soggetto_display,
    CONCAT_WS(' ', ru.nome, ru.cognome) AS risorsa_umana_display,
    uo.descrizione AS unita_organizzativa_descrizione
FROM pratiche.pratiche p
JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
JOIN config.stati_pratiche sp ON sp.id = p.stato_id
JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
LEFT JOIN anagrafiche.soggetti s ON s.id = p.soggetto_id
LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = p.risorsa_umana_id
LEFT JOIN config.unita_organizzative uo ON uo.id = p.unita_organizzativa_id
```

**Stessa cosa per list_flussi**: aggiungere JOIN a `config.stati_flussi_pratiche`, `pratiche.template_flussi`.

### 2.3 Aggiornare _map_pratica_row

Riscrivere il mapping con **named columns** (cursor.description) invece di indici posizionali.

Pattern suggerito:

```python
@staticmethod
def _map_row(cursor, row) -> dict:
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))
```

Questo elimina la fragilita' degli indici posizionali e rende il codice resistente a modifiche dello schema.

### 2.4 Aggiornare crea_pratica nel service

**File**: `backend/apps/pratiche/services/pratiche_service.py`

Aggiungere parametri e validazione:

```python
def crea_pratica(
    *,
    emittente_fiscale_id: int,
    tipo_prestazione_id: int,
    soggetto_id: str | None = None,
    soggetto_ruolo_id: int | None = None,      # NUOVO
    istanza_utility_id: int | None = None,      # NUOVO
    priorita_id: int,
    # ... altri ...
) -> int:
    # Validazione coerenza contesto
    if istanza_utility_id is not None and soggetto_ruolo_id is None:
        raise ServiceError("istanza_utility_id richiede soggetto_ruolo_id")
    if soggetto_ruolo_id is not None and soggetto_id is None:
        raise ServiceError("soggetto_ruolo_id richiede soggetto_id")
    # ... guard pre/post-attivazione (G5) ...
```

### 2.5 Guard pre/post-attivazione (G5)

Nel service, prima dell'INSERT:

```python
# Leggi pre_attivazione e post_attivazione dal tipo_prestazione
tipo = repo.get_tipo_prestazione(tipo_prestazione_id)

if tipo['pre_attivazione'] or tipo['post_attivazione']:
    # Verifica stato BA del soggetto per l'emittente
    ba = anag_repo.get_billing_account_attivo(soggetto_id, emittente_fiscale_id)
    ha_ba_attivo = ba is not None and ba['data_attivazione'] is not None

    if tipo['pre_attivazione'] and ha_ba_attivo:
        raise ServiceError("Tipo prestazione ammesso solo PRE-attivazione")
    if tipo['post_attivazione'] and not ha_ba_attivo:
        raise ServiceError("Tipo prestazione ammesso solo POST-attivazione")
```

---

## Fase 3 — Backend: Note e Allegati CRUD

### 3.1 Repository metodi note

**File**: `backend/apps/pratiche/db/pratiche_repository.py` (estensione)

```python
# Note pratiche
list_note_pratica(pratica_id) -> list[dict]
create_nota_pratica(pratica_id, tipo_nota_codice, testo) -> int
update_nota_pratica(nota_id, pratica_id, testo) -> bool
delete_nota_pratica(nota_id, pratica_id) -> bool

# Note flussi
list_note_flusso(pratica_id, flusso_id) -> list[dict]
create_nota_flusso(flusso_id, pratica_id, tipo_nota_codice, testo) -> int
```

### 3.2 API endpoint note

| Metodo | URL | Descrizione |
|--------|-----|-------------|
| GET | `/pratiche/{id}/note/` | Lista note pratica |
| POST | `/pratiche/{id}/note/` | Crea nota |
| PATCH | `/pratiche/{id}/note/{nota_id}/` | Aggiorna nota |
| DELETE | `/pratiche/{id}/note/{nota_id}/` | Elimina nota |

### 3.3 Allegati (stessa struttura)

Stesso pattern CRUD per allegati. Upload file da gestire con storage (filesystem o object storage).
Questo e' un sottoprogetto a se' — per ora API CRUD sul record DB, upload file posticipato.

---

## Fase 4 — Frontend: aggiornamento completo

### 4.1 Store pratiche

- Aggiornare `create()` per passare `soggetto_id`, `soggetto_ruolo_id`, `istanza_utility_id`
- I campi display (`stato_descrizione`, `soggetto_display`, ecc.) ora arrivano dal backend

### 4.2 PraticheSearchTable

- Rimuovere lookup client-side per stato/priorita' nelle colonne (ora arrivano dal backend)
- I filtri Select continuano a usare lookup (servono per popolare le opzioni)

### 4.3 PraticaDrawer — Creazione

Aggiungere sezione selezione soggetto:

1. **Senza soggetto** (pratica interna) — toggle o checkbox
2. **Con soggetto** — AutoComplete server-side (pattern SoggettoResolver)
3. **Con ruolo** — dopo selezione soggetto, mostra i ruoli attivi (Select)
4. **Con istanza** — dopo selezione ruolo cliente, mostra le istanze/utility (Select)

Il form si adatta dinamicamente: soggetto → ruolo → istanza (cascata).

### 4.4 PraticaDrawer — Dettaglio edit

- Mostrare soggetto, ruolo, istanza/utility come campi readonly nell'header
- Usare i campi display dal backend (niente lookup client-side per i dati gia' presenti)

### 4.5 Tab Note (G10)

Componente `PraticaNoteTab.vue`:

- Lista note con tipo, testo, data, utente
- Form inline per nuova nota (Select tipo + Textarea)
- Edit/delete su note esistenti

### 4.6 Tab Allegati (G11)

Componente `PraticaAllegatiTab.vue` — v1 senza upload file:

- Lista allegati con tipo, nome, data, utente
- In futuro: upload file + download

---

## Fase 5 — Test e smoke test

### 5.1 Aggiornare test Django

- Aggiornare test `crea_pratica` per i nuovi campi (soggetto_ruolo_id, istanza_utility_id)
- Aggiungere test guard pre/post-attivazione
- Aggiungere test coerenza contesto (istanza senza ruolo → errore)
- Aggiornare test API per verificare che la risposta contenga campi display

### 5.2 Aggiornare smoke test

- `smoke-test-pratiche.sh`: verificare che GET lista/dettaglio ritornino campi display
- Aggiungere test creazione pratica con soggetto + ruolo
- Aggiungere test note CRUD

---

## Ordine di esecuzione

```text
Fase 1 (DB)
  1.4 Guard contesto ──> 1.1 ALTER pratiche ──> 1.2 fn_resolve_contesto ──> 1.3 Codice prefisso
                                │
                                v
Fase 2 (Backend)
  2.1 TypedDict ──> 2.2 SQL JOIN ──> 2.3 _map_row ──> 2.4 crea_pratica ──> 2.5 Guard attivazione
                                                                               │
                                                                               v
Fase 3 (Backend)
  3.1 Repo note ──> 3.2 API note ──> 3.3 Allegati (record DB, no upload)
                                                    │
                                                    v
Fase 4 (Frontend)
  4.1 Store ──> 4.2 SearchTable ──> 4.3 Drawer crea ──> 4.4 Drawer edit ──> 4.5 Note ──> 4.6 Allegati
                                                                                           │
                                                                                           v
Fase 5 (Test)
  5.1 Test Django ──> 5.2 Smoke test
```

**Stima**: le fasi sono sequenziali ma ogni fase e' piccola (1-2 sessioni di lavoro).

---

## Funzioni DB utili (esistenti e nuove)

### Esistenti da sfruttare

| Funzione | Schema | Uso |
|----------|--------|-----|
| `dbops.fn_run_automations()` | dbops | Trigger standard (audit, tx_id, storico, lock) — applicati automaticamente |
| `dbops.fn_gen_codice()` | dbops | Generazione codici con sequenza — da usare per il prefisso pratica |
| `config.fn_get_lookup_codici()` | config | Lookup generiche — gia' usate dal frontend |
| `pratiche.fn_check_prerequisiti_flusso()` | pratiche | Verifica prerequisiti flusso |
| `pratiche.fn_genera_pratica_da_flusso()` | pratiche | Generazione cross-pratica |
| `pratiche.fn_calcola_tempo_netto_da_a()` | pratiche | Calcolo tempo netto tra flussi |

### Nuove da creare

| Funzione | Schema | Scopo |
|----------|--------|-------|
| `pratiche.fn_resolve_contesto_pratica()` | pratiche | Ritorna 'INT'/'SOG'/'CLI'/'FOR' dato soggetto + ruolo |
| `pratiche.trgfn_pratiche_codice_prefisso()` | pratiche | Trigger BEFORE INSERT: genera codice con prefisso dominio |
| `pratiche.trgfn_pratiche_guard_contesto()` | pratiche | Trigger BEFORE INSERT/UPDATE: coerenza soggetto-ruolo-istanza |

---

## Decisioni prese

1. **Refactor diretto**: nessuna retrocompatibilita' con v1 — il modulo non e' in produzione
2. **Collegamento a 3 livelli**: soggetto_id + soggetto_ruolo_id + istanza_utility_id sulla tabella pratiche
3. **Display fields via JOIN**: il backend ritorna dati pronti per la UI, il frontend non fa lookup per dati gia' in lista
4. **Named columns nel mapping**: basta indici posizionali, si usa `cursor.description`
5. **Guard pre/post-attivazione nel service**: logica cross-schema non adatta a trigger DB
6. **Codice prefisso dal trigger DB**: usa `fn_resolve_contesto_pratica` + `fn_gen_codice`

---

*Piano di completamento — Gestione Pratiche v2 — ZeroERP (28 marzo 2026)*
