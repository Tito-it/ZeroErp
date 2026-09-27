# Analisi BE — Difetti di codice emersi dalla verifica delle doc API

> **Origine:** verifica «doc API contro codice», 2026-09-24, partita dal
> cantiere [brief-db-guard-date-validita.md](../work-done/brief-db-guard-date-validita.md)
> (Tid: *«mi faresti un controllo delle documentazione api che non coincide più
> con gli sviluppi»*, poi *«per gruppo, iniziamo da core»*). Letti a confronto
> i 47 documenti di `docs/it/backend/core/manual/` col codice, più
> `anagrafiche/manual/api_conti_bancari_ruolo.md`.
>
> **Cosa contiene:** i difetti **del codice** trovati per strada. Le doc
> vengono corrette a parte per descrivere il comportamento **attuale**, con un
> rimando qui accanto a ogni difetto aperto («⚠️ Difetto noto»). Quando un
> difetto si chiude, si aggiornano insieme il codice, la sua doc e la riga qui.
>
> **Stato:** ⏳ aperto — Tid (2026-09-24): *«partendo da quelle più gravi»*.
> Chiusi: **M-1** (e con lui **S-3**), **M-2**, **M-3**; **M-4** il
> 2026-09-25 nel cantiere accessi (lotto L-1); **F-2** il 2026-09-25 dal DB;
> **E-3, S-1, S-5, S-6, F-4, F-9** il 2026-09-27; **F-3** a metà. **M-5, M-6**
> restano nel cantiere accessi, lotto **L-5** ancora da fare
> ([piano-be-fe-accessi-credenziale-e-vesti.md](piano-be-fe-accessi-credenziale-e-vesti.md) §4.3).
> Le doc di `core/manual/` e `api_conti_bancari_ruolo.md` sono già
> allineate al comportamento attuale e rimandano qui (2026-09-24).
>
> **Ultima verifica sul codice: 2026-09-27**, sulle voci M-5, M-6, E-1, E-3,
> S-1, S-5, S-6, F-3, F-4, F-9. Le altre (E-2, E-4…E-10, S-2, S-4, F-1,
> F-5…F-8, §5) sono ferme al 2026-09-25.
>
> **Come leggere «Verificato»:** ✅ = riletto sul codice da chi scrive
> (2026-09-24); 🔎 = segnalato con prova `file:riga` dalla verifica per lotti,
> da rileggere prima di correggere.

---

## 1. Difetti del modello — priorità massima

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| M-1 | ✅ **CHIUSO 2026-09-24.** ~~La cache Redis dei permessi è per `auth_user`, ma i valori dipendono da veste ed emittente attivo~~ — più la riscrittura a ogni richiesta che rinnovava il TTL. Ora la chiave è (utente, **contesto di sessione**: identità + emittente **effettivo** della GUC, segnato da `set_jwt_gucs`); senza contesto la L2 non si usa; invalidazione per **generazione** utente/globale; scrittura solo se la richiesta ha aggiunto voci; il middleware non precarica più (non può conoscere il contesto). Test: `test_permissions_cache` (su LocMem vera), `test_permissions_cache_richiesta`, `test_jwt_audit_authentication` n. 13. Doc: `permissions_cache.md`, `permissions_resolver.md`, `jwt_audit_middleware.md`, catalogo BB | `core/services/permissions_cache.py`, `core/api/permissions.py`, `core/api/jwt_audit_authentication.py`, `core/middleware/jwt_audit_middleware.py` | ✅ |
| M-2 | ✅ **CHIUSO 2026-09-24** (ok Tid). ~~Il cambio password emette token senza veste~~: ora la sessione si riapre nella stessa veste con la catena del login, estratta nel BB `emetti_refresh_veste` (regola del 2: login + cambio password); l'identità si rilegge **prima** di cambiare la password (revocata → 401 `E_IDENTITA_NON_ATTIVA`, password intatta); l'audit LOGIN registra il `sid`. Test: `test_change_password_token_veste`. Doc: `api_token_cambio_password.md`, `api_multi_veste_token.md`, catalogo BB | `core/api/change_password_view.py`, `core/api/multi_veste_token_serializer.py` | ✅ |
| M-3 | ✅ **CHIUSO 2026-09-24** (strada decisa da Tid). ~~Invito portale/shop con email nuova: il reinvio è impossibile~~. Ora il flusso si sceglie sulla **credenziale** (`PortaleRepository.auth_user_ha_password`: l'utente creato da un invito resta col segnaposto `!` finché non attiva), non su «auth_user appena creato»; l'identità nasce `attivo=false` in **entrambi** i flussi e la accende il consumo del token (`_attiva_identita_o_rifiuta` nelle due view di attivazione, INVITO e CROSS); niente più password temporanea. Stato accessi: PENDING fino all'attivazione. ⚠️ Dati di sviluppo: gli invitati creati prima di oggi hanno una password temporanea *utilizzabile* e l'identità attiva — per loro il reinvio resta CROSS finché non si correggono a mano. Test: `test_reinvio_a_chi_non_ha_mai_attivato_resta_invito`, `test_flow_invito_identita_sparita_solleva`, happy path aggiornati. Doc: `api_invito_portale_shop.md`, catalogo BB | `portale/services/invito_portale_service.py`, `portale/db/portale_repository.py`, `portale/api/views.py`, `shop/api/views_attivazione.py` | ✅ |
| M-4 | ✅ **CHIUSO 2026-09-25** nel cantiere accessi, lotto L-1 ([piano](piano-be-fe-accessi-credenziale-e-vesti.md) §3.1-bis; DB: [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md) P-1). Tentativi e blocco ora stanno sulla **credenziale** + provenienza: `AuthRepository.check_blocco_login(uid, provenienza=)` / `registra_tentativo_login`, niente più `identita_id` né filtro sulla veste. ~~**Blocco login solo sulla veste OPERATORE.** `fn_check_blocco_login` e `fn_registra_tentativo_login` filtrano `ruolo_applicativo = 'OPERATORE'`: chi ha solo la veste portale o shop non viene mai bloccato, benché `PortaleTokenView` dichiari il contrario; chi è operatore e cliente viene bloccato come operatore sbagliando sul portale. ➜ ⭐ **Tid, 2026-09-24: il blocco è della CREDENZIALE, e il ciclo di vita degli accessi è uno solo per tutte le vesti** — cantiere a sé: [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md)~~ | `core/db/auth_repository.py`, `core/api/auth_views.py` | ✅ |
| M-5 | **Disattivare un operatore spegne tutte le vesti della credenziale** e le rinomina `DISABILITATO` (UPDATE su `identita_digitali` per `auth_user_id`, senza filtro sul ruolo). ➜ [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md) §3.1; si chiude col lotto L-5 del piano accessi (da fare, 2026-09-25) | `amm_software/db/amm_software_repository.py:343-346` (`disabilita_operatore` a riga 509) | ✅ |
| M-6 | **Riattivare un operatore porta a `OPERATORE` tutte le sue identità** (➜ L-5: `riattiva_operatore` si ritira, si riattiva col reinvio — D-3): su una credenziale con anche una veste cliente/fornitore il guard di coerenza e l'unique `(auth_user_id, ruolo_applicativo) WHERE attivo` la fanno fallire (deduzione dai vincoli, da provare con un caso costruito). ➜ [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md) §3.1 | `amm_software/db/amm_software_repository.py:539` (`riattiva_operatore`) | ✅ codice · 🔎 esito |

## 2. Contratto degli errori

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| E-1 | **Codici emessi ma non a catalogo** (niente classe, niente `ui_action`, niente ripiego): `E_ANAG_CONTO_NOT_FOUND`, `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` (un «non trovato» esce **400** «Errore di validazione.»), `E_GUC_RESET_FAILED`, `E_DB_ROLE_UNSAFE`, `E_CAMBIO_PASSWORD_RICHIESTO`, `E_CAMBIO_PASSWORD_CHECK_FALLITO`. ➜ righe nel CSV del catalogo: **richiesta al team DB** | `anagrafiche/error_codes.py:7-8`, `core/middleware/jwt_audit_middleware.py:187,214,225`, `core/middleware/password_change_middleware.py:79,92` | ✅ (i primi quattro) |
| E-2 | **Il cancello `test_ogni_codice_usato_e_dichiarato` non vede le costanti importate**: risolve solo quelle definite nello stesso modulo (`_costanti_modulo`). È il motivo per cui E-1 è passato. Va esteso agli import da `error_codes.py` (e simili), poi rieseguito: potrebbe trovare altri codici | `core/tests/test_error_codes_declared_guardrail.py:82-128` | ✅ |
| E-3 | ✅ **CHIUSO 2026-09-27.** La mappa di `drf_exception_handler` confronta per **classe** (`isinstance`, `_codice_drf`), non per nome: `InvalidToken` (token scaduto o illeggibile) esce 401 `E_AUTHENTICATION_FAILED` nell'envelope. Il FE guarda solo lo status 401: il refresh non cambia. Test: `test_drf_exception_handler` n. 5. ~~Token scaduto o invalido fuori envelope: `_DRF_ERROR_CODE_MAP` confronta il nome esatto della classe~~ | `core/api/error_responses.py` | ✅ |
| E-4 | **«Non trovato» / «negato» che escono 400**: `E_EMAIL_OP`, `E_EMAIL_ADMIN`, `E_OUTBOX`, `E_INVITO_PORTALE` («Cliente … non trovato»), `E_INVITO_OPERATORE` (tutti DATO_ERRATO); `user_id` inesistente in permessi effettivi/audit con `E_CORE_VALIDATION` | `core/api/email_views.py:62,68-72,217`, `amm_software/api/email_views.py:170,210,334`, `core/api/views.py:182-188,337-344` | 🔎 |
| E-5 | **I messaggi mirati di `ZeroERPPermission` non arrivano al client**: `drf_exception_handler` li sostituisce con la frase di `E_PERMISSION_DENIED`. Esistono già `E_REPARTO_SENZA_PROFILO` ed `E_USER_DISABILITATO`, mai sollevati | `core/api/permissions.py:124,146,248`, `error_responses.py:109-128` | 🔎 |
| E-6 | **Envelope incoerente per JSON non valido**: `invalid_json_response` / `invalid_payload_response` rispondono `{"error": "invalid_payload"}` (stringa, non oggetto); ogni `ValueError` sollevato dentro `handle_post_json` perde codice e messaggio | `core/api/error_responses.py:23-37`, `endpoint_helpers.py:163-175` | 🔎 |
| E-7 | **Conti bancari: ogni `IntegrityError` diventa `E_ANAG_DUPLICATO`** («già associato») anche per `uso` fuori elenco in PATCH (`CHECK`) o istanza inesistente (FK); PATCH senza campi ammessi → 404 «non trovata» | `anagrafiche/services/_validators.py:92-157`, `conti_bancari_repository.py:51-69` | ✅ |
| E-8 | **Refresh illeggibile → 403 `E_VESTE_NON_ATTIVA`** invece di 401 | `core/api/auth_views.py:320-327` | ✅ |
| E-9 | **Parametro inesistente nell'upsert override → `E_DATABASE`** (`parameter_id` NULL) invece di `E_PARAMETER_NOT_FOUND` 404 | `core/db/parameter_repository.py:168-172`, `parameter_service.py:145-149` | 🔎 |
| E-10 | **Dettaglio ricerca universale: mai 404.** `fn_get_search_detail` restituisce sempre `{tipo_ruolo, righe: []}`: il ramo `E_SEARCH_NOT_FOUND` è codice morto. Decidere il contratto (404 o lista vuota) | `core/api/search_view.py:289-294` | 🔎 |

## 3. Sicurezza e audit

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| S-1 | ✅ **CHIUSO 2026-09-27.** L'`X-Request-ID` del client si tiene solo se è un UUID (BB `optional_uuid`, forma canonica anche nella risposta); altrimenti se ne genera uno, senza rifiutare la richiesta. Test: `core/tests/middleware/test_request_context_middleware.py`. ~~Accettato senza controllo e scritto in colonne `uuid`: con un valore non-UUID l'INSERT dell'audit falliva~~ | `core/middleware/request_context_middleware.py` | ✅ |
| S-2 | **`JwtAuditMiddleware.process_view` inerte per i client Bearer**: `request.user` lì è AnonymousUser (lo dice la sua docstring). Precaricamento L2 e rifiuto dei DISABILITATO non scattano; resta solo `ZeroERPPermission`. Stesso schema da verificare in `PasswordChangeRequiredMiddleware.process_view` | `core/middleware/jwt_audit_middleware.py:98-140`, `password_change_middleware.py:53-55` | 🔎 |
| S-3 | ✅ **CHIUSO 2026-09-24 con M-1.** ~~`permissions_cache.invalidate_all()` non cancella niente~~: ora cambia la generazione globale, niente più `delete_pattern` | `core/services/permissions_cache.py` | ✅ |
| S-4 | **`get_ruolo_applicativo`, ripiego non deterministico**: `LIMIT 1` senza `ORDER BY` su un'identità attiva qualsiasi | `core/services/permissions_resolver.py:103-111` | 🔎 |
| S-6 | ✅ **CHIUSO 2026-09-27** (solo backend, decisione Tid). ⚠️ La diagnosi del 24-09 era più larga del difetto: letti i corpi, livelli d'area/oggetto e super admin esistono **solo per la veste OPERATORE** (passi 0-1 di `fn_resolve_livello_area`/`_oggetto`), e la GUC fa da cancello per chi guarda, non presta la veste al consultato: i livelli di un altro utente erano già giusti. Sbagliato era il solo campo `ruolo_applicativo` di permessi-effettivi (la veste di chi guarda: per un cliente del portale diceva OPERATORE, provato sul DB vero). Ora la risposta porta `veste_operatore_attiva` del consultato (`PermissionResolver.has_veste_operatore_attiva` → `script.fn_has_identita_attiva`); `get_ruolo_applicativo` dichiara che risponde per la sessione. Nessun consumatore FE dell'endpoint. Test: `test_permessi_effettivi_api` n. 7. Doc: `api_permessi_effettivi.md`, `permissions_resolver.md`, api.md §Identità | `core/api/views.py`, `core/services/permissions_resolver.py` | ✅ |
| S-5 | ✅ **CHIUSO 2026-09-27** (decisione Tid: la password non si tocca). ⚠️ La diagnosi del 24-09 era incompleta: anche il **login** ripuliva la password (`PasswordField` di SimpleJWT è un `CharField`, `trim_whitespace=True`), quindi i due lati erano coerenti e togliere lo strip solo in scrittura avrebbe chiuso fuori chi ha spazi ai bordi. Ora nessuno dei due la ripulisce: `SidTokenObtainPairSerializer` (tre porte) con `trim_whitespace=False`, e niente `.strip()` in reset, attivazione e cambio password (anche sulla password attuale). Lo username resta ripulito. Test: `test_multi_veste_token_serializer` n. 11 | `core/api/token_serializers.py`, `password_reset_views.py`, `attivazione_veste_views.py`, `change_password_view.py` | ✅ |

## 4. Funzionali

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| F-1 | **Bozza email bloccata in READY**: `confirm_and_send` porta a READY con commit e **dopo** cerca l'account; se manca resta READY, non rinviabile né annullabile | `core/services/email_outbox_service.py:140-144` | 🔎 |
| F-2 | ✅ **CHIUSO 2026-09-25** dal database ([brief-db-email-visibilita-per-ambito.md](../work-done/brief-db-email-visibilita-per-ambito.md) §8): «gli allegati si toccano solo in bozza» è il guard `config.trgfn_email_allegato_guard_solo_bozza` (`E_EMAIL_ALLEGATO_NON_BOZZA`, 409), che su una mail spedita rifiuta prima che il file venga toccato; `remove_attachment` lo lascia al DB, `add_attachment` lo dice prima di scrivere il file con lo stesso codice, `cancel_draft` toglie le righe prima di `CANCELLED`. Test: `core/tests/db/test_email_bozza_invio_db` n. 2-3. ~~**Si cancella l'allegato di una mail già spedita**: `remove_attachment` non controlla DRAFT, e `copy_allegati_to_log` aggiorna la stessa riga invece di copiarla~~ | `email_outbox_service.py`, `email_repository.py` | ✅ |
| F-3 | 🟡 **Metà chiusa.** ✅ I token precedenti si invalidano (BB `InvitoVeste.emetti`, A-4: dentro la transazione del nuovo). ⏳ Aperta: **`inviato: true` anche a email fallita** — `InvitoVeste.spedisci` logga l'errore e prosegue, il service risponde comunque `inviato: true` (verificato 2026-09-27) | `anagrafiche/services/invito_operatore_service.py`, `core/services/invito_veste.py` | ✅ |
| F-4 | ✅ **CHIUSO 2026-09-27.** `page`/`page_size` < 1 → 400 `E_VALIDATION_INPUT` prima del DB; `data_a` include il giorno (`valid_from < data + interval '1 day'`, idioma di `dbops_repository`), provato sul DB vero. Test: `test_permissions_audit` n. 15-16. ~~`page` ≤ 0 → OFFSET negativo; `data_a` esclude il giorno indicato~~ | `core/api/views.py`, `permissions_audit_repository.py` | ✅ |
| F-5 | **Override parametri asimmetrici**: upsert user/emittente e `delete_emittente_override` non includono `categoria_cliente_id` fra le colonne che devono essere NULL | `core/db/parameter_repository.py:198-251` | 🔎 |
| F-6 | **`/parameters/settings/`: `billing_account_id` non controllato** — inesistente = categoria NULL in silenzio, nessun controllo di scope | `core/api/views_parameters.py:264-273` | 🔎 |
| F-7 | **Note partizionate**: i vincoli locali di offerta/ordine/DDT/fattura cadono su `E_NOTA_VALIDATION` (400) invece del codice mappato | `partitioned_note_service.py:76-150` | 🔎 |
| F-8 | **Lookup codici oltre l'ultima pagina → `count: 0`** (`COUNT(*) OVER()` su pagina vuota) | `core/db/dbops_repository.py:466,496-497` | 🔎 |
| F-9 | ✅ **CHIUSO 2026-09-27**, e più largo del previsto: non solo il logout, ma **90 letture grezze di `request.data` in 35 file** (refresh del token compreso): con una lista nel corpo erano 500, e `dict(request.data)` su una lista di coppie la trasformava in un oggetto in silenzio. Ora tutte passano dal BB `corpo_oggetto(request)` (`payload_validators`, regola `oggetto_json` condivisa con `handle_post_json`): 400 `E_VALIDATION_INPUT` nell'envelope, anche per JSON illeggibile. Ritirate le 2 copie `isinstance(request.data, dict) else {}` di `documenti`. Test: `core/tests/api/test_corpo_oggetto.py`. Doc: api.md, catalogo BB | `core/api/payload_validators.py`, `request_parsers.py` + 35 view | ✅ |
| F-10 | **`parse_json_body` e body non UTF-8**: `UnicodeDecodeError` non ha il messaggio `invalid_json` | `core/api/request_parsers.py:19` | 🔎 |

## 5. Minori (docstring e percorsi)

- `EmittenteFiscaleScopeMixin` esce subito per il super admin e salta l'intersezione con l'emittente attivo che `fn_get_emittenti_scope_pk_ids` applica; il mixin non ha utilizzatori. Docstring ferma a «nessuna riga = vede tutto».
- `jwt_audit_middleware.py:76` dice «5 GUC» (sono 6); `permissions_resolver.py:62` cita `fn_is_super_admin*.sql` (i file sono `test-fn-is-super-admin*.sql`).
- `backend/deploy/sveglie.json`, chiave `_ritirate`: rimanda a `work-in-progress/brief-db-sveglia-dei-processi.md`, ora in `work-done/`.

## 6. Omissioni della doc (non difetti di codice)

- Le sei rotte `lookup/*` di `core/api/views_lookup.py` (`utilities-per-emittente`, `conti-contabili`, `tipi-ruoli-natura`, `sistema-codici`, `forme-giuridiche`, `comuni`; `urls_v1.py:141-174`) non hanno nessuna doc.
- Conti bancari del **soggetto** (`soggetti/<id>/conti-bancari/`) e i due lookup IBAN e filiali: nessuna doc; `api_conti_bancari_ruolo.md` copre solo il ruolo.

## 7. Richieste al team DB

- **E-1**: le sei righe nel CSV del catalogo codici (classe decisa sul modello: i due `*_NOT_FOUND` → NON_TROVATO; i due del middleware e `E_CAMBIO_PASSWORD_CHECK_FALLITO` → TECNICO; `E_CAMBIO_PASSWORD_RICHIESTO` → da decidere con Tid). Poi il BE rigenera e scrive i ripieghi.
- **M-4** (e M-5, M-6): non più una richiesta isolata — il brief DB è [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md) (P-1 e P-2 applicati il 2026-09-25); per M-5/M-6 resta il lotto BE L-5.
- ⚠️ **E-1 ancora aperta (2026-09-25)**: nessuno dei sei codici è in `error_policies_generated.py`. Il commit `3aaad8093` ha registrato altri codici (brief storico colonna FK), non questi.

---
{% include-markdown "signature-core.md" %}
