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
| `crea_pratica(...)` | emittente_fiscale_id, tipo_prestazione_id, priorita_id, ... | `int` (pratica_id) | Crea pratica con stato APERTA (la pratica nasce aperta) |
| `aggiorna_pratica(pratica_id, data)` | pratica_id, dict campi | `None` | Aggiorna campi consentiti |
| `cambia_stato_pratica(pratica_id, nuovo_stato)` | pratica_id, codice_interno stato | `None` | Transizione stato pratica |
| `assegna_pratica(pratica_id, ...)` | pratica_id, risorsa_umana_id?, unita_organizzativa_id? | `None` | Assegna risorsa/UO |
| `cerca_pratiche(...)` | emittente_fiscale_id, filtri, limit, offset | `(list, int)` | Ricerca paginata |

### Flussi

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `crea_flusso(...)` | pratica_id, template_flusso_id (**obbligatorio**, > 0), ... | `int` (flusso_id) | Crea flusso con stato DA_ESEGUIRE |
| `avvia_flusso(flusso_id, user?)` | flusso_id | `dict \| None` | Transizione → IN_CORSO (+ dispatch handler; auto-completa con `esito_default` se handler ok **o** `modalita_esito = AUTOMATICO`) |
| `avvia_e_completa_flusso(flusso_id, esito, note_esito?, user?)` | flusso_id, esito | `None` | **CONTESTUALE** (2026-06-17): DA_ESEGUIRE → IN_CORSO → COMPLETATO in una transazione; riusa `completa_flusso`. NON esegue l'handler di avvio (esito deciso dall'operatore) |
| `completa_flusso(flusso_id, esito, note_esito?, user?)` | flusso_id, esito | `None` | Transizione → COMPLETATO (+ dispatch handler evento COMPLETATO). Esito validato da `_require_esito_valido` (`ESITI_FLUSSO_AMMESSI`) |
| `cambia_stato_flusso(flusso_id, nuovo_stato, ...)` | flusso_id, codice_interno, esito?, note_esito? | `None` | Transizione generica |
| `assegna_flusso(flusso_id, *, risorsa_umana_id?, unita_organizzativa_id?, set_risorsa?, set_unita?)` | flusso_id + flag `set_*` | `None` | Assegna lo step a operatore/reparto (flag `set_*` = chiave presente; `None` = de-assegna). Trigger giornale `FLUSSO_ASSEGNAZIONE_CAMBIATA`. Vedi [api_flusso_assegnazione](api_flusso_assegnazione.md) |

### Sospensioni

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `sospendi_pratica(pratica_id, motivo, *, data_riattivazione_prevista?)` | pratica_id, motivo, data opzionale | `int` (sospensione_id) | Sospende pratica intera; trigger propaga ai flussi |
| `riattiva_pratica(pratica_id)` | pratica_id | `None` | Riattiva pratica sospesa; trigger ripristina flussi |
| `sospendi_flusso(pratica_id, flusso_id, motivo, *, data_riattivazione_prevista?)` | pratica_id, flusso_id, motivo, data opzionale | `int` (sospensione_id) | Sospende singolo flusso |
| `riattiva_flusso(pratica_id, flusso_id)` | pratica_id, flusso_id | `None` | Riattiva singolo flusso sospeso |
| `get_sospensioni(pratica_id)` | pratica_id | `list[SospensioneRow]` | Lista sospensioni pratica (tutte) |
| `get_calcoli_tempo(pratica_id)` | pratica_id | `list[CalcoloTempoRow]` | Calcoli tempo prestazione da/a |

### Coda lavoro e competenze

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `get_coda_lavoro(risorsa_umana_id, emittente_fiscale_id)` | risorsa_umana_id, emittente_fiscale_id | `list[CodaLavoroRow]` | Coda lavoro operatore su 4 livelli (ASSEGNATO/COMPETENZA/REPARTO/LIBERO) |
| `prendi_in_carico(flusso_id, risorsa_umana_id)` | flusso_id, risorsa_umana_id | `bool` | Presa in carico flusso DA_ESEGUIRE (eligibilità reparto-first; traduce gli errori DB `FLUSSI_COMPETENZA_MANCANTE`/`FLUSSI_PRESA_NON_ELIGIBILE`) |
| `list_operatori_reparto(unita_organizzativa_id)` | unita_organizzativa_id | `list[dict]` | Operatori attivi del reparto (picker assegnazione). Vedi [api_operatori_reparto](api_operatori_reparto.md) |
| `get_competenze_flussi()` | — | `list[CompetenzaFlussoRow]` | Matrice competenze con display fields |
| `crea_competenza_flusso(...)` | template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo? | `int` (competenza_id) | Crea competenza (admin) |
| `elimina_competenza_flusso(competenza_id)` | competenza_id | `None` | Elimina competenza (admin) |

### Supporto

| Funzione | Input | Output | Descrizione |
|---|---|---|---|
| `verifica_prerequisiti(pratica_id, template_flusso_id)` | pratica_id, template_flusso_id | `list[PrerequisitoCheckRow]` | Check prerequisiti (pura lettura) |
| `get_canali_disponibili(template_flusso_id)` | template_flusso_id | `list[CanalePraticaRow]` | Canali abilitati per template |
| `dispatch_handler(flusso_id, user?)` | flusso_id | `dict \| None` | Invoca l'handler IN_CORSO del template (`template_flussi.handler_id`) se configurato |
| `dispatch_handler_eventi(flusso_id, evento, esito?, user?)` | flusso_id, evento | `None` | Esegue gli handler legati all'evento (`template_flussi_handler_eventi`), esito-aware, in ordine di sequenza. Binding senza impl registrata → `E_HANDLER_NON_REGISTRATO` |
| `verifica_flusso_pratica(repo, pratica_id, flusso_id)` | repo, pratica_id, flusso_id | `dict` | Verifica esistenza e ownership flusso/pratica |
| `get_giornale(pratica_id, limit, offset)` | pratica_id, limit, offset | `(list[GiornaleRow], int)` | Giornale paginato |
| `get_formule_tempo(tipo_prestazione_id)` | tipo_prestazione_id | `list[FormulaTempoRow]` | Formule tempo attive per tipo |

## Regole

- Tutte le funzioni di scrittura sono wrappate in `@transaction.atomic()`.
- Validazione con `ErrorManager.require` + `assert` per type safety.
- Esiti flusso ammessi: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`.
- `dispatch_handler`: import inline di `handler_registry.get_handler` per evitare import circolari; ritorna `None` se il flusso non ha template, non ha handler_key, o l'handler non e' registrato.
- `dispatch_handler_eventi` (2026-06-15): preambolo condiviso con `dispatch_handler` via `_flusso_per_dispatch` (fetch + guard + check template). Diversamente da `dispatch_handler`, un binding seedato senza impl registrata e' fail-fast (`E_HANDLER_NON_REGISTRATO`): non si completa un flusso saltando l'azione di dominio promessa. Eseguito nella transazione del completamento (atomicita' cambio stato + azione dominio). Chiamato da `completa_flusso` e dall'auto-completamento di `avvia_flusso`.
- `assegna_pratica`: noop se nessun campo di assegnazione fornito.
- Le funzioni sospensione verificano unicita' sospensione attiva prima dell'INSERT.
- `verifica_flusso_pratica(repo, pratica_id, flusso_id)`: helper **pubblico** per ownership check flusso/pratica. Usato internamente dal service (sospensioni, flussi) e dalle views API (alias `_get_flusso_verificato`). Unica fonte di verita' per la verifica esistenza + appartenenza flusso.

### Workflow v2 (2026-06-12, analisi-pratiche-workflow-v2)

- `cerca_pratiche`: lente di contesto canonica D1 — parametri
  `soggetto_ruolo_id` / `istanza_utility_id` / `solo_interne` mutuamente
  alternativi; due o piu' lenti → `ServiceError`
  `E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI` (lo stesso del guard DB;
  fino al 2026-10-21 qui usciva la forma ritirata senza `E_`,
  fail-fast in Python; la fn `fn_lista_pratiche_per_contesto` resta la
  difesa in profondita'). Nuovi filtri `priorita_id` / `risorsa_umana_id`
  (fix: prima inviati dalla dashboard ma ignorati).
- Traduzione errori guard DB via `_KNOWN_DB_ERROR_MARKERS` (substring sul
  messaggio italiano, pattern di `lookup_service`): `crea_flusso` →
  `PRATICHE_FLUSSO_NON_RIPETIBILE` (483, guard ripetibilita' D3);
  `cambia_stato_pratica` → `PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI`
  (485, guard chiusura D4). ⚠ I marker reggono perche' il catalogo ha solo
  righe `it` per questi codici: aggiungendo traduzioni vanno estesi
  (degrado sicuro: fallback `E_DATABASE`).
- `dispatch_handler`: `meta` e `handler_params` passano da
  `coerce_jsonb_dict` (psycopg puo' restituire jsonb come `str`; senza
  coerce la configurazione andrebbe persa in silenzio — bug 2026-06-11).

## Dipendenze DB

- `pratiche.pratiche` (CRUD via PraticheRepository)
- `pratiche.flussi` (CRUD via PraticheRepository)
- `pratiche.giornale` (lettura via PraticheRepository)
- `config.stati_pratiche` (risoluzione stato pratica)
- `config.stati_flussi_pratiche` (risoluzione stato flusso)
- `pratiche.handler_flussi` (lookup handler_key)
- `pratiche.template_flussi_handler_eventi` (binding handler per evento COMPLETATO, esito-aware)
- `pratiche.fn_check_prerequisiti_flusso` (verifica prerequisiti)
- `pratiche.template_flussi_canali` + `config.canali_pratiche` (canali)
- `pratiche.sospensioni` (CRUD sospensioni via PraticheRepository)
- `pratiche.calcoli_tempo` (lettura via PraticheRepository)
- `pratiche.competenze_flussi` (CRUD competenze via PraticheRepository)
- `pratiche.fn_coda_lavoro_operatore` (coda lavoro operatore)
- `pratiche.fn_prendi_in_carico_flusso` (presa in carico con FOR UPDATE)
- `pratiche.fn_lista_pratiche_per_contesto` (lente contesto D1, semi-join in `list_pratiche`)
- `pratiche.fn_check_ripetibilita_flusso` + `fn_check_chiusura_pratica` (percorso arricchito D3/D4)

## Note di migrazione

- Le funzioni inline `_resolve_stato_pratica`, `_resolve_stato_flusso`, `_get_handler_key` sono state migrate nel `PraticheRepository` come metodi di istanza.
- `cambia_stato_flusso` e' stata aggiunta per gestire transizioni generiche (SOSPESO, ANNULLATO) senza passare dalla view con logica inline.
- v2.2 (1 aprile 2026): `_verifica_flusso_pratica` rinominata `verifica_flusso_pratica` (pubblica). La funzione duplicata in `views.py` e' stata sostituita con alias al service. Repository allineato ai building block core (`row_to_dict`/`rows_to_list`, `ErrorManager.require` su tutti i fetchone). `pratica_select_sql()`/`pratica_joins_sql()` esposti come classmethod pubblici per uso cross-repository.
- (17 giugno 2026) **Esito configurabile** (`template_flussi.modalita_esito`/`esito_default`): nuovo `avvia_e_completa_flusso` (CONTESTUALE, riusa `completa_flusso`); `avvia_flusso` auto-completa con `esito_default` (fallback `_ESITO_AUTO_FALLBACK = POSITIVO`) anche per `AUTOMATICO`; validazione esito estratta in `_require_esito_valido`/`ESITI_FLUSSO_AMMESSI` (de-duplica la tupla tra completa/avvia_e_completa); query leggera `PraticheRepository.get_flusso_esito_config` per il path di avvio; proiezione `get_flusso` arricchita con `template_modalita_esito`/`template_esito_default`. Vedi [api_flusso_stato](api_flusso_stato.md) e i brief `brief-design-esito-configurabile-flussi` / `brief-db-esito-configurabile-flussi`.
