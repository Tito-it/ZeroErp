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
| **G7** | BE | Guard pre/post-attivazione nel service | ✅ |
| **G8** | FE | Aggiornare store/drawer/searchTable per i nuovi campi | ✅ |

### Priorita' MEDIA — Funzionalita' di dominio

| # | Area | Descrizione | Stato |
|---|------|-------------|-------|
| **G9** | DB | Note pratiche/flussi — tabelle esistono, trigger giornale gia' operativi | ✅ (gia' in v1) |
| **G10** | DB | Allegati pratiche/flussi — tabelle esistono, trigger giornale gia' operativi | ✅ (gia' in v1) |
| **G11** | BE | Note pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) | ✅ |
| **G12** | BE | Allegati pratiche/flussi — CRUD endpoint (tabelle esistono, API manca) | ✅ |
| **G13** | FE | Tab Note nel drawer pratica | ✅ |
| **G14** | FE | Tab Allegati nel drawer pratica | ✅ |

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

## Fase 6 — Miglioramenti operativi (v2.1)

Miglioramenti emersi dall'analisi dell'interfaccia operativa e della gestione assegnazioni.
Prerequisito: fasi 1-5 completate.

### 6.1 Nuova colonna `data_apertura` su `pratiche.pratiche`

**Problema**: oggi la pratica ha `data_insert` (creazione record) e `data_scadenza`, ma non
registra **quando** e' passata da BOZZA ad APERTA. Questa informazione e' nel giornale
(evento STATO_CAMBIATO) ma serve una query complessa per recuperarla. Per la UI dashboard
e per i calcoli SLA serve un accesso diretto.

**Migration**: ALTER TABLE + trigger

```sql
ALTER TABLE pratiche.pratiche
    ADD COLUMN data_apertura TIMESTAMPTZ;

COMMENT ON COLUMN pratiche.pratiche.data_apertura IS
    'Timestamp di passaggio da BOZZA ad APERTA. Valorizzato automaticamente dal trigger.';
```

**Trigger**: aggiornare `trgfn_pratiche_guard_transizione` (o creare trigger dedicato BEFORE UPDATE OF stato_id):

```sql
-- Quando stato cambia da BOZZA → APERTA, valorizza data_apertura
IF OLD.stato_id = v_bozza_id AND NEW.stato_id = v_aperta_id THEN
    NEW.data_apertura := NOW();
END IF;
```

**Regole**:

- Valorizzata una sola volta (solo transizione BOZZA → APERTA)
- Non sovrascrivibile manualmente (guard o immutabilita' dopo prima valorizzazione)
- NULL per pratiche ancora in BOZZA

---

### 6.2 Tabella `pratiche.competenze_flussi` — matrice competenze operatore

**Perche' nasce**: il modello attuale assegna un operatore alla pratica (`pratiche.risorsa_umana_id`)
e uno al flusso (`flussi.risorsa_umana_id`), ma non esiste un modo per sapere **chi e' abilitato
a eseguire un certo tipo di flusso** in un certo reparto. Senza questa informazione, la coda
di lavoro dell'operatore non puo' mostrare "flussi che posso prendere in carico" — solo quelli
gia' assegnati esplicitamente.

**Cosa risolve**: permette di costruire una coda di lavoro a tre livelli:

1. **Assegnati a me** — flussi con `risorsa_umana_id = operatore corrente`
2. **Da prendere** — flussi non ancora assegnati, dove l'operatore ha competenza
3. **Del mio reparto** — flussi della mia unita' organizzativa (visibilita')

**Migration**: nuova tabella

```sql
CREATE TABLE pratiche.competenze_flussi (
    id                      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    template_flusso_id      INTEGER NOT NULL
        REFERENCES pratiche.template_flussi(id) ON DELETE NO ACTION,
    unita_organizzativa_id  INTEGER NOT NULL
        REFERENCES config.unita_organizzative(id) ON DELETE NO ACTION,
    risorsa_umana_id        BIGINT NOT NULL
        REFERENCES anagrafiche.risorse_umane(id) ON DELETE NO ACTION,
    attivo                  BOOLEAN NOT NULL DEFAULT true,
    meta                    JSONB NOT NULL DEFAULT '{}',
    data_insert             TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert             TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update             TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update             TEXT NOT NULL DEFAULT CURRENT_USER,
    CONSTRAINT uq_competenze_flussi
        UNIQUE (template_flusso_id, unita_organizzativa_id, risorsa_umana_id)
);

COMMENT ON TABLE pratiche.competenze_flussi IS
    'Matrice competenze: per ogni tipo di flusso e reparto, quali operatori sono abilitati.';
```

**Semantica**: la riga dice "l'operatore X, nel reparto Y, e' abilitato a eseguire flussi
del tipo Z". E' configurazione statica, gestita dall'amministratore quando si aggiungono
tipi prestazione o operatori.

**Esempio dati**:

| template_flusso_id | unita_organizzativa_id | risorsa_umana_id | attivo |
| ------------------ | ---------------------- | ---------------- | ------ |
| VALUTAZIONE        | REPARTO_COMMERCIALE    | operatore_A      | true   |
| DIAGNOSI_TECNICA   | REPARTO_TECNICO        | operatore_B      | true   |
| DIAGNOSI_TECNICA   | REPARTO_TECNICO        | operatore_C      | true   |
| FATTURAZIONE       | REPARTO_AMMINISTRATIVO | operatore_D      | true   |

### 6.3 Funzioni DB per la coda di lavoro

**`pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id, p_emittente_fiscale_id)`**

Restituisce i flussi pendenti per un operatore, raggruppati per livello:

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_coda_lavoro_operatore(
    p_risorsa_umana_id   BIGINT,
    p_emittente_fiscale_id BIGINT
)
RETURNS TABLE (
    livello             TEXT,       -- 'ASSEGNATO', 'COMPETENZA', 'REPARTO'
    flusso_id           BIGINT,
    pratica_id          BIGINT,
    pratica_codice      TEXT,
    pratica_descrizione TEXT,
    priorita_codice     VARCHAR,
    tipo_prestazione    VARCHAR,
    template_flusso_codice VARCHAR,
    template_flusso_descrizione TEXT,
    stato_flusso_codice VARCHAR,
    sequenza            INTEGER,
    data_scadenza       DATE,
    risorsa_assegnata   TEXT        -- NULL se non assegnato
)
LANGUAGE sql STABLE
AS $$
    -- Scopo: restituire la coda di lavoro di un operatore in tre livelli
    --        di priorita': flussi assegnati, flussi per competenza, flussi del reparto.

    -- 1. Flussi assegnati direttamente all'operatore
    SELECT 'ASSEGNATO', f.id, p.id, p.codice, p.descrizione,
           pp.codice_interno, tp.codice, tf.codice, tf.descrizione,
           sf.codice_interno, f.sequenza, COALESCE(f.data_scadenza, p.data_scadenza),
           NULL
    FROM pratiche.flussi f
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
    JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
    LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
    JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
    WHERE f.risorsa_umana_id = p_risorsa_umana_id
      AND p.emittente_fiscale_id = p_emittente_fiscale_id
      AND sf.codice_interno IN ('DA_ESEGUIRE', 'IN_CORSO')

    UNION ALL

    -- 2. Flussi non assegnati dove l'operatore ha competenza
    SELECT 'COMPETENZA', f.id, p.id, p.codice, p.descrizione,
           pp.codice_interno, tp.codice, tf.codice, tf.descrizione,
           sf.codice_interno, f.sequenza, COALESCE(f.data_scadenza, p.data_scadenza),
           NULL
    FROM pratiche.flussi f
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
    JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
    JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
    JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
    JOIN pratiche.competenze_flussi cf
      ON cf.template_flusso_id = f.template_flusso_id
      AND cf.risorsa_umana_id = p_risorsa_umana_id
      AND cf.attivo = true
    WHERE f.risorsa_umana_id IS NULL
      AND p.emittente_fiscale_id = p_emittente_fiscale_id
      AND sf.codice_interno = 'DA_ESEGUIRE'

    UNION ALL

    -- 3. Flussi del reparto dell'operatore (visibilita')
    SELECT 'REPARTO', f.id, p.id, p.codice, p.descrizione,
           pp.codice_interno, tp.codice, tf.codice, tf.descrizione,
           sf.codice_interno, f.sequenza, COALESCE(f.data_scadenza, p.data_scadenza),
           CONCAT_WS(' ', ru.nome, ru.cognome)
    FROM pratiche.flussi f
    JOIN pratiche.pratiche p ON p.id = f.pratica_id
    JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
    JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
    LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
    JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
    LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = f.risorsa_umana_id
    WHERE f.unita_organizzativa_id IN (
        SELECT cf2.unita_organizzativa_id
        FROM pratiche.competenze_flussi cf2
        WHERE cf2.risorsa_umana_id = p_risorsa_umana_id AND cf2.attivo = true
    )
      AND f.risorsa_umana_id IS DISTINCT FROM p_risorsa_umana_id
      AND p.emittente_fiscale_id = p_emittente_fiscale_id
      AND sf.codice_interno IN ('DA_ESEGUIRE', 'IN_CORSO')

    ORDER BY
        CASE livello WHEN 'ASSEGNATO' THEN 1 WHEN 'COMPETENZA' THEN 2 ELSE 3 END,
        priorita_codice DESC,
        data_scadenza NULLS LAST,
        sequenza;
$$;
```

**`pratiche.fn_prendi_in_carico_flusso(p_flusso_id, p_risorsa_umana_id)`**

Assegna un flusso DA_ESEGUIRE all'operatore, verificando la competenza:

```sql
-- Scopo: assegnare un flusso non assegnato all'operatore corrente,
--        verificando che abbia competenza per quel tipo di flusso.
-- Regole:
--   1. Il flusso deve essere DA_ESEGUIRE
--   2. Il flusso non deve essere gia' assegnato (o assegnato allo stesso operatore)
--   3. L'operatore deve avere competenza attiva per il template_flusso_id
-- Risultato: aggiorna flussi.risorsa_umana_id e restituisce true/false.
```

---

### 6.4 Interfaccia operativa — PraticheDashboard (✅ IMPLEMENTATA)

L'interfaccia operativa abbandona il pattern drawer-centrico in favore di un
**layout dashboard** con sidebar + master-detail, adattivo per desktop e tablet.

#### Stato iniziale — lista vuota

All'apertura la dashboard mostra **solo i filtri e un messaggio** "Eseguire una ricerca
per visualizzare le pratiche". La sidebar coda lavoro e l'area flussi sono nascoste.
La ricerca testuale richiede **minimo 3 caratteri**. Se si svuota la search senza
filtri attivi, la dashboard torna allo stato iniziale.

```text
┌──────────────────────────────────────────────────────────┐
│  [🔍 Cerca...]  [Stato ▼]  [Priorita' ▼]  [Dal] [Al]  [+ Nuovo]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│                    🔍                                     │
│     Eseguire una ricerca per visualizzare le pratiche    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Seleziona una pratica per vedere i flussi               │
│  ┌─────────────────┬─────────────────┐                   │
│  │   (vuoto)       │   (vuoto)       │                   │
│  └─────────────────┴─────────────────┘                   │
└──────────────────────────────────────────────────────────┘
```

#### Layout desktop dopo ricerca (>= 1280px)

```text
┌──────────────────────────────────────────────────────────┐
│  [🔍 Cerca...]  [Stato ▼]  [Priorita' ▼]  [Dal] [Al]  [+ Nuovo]  │
├──────────┬───────────────────────────────────────────────┤
│          │  [Paginatore: ◀ 1/3 ▶ | 10/pag]              │
│ CODA     │───────────────────────────────────────────────│
│ LAVORO   │  Codice   │ Tipo │ Soggetto │ Stato │ Prio.  │
│──────────│───────────┼──────┼──────────┼───────┼────────│
│■ASSEGNATI│  PRA-001  │ MAN  │ Rossi    │ APERTA│ ALTA   │
│ PRA-0042 │  PRA-002  │ ASS  │ Bianchi  │ BOZZA │ NORM   │
│ Diagnosi │  PRA-003  │ REC  │ Verdi    │ APERTA│ URG    │
│ ● IN_COR │                    (scroll interno)           │
│          ├───────────────────────────────────────────────│
│■DA PREND.│  📂 Visualizzazione pratica codice: PRA-001   │
│ PRA-0051 │───────────────────────────────────────────────│
│ Assegnaz.│  DA FARE (3)       │  COMPLETATI (1)          │
│ [Prendi] │  ○ Valutazione     │  ✓ Ricezione [POSITIVO]  │
│          │  ○ Diagnosi        │                          │
│■REPARTO  │  ● Assegnamento    │                          │
│ PRA-0072 │                    │                          │
│ (Marco)  │                    │                          │
└──────────┴───────────────────────────────────────────────┘
```

**Sidebar sinistra** (260px): coda lavoro dell'operatore con titolo verde info e
sottolineatura sotto il testo. Tre sezioni con badge contatore e separatore verde
tra i gruppi:

- **Assegnati a me**: flussi con `risorsa_umana_id = me`, stato DA_ESEGUIRE o IN_CORSO.
  Mostra tag stato + tag priorita'.
- **Da prendere**: flussi non assegnati dove ho competenza (tabella `competenze_flussi`).
  Mostra tag stato + bottone "Prendi in carico".
- **Del mio reparto**: flussi della mia unita' organizzativa.
  Mostra tag stato + nome risorsa assegnata.

La sidebar e' allineata verticalmente con le righe della tabella (spacer 90px replica
l'altezza toolbar filtri + paginator).

**Area principale superiore**: tabella pratiche con **paginazione a 10 righe**. Click su
riga seleziona la pratica per la sezione inferiore. La DataTable usa scroll interno
calcolato dinamicamente via `ResizeObserver` (non `scrollHeight="flex"`).

**Barra contesto pratica**: sopra l'area flussi, mostra "Visualizzazione pratica codice:
PRA-XXXXX" (verde info con icona) quando una pratica e' selezionata, oppure "Seleziona
una pratica per vedere i flussi" (grigio corsivo) quando nessuna.

**Area flussi** (230px fissi): split in due colonne — flussi da fare (card cliccabili,
aprono FlussoDrawer) e flussi completati (readonly con esito). Ogni card mostra
sequenza, stato tag, codice template, descrizione, scadenza.

**Azioni**:

- Click su elemento sidebar → seleziona la pratica corrispondente e carica i flussi
- Click "Prendi in carico" su elemento COMPETENZA → `fn_prendi_in_carico_flusso`, ricarica coda
- Click su flusso "da fare" nell'area inferiore → apre FlussoDrawer per esecuzione
- Click riga tabella → seleziona pratica, carica flussi sotto
- Click "Nuovo" → apre PraticaDrawer in creazione

#### Layout tablet/mobile (< 1280px)

```text
┌──────────────────────────────────────────┐
│  [🔍 Cerca...]  [Stato ▼]  [+ Nuovo]    │
├──────────────────────────────────────────┤
│  CODA LAVORO (160px, scroll orizzontale) │
│  ■ Assegnati ■ Da prendere ■ Reparto    │
╞══════════════════════════════════════════╡
│  PRA-001 │ MAN │ Rossi │ APERTA │ ALTA  │
│  PRA-002 │ ASS │ Bianchi │ BOZZA │ NORM │
│  PRA-003 │ REC │ Verdi │ APERTA │ URG   │
│  ... (niente scroll interno, pagina      │
│       scrolla verticalmente)             │
├──────────────────────────────────────────┤
│  📂 Visualizzazione pratica: PRA-001     │
│  DA FARE (2)    │  COMPLETATI (1)        │
│  ○ Valutazione  │  ✓ Ricezione           │
│  ○ Diagnosi     │                        │
└──────────────────────────────────────────┘
```

Su schermi piccoli:

- Layout verticale (`flex-direction: column`), container scrolla (`overflow-y: auto`)
- Sidebar coda lavoro: 160px fissi, larghezza 100%, senza spacer
- DataTable **senza scroll interno** (`scrollable=false`): le righe si espandono, la pagina scrolla
- Area flussi: 200px fissi in fondo
- Il separatore sidebar rimane verde info per coerenza visiva

#### FlussoDrawer (✅ IMPLEMENTATO)

Drawer di esecuzione flusso (larghezza STANDARD = 640px). Il contenuto si adatta
allo stato corrente del flusso:

- **DA_ESEGUIRE**: header con codice pratica, stato, template, data — bottone "Avvia flusso"
- **IN_CORSO**: form completamento con Select esito (POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE)
  + Textarea note esito — bottone "Completa" (disabilitato senza esito)
- **COMPLETATO**: mostra esito con Tag severity (verde/rosso/arancio) + note esito readonly

La severity dell'esito usa `esitoFlussoSeverity()` centralizzata in `core/utils/severity.js`
(riusabile ovunque serva mostrare un esito flusso).

#### Componenti Vue (✅ IMPLEMENTATI)

```text
src/pratiche/
├── views/
│   ├── PraticheDashboard.vue            -- layout dashboard (sidebar + master-detail)
│   └── PraticheView.vue                 -- layout semplice (fallback, SearchTable + Drawer)
├── components/
│   ├── PraticheCodaLavoro.vue           -- sidebar: coda lavoro 3 livelli (riutilizzabile)
│   ├── PraticheSearchTable.vue          -- tabella master con scroll dinamico
│   ├── PraticaFlussiPanel.vue           -- pannello flussi split da fare/completati (riutilizzabile)
│   ├── PraticaDrawer.vue               -- drawer testata pratica (creazione + edit con tab)
│   ├── FlussoDrawer.vue                 -- drawer esecuzione flusso (riutilizzabile)
│   ├── PraticaFlussiTab.vue            -- tab flussi nel drawer pratica
│   ├── PraticaNoteTab.vue              -- tab note nel drawer pratica
│   ├── PraticaAllegatiTab.vue          -- tab allegati nel drawer pratica
│   └── PraticaGiornaleTab.vue          -- tab giornale nel drawer pratica
```

**Principio riusabilita'**: `PraticheCodaLavoro`, `PraticaFlussiPanel` e `FlussoDrawer` sono
componenti puri — ricevono dati via props, emettono eventi, zero dipendenza diretta dallo store.
Possono essere riusati in altri contesti (es. dashboard ticket quando il modulo assistenza sara'
sviluppato).

#### Dettagli implementativi

- **Paginazione**: default 10 righe (store `filters.limit = 10`)
- **Search minimo 3 caratteri**: lo store blocca `fetchList()` se search < 3 e nessun filtro attivo
- **Clear search torna a stato vuoto**: `hasSearched = false`, sidebar e flussi scompaiono
- **Scroll DataTable**: desktop usa `ResizeObserver` + `getBoundingClientRect()` per calcolare
  `scrollHeight` dinamico. Mobile disabilita scroll interno (`scrollable=false`)
- **Ricalcolo layout**: watch su `hasSearched` emette `window.dispatchEvent(new Event('resize'))`
  con delay 50ms per forzare PrimeVue a riadattarsi
- **Helper `get_risorsa_umana_id`**: in `core/api/endpoint_helpers.py`, risolve JWT → risorsa_umana
  con cache per-request (`setattr(request, '_risorsa_umana_id', ...)`)
- **Colonna data_apertura**: mostra `data_apertura` (non `data_insert`) sia nella SearchTable
  che nel PraticaDrawer

#### Bloccante: GRANT mancanti

La tabella `pratiche.competenze_flussi` non ha ancora i GRANT per il ruolo applicativo Django.
Lo smoke test test 26 (coda lavoro) fallisce con "permesso negato". Da risolvere lato DB
prima del test completo.

---

### 6.5 API necessarie per la dashboard

| Metodo | Endpoint                                          | Descrizione                    | Funzione DB                    |
| ------ | ------------------------------------------------- | ------------------------------ | ------------------------------ |
| GET    | `/api/v1/pratiche/coda-lavoro/`                   | Coda lavoro operatore corrente | `fn_coda_lavoro_operatore`     |
| POST   | `/api/v1/pratiche/flussi/{fid}/prendi-in-carico/` | Prendi in carico flusso        | `fn_prendi_in_carico_flusso`   |
| GET    | `/api/v1/pratiche/competenze-flussi/`             | Lista competenze (admin)       | SELECT diretto                 |
| POST   | `/api/v1/pratiche/competenze-flussi/`             | Crea competenza (admin)        | INSERT                         |
| DELETE | `/api/v1/pratiche/competenze-flussi/{id}/`        | Rimuovi competenza (admin)     | DELETE                         |

L'endpoint coda-lavoro ricava `risorsa_umana_id` dall'utente autenticato (JWT → risorse_umane).

---

### 6.6 Riepilogo migration DB fase 6

| #  | Oggetto                                                    | Tipo | Stato | Note                              |
| -- | ---------------------------------------------------------- | ---- | ----- | --------------------------------- |
| M1 | `ALTER pratiche.pratiche ADD COLUMN data_apertura`         | DDL  | ✅    | DATE nullable                     |
| M2 | Trigger valorizzazione `data_apertura` (BOZZA → APERTA)  | Code | ✅    | Fase m50, immutabile, CURRENT_DATE |
| M3 | `CREATE TABLE pratiche.competenze_flussi`                 | DDL  | ✅    | Con unique composite, FK rinominate |
| M4 | `CREATE FUNCTION pratiche.fn_coda_lavoro_operatore(...)`  | Code | ✅    | CTE singola scansione, 3 livelli  |
| M5 | `CREATE FUNCTION pratiche.fn_prendi_in_carico_flusso(...)` | Code | ✅    | FOR UPDATE + ROW_COUNT check      |
| M7 | `CREATE FUNCTION pratiche.fn_prendi_in_carico_flusso(...)` | Code | Funzione PL/pgSQL |

**Ordine**: M1 → M2 → M3 → M4 → M5

---

## Fase 7 — Piano Backend

Prerequisito: fase 6 DB completata (migration M1-M5 applicate).

Il backend pratiche v1 e' gia' sostanzialmente completo (40+ metodi repository,
30+ service, 26 view API, 36 endpoint). La fase 7 aggiorna il codice esistente
per i nuovi campi v2 e aggiunge gli endpoint per coda lavoro e competenze.

### Stato attuale backend v1

| Componente | File | Righe | Stato |
| ---------- | ---- | ----- | ----- |
| Types | `types.py` | 189 | 11 TypedDict, da aggiornare |
| Repository | `pratiche_repository.py` | 825 | 40+ metodi, SQL da riscrivere con JOIN display |
| Repository gen. | `generazione_repository.py` | 94 | Completo, invariato |
| Service | `pratiche_service.py` | 707 | 30+ metodi, da aggiornare per nuovi campi |
| Service gen. | `generazione_service.py` | 87 | Completo, invariato |
| Handler registry | `handler_registry.py` | 41 | Completo, invariato |
| Views | `views.py` | 924 | 26 view, da aggiornare + nuove |
| Routes | `urls_v1.py` | 70 | 36 path, da estendere |
| Test API | `tests/api/` | 969 | 5 file, da aggiornare |
| Test service | `tests/services/` | 557 | 5 file, da aggiornare |

### Cosa NON cambia

- `generazione_service.py` / `generazione_repository.py` — gia' operativi
- `handler_registry.py` — invariato (HANDLER_MAP vuoto, estendibile)
- Endpoint sospensioni, giornale, calcoli tempo, formule tempo — gia' completi
- Endpoint note e allegati — gia' completi
- Pattern architetturale (3 layer, DomainAPIView, handle_post_json)

### Cosa viene eliminato/semplificato

- Indici posizionali nel mapping row → dict: sostituiti da `cursor.description`
- Lookup client-side per stato/priorita'/tipo: ora il backend li restituisce via JOIN

### Fase A — Types (`types.py`)

| # | Azione | Dettaglio |
| - | ------ | --------- |
| A1 | Aggiornare `PraticaRow` | Aggiungere: `soggetto_ruolo_id`, `istanza_utility_id`, `data_apertura`, campi display (tipo_prestazione_codice, tipo_prestazione_descrizione, stato_codice_interno, stato_descrizione, priorita_codice_interno, priorita_descrizione, soggetto_display, risorsa_umana_display, unita_organizzativa_descrizione) |
| A2 | Aggiungere `CompetenzaFlussoRow` | TypedDict per `pratiche.competenze_flussi` |
| A3 | Aggiungere `CodaLavoroRow` | TypedDict per risultato `fn_coda_lavoro_operatore` (livello, flusso_id, pratica_id, pratica_codice, ecc.) |

### Fase B — Repository (`pratiche_repository.py`)

| # | Azione | Dettaglio |
| - | ------ | --------- |
| B1 | Riscrivere `list_pratiche` SQL | JOIN a tipi_prestazione, stati_pratiche, priorita_pratiche, soggetti, risorse_umane, unita_organizzative. Aggiungere campi v2 (soggetto_ruolo_id, istanza_utility_id, data_apertura) |
| B2 | Riscrivere `get_pratica` SQL | Stessi JOIN di B1 per coerenza |
| B3 | Riscrivere mapping row → dict | Usare `cursor.description` per named columns. Pattern: `cols = [d[0] for d in cursor.description]; dict(zip(cols, row))` |
| B4 | Aggiornare `create_pratica` | Aggiungere `soggetto_ruolo_id`, `istanza_utility_id` nell'INSERT |
| B5 | Aggiungere `list_coda_lavoro` | Chiama `SELECT * FROM pratiche.fn_coda_lavoro_operatore(p_risorsa_umana_id, p_emittente_fiscale_id)` |
| B6 | Aggiungere `prendi_in_carico_flusso` | Chiama `SELECT pratiche.fn_prendi_in_carico_flusso(p_flusso_id, p_risorsa_umana_id)` |
| B7 | Aggiungere CRUD `competenze_flussi` | `list_competenze(emittente_id)`, `create_competenza(data)`, `delete_competenza(id)` |

### Fase C — Service (`pratiche_service.py`)

| # | Azione | Dettaglio |
| - | ------ | --------- |
| C1 | Aggiornare `crea_pratica` | Accettare `soggetto_ruolo_id`, `istanza_utility_id`. Guard coerenza contesto gia' presente — verificare allineamento con trigger DB |
| C2 | Aggiungere `get_coda_lavoro` | Delega a repository. Ricava `risorsa_umana_id` dall'utente autenticato |
| C3 | Aggiungere `prendi_in_carico` | Delega a repository con validazione parametri |
| C4 | Aggiungere CRUD competenze | `list_competenze`, `crea_competenza`, `elimina_competenza` (operazioni admin) |

### Fase D — API Views (`views.py`) + Routes (`urls_v1.py`)

| # | Azione | Dettaglio |
| - | ------ | --------- |
| D1 | Aggiornare `ApiPraticheList.post` | Accettare `soggetto_ruolo_id`, `istanza_utility_id` nel payload |
| D2 | Aggiungere `ApiCodaLavoro` | `GET /api/v1/pratiche/coda-lavoro/` — coda lavoro operatore corrente |
| D3 | Aggiungere `ApiPrendiInCarico` | `POST /api/v1/pratiche/flussi/{fid}/prendi-in-carico/` |
| D4 | Aggiungere `ApiCompetenzeFlussiList` | `GET/POST /api/v1/pratiche/competenze-flussi/` (admin) |
| D5 | Aggiungere `ApiCompetenzaFlussoDetail` | `DELETE /api/v1/pratiche/competenze-flussi/{id}/` (admin) |
| D6 | Aggiungere route in `urls_v1.py` | 4 nuove path per D2-D5 |

### Fase E — Test

| # | Azione | Dettaglio |
| - | ------ | --------- |
| E1 | Aggiornare test `crea_pratica` | Nuovi campi (soggetto_ruolo_id, istanza_utility_id) |
| E2 | Aggiornare test API list/detail | Verificare campi display nella risposta |
| E3 | Aggiungere test coda lavoro | Service + API (mock fn_coda_lavoro_operatore) |
| E4 | Aggiungere test prendi in carico | Service + API (mock fn_prendi_in_carico_flusso) |
| E5 | Aggiungere test competenze CRUD | Service + API |

### Ordine di esecuzione

```text
Fase A (types)
  A1 PraticaRow → A2 CompetenzaFlussoRow → A3 CodaLavoroRow
                                                │
                                                v
Fase B (repository)
  B3 mapping named → B1 list_pratiche → B2 get_pratica → B4 create_pratica
                                                          │
                                                          v
                     B5 coda_lavoro → B6 prendi_in_carico → B7 competenze CRUD
                                                              │
                                                              v
Fase C (service)
  C1 crea_pratica → C2 coda_lavoro → C3 prendi_in_carico → C4 competenze
                                                              │
                                                              v
Fase D (views + routes)
  D1 create payload → D2 coda_lavoro → D3 prendi → D4-D5 competenze → D6 routes
                                                                        │
                                                                        v
Fase E (test)
  E1 create → E2 list/detail → E3 coda → E4 prendi → E5 competenze
```

---

## Elementi futuri (NON in v2)

- Codice pratica con prefisso dinamico (CLI/SOG/FOR/INT) — trigger dedicato quando richiesto
- Tabelle estensione `ext_*` per dati specifici per tipo flusso (Anello 3)
- Handler concreti nel registry per automazioni dominio-specifiche
- Upload file allegati (storage filesystem/object storage)

---

*Piano di completamento — Gestione Pratiche v2 — ZeroERP (29 marzo 2026)*
