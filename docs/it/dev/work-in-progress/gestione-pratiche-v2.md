# Gestione Pratiche v2 — Piano di completamento

> **Stato**: In corso (DB completato, BE/FE da fare)
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
| DB Schema | 20 migrazioni, 15+ tabelle | Manca collegamento ruolo/istanza |
| DB Trigger/Funzioni | 34 migrazioni, tutte operative | OK |
| Backend Repository | 2 file | list/get ritornano solo ID, mancano JOIN display |
| Backend Service | 31 metodi | Manca guard pre/post-attivazione |
| Backend API | 20 view, 19 endpoint | Dati incompleti per la UI |
| Backend Test | 94 test OK | Coprono logica, non display fields |
| Frontend | Store + SearchTable + Drawer + Flussi + Giornale | Non funzionante: mancano dati display dal backend |

---

## Gap da colmare (ordine di sviluppo)

### Priorita' ALTA — Senza questi il frontend non funziona

| # | Area | Descrizione | Stato |
|---|------|-------------|-------|
| **G1** | DB | Aggiungere `soggetto_ruolo_id` e `istanza_utility_id` a `pratiche.pratiche` | ✅ |
| **G2** | DB | Trigger guard coerenza soggetto-ruolo-istanza | ✅ |
| **G3** | DB | Codice pratica via `config.sistema_codici` (prefisso fisso standard) | ✅ |
| **G4** | BE | Aggiornare `PraticaRow` TypedDict con nuovi campi display | da fare |
| **G5** | BE | Repository: JOIN display fields su list/get | da fare |
| **G6** | BE | Aggiornare `crea_pratica` per accettare soggetto_ruolo_id e istanza_utility_id | da fare |
| **G7** | BE | Guard pre/post-attivazione nel service | da fare |
| **G8** | FE | Aggiornare store/drawer/searchTable per i nuovi campi | da fare |

### Priorita' MEDIA — Funzionalita' di dominio

| # | Area | Descrizione | Stato |
|---|------|-------------|-------|
| **G9** | DB | Note pratiche/flussi — tabelle esistono, trigger giornale gia' operativi | ✅ (gia' in v1) |
| **G10** | DB | Allegati pratiche/flussi — tabelle esistono, trigger giornale gia' operativi | ✅ (gia' in v1) |
| **G11** | BE | Note pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) | da fare |
| **G12** | BE | Allegati pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) | da fare |
| **G13** | FE | Tab Note nel drawer pratica | da fare |
| **G14** | FE | Tab Allegati nel drawer pratica | da fare |

### Priorita' BASSA — Automazioni e estensioni

| # | Area | Descrizione | Stato |
|---|------|-------------|-------|
| **G15** | BE | pgAgent job riattivazione automatica sospensioni | da fare |
| **G16** | BE | SLA alert (WARNING/CRITICO da calcoli_tempo) | da fare |
| **G17** | DB | Tabelle estensione ext_* (Anello 3, quando servono) | futuro |
| **G18** | BE | Handler concreti nel registry (quando i domini li usano) | futuro |

---

## Fase 1 — DB: Collegamento anagrafico + codice (✅ COMPLETATA)

### 1.1 ALTER pratiche.pratiche — nuovi campi opzionali

**Migration**: `00_schema/pratiche/20260328-11-alter-pratiche-add-ruolo-istanza-mctit.yaml` ✅

```sql
-- Collegamento opzionale al ruolo anagrafico del soggetto
ALTER TABLE pratiche.pratiche
  ADD COLUMN soggetto_ruolo_id BIGINT
    REFERENCES anagrafiche.soggetti_ruoli(id);

-- Collegamento opzionale alla istanza/utility del soggetto
ALTER TABLE pratiche.pratiche
  ADD COLUMN istanza_utility_id BIGINT
    REFERENCES anagrafiche.istanze_utilities(id);

COMMENT ON COLUMN pratiche.pratiche.soggetto_ruolo_id IS
  'FK opzionale a soggetti_ruoli — quando la pratica e'' nel contesto di un ruolo (cliente, fornitore)';
COMMENT ON COLUMN pratiche.pratiche.istanza_utility_id IS
  'FK opzionale a istanze_utilities — quando la pratica e'' nel contesto di una istanza/utility';
```

> **NOTA**: la FK di `istanza_utility_id` punta a `anagrafiche.istanze_utilities(id)`,
> NON a `istanze_dati_precontrattuali` (quella e' una tabella figlia con dati specifici
> di pre-contratto, non la tabella master delle istanze).

**Vincoli logici** (validati dal trigger guard §1.2):

- `istanza_utility_id` richiede `soggetto_ruolo_id` (non puo' avere istanza senza ruolo)
- `soggetto_ruolo_id` richiede `soggetto_id` (il ruolo deve appartenere al soggetto)
- Tutti opzionali (pratica interna: tutti NULL)

**Catena collegamento**:

```text
pratiche.pratiche
  └── soggetto_id (UUID)              → anagrafiche.soggetti
  └── soggetto_ruolo_id (BIGINT)      → anagrafiche.soggetti_ruoli
  └── istanza_utility_id (BIGINT)     → anagrafiche.istanze_utilities
                                            └── → billing_account → utility
```

### 1.2 Trigger guard coerenza soggetto-ruolo-istanza

**Migration**: `20_code/pratiche/20260328-12-create-trgfn-pratiche-guard-contesto-mctit.yaml` ✅

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
RETURNS trigger
LANGUAGE plpgsql AS $$
-- Scopo: validare la coerenza gerarchica del contesto anagrafico
--        sulla pratica: soggetto → ruolo → istanza.
-- Regole:
--   1. istanza_utility_id NOT NULL → soggetto_ruolo_id obbligatorio
--   2. soggetto_ruolo_id NOT NULL → soggetto_id obbligatorio
--   3. soggetto_ruolo_id deve appartenere a soggetto_id
--   4. istanza_utility_id deve appartenere al soggetto_id
DECLARE
    v_soggetto_id_ruolo  anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_soggetto_id_istanza anagrafiche.istanze_utilities.soggetto_id%TYPE;
BEGIN
    -- ... (4 regole con fn_log_and_raise_error)
    RETURN NEW;
END;
$$;

-- Trigger BEFORE INSERT/UPDATE OF soggetto_id, soggetto_ruolo_id, istanza_utility_id
CREATE TRIGGER trg_pratiche_a10_guard_contesto_ins_upd
  BEFORE INSERT OR UPDATE OF soggetto_id, soggetto_ruolo_id, istanza_utility_id
  ON pratiche.pratiche
  FOR EACH ROW
  EXECUTE FUNCTION pratiche.trgfn_pratiche_guard_contesto();
```

**Messaggi errore** (aggiunti in `config.messaggi_errore.csv`):

| Codice | ID | Messaggio |
|--------|----|-----------|
| `PRATICHE_ISTANZA_SENZA_RUOLO` | 304 | istanza_utility_id richiede soggetto_ruolo_id |
| `PRATICHE_RUOLO_SENZA_SOGGETTO` | 305 | soggetto_ruolo_id richiede soggetto_id |
| `PRATICHE_RUOLO_NON_COERENTE` | 306 | Il ruolo %s non appartiene al soggetto %s |
| `PRATICHE_ISTANZA_NON_COERENTE` | 307 | L'istanza %s non appartiene al soggetto %s |

> **Nota**: la validazione nel trigger DB e' la linea di difesa ultima.
> Il service Python puo' fare le stesse verifiche per dare errori user-friendly,
> ma il DB garantisce l'integrita' anche per accessi diretti.

### 1.3 Codice pratica — sistema standard

Il codice pratica usa il meccanismo centralizzato `config.sistema_codici` +
`script.fn_generate_codice()`, con prefisso fisso `PRA`.

**Azione**: aggiunta riga in `80_data/sql/config/sistema_codici.csv` (id=16) ✅

Il trigger `trg_sistema_codici_z90_sync_gen_codice_ins_upd_dlt` crea automaticamente:

- Sequenza `pratiche.pratiche_codice_seq`
- Trigger function `pratiche.trgfn_pratiche_gen_codice()`
- Trigger `trg_pratiche_a10_gen_codice_ins_upd`

Formato generato: `PRA-0000001`, `PRA-0000002`, ecc.

> **Scelta progettuale**: per ora prefisso fisso `PRA`. Se in futuro servira'
> un prefisso dinamico (CLI/SOG/FOR/INT basato sul contesto anagrafico),
> si creera' un trigger dedicato `trgfn_pratiche_codice_prefisso()` con la
> logica di risoluzione contesto. Questo NON e' necessario nella v2.

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
    # Validazione coerenza contesto (stesse regole del trigger DB,
    # ma qui per dare errori user-friendly via ServiceError)
    if istanza_utility_id is not None and soggetto_ruolo_id is None:
        raise ServiceError("istanza_utility_id richiede soggetto_ruolo_id")
    if soggetto_ruolo_id is not None and soggetto_id is None:
        raise ServiceError("soggetto_ruolo_id richiede soggetto_id")
    # ... guard pre/post-attivazione (G7) ...
```

### 2.5 Guard pre/post-attivazione (G7)

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

### 4.5 Tab Note (G13)

Componente `PraticaNoteTab.vue`:

- Lista note con tipo, testo, data, utente
- Form inline per nuova nota (Select tipo + Textarea)
- Edit/delete su note esistenti

### 4.6 Tab Allegati (G14)

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
Fase 1 (DB) ✅ COMPLETATA
  1.1 ALTER pratiche ──> 1.2 Guard contesto ──> 1.3 Codice sistema_codici
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

---

## Riepilogo file migration DB

| N. | STEP | Percorso | Tipo | Stato |
|----|------|----------|------|-------|
| 1 | 1.1 | `00_schema/pratiche/20260328-11-alter-pratiche-add-ruolo-istanza-mctit.yaml` | DDL | ✅ |
| 2 | 1.2 | `20_code/pratiche/20260328-12-create-trgfn-pratiche-guard-contesto-mctit.yaml` | Trigger fn + trigger | ✅ |
| 3 | 1.3 | `80_data/sql/config/sistema_codici.csv` — riga `pratica` (id=16, PRA) | Seed | ✅ |
| 4 | 1.2 | `80_data/sql/config/messaggi_errore.csv` — 4 messaggi (id 304-307) | Seed | ✅ |

---

## Funzioni DB — riepilogo

### Esistenti (gia' operative, da sfruttare)

| Funzione | Schema | Uso nel contesto |
|----------|--------|------------------|
| `script.fn_generate_codice()` | script | Generazione codice pratica (via sistema_codici) |
| `script.fn_log_and_raise_error()` | script | Errori nel trigger guard contesto |
| `pratiche.fn_check_prerequisiti_flusso()` | pratiche | Verifica prerequisiti flusso (invariata) |
| `pratiche.fn_genera_pratica_da_flusso()` | pratiche | Generazione cross-pratica (invariata) |
| `pratiche.fn_calcola_tempo_netto_da_a()` | pratiche | Calcolo tempo netto tra flussi (invariata) |
| `pratiche.fn_valuta_tempo_esecuzione_da_a()` | pratiche | Valutazione SLA (OK/WARNING/CRITICO/SFORATO) |
| `pratiche.trgfn_pratiche_guard_transizione()` | pratiche | Guard transizioni stato pratica |
| `pratiche.trgfn_flussi_guard_transizione()` | pratiche | Guard transizioni stato flusso |
| `pratiche.trgfn_flussi_guard_prerequisiti()` | pratiche | Guard prerequisiti flusso |
| `pratiche.trgfn_flussi_generazione()` | pratiche | Generazione cross-pratica automatica |
| `pratiche.trgfn_flussi_calcolo_tempo_completamento()` | pratiche | Calcolo tempo al completamento |
| `pratiche.trgfn_sospensioni_propaga()` | pratiche | Propagazione sospensione ai flussi |
| `pratiche.trgfn_sospensioni_riattiva()` | pratiche | Ripristino stati alla riattivazione |
| `pratiche.trgfn_sospensioni_guard_coerenza_flusso()` | pratiche | Guard coerenza flusso/pratica |
| `pratiche.trgfn_calcoli_tempo_guard_immutabili()` | pratiche | Guard campi immutabili calcoli |
| `pratiche.trgfn_pratiche_giornale_ins()` | pratiche | Giornale: PRATICA_CREATA |
| `pratiche.trgfn_pratiche_giornale_stato()` | pratiche | Giornale: STATO_CAMBIATO |
| `pratiche.trgfn_pratiche_giornale_assegnazione()` | pratiche | Giornale: ASSEGNAZIONE_CAMBIATA |
| `pratiche.trgfn_pratiche_giornale_priorita()` | pratiche | Giornale: PRIORITA_CAMBIATA |
| `pratiche.trgfn_flussi_giornale_ins()` | pratiche | Giornale: FLUSSO_CREATO |
| `pratiche.trgfn_flussi_giornale_stato()` | pratiche | Giornale: FLUSSO_STATO_CAMBIATO |
| `pratiche.trgfn_note_pratiche_giornale()` | pratiche | Giornale: NOTA_AGGIUNTA (pratica) |
| `pratiche.trgfn_note_flussi_giornale()` | pratiche | Giornale: NOTA_AGGIUNTA (flusso) |
| `pratiche.trgfn_allegati_pratiche_giornale()` | pratiche | Giornale: ALLEGATO_AGGIUNTO (pratica) |
| `pratiche.trgfn_allegati_flussi_giornale()` | pratiche | Giornale: ALLEGATO_AGGIUNTO (flusso) |
| `pratiche.trgfn_sospensioni_giornale_ins()` | pratiche | Giornale: SOSPENSIONE_REGISTRATA |
| `pratiche.trgfn_sospensioni_giornale_riattivazione()` | pratiche | Giornale: SOSPENSIONE_CHIUSA |

### Create in v2

| Funzione | Schema | Scopo |
|----------|--------|-------|
| `pratiche.trgfn_pratiche_guard_contesto()` | pratiche | Guard coerenza soggetto-ruolo-istanza ✅ |

> **Rimossi dal piano v2** (non necessari ora):
>
> - `fn_resolve_contesto_pratica()` — serviva per prefisso dinamico, non piu' richiesto
> - `trgfn_pratiche_codice_prefisso()` — sostituito da sistema_codici standard
> - Tabella contatori codice — non necessaria con sequenza standard

---

## Decisioni prese

1. **Refactor diretto**: nessuna retrocompatibilita' con v1 — il modulo non e' in produzione
2. **Collegamento a 3 livelli**: soggetto_id + soggetto_ruolo_id + istanza_utility_id sulla tabella pratiche
3. **FK istanza_utility_id**: punta a `anagrafiche.istanze_utilities(id)`, NON a `istanze_dati_precontrattuali`
4. **Display fields via JOIN**: il backend ritorna dati pronti per la UI, il frontend non fa lookup per dati gia' in lista
5. **Named columns nel mapping**: basta indici posizionali, si usa `cursor.description`
6. **Guard pre/post-attivazione nel service**: logica cross-schema non adatta a trigger DB
7. **Codice prefisso standard**: usa `config.sistema_codici` con prefisso fisso `PRA` (no prefisso dinamico in v2)
8. **Guard contesto nel trigger DB**: linea di difesa ultima, il service replica per errori user-friendly

---

## Elementi futuri (NON in v2)

- Codice pratica con prefisso dinamico (CLI/SOG/FOR/INT) — trigger dedicato quando richiesto
- Tabelle estensione `ext_*` per dati specifici per tipo flusso (Anello 3)
- Handler concreti nel registry per automazioni dominio-specifiche
- Upload file allegati (storage filesystem/object storage)

---

*Piano di completamento — Gestione Pratiche v2 — ZeroERP (28 marzo 2026)*
