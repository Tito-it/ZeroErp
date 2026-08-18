# Brief BE/FE — Porta oneri + permessi prezzo commessa

> **Tipo**: brief BE/FE · **Target**: `dev/backend-tid` + FE · **Data**: 2026-07-21
> · **Owner**: Tid · **Priorità**: 🟠 ALTA
> **Stato**: 🟢 **REALIZZATO (2026-07-23)** — A1/A2/A3 · B1 · C1/C2 · test in
> working tree, **suite backend 3300 verdi**, build FE verde, guardrail i18n
> pulito. Prerequisiti DB erano pronti (apply dev + pgTAP verdi, 2026-07-21).
> **Seed `carica_voce_manuale` FATTO e applicato su dev** (id 29, area vendite,
> §6) e backend ricaricato: la porta è **operativa in-app**. Il changeset del
> team DB non è ancora pushato, quindi la riga CSV non si vede dal branch BE.
> **➡️ BRIEF CHIUSO (2026-07-27)**: validazione in-app fatta da Tid (all'epoca
> serviva prima ricostruire una catena minima — `vendite.commesse` era vuota su
> dev) e **C3 completato** (`E_ONERE_SEGMENT_DUPLICATO` → 409 `show_error_banner`
> in `error_policies.py`: senza, il codice cadeva sul fallback 400, che evidenzia
> i campi del form invece di invitare a riprovare).
> ⚠️ Il codice è nel working tree, **non committato**; il changeset del seed
> `carica_voce_manuale` non è pushato dal team DB (la riga CSV non si vede dal
> branch BE, ma è applicata su dev).
> **Origine**: step 10 («comunicazione BE/FE») del
> [brief-db-immutabilita-quantita-e-porta-oneri.md](brief-db-immutabilita-quantita-e-porta-oneri.md),
> che copre anche gli step 2 (ponte approvazione) e 8 (permessi prezzo N5/N7)
> lì dichiarati «fuori perimetro DB». Design a monte:
> [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md) DL-27.

## 1. Scopo e confine

Tre lavorazioni indipendenti (ordinabili a piacere; la C può andare per prima):

- **A — Porta oneri** (il pezzo di sostanza): endpoint + UI per «aggiungi onere»
  su commessa, wrapper della madre DB `vendite.fn_aggiungi_onere_commessa`.
  La riga nasce `APPROVATA`, qta=1, `tipo_movimento='ONERE'`, sourceless — tutta
  la disciplina è **già nel DB**; il BE aggiunge SOLO il presidio permessi
  (`post_permission`) e il passaggio parametri. Zero logica di business in Python.
- **B — Ponte approvazione (hardening)**: il push approva **le proprie righe**
  (`p_righe_ids`), non tutte le NON_EMESSA della commessa.
- **C — Permessi prezzo N5/N7**: cablare `post_permission` sui tre endpoint
  prezzo di commessa (riallinea / variazione eccezionale / sblocca), oggi coperti
  dal solo permesso generico di scrittura area vendite (trappola T2 del brief DB).

### Fuori perimetro

- Slice NC / righe negative in fattura (contratto rinviato dal brief DB §6).
- Processo automatico chiamante della porta (la madre DB lo supporta già; quando
  servirà, riuserà il service di questa slice — nessuna predisposizione extra).
- Admin CRUD del vocabolario `config.causali_onere` e degli articoli-onere: si
  gestiscono da seed CSV (DB); niente UI dedicata in v1.
- Guard immutabilità quantità (550/551): **nessun lavoro BE** — verificato che
  nessun percorso Python scrive `quantita`; al BE resta solo il mapping errori (§3.4).

## 2. Contratto DB (verificato sul vivo, 2026-07-21)

Firma reale della madre ([doc auto-gen](../../dbzero/vendite/funzioni/fn_aggiungi_onere_commessa.md)):

```sql
vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        bigint,   -- obbligatorio
  p_istanza_utility_id bigint,   -- obbligatorio
  p_articolo_onere_id  uuid,     -- obbligatorio: articolo con causale_onere_id NOT NULL
  p_importo            numeric,  -- obbligatorio, > 0 (il prezzo È l'importo, qta=1)
  p_tipo_doc_fiscale_id bigint,  -- obbligatorio (la riga nasce emittibile)
  p_motivo             text DEFAULT NULL,
  p_data_attivita      date DEFAULT NULL  -- default CURRENT_DATE
) RETURNS bigint  -- attivita_id
```

La fn deriva **da sola** causale, uom (e a valle IVA) dall'articolo-onere,
genera `segment_key = MAN:<commessa>:<progressivo>`, scrive l'audit su
`commesse_attivita_log` (evento `ONERE_AGGIUNTO`). Errori parlanti:
`E_PARAMETRO_INVALIDO`, `E_ONERE_IMPORTO_NON_VALIDO`, `E_ONERE_ARTICOLO_MANCANTE`.

Fatti a contorno:

- **5 articoli-onere seedati** (natura `SERVIZIO_UNA_TANTUM`, uom `NR`, IVA
  propria: 4×22%, penale Escluso art.15), uno per causale
  (`ONERE_SENZA_CONTRATTO`, `SPESE_TRASFERTA`, `MAGGIORAZIONE_URGENZA`,
  `SPESE_AMMINISTRATIVE`, `PENALE`). Discriminatore:
  `catalogo.articoli.causale_onere_id IS NOT NULL` (1:1, UNIQUE).
- `config.causali_onere` = vocabolario mono-lingua standard (`codice`,
  `descrizione`) — il FE **non lo interroga** in v1: la causale viaggia
  nell'articolo.
- La riga onere fa il giro completo onere→emissione→AF→fattura con IVA per-onere
  (pgTAP `test-porta-oneri-giro-completo-v1` 12/12); il contatore merce è cieco
  alle righe `MAN:` (tripla cintura, pgTAP dedicato).
- `config.tipi_doc_fiscale` è **già** nella whitelist lookup
  (`dbops_repository._REL_CONSENTITE`) → il FE la legge via lookupCodici,
  nessun endpoint nuovo.

## 3. Piano Backend

### 3.1 — A: endpoint «aggiungi onere»

`POST /api/v1/vendite/commesse/<int:commessa_id>/aggiungi-onere/`

- View `ApiCommessaAggiungiOnere(DomainAPIView)` in `apps/vendite/api/views.py`,
  `area_funzionale = "vendite"`, **`post_permission = "carica_voce_manuale"`**
  (codename nuovo, §6), pattern `handle_post_json` come le sorelle di commessa.
- Payload: `{ articolo_onere_id, importo, istanza_utility_id,
  tipo_doc_fiscale_id, motivo?, data_attivita? }`. Validazioni Python solo
  presenza/tipo (`ErrorManager.require` + assert); la semantica (importo > 0,
  articolo È un onere, attivo) resta al DB — non duplicarla.
- Service `commesse_service.aggiungi_onere_commessa(...)` → repo
  `commesse_repository.aggiungi_onere(...)` (wrapper 1:1 della fn, stesso stile
  di `approva_commessa_attivita`). Risposta: `{ attivita_id }` + eco della riga
  creata (riletta con i display fields della lista attività, così il drawer
  aggiorna senza seconda chiamata — [[feedback_display_fields_backend]]).
- `@extend_schema` su `post` (obbligo CI drf-spectacular).

### 3.2 — A: lookup articoli-onere

Estendere **`ApiArticoliLookup`** (catalogo) con filtro opzionale
`solo_oneri=true` → `WHERE causale_onere_id IS NOT NULL AND attivo`, e includere
nei risultati `causale_onere_codice`/`descrizione` + descrizione IVA quando il
filtro è attivo (display fields via JOIN). Niente endpoint dedicato
([[feedback_lookup_whitelist_first]] per spirito: si riusa la porta esistente).
⚠️ Nome parametro italiano, NON `format`/nomi riservati DRF
([[feedback_drf_format_magic_param]]).

### 3.3 — B: ponte approvazione (`p_righe_ids`)

In `commesse_service` il ponte post-push chiama oggi
`repo.approva_commessa_attivita(commessa_id=..., user=...)` senza `righe_ids`
(→ NULL → approva TUTTE le NON_EMESSA, anche righe non sue). Il repo supporta
già il parametro. Fix: gli handler del push raccolgono gli `attivita_id`
upsertati nella lavorazione corrente e il ponte li passa esplicitamente.
Prima del fix: grep dei test esistenti che assumono il comportamento «approva
tutto» ([[feedback_guard_breaks_existing_tests]] citato dal brief DB §4b) e
adeguarli — il nuovo comportamento è quello giusto, i test si allineano.
Nota: l'endpoint interattivo A-1 (`approva_attivita_commessa`, per selezione o
tutte) NON cambia — lì il «tutte» è una scelta esplicita dell'operatore.

### 3.4 — C: permessi prezzo N5/N7 + mapping errori

- Aggiungere **`post_permission = "prezzo_override_manuale"`** (codename
  esistente, già seedato area vendite) alle tre view in `apps/vendite/api/views.py`:
  `ApiCommessaAttivitaRiallineaPrezzo`, `ApiCommessaAttivitaVariazionePrezzoEccezionale`,
  `ApiCommessaAttivitaSbloccaPrezzo`. Coerente con i gate già vivi su
  preventivi/contratti/DDT; nessun codename nuovo.
- `error_policies.py`: mappare i codici DB nuovi → HTTP status + azione UI:
  `E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE` (550) e
  `E_ATTIVITA_FATTURABILE_QUANTITA_IMMUTABILE` (551) → 409;
  `E_ONERE_IMPORTO_NON_VALIDO` / `E_ONERE_ARTICOLO_MANCANTE` (+ eventuale codice
  del CHECK biconditional causale) → 400/422 secondo policy esistente. Nomi e
  numeri esatti dalla doc auto-gen / `config.messaggi_errore`, non da questo brief.

### 3.5 — C: codice 557 dalla slice DB «race segment_key» (2026-07-23)

Il fix DB della race sul progressivo `segment_key` della porta oneri
([brief-db-race-segment-key-onere.md](../work-done/brief-db-race-segment-key-onere.md),
sviluppato 2026-07-23) introduce un guard con un codice errore nuovo, che il BE
**deve registrare**:

```python
"E_ONERE_SEGMENT_DUPLICATO": ErrorPolicy(
    code="E_ONERE_SEGMENT_DUPLICATO",
    http_status=409,
    ui_action="show_error_banner",
    user_message="Onere non creato per una modifica concorrente. Riprovare.",
),
```

**409 e non 400**: non è un input da correggere, è un conflitto di concorrenza
**ritentabile** — stessa famiglia dei 409 di immutabilità qui sopra. Verificato:
senza questa voce il codice cade sul **fallback 400** dei codici `E_*` non
mappati, con azione UI sbagliata (l'operatore vedrebbe evidenziati i campi del
form invece di un invito a ripetere l'operazione).

Nessun'altra modifica BE: la firma di `vendite.fn_aggiungi_onere_commessa` non
cambia, quindi `commesse_repository.aggiungi_onere` e
`commesse_service.aggiungi_onere_commessa` restano identici.

## 4. Piano Frontend

Tutto dentro **`CommessaGestioneDrawer.vue`** (il drawer di governo, Fase A-4
cockpit) — nessuna vista nuova.

### 4.1 — Pannello «Aggiungi onere»

- Pulsante/pannello-azione visibile se `!isReadonly &&
  useActionPermission('carica_voce_manuale')` — stesso pattern del gate
  `canApprovare` già presente nel drawer.
- ⚠️ Il drawer post-DRAFT è `.app-readonly`: il pannello-azione va in wrapper
  **`app-escape`** ([[feedback_app_escape_pannelli_processo]] — 2 bug bloccanti
  storici trovati così).
- Dialog di caricamento con: **articolo-onere** (Select dai risultati di
  `articoli/lookup/?solo_oneri=true` — 5 voci, niente autocomplete server-side;
  mostrare descrizione + causale + IVA così l'operatore vede cosa sta
  caricando), **importo** (InputNumber > 0, valuta), **istanza utility**
  (lookup ricco esistente `anagrafiche/istanze-utility/lookup/` scopato sul
  billing account della commessa — [[feedback_billing_account_lookup]]),
  **tipo doc fiscale** (lookupCodici `config.tipi_doc_fiscale`), **motivo**
  (textarea opzionale), **data attività** (DatePicker, default oggi, opzionale).
- Conferma → `POST aggiungi-onere/` → toast esito + `ricaricaTutto()` (la riga
  appare APPROVATA nella lista attività). Errori DB → messaggio parlante
  dall'envelope, nessuna traduzione client dei codici.
- API client: nuovo metodo in `src/vendite/api/commesse.js`.

### 4.2 — Gate FE azioni prezzo (specchio di 3.4)

Le tre azioni riga esistenti (riallinea / variazione / sblocca) nel
`CommessaGestioneDrawer` vanno nascoste senza permesso:
`useActionPermission('prezzo_override_manuale')`, stesso predicato combinato
readonly+permesso già usato per l'approvazione. Oggi il menu le mostra a
chiunque scriva sull'area — dopo il cablaggio BE (3.4) fallirebbero con 403:
il gate FE le fa sparire invece ([[feedback_row_actions_menu]] per lo stile kebab).

### 4.3 — i18n

Chiavi nuove sotto `vendite.commesse.*` in **it.json E en.json**,
`scripts/check_i18n_keys.py` verde. Nessuna chiave per le causali (mono-lingua
dal DB, decisione ratificata nel brief DB §4c.3).

## 5. Test

- **Service** (`apps/vendite/tests/services/`, unittest + mock DB, CI-safe):
  aggiungi_onere passa i parametri alla fn e rilegge la riga; payload incompleto
  → `ServiceError`; ponte push chiama `approva_commessa_attivita` con i SOLI id
  upsertati (test del fix B, il più importante: fissa il contratto).
- **API** (`apps/vendite/tests/api/`): 403 senza `carica_voce_manuale`; 200 con
  permesso (fn mockata); 403 sulle tre view prezzo senza
  `prezzo_override_manuale` (oggi passerebbero — il test documenta la chiusura
  di T2); envelope errori 550/551/552+ → status della policy.
- Adeguamento test esistenti del push che assumono «approva tutto» (3.3).
- FE: smoke manuale nel drawer (validazione in-app Tid); nessun test FE
  automatico richiesto in v1.

## 6. Micro-prerequisito DB (una riga, team DB su `dev/db-tid`)

Append a `80_data/sql/config/azioni_processo.csv`:
codename **`carica_voce_manuale`**, `area_id = 2` (vendite), descrizione
«Carica voce manuale (onere) su commessa», `pericolosa = f`, `attivo = t` —
stesso formato della riga 26 (`approva_attivita_commessa`).
`prezzo_override_manuale` esiste già (riga 9): per la lavorazione C non serve
nulla lato DB. Il BE-A può partire subito e testare col permesso mockato;
serve il seed solo per la validazione in-app.

## 7. Documentazione da aggiornare a fine slice

- `docs/it/dev/api.md`: endpoint nuovo + `post_permission` aggiunti a N5/N7.
- Manuale backend (`docs/it/backend/vendite/manual/`): sezione porta oneri
  (struttura standard Scopo/Contesto/Input/Output/Regole/Dipendenze DB).
- Il brief DB gemello passa in `work-done/` insieme a questo.

## 8. Avanzamento

| # | Step | Stato |
|---|---|---|
| A1 | Endpoint + service + repo `aggiungi-onere` (`post_permission carica_voce_manuale`) (§3.1) | ✅ **FATTO (2026-07-23)** — `POST /vendite/commesse/<id>/oneri/` (`ApiCommessaOneri`, Idempotency-Key obbligatoria) → `commesse_service.aggiungi_onere_commessa` → `CommesseRepository.aggiungi_onere` (una SELECT di madre = unità atomica). Istanza utility **derivata dal BA della commessa** quando assente (scelta migliorativa rispetto al brief: la commessa è per costruzione (BA, utility) e il BA ha una sola istanza → campo tolto alla UI, override sempre possibile). Errori della madre tradotti col LORO codice via `ErrorManager.raise_from_database_error`. |
| A2 | Lookup articoli-onere: filtro `solo_oneri` su `ApiArticoliLookup` (§3.2) | ✅ **FATTO** — query param `solo_oneri`, JOIN `catalogo.articoli` + `config.causali_onere`, display fields `causale_onere_id/_codice/_descrizione` aggiunti solo quando il filtro è attivo. Nessun endpoint nuovo; il JOIN su `articoli` è ora condiviso col filtro natura (una volta sola, stesso alias). |
| A3 | FE pannello «Aggiungi onere» in `CommessaGestioneDrawer` (app-escape) (§4.1) | ✅ **FATTO** — azione in `DrawerActionsBar` (che applica `app-escape` e fa da gate nativo via `action: 'carica_voce_manuale'` + `hideWhenReadonly`) + `AppDialog` con Select ricco `app-lookup-option` (descrizione + tag IVA + causale: l'IVA è per-onere e va vista alla scelta), importo, tipo doc (`LookupSelect rel=config.tipi_doc_fiscale`), data e motivo. |
| B1 | Ponte approvazione: push passa `p_righe_ids` + adeguamento test (§3.3) | ✅ **FATTO** — `fn_batch_upsert_commessa_attivita` ritorna solo contatori: gli id si risolvono dalle chiavi naturali `(commessa_id, segment_key)` con `list_attivita_ids_by_segments` (un round-trip, `unnest` di due array), tracciati in `HandlerResult.attivita_ids_per_commessa` e passati al ponte. Nessuna riga = nessuna approvazione (le BOZZA di terzi restano intatte), ma la testata va comunque a PRONTA. 4 test esistenti adeguati al nuovo contratto + 1 nuovo che fissa il fix. |
| C1 | `post_permission prezzo_override_manuale` su N5/N7 + mapping errori 550-554 (§3.4) | ✅ **FATTO** — gate su tutte e tre le view prezzo di commessa; 6 codici registrati in `error_policies.py` (550/551 → **409**, oneri 552/553/554 + tipo_doc → 400). |
| C2 | FE gate azioni prezzo con `useActionPermission` (§4.2) | ✅ **FATTO** — `buildRowActions` ritorna vuoto senza `prezzo_override_manuale`: il kebab non propone azioni che finirebbero in 403. |
| C3 | Registrare `E_ONERE_SEGMENT_DUPLICATO` (557) → **409** in `error_policies.py` (§3.5) | ✅ **FATTO** (verificato 2026-07-27: `error_policies.py`, `http_status=409` + `show_error_banner`, messaggio «Onere non creato per una modifica concorrente. Riprovare.») — arriva dal fix DB della race sul progressivo `segment_key` ([brief-db-race-segment-key-onere.md](../work-done/brief-db-race-segment-key-onere.md), DB sviluppato 2026-07-23). Senza la voce il codice cade sul fallback **400** (azione UI sbagliata: campi del form evidenziati invece dell'invito a riprovare). Nessun'altra modifica BE: la firma della madre non cambia. |
| D1 | Seed `carica_voce_manuale` (team DB, §6) | ✅ **FATTO (2026-07-23)** — riga CSV scritta dal team DB e **applicata su dev**: verificato sul DB vivo `config.azioni_processo` id **29**, area `vendite`, `attivo=true`. Il changeset non è ancora pushato su `dev/db-tid` (per questo non compare nel working tree BE): arriverà col prossimo push del team DB |
| E1 | Test §5 verdi + i18n check verde | ✅ **FATTO** — `CommessaPortaOneriServiceTests` (7 casi: happy path, istanza esplicita, 8 payload invalidi, 404, traduzione dei 4 errori madre, fallback) + `VenditeCommessaOneriApiTests` (6 casi: ok, JWT, errore dominio, permesso negato/consentito, gate prezzo sui 3 endpoint). **Suite backend 3300 verdi**, `check_i18n_keys.py` pulito, `vite build` verde. |
| E2 | Doc §7 + validazione in-app Tid → brief in work-done | 🟡 **PARZIALE** — manuale [api_commessa_oneri.md](../../backend/vendite/manual/api_commessa_oneri.md) scritto + `api.md` aggiornato (bullet «Vendite — Commesse»). ✅ **Validazione in-app fatta (Tid, 2026-07-27)**. |
