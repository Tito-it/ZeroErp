# Area 'core' (Backend)

## API
- [api-domain-conventions](manual/api-domain-conventions.md) — Definire uno standard unico per costruire future API di dominio.
- [api_config_tables](manual/api_config_tables.md) — Un solo gruppo di endpoint per **leggere e manutenere le tabelle di configurazione** (config.* e le altre della lista), senza scrivere una view per ognuna. E' il lato server del pannello di configurazione generico: il F…
- [api_diagnostics_error_envelope](manual/api_diagnostics_error_envelope.md) — Fornire un endpoint tecnico per validare contratto error envelope e policy retry.
- [api_email](manual/api_email.md) — Sistema completo di invio email con risoluzione automatica account SMTP e template per reparto/contesto. Supporta invio diretto, bozze editabili (outbox), allegati, consultazione log. Ogni email e' tracciata in config.e…
- [api_endpoint_helpers](manual/api_endpoint_helpers.md) — Centralizzare il flusso standard dei POST JSON (parse, validazione base, envelope, idempotenza).
- [api_gestione_code](manual/api_gestione_code.md) — Documentare gli endpoint della **UI di gestione code** (brief brief-be-fe-gestione-code-lavori-stampa): conteggi per il badge top bar, liste della coda lavori generica (dbops.coda_lavori) e della coda stampa (vendite.fa…
- [api_invito_operatore](manual/api_invito_operatore.md) — Permette all'admin di invitare un operatore via email. L'operatore riceve un link e attiva la sua **veste operatore**: sceglie la password se non ne ha ancora una, altrimenti conferma con un clic. Nessuna password viene…
- [api_invito_portale_shop](manual/api_invito_portale_shop.md) — Documenta i flussi end-to-end di **onboarding self-service** delle vesti non-operatore (CLIENTE_PORTALE, FORNITORE_PORTALE, SHOP_CUSTOMER). L'admin invia un invito email partendo dal cliente o fornitore anagrafico; l'ut…
- [api_logout](manual/api_logout.md) — Revoca la sessione del refresh token corrente (blacklist di tutti i token col suo sid), registra l'evento LOGOUT nella tabella dbops.sessioni_utente e cancella il cookie di refresh dal browser.
- [api_lookup_codici](manual/api_lookup_codici.md) — Espone una ricerca generica su tabelle di configurazione con struttura id / codice / descrizione. Permette autocompletamento e ricerca ILIKE da UI senza dover creare endpoint dedicati per ogni tabella config.
- [api_lookup_dedicati](manual/api_lookup_dedicati.md) — Descrivere i lookup **dedicati** di core che non hanno una pagina propria: tipi soggetto dettaglio, tipi ruolo per natura, forme giuridiche, utility per emittente, conti contabili, sistema codici e autocomplete dei comu…
- [api_multi_veste_token](manual/api_multi_veste_token.md) — Documenta il contratto HTTP degli endpoint di autenticazione post refactor multi-face (§8.3.1-§8.3.5): 3 login + 3 refresh, uno per namespace (admin / portale / shop). Ogni namespace espone solo il subset di vesti che g…
- [api_note_documento](manual/api_note_documento.md) — Il CRUD delle **note partizionate** appese a un documento: preventivo, offerta, contratto, ordine, DDT, fattura. **Un solo contratto**, sei montaggi — qui e' descritto una volta, e le pagine di dominio dicono solo cosa…
- [api_pagination](manual/api_pagination.md) — Leggere la finestra di ogni lista in un dialetto solo, `limit`/`offset`, e rispondere con l'envelope paginato standard.
- [api_parameter_settings](manual/api_parameter_settings.md) — Esporre via HTTP la gestione dei parametri di sistema con risoluzione override multi-livello (user, categoria cliente, group, emittente fiscale) e CRUD override (personale, emittente, categoria cliente).
- [api_parameters](manual/api_parameters.md) — Espone la gestione dei parametri di sistema (config.parameters) con risoluzione override multi-livello per l'utente autenticato. Supporta:
- [api_password_reset](manual/api_password_reset.md) — Permette all'operatore di reimpostare la propria password via email, senza intervento admin. Tre endpoint pubblici (non autenticati) con rate limiting.
- [api_permessi_audit](manual/api_permessi_audit.md) — Endpoint che restituisce la timeline audit delle modifiche ai permessi di un utente. Interroga le 8 tabelle storico del sistema permessi (5 per utente + 3 per reparto) con filtri opzionali e paginazione.
- [api_permessi_effettivi](manual/api_permessi_effettivi.md) — Esporre un endpoint diagnostico che restituisce i permessi effettivi risolti per un utente, iterando tutte le aree funzionali attive e mostrando il livello di accesso, le azioni consentite e lo stato del profilo reparto.
- [api_response_envelope](manual/api_response_envelope.md) — Definire il formato uniforme delle risposte successo/errore per tutte le API.
- [api_retry_policies](manual/api_retry_policies.md) — Uniformare gestione idempotency key e semantica retry lato API.
- [api_routing_core](manual/api_routing_core.md) — Indice delle rotte del dominio core: per ogni path, la view che lo serve e la doc che ne descrive il contratto.
- [api_search_universale](manual/api_search_universale.md) — Espone la ricerca universale soggetti a due livelli: lista paginata (livello 1) e dettaglio per tipo ruolo con row expansion (livello 2).
- [api_search_validation](manual/api_search_validation.md) — Evitare query di ricerca troppo generiche che degradano performance e selettivita`.
- [api_secondo_fattore](manual/api_secondo_fattore.md) — Gestisce il secondo fattore di autenticazione (codice a tempo, RFC 6238) di una credenziale: la configurazione fatta dalla persona stessa (QR, chiave, codici di recupero, conferma), la rigenerazione dei codici di recupe…
- [api_sessioni_attive](manual/api_sessioni_attive.md) — Permette all'utente autenticato di visualizzare le proprie sessioni attive (esclusa quella corrente) e di revocare sessioni sospette.
- [api_throttling](manual/api_throttling.md) — Limitare burst di chiamate sugli endpoint search per proteggere backend e DB, e i tentativi ripetuti sugli endpoint anonimi di login e reset password.
- [api_tipi_entita_lookup](manual/api_tipi_entita_lookup.md) — Restituire i **tipi di entità vivi** del catalogo config.tipi_entita — codice, etichetta_key (l'indirizzo i18n che il DB dichiara per ciascuno), key_selector — per i filtri e i picker che nominano *su quale cosa* è succ…
- [api_token_cambio_password](manual/api_token_cambio_password.md) — Building block per token monouso (inviti, reset password, conferme) e meccanismo di cambio password obbligatorio al primo accesso. I due componenti lavorano insieme: il flag deve_cambiare_password forza il cambio, il To…
- [api_tracciamento](manual/api_tracciamento.md) — Espone in lettura i tre livelli di tracciamento del sistema: audit log operativo, task registry multi-dominio e log esecuzioni job pgAgent. Fornisce agli anelli esterni e alla futura UI una vista unificata sulle operazi…
- [api_user_profile](manual/api_user_profile.md) — Restituisce il profilo completo dell'utente autenticato: dati anagrafici (soggetto), risorse umane, is_super_admin/ruolo_applicativo, dati emittente fiscale associato e **dettaglio dell'identita digitale del JWT corrent…
- [api_write_checklist](manual/api_write_checklist.md) — Fornire una checklist operativa pronta per nuovi endpoint write (POST/PUT/PATCH/DELETE con side effect).
- [error-handling-api](manual/error-handling-api.md) — Definire un contratto errore uniforme per tutte le API backend Django.
- [payload-validation-api](manual/payload-validation-api.md) — Centralizzare validazioni/coercizioni dei payload JSON API per ridurre logica duplicata nelle view dominio.
- [request-context-api](manual/request-context-api.md) — Assegnare metadati di correlazione request (request_id) e idempotenza (idempotency_key) in modo uniforme per tutte le API.
- [request-parsing-api](manual/request-parsing-api.md) — Centralizzare parsing JSON/body e parsing date ISO per le API Django.

## Utility
- [value-normalizer](manual/value-normalizer.md) — Centralizzare utility riusabili di normalizzazione valori input.

## Altri contenuti
- [auth_views_audit](manual/auth_views_audit.md) — Override delle view SimpleJWT per agganciare: (a) l'audit login/refresh nella tabella dbops.sessioni_utente, (b) lo stato della credenziale — blocco dell'admin, freno per provenienza, attesa crescente —, (c) il throttle…
- [gen-bk-docs](manual/gen-bk-docs.md) — Automatizzare la generazione degli indici index.md (e opzionalmente index.ci.md) per docs/it/backend/<area>/, includendo una descrizione breve estratta dalla sezione **Scopo**.
- [jwt_audit_authentication](manual/jwt_audit_authentication.md) — Subclass DRF di rest_framework_simplejwt.authentication.JWTAuthentication che, subito dopo un authenticate() di successo e prima che il view body inizi a scrivere:
- [jwt_audit_middleware](manual/jwt_audit_middleware.md) — Middleware Django per le request /api/*. Responsabilita':
- [permissions_cache](manual/permissions_cache.md) — Cache Redis L2 per i permessi utente. Integra la cache per-request (L1 dict) con Redis (L2) per evitare query DB su ogni richiesta HTTP.
- [permissions_resolver](manual/permissions_resolver.md) — Risolutore centrale dei permessi ZeroErp: una classe statica che **delega ogni decisione alle funzioni SQL script.fn_*** e tiene una cache per-request per non ripetere lo stesso round-trip due volte nella stessa richies…
- [request_log_middleware](manual/request_log_middleware.md) — Registrare ogni request API (/api/*, anonime comprese) nella tabella dbops.request_log con metodo, path, status, durata e utente.
- [session_audit_service](manual/session_audit_service.md) — Registrare eventi di sessione JWT (login, refresh, logout, revoca) nella tabella dbops.sessioni_utente.
- [sola_lettura_middleware](manual/sola_lettura_middleware.md) — Far girare ogni richiesta GET e HEAD delle API dentro una transazione di **sola lettura** garantita dal DB: una scrittura tentata dalla view fallisce, qualunque codice la tenti, e arriva come E_SCRITTURA_IN_LETTURA.
- [sveglie_processi](manual/sveglie_processi.md) — Dire **chi sveglia ogni processo automatico del backend**, con quale cadenza e **con quale riga di comando** — da una sede sola, leggibile da due programmi.
- [zeroerp_permission](manual/zeroerp_permission.md) — Permission class DRF centrale per ZeroErp. Risolve automaticamente l'area funzionale dallo schema del model e verifica il livello di accesso tramite PermissionResolver.
