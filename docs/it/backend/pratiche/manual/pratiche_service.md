# pratiche_service (Django)

## Scopo

Facade applicativo per operazioni su pratiche, flussi, prerequisiti, giornale e handler dispatch. API interna cross-dominio: altre app Django (vendite, anagrafiche, acquisti) importano e usano queste funzioni per creare/gestire pratiche legate ai propri eventi.

## Contesto

Il modulo vive in `apps/pratiche/services/pratiche_service.py`. Non e' una classe ma un modulo di funzioni top-level, seguendo il pattern facade. Ogni funzione con side-effect e' wrappata in `@transaction.atomic()`. Le validazioni usano `ErrorManager.require` con `assert` successivo per il type checker.

Il servizio delega tutte le operazioni DB al `PraticheRepository` e le operazioni di stato alle tabelle config tramite `resolve_stato_pratica` / `resolve_stato_flusso`.

## Input

- Parametri dominio `pratiche`: `pratica_id`, filtri ricerca, payload aggiornamento, assegnazione.
- Parametri dominio `flussi`: `flusso_id`, `template_flusso_id`, `nuovo_stato`, `esito`.
- Parametri di supporto: paginazione (`limit`, `offset`), `meta`/`note_esito`.

## Output

### Pratiche

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `crea_pratica(...)` | emittente_fiscale_id, tipo_prestazione_id, priorita_id, ... | `int` (pratica_id) | Crea pratica con stato BOZZA |
| `aggiorna_pratica(pratica_id, data)` | pratica_id, dict campi | `None` | Aggiorna campi consentiti |
| `cambia_stato_pratica(pratica_id, nuovo_stato)` | pratica_id, codice_interno stato | `None` | Transizione stato pratica |
| `assegna_pratica(pratica_id, ...)` | pratica_id, risorsa_umana_id?, unita_organizzativa_id? | `None` | Assegna risorsa/UO |
| `cerca_pratiche(...)` | emittente_fiscale_id, filtri, limit, offset | `(list, int)` | Ricerca paginata |

### Flussi

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `crea_flusso(...)` | pratica_id, template_flusso_id?, ... | `int` (flusso_id) | Crea flusso con stato DA_ESEGUIRE |
| `avvia_flusso(flusso_id)` | flusso_id | `None` | Transizione → IN_CORSO |
| `completa_flusso(flusso_id, esito, note_esito?)` | flusso_id, esito | `None` | Transizione → COMPLETATO |
| `cambia_stato_flusso(flusso_id, nuovo_stato, ...)` | flusso_id, codice_interno, esito?, note_esito? | `None` | Transizione generica |

### Sospensioni

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `sospendi_pratica(pratica_id, motivo, *, data_riattivazione_prevista?)` | pratica_id, motivo, data opzionale | `int` (sospensione_id) | Sospende pratica intera; trigger propaga ai flussi |
| `riattiva_pratica(pratica_id)` | pratica_id | `None` | Riattiva pratica sospesa; trigger ripristina flussi |
| `sospendi_flusso(pratica_id, flusso_id, motivo, *, data_riattivazione_prevista?)` | pratica_id, flusso_id, motivo, data opzionale | `int` (sospensione_id) | Sospende singolo flusso |
| `riattiva_flusso(pratica_id, flusso_id)` | pratica_id, flusso_id | `None` | Riattiva singolo flusso sospeso |
| `get_sospensioni(pratica_id)` | pratica_id | `list[SospensioneRow]` | Lista sospensioni pratica (tutte) |
| `get_calcoli_tempo(pratica_id)` | pratica_id | `list[CalcoloTempoRow]` | Calcoli tempo prestazione da/a |

### Supporto

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `verifica_prerequisiti(pratica_id, template_flusso_id)` | pratica_id, template_flusso_id | `list[PrerequisitoCheckRow]` | Check prerequisiti (pura lettura) |
| `get_canali_disponibili(template_flusso_id)` | template_flusso_id | `list[CanalePraticaRow]` | Canali abilitati per template |
| `dispatch_handler(flusso_id)` | flusso_id | `dict \| None` | Invoca handler Python se configurato |
| `get_giornale(pratica_id, limit, offset)` | pratica_id, limit, offset | `(list[GiornaleRow], int)` | Giornale paginato |

## Regole

- Tutte le funzioni di scrittura sono wrappate in `@transaction.atomic()`.
- Validazione con `ErrorManager.require` + `assert` per type safety.
- Esiti flusso ammessi: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`.
- `dispatch_handler`: import inline di `handler_registry.get_handler` per evitare import circolari; ritorna `None` se il flusso non ha template, non ha handler_key, o l'handler non e' registrato.
- `assegna_pratica`: noop se nessun campo di assegnazione fornito.
- Le funzioni sospensione verificano unicita' sospensione attiva prima dell'INSERT.
- `_verifica_flusso_pratica(repo, pratica_id, flusso_id)`: helper privato per ownership check flusso/pratica riusato da `sospendi_flusso` e `riattiva_flusso`.

## Dipendenze DB

- `pratiche.pratiche` (CRUD via PraticheRepository)
- `pratiche.flussi` (CRUD via PraticheRepository)
- `pratiche.giornale` (lettura via PraticheRepository)
- `config.stati_pratiche` (risoluzione stato pratica)
- `config.stati_flussi_pratiche` (risoluzione stato flusso)
- `pratiche.handler_flussi` (lookup handler_key)
- `pratiche.fn_check_prerequisiti_flusso` (verifica prerequisiti)
- `pratiche.template_flussi_canali` + `config.canali_pratiche` (canali)
- `pratiche.sospensioni` (CRUD sospensioni via PraticheRepository)
- `pratiche.calcoli_tempo` (lettura via PraticheRepository)

## Note di migrazione

- Le funzioni inline `_resolve_stato_pratica`, `_resolve_stato_flusso`, `_get_handler_key` sono state migrate nel `PraticheRepository` come metodi di istanza.
- `cambia_stato_flusso` e' stata aggiunta per gestire transizioni generiche (SOSPESO, ANNULLATO) senza passare dalla view con logica inline.
