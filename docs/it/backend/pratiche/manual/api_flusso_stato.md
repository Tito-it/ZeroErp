# API flusso_stato (Django)

## Scopo

Esporre via HTTP le transizioni di stato di un flusso: avvio (IN_CORSO), completamento (COMPLETATO con esito) e transizioni generiche (SOSPESO, ANNULLATO, ecc.).

## Contesto

Endpoint di scrittura con ownership check. Smista la richiesta in base al valore di `nuovo_stato` **e allo stato corrente** del flusso:

- `IN_CORSO` → `pratiche_service.avvia_flusso` (passa l'utente acting)
- `COMPLETATO` da stato `DA_ESEGUIRE` → `pratiche_service.avvia_e_completa_flusso`
  (avvio + esito in un'unica azione: modalita CONTESTUALE, vedi sotto)
- `COMPLETATO` da stato `IN_CORSO` → `pratiche_service.completa_flusso` (con esito obbligatorio)
- Altro → `pratiche_service.cambia_stato_flusso` (transizione generica)

**Modalita esito (config `template_flussi`, 2026-06-17)**: lo step-template porta
`modalita_esito` (`MANUALE` | `AUTOMATICO` | `CONTESTUALE`) + `esito_default`
(dominio di `flussi.esito`), che governano come si ottiene l'esito:

- **MANUALE** (default, comportamento storico): avvio → poi completamento con esito
  scelto dall'operatore.
- **AUTOMATICO**: `avvia_flusso` auto-completa con `esito_default` senza scelta umana
  (un'unica azione "Avvia e completa"). Ammesso **solo** su `direzione = 'INTERNA'`
  (guard DB `trgfn_template_flussi_guard_modalita_esito`, Inv2).
- **CONTESTUALE**: la FE invia direttamente `nuovo_stato = COMPLETATO` da `DA_ESEGUIRE`;
  l'endpoint instrada ad `avvia_e_completa_flusso`, che porta `DA_ESEGUIRE → IN_CORSO →
  COMPLETATO` con l'esito confermato dall'operatore (`esito_default` pre-selezionato),
  in **una sola transazione** (la matrice transizioni non ha la 1→3 diretta: si passa
  sempre da `IN_CORSO`).

**Dispatch handler all'avvio**: se il flusso ha un `template_flusso_id` il cui
template ha un `handler_id` (tabella `pratiche.handler_flussi`), `avvia_flusso`
esegue l'handler (`dispatch_handler`) e, su successo, **completa** il flusso con
esito `esito_default` (fallback `POSITIVO` per i template con handler ma senza
`esito_default`, retro-compatibile col vecchio comportamento) — tutto in **una sola
transazione** (IN_CORSO + execute + COMPLETATO). L'auto-completamento scatta anche
quando `modalita_esito = AUTOMATICO` (anche **senza** handler). Su eccezione
dell'handler l'intera transizione rolla (il flusso torna `DA_ESEGUIRE`,
ri-eseguibile) e l'errore parlante propaga. Per i flussi MANUALE senza handler,
l'avvio porta solo a `IN_CORSO` (completamento manuale).

> `avvia_e_completa_flusso` (CONTESTUALE) **non** esegue l'handler di avvio: e' la
> modalita "esito deciso dall'operatore". Riusa `completa_flusso` per il
> completamento, quindi le azioni di dominio su evento `COMPLETATO`
> (`template_flussi_handler_eventi`, esito-aware) scattano comunque con l'esito scelto.

**Azioni di dominio al completamento (data-driven, 2026-06-15)**: al passaggio a
`COMPLETATO`, `completa_flusso` esegue gli handler server-side legati all'evento
in `pratiche.template_flussi_handler_eventi` (esito-aware: scattano solo se
`esito_richiesto` combacia con l'esito effettivo, `NULL` = qualsiasi), nella
**stessa transazione** del cambio stato. Esempio seedato: il flusso
`APPROVAZIONE_CLIENTE` di una pratica PREVENTIVI, completato `POSITIVO`, esegue
l'handler `vendita.accetta_preventivo` che porta il preventivo ROOT collegato ad
`ACCETTATO`. Sostituisce il vecchio endpoint dedicato M2: la FE chiama il
completamento **generico** e il motore esegue l'azione di dominio.

**Contesto d'azione al completamento (`meta`, 2026-06-30)**: il body può includere un
oggetto `meta` opzionale, inoltrato agli handler di evento `COMPLETATO` come `extra_meta`
(fuso sopra `flussi.meta`, **senza persisterlo**: è input d'azione, non stato — le scelte
durevoli le scrive l'handler sul dominio). È il canale con cui l'operatore passa i dati di
processo che l'esito richiede. Esempio: l'accettazione del preventivo nel percorso pratica
non usa più una politica neutra cablata: la FE apre il dialog di accettazione (modalità di
fatturazione + competenza) al completamento di `APPROVAZIONE_CLIENTE`, e l'handler
`vendita.accetta_preventivo` legge `meta.fatturazione_immediata` / `meta.competenza_mese` e
li persiste sul preventivo (DIFFERITA senza competenza → `E_VENDITA_COMPETENZA_RICHIESTA`).

La generazione automatica cross-pratica al completamento e' gestita dal trigger DB `trgfn_flussi_generazione`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/stato/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `nuovo_stato` (string, **obbligatorio**) — codice_interno dello stato (es. `IN_CORSO`, `COMPLETATO`, `SOSPESO`, `ANNULLATO`)
  - `esito` (string, obbligatorio se `nuovo_stato = COMPLETATO`) — `codice_interno` dal
    vocabolario `config.esiti_flussi_pratiche` (il FE lo alimenta via lookup generico,
    whitelist 2026-07-02). Gli **esiti di ramo** (`MERCE_PRESENTE`, `SOLO_SERVIZI`) sono
    calcolati dal dominio e **non selezionabili da questo endpoint** (guard
    `require_esito_selezionabile_operatore` → `E_FLUSSO_VALIDATION`)
  - `note_esito` (string, opzionale) — note sull'esito
  - `meta` (object, opzionale) — **contesto d'azione** del completamento, inoltrato agli
    handler di dominio su evento `COMPLETATO` (fuso sopra `flussi.meta`, **non persistito**
    sul flusso). Usato quando l'esito richiede dati di processo: es. l'accettazione del
    preventivo (`APPROVAZIONE_CLIENTE`/`POSITIVO`) riceve `{"fatturazione_immediata": bool,
    "competenza_mese": "YYYY-MM-DD"|null}` che l'handler persiste **sul preventivo**.
    Valido solo con `nuovo_stato = COMPLETATO` (instrada a `completa_flusso` /
    `avvia_e_completa_flusso`); ignorato sugli altri stati.

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: ownership mismatch (`E_FLUSSO_OWNERSHIP`), esito non valido o **esito di ramo non
  selezionabile manualmente** (`E_FLUSSO_VALIDATION`), `nuovo_stato` assente o vuoto
  (`E_FLUSSO_VALIDATION`, campo `nuovo_stato`), `nuovo_stato` che non esiste a catalogo
  (`E_FLUSSO_VALIDATION`, campo `nuovo_stato`; fino al 2026-10-20 era un `500
  E_CONFIG_MANCANTE`)
- `400`: completamento manuale di uno step con `modalita_esito = DOMINIO` (es.
  SMISTAMENTO: si chiude con l'azione di dominio dedicata) → `E_FLUSSO_VALIDATION`
  (guard `require_completamento_operatore_ammesso`, prima del guard DB di classe id 504)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)
- `409`: **pratica terminale** (`E_PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE`, catalogo DB id 491): transizione/modifica di un flusso di una pratica `CHIUSA`/`ANNULLATA`. Guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`.
- `409`: **chiusura prematura** (`E_PRATICHE_CHIUSURA_FLUSSO_PREMATURO`, catalogo DB id 492): il flusso "di chiusura" (`template_flussi.chiude_pratica`) non puo' essere completato finche' restano altri obbligatori bloccanti. Guard `trg_flussi_a10_guard_chiusura_prematura_upd`.
- `409`: **transizione non ammessa** (`E_FLUSSI_TRANSIZIONE_NON_AMMESSA`, catalogo DB id 302): la coppia `(stato_da, stato_a)` non e' in `config.transizioni_stati_flussi_pratiche` (attiva). Guard `trgfn_flussi_guard_transizione`.
- `400`: **esito obbligatorio** (`E_FLUSSI_ESITO_OBBLIGATORIO`, DATO_ERRATO, catalogo DB id 477): passaggio a `COMPLETATO` senza `esito` (raggiungibile solo via `cambia_stato_flusso`; `completa_flusso` valida l'esito a monte con `E_FLUSSO_VALIDATION`). Guard `trgfn_flussi_guard_esito_completato`.
- `400`: esito di classe sbagliata per lo step (`E_FLUSSI_ESITO_NON_AMMESSO`, DATO_ERRATO, guard DB id 504)

## Regole

- Ownership check prima di qualsiasi operazione; lo stato corrente del flusso (letto dal `get_flusso` di verifica) instrada il completamento (CONTESTUALE da `DA_ESEGUIRE` vs completamento da `IN_CORSO`).
- Se `nuovo_stato = COMPLETATO`, `esito` e' obbligatorio e deve esistere **attivo** nel
  vocabolario `config.esiti_flussi_pratiche` (lettura DB in
  `pratiche_service._require_esito_valido` — nessun mirror applicativo: un nuovo esito
  seedato e' automaticamente valido). In piu', sul percorso operatore (questo endpoint)
  l'esito deve essere un **verdetto** (`is_verdetto = true`): gli esiti di ramo
  (`is_verdetto = false`, es. `MERCE_PRESENTE`/`SOLO_SERVIZI`, calcolati dal dominio via
  `completa_step_pratica`) sono respinti dal guard `require_esito_selezionabile_operatore`
  con errore parlante `E_FLUSSO_VALIDATION`. Il Select FE filtra alla fonte sul campo
  `selezionabile_operatore` esposto dal lookup (derivato da `is_verdetto`).
- Se `nuovo_stato = COMPLETATO` e lo stato corrente è `DA_ESEGUIRE` (modalita CONTESTUALE), il servizio esegue `avvia_e_completa_flusso` (avvio + esito atomico); altrimenti `completa_flusso` da `IN_CORSO`.
- Se `nuovo_stato = IN_CORSO`, il servizio transiziona a `IN_CORSO` e, se il flusso ha un handler **o** `modalita_esito = AUTOMATICO`, lo completa con `esito_default` (vedi Contesto). L'utente acting è passato all'handler (`p_user` delle fn DB).
- Per qualsiasi altro stato, il servizio delega a `cambia_stato_flusso` con validazione stato non vuoto.
- Tutte le transizioni sono wrappate in `@transaction.atomic()`.
- Al completamento con esito, il trigger DB `trgfn_flussi_generazione` verifica le regole di generazione automatica (`auto = true`) e crea nuove pratiche se applicabile.
- **Chiusura workflow-driven** (2026-06-14): al completamento di un flusso il trigger `trgfn_flussi_autochiusura_pratica` puo' auto-chiudere la pratica padre (`APERTA → CHIUSA`, solo da `APERTA`). Modello misto: tipo prestazione **con** flusso di chiusura (`template_flussi.chiude_pratica`) → chiude al completamento di quel flusso; **senza** → chiude quando non restano obbligatori bloccanti (`fn_check_pratica_chiudibile`). Non esiste piu' un'azione manuale "Chiudi" lato FE.
- Il service traduce gli errori dei guard di cui sopra nei codici parlanti 491/492 via marker (`pratiche_service._KNOWN_DB_ERROR_MARKERS`).
- Permission: `cambia_stato_flusso` (area `pratiche`).

## Dipendenze DB

- `pratiche.flussi` (UPDATE stato_id, esito, note_esito)
- `config.stati_flussi_pratiche` (risoluzione codice_interno → id)
- `config.esiti_flussi_pratiche` (SELECT `attivo`, `is_verdetto` per la validazione
  esito: esistenza + selezionabilita' operatore)
- `pratiche.trgfn_flussi_generazione` (trigger su UPDATE per generazione automatica)
- `pratiche.trgfn_flussi_autochiusura_pratica` (trigger su UPDATE→COMPLETATO: auto-chiusura pratica)
- `pratiche.trgfn_flussi_guard_pratica_terminale` / `trgfn_flussi_guard_chiusura_prematura` (guard)
- `pratiche.template_flussi_handler_eventi` + `pratiche.handler_flussi` (binding handler per evento `COMPLETATO`, esito-aware, letti dal dispatch al completamento)

## Note di migrazione

- (2 luglio 2026) **Esiti data-driven end-to-end (`is_verdetto`)**: con il `Select` esiti
  FE diventato data-driven dal vocabolario globale (`config.esiti_flussi_pratiche` aggiunta
  alla whitelist del lookup generico core), serviva distinguere i **verdetti**
  dell'operatore dagli **esiti di ramo** calcolati dal dominio (`MERCE_PRESENTE`/
  `SOLO_SERVIZI`, bivio SMISTAMENTO — mai input utente). Risolto col riuso della colonna
  `is_verdetto` (DEFAULT false fail-closed, team DB): il lookup espone
  `selezionabile_operatore` derivato (il FE filtra il Select alla fonte), l'endpoint
  respinge i non-verdetto via `require_esito_selezionabile_operatore` (repo iniettabile,
  `E_FLUSSO_VALIDATION`), e la validazione di esistenza (`_require_esito_valido`) legge il
  vocabolario a DB. **Bonifica**: eliminati i mirror hardcoded `ESITI_FLUSSO_AMMESSI` e
  `ESITI_FLUSSO_RAMO` — una sola verità. I BB di dominio (`completa_step_pratica` →
  `completa_flusso`) restano liberi di passare gli esiti di ramo. Chiude
  `brief-db-esiti-flussi-selezionabilita.md` (opzione riuso, nessuna colonna nuova).
- (30 giugno 2026) **Contesto d'azione `meta` al completamento**: `completa_flusso` e
  `avvia_e_completa_flusso` accettano un `meta` opzionale, inoltrato a
  `dispatch_handler_eventi(..., extra_meta=meta)` e fuso sopra `flussi.meta` **senza
  persistenza**. Abilita l'accettazione preventivo uniforme al programma standalone:
  modalità di fatturazione + competenza scelte dall'operatore (non più politica neutra
  cablata né `handler_params` sul CONFERMA). L'handler `vendita.accetta_preventivo` legge i
  due valori da `meta` e li persiste sul preventivo; fallback retro-compatibile (meta assente
  → politica neutra). Vedi `analisi-uniformita-pratica-preventivi.md` (Fase 1).
- (17 giugno 2026) **Esito configurabile sullo step** (colonne `template_flussi.modalita_esito`
  e `esito_default`, migration `20260617-01`/`-02`): `avvia_flusso` auto-completa con
  `esito_default` quando l'handler ritorna un risultato **oppure** `modalita_esito =
  AUTOMATICO`; nuovo `avvia_e_completa_flusso` per la modalita CONTESTUALE (instradato
  dall'endpoint quando `COMPLETATO` arriva da `DA_ESEGUIRE`). Proiezione `get_flusso`
  arricchita con `template_modalita_esito`/`template_esito_default` (consumati dal
  `FlussoDrawer` FE); query leggera `PraticheRepository.get_flusso_esito_config` per il
  path di avvio. Validazione esito centralizzata (`_require_esito_valido` /
  `ESITI_FLUSSO_AMMESSI`). Le invarianti di coerenza del template (esito_default
  obbligatorio se non MANUALE; AUTOMATICO solo INTERNA) sono enforce-ate a config-time
  dal guard DB `trgfn_template_flussi_guard_modalita_esito` (codici 494/495), **non** da
  questo endpoint.
- La risoluzione stato avviene esplicitamente prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
- La generazione automatica cross-pratica e' completamente lato DB; il backend non ha logica di generazione automatica.
- (15 giugno 2026) Azioni di dominio al completamento **data-driven**: `completa_flusso`
  (e l'auto-completamento di `avvia_flusso`) eseguono gli handler legati all'evento
  `COMPLETATO` da `template_flussi_handler_eventi` (esito-aware), nella stessa
  transazione. `completa_flusso` riceve l'utente acting (`user`) inoltrato agli
  handler. Rimosso l'endpoint dedicato M2 (`approvazione-flusso/`): l'accettazione
  del preventivo e' ora l'handler `vendita.accetta_preventivo` su `APPROVAZIONE_CLIENTE`
  COMPLETATO+POSITIVO. Binding senza handler registrato → `E_HANDLER_NON_REGISTRATO` (fail-fast).
- (14 giugno 2026) Chiusura guidata dal workflow: auto-chiusura al completamento dei flussi (lato DB), rimossa l'azione manuale "Chiudi" dal FE. Aggiunti i codici parlanti 491 (pratica terminale) e 492 (chiusura prematura del flusso di chiusura), mappati via marker; `avvia/completa/cambia_stato_flusso` ora wrappano i `DatabaseError` in `_raise_known_db_error`.
