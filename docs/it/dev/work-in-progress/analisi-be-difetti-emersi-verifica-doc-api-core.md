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
> **Stato:** ⏳ aperto — nessun difetto corretto. Ordine di lavoro da decidere
> con Tid. Le doc di `core/manual/` e `api_conti_bancari_ruolo.md` sono già
> allineate al comportamento attuale e rimandano qui (2026-09-24).
>
> **Come leggere «Verificato»:** ✅ = riletto sul codice da chi scrive
> (2026-09-24); 🔎 = segnalato con prova `file:riga` dalla verifica per lotti,
> da rileggere prima di correggere.

---

## 1. Difetti del modello — priorità massima

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| M-1 | **La cache Redis dei permessi è per `auth_user`, ma i valori dipendono da veste ed emittente attivo.** Dentro ci sono `ruolo_applicativo`, `area:*` (`fn_resolve_livello_area` legge `app.ruolo_applicativo`), `emittenti_pk_ids`, `emittente_for_user`. Nessuna invalidazione al cambio di emittente attivo né al login con un'altra veste. In più `_save_cache_to_redis` riscrive a **ogni** richiesta (la condizione `not already_from_redis or len(cache_dict) > 0` è sempre vera): il TTL di 300 s si rinnova e per un utente attivo la voce non scade mai. Effetto: un utente con due vesti, o che cambia emittente, può ricevere livelli e perimetro dell'altro contesto | `core/services/permissions_cache.py:23-25`, `core/api/permissions.py:253-276`, `core/services/permissions_resolver.py:115-286` | ✅ |
| M-2 | **Il cambio password emette token senza veste.** `RefreshToken.for_user(user)` non inietta `identita_id`, `ruolo_applicativo`, `sid`; il FE li installa e la richiesta dopo esce 401 `E_JWT_SENZA_IDENTITA`. Colpisce il cambio obbligatorio al primo accesso. Anche l'audit LOGIN registra il `jti` al posto del `sid`. Il token va emesso con la stessa catena del login | `core/api/change_password_view.py:97-103`, FE `core/views/ChangePasswordView.vue:44-45` | ✅ |
| M-3 | **Invito portale/shop con email nuova: il reinvio è impossibile.** Il primo invito crea `auth_user` + identità **già** `attivo=true`; il reinvio trova l'utente (`was_created=False`), passa al flow CROSS e `_ensure_identita` rifiuta «ha già accesso». Stato-accessi mostra ATTIVO a chi non ha mai attivato. Disattiva → reinvia passa, ma spedisce un token CROSS (senza scelta password) a chi ha solo la password temporanea | `portale/services/invito_portale_service.py:225-262, 505-517, 690-718` | ✅ |
| M-4 | **Blocco login solo sulla veste OPERATORE.** `fn_check_blocco_login` e `fn_registra_tentativo_login` filtrano `ruolo_applicativo = 'OPERATORE'`: chi ha solo la veste portale o shop non viene mai bloccato, benché `PortaleTokenView` dichiari il contrario. ➜ **lato DB** | `dbzero/script/funzioni/fn_check_blocco_login.md`, `auth_views.py:257-261` | ✅ |

## 2. Contratto degli errori

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| E-1 | **Codici emessi ma non a catalogo** (niente classe, niente `ui_action`, niente ripiego): `E_ANAG_CONTO_NOT_FOUND`, `E_ANAG_CONTO_SOGGETTO_NOT_FOUND` (un «non trovato» esce **400** «Errore di validazione.»), `E_GUC_RESET_FAILED`, `E_DB_ROLE_UNSAFE`, `E_CAMBIO_PASSWORD_RICHIESTO`, `E_CAMBIO_PASSWORD_CHECK_FALLITO`. ➜ righe nel CSV del catalogo: **richiesta al team DB** | `anagrafiche/error_codes.py:7-8`, `core/middleware/jwt_audit_middleware.py:187,214,225`, `core/middleware/password_change_middleware.py:79,92` | ✅ (i primi quattro) |
| E-2 | **Il cancello `test_ogni_codice_usato_e_dichiarato` non vede le costanti importate**: risolve solo quelle definite nello stesso modulo (`_costanti_modulo`). È il motivo per cui E-1 è passato. Va esteso agli import da `error_codes.py` (e simili), poi rieseguito: potrebbe trovare altri codici | `core/tests/test_error_codes_declared_guardrail.py:82-128` | ✅ |
| E-3 | **Token scaduto o invalido fuori envelope.** `InvalidToken` di SimpleJWT deriva da `AuthenticationFailed`, ma `_DRF_ERROR_CODE_MAP` confronta il nome esatto della classe: il 401 esce nel formato grezzo di DRF | `core/api/error_responses.py:85-109` | ✅ |
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
| S-1 | **`X-Request-ID` del client accettato senza controllo** e scritto in colonne `uuid`: con un valore non-UUID l'INSERT di `dbops.request_log` e di `dbops.sessioni_utente` fallisce (loggato e basta) → si perde l'audit di login e revoche. Il valore torna in risposta senza limite di lunghezza | `core/middleware/request_context_middleware.py:17`, `request_log_middleware.py:129`, `core/db/session_audit_repository.py:37` | ✅ |
| S-2 | **`JwtAuditMiddleware.process_view` inerte per i client Bearer**: `request.user` lì è AnonymousUser (lo dice la sua docstring). Precaricamento L2 e rifiuto dei DISABILITATO non scattano; resta solo `ZeroERPPermission`. Stesso schema da verificare in `PasswordChangeRequiredMiddleware.process_view` | `core/middleware/jwt_audit_middleware.py:98-140`, `password_change_middleware.py:53-55` | 🔎 |
| S-3 | **`permissions_cache.invalidate_all()` non cancella niente**: `delete_pattern` di django_redis aggiunge da sé prefisso e versione. Latente (nessun chiamante) | `core/services/permissions_cache.py:96` | 🔎 |
| S-4 | **`get_ruolo_applicativo`, ripiego non deterministico**: `LIMIT 1` senza `ORDER BY` su un'identità attiva qualsiasi | `core/services/permissions_resolver.py:103-111` | 🔎 |
| S-6 | **`get_ruolo_applicativo(user)` risponde per chi chiama, non per `user`**: legge prima la GUC `app.ruolo_applicativo` della richiesta e ignora l'argomento. In permessi-effettivi, consultando un altro utente, `ruolo_applicativo` è la veste del chiamante. Da verificare lo stesso effetto sui livelli d'area, perché `fn_resolve_livello_area` legge la stessa GUC | `core/services/permissions_resolver.py:92-115`, `core/api/views.py:200` | ✅ |
| S-5 | **Password ripulite dagli spazi**: reset e attivazione operatore fanno `.strip()` su `new_password` → la password salvata può differire da quella digitata | `core/api/password_reset_views.py:143-144`, `attivazione_view.py:76-77` | 🔎 |

## 4. Funzionali

| # | Difetto | Dove | Verificato |
| --- | --- | --- | --- |
| F-1 | **Bozza email bloccata in READY**: `confirm_and_send` porta a READY con commit e **dopo** cerca l'account; se manca resta READY, non rinviabile né annullabile | `core/services/email_outbox_service.py:140-144` | 🔎 |
| F-2 | **Si cancella l'allegato di una mail già spedita**: `remove_attachment` non controlla DRAFT, e `copy_allegati_to_log` aggiorna la stessa riga invece di copiarla | `email_outbox_service.py:291-296`, `email_repository.py:954-962` | 🔎 |
| F-3 | **Invito operatore `inviato: true` anche a email fallita**; `invia_invito` non invalida i token precedenti | `invito_operatore_service.py:46-152` | 🔎 |
| F-4 | **Permessi-audit**: `page` ≤ 0 → OFFSET negativo, errore DB; `data_a` esclude il giorno indicato (confronto con la mezzanotte) | `core/api/views.py:360-365`, `permissions_audit_repository.py:144-151` | 🔎 |
| F-5 | **Override parametri asimmetrici**: upsert user/emittente e `delete_emittente_override` non includono `categoria_cliente_id` fra le colonne che devono essere NULL | `core/db/parameter_repository.py:198-251` | 🔎 |
| F-6 | **`/parameters/settings/`: `billing_account_id` non controllato** — inesistente = categoria NULL in silenzio, nessun controllo di scope | `core/api/views_parameters.py:264-273` | 🔎 |
| F-7 | **Note partizionate**: i vincoli locali di offerta/ordine/DDT/fattura cadono su `E_NOTA_VALIDATION` (400) invece del codice mappato | `partitioned_note_service.py:76-150` | 🔎 |
| F-8 | **Lookup codici oltre l'ultima pagina → `count: 0`** (`COUNT(*) OVER()` su pagina vuota) | `core/db/dbops_repository.py:466,496-497` | 🔎 |
| F-9 | **Logout con body JSON a lista → 500** (`request.data.get` su una lista) | `core/api/logout_view.py:32` | 🔎 |
| F-10 | **`parse_json_body` e body non UTF-8**: `UnicodeDecodeError` non ha il messaggio `invalid_json` | `core/api/request_parsers.py:19` | 🔎 |

## 5. Minori (docstring e percorsi)

- `EmittenteFiscaleScopeMixin` esce subito per il super admin e salta l'intersezione con l'emittente attivo che `fn_get_emittenti_scope_pk_ids` applica; il mixin non ha utilizzatori. Docstring ferma a «nessuna riga = vede tutto».
- `jwt_audit_middleware.py:78` dice «5 GUC» (sono 6); `permissions_resolver.py:62` cita `fn_is_super_admin*.sql` (i file sono `test-fn-is-super-admin*.sql`).
- `backend/deploy/sveglie.json`, chiave `_ritirate`: rimanda a `work-in-progress/brief-db-sveglia-dei-processi.md`, ora in `work-done/`.

## 6. Omissioni della doc (non difetti di codice)

- Le sei rotte `lookup/*` di `core/api/views_lookup.py` (`utilities-per-emittente`, `conti-contabili`, `tipi-ruoli-natura`, `sistema-codici`, `forme-giuridiche`, `comuni`; `urls_v1.py:141-174`) non hanno nessuna doc.
- Conti bancari del **soggetto** (`soggetti/<id>/conti-bancari/`) e i due lookup IBAN e filiali: nessuna doc; `api_conti_bancari_ruolo.md` copre solo il ruolo.

## 7. Richieste al team DB

- **E-1**: le sei righe nel CSV del catalogo codici (classe decisa sul modello: i due `*_NOT_FOUND` → NON_TROVATO; i due del middleware e `E_CAMBIO_PASSWORD_CHECK_FALLITO` → TECNICO; `E_CAMBIO_PASSWORD_RICHIESTO` → da decidere con Tid). Poi il BE rigenera e scrive i ripieghi.
- **M-4**: il blocco login esteso alle vesti portale e shop.

---
{% include-markdown "signature-core.md" %}
