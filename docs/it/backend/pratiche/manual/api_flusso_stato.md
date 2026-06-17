# API flusso_stato (Django)

## Scopo

Esporre via HTTP le transizioni di stato di un flusso: avvio (IN_CORSO), completamento (COMPLETATO con esito) e transizioni generiche (SOSPESO, ANNULLATO, ecc.).

## Contesto

Endpoint di scrittura con ownership check. Smista la richiesta in base al valore di `nuovo_stato`:

- `IN_CORSO` → `pratiche_service.avvia_flusso` (passa l'utente acting)
- `COMPLETATO` → `pratiche_service.completa_flusso` (con esito obbligatorio)
- Altro → `pratiche_service.cambia_stato_flusso` (transizione generica)

**Dispatch handler all'avvio**: se il flusso ha un `template_flusso_id` il cui
template ha un `handler_id` (tabella `pratiche.handler_flussi`), `avvia_flusso`
esegue l'handler (`dispatch_handler`) e, su successo, **completa** il flusso con
esito `POSITIVO` — tutto in **una sola transazione** (IN_CORSO + execute +
COMPLETATO). Su eccezione dell'handler l'intera transizione rolla (il flusso
torna `DA_ESEGUIRE`, ri-eseguibile) e l'errore parlante propaga. Per i flussi
senza handler, l'avvio porta solo a `IN_CORSO` (completamento manuale).

**Azioni di dominio al completamento (data-driven, 2026-06-15)**: al passaggio a
`COMPLETATO`, `completa_flusso` esegue gli handler server-side legati all'evento
in `pratiche.template_flussi_handler_eventi` (esito-aware: scattano solo se
`esito_richiesto` combacia con l'esito effettivo, `NULL` = qualsiasi), nella
**stessa transazione** del cambio stato. Esempio seedato: il flusso
`APPROVAZIONE_CLIENTE` di una pratica PREVENTIVI, completato `POSITIVO`, esegue
l'handler `vendita.accetta_preventivo` che porta il preventivo ROOT collegato ad
`ACCETTATO`. Sostituisce il vecchio endpoint dedicato M2: la FE chiama il
completamento **generico** e il motore esegue l'azione di dominio.

La generazione automatica cross-pratica al completamento e' gestita dal trigger DB `trgfn_flussi_generazione`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/stato/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `nuovo_stato` (string, **obbligatorio**) — codice_interno dello stato (es. `IN_CORSO`, `COMPLETATO`, `SOSPESO`, `ANNULLATO`)
  - `esito` (string, obbligatorio se `nuovo_stato = COMPLETATO`) — esito del flusso: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`
  - `note_esito` (string, opzionale) — note sull'esito

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: ownership mismatch (`E_FLUSSO_OWNERSHIP`), esito non valido (`E_FLUSSO_VALIDATION`), stato vuoto (`E_FLUSSO_VALIDATION`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)
- `409`: **pratica terminale** (`PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE`, catalogo DB id 491): transizione/modifica di un flusso di una pratica `CHIUSA`/`ANNULLATA`. Guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`.
- `409`: **chiusura prematura** (`PRATICHE_CHIUSURA_FLUSSO_PREMATURO`, catalogo DB id 492): il flusso "di chiusura" (`template_flussi.chiude_pratica`) non puo' essere completato finche' restano altri obbligatori bloccanti. Guard `trg_flussi_a10_guard_chiusura_prematura_upd`.
- `409`: **transizione non ammessa** (`FLUSSI_TRANSIZIONE_NON_AMMESSA`, catalogo DB id 302): la coppia `(stato_da, stato_a)` non e' in `config.transizioni_stati_flussi_pratiche` (attiva). Guard `trgfn_flussi_guard_transizione`.
- `409`: **esito obbligatorio** (`FLUSSI_ESITO_OBBLIGATORIO`, catalogo DB id 477): passaggio a `COMPLETATO` senza `esito` (raggiungibile solo via `cambia_stato_flusso`; `completa_flusso` valida l'esito a monte con `E_FLUSSO_VALIDATION`). Guard `trgfn_flussi_guard_esito_completato`.
- `500`: stato non trovato in config (`E_CONFIG_MANCANTE`)

## Regole

- Ownership check prima di qualsiasi operazione.
- Se `nuovo_stato = COMPLETATO`, `esito` e' obbligatorio e deve essere uno tra: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`.
- Se `nuovo_stato = IN_CORSO`, il servizio transiziona a `IN_CORSO` e, se il flusso ha un handler, lo esegue e completa il flusso (vedi Contesto). L'utente acting è passato all'handler (`p_user` delle fn DB).
- Per qualsiasi altro stato, il servizio delega a `cambia_stato_flusso` con validazione stato non vuoto.
- Tutte le transizioni sono wrappate in `@transaction.atomic()`.
- Al completamento con esito, il trigger DB `trgfn_flussi_generazione` verifica le regole di generazione automatica (`auto = true`) e crea nuove pratiche se applicabile.
- **Chiusura workflow-driven** (2026-06-14): al completamento di un flusso il trigger `trgfn_flussi_autochiusura_pratica` puo' auto-chiudere la pratica padre (`APERTA → CHIUSA`, solo da `APERTA`). Modello misto: tipo prestazione **con** flusso di chiusura (`template_flussi.chiude_pratica`) → chiude al completamento di quel flusso; **senza** → chiude quando non restano obbligatori bloccanti (`fn_check_pratica_chiudibile`). Non esiste piu' un'azione manuale "Chiudi" lato FE.
- Il service traduce gli errori dei guard di cui sopra nei codici parlanti 491/492 via marker (`pratiche_service._KNOWN_DB_ERROR_MARKERS`).
- Permission: `cambia_stato_flusso` (area `pratiche`).

## Dipendenze DB

- `pratiche.flussi` (UPDATE stato_id, esito, note_esito)
- `config.stati_flussi_pratiche` (risoluzione codice_interno → id)
- `pratiche.trgfn_flussi_generazione` (trigger su UPDATE per generazione automatica)
- `pratiche.trgfn_flussi_autochiusura_pratica` (trigger su UPDATE→COMPLETATO: auto-chiusura pratica)
- `pratiche.trgfn_flussi_guard_pratica_terminale` / `trgfn_flussi_guard_chiusura_prematura` (guard)
- `pratiche.template_flussi_handler_eventi` + `pratiche.handler_flussi` (binding handler per evento `COMPLETATO`, esito-aware, letti dal dispatch al completamento)

## Note di migrazione

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
