# Sviluppo — Multi-Face Auth (Portale Clienti, Portale Fornitori, Shop Online)

> Documento di pianificazione implementazione per il modello multi-face auth.
> Data creazione: 2026-04-18
> Stato: **Pianificazione iniziale** — da rivedere ed evadere in fasi
>
> Guida architetturale: [architettura-multi-face-auth](/guide/architettura-multi-face-auth)
>
> Doc collegate:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi)
> * [user_emittenti_fiscali (manual)](/dbzero/config/manual/user_emittenti_fiscali)
> * [risorse_umane_auth_user (manual)](/dbzero/anagrafiche/manual/risorse_umane_auth_user)
> * [profili_reparto_aree (manual)](/dbzero/config/manual/profili_reparto_aree)

---

## 1. Contesto

Oggi l'accesso al software e' modellato solo sul **dipendente interno** (risorsa
umana). Vogliamo estendere il modello per supportare:

* **Clienti** che accedono a un portale per vedere i propri documenti
* **Fornitori** che accedono a un portale per vedere ordini e pagamenti
* **Clienti del negozio online** con registrazione self-service

La guida architetturale spiega il **come** (nuovo bridge, profili generalizzati,
scope policy, RLS, namespace API separati). Questo WIP elenca **cosa fare
concretamente**, in ordine di dipendenza, con checkbox per tracciare l'avanzamento.

---

## 2. Principi guida per lo sviluppo

* **Additive, non distruttivo**: `risorse_umane_auth_user` resta in produzione
  fino a fine migrazione. Nuove tabelle convivono con quelle vecchie
* **DB-first**: le regole di scope vivono in funzioni SQL + RLS, non nel backend
* **Sviluppo concentrico**: DB → backend → frontend, per fascia di maturita'
  (vedi `docs/it/sviluppo-concentrico.md`)
* **Nessun hardcoded**: usare codici e lookup, mai ID numerici
* **Test prima di attivare**: ogni fase ha una suite pgTAP + Django + smoke
  prima di essere dichiarata chiusa

---

## 3. Prerequisiti da verificare (esplorativo)

Prima di scrivere DDL, verificare l'attuale stato del sistema per evitare
sorprese:

- [ ] 3.1 Leggere [risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)
      e censire **tutti** i trigger BEFORE/AFTER attualmente installati
- [ ] 3.2 Censire chi chiama `fn_sync_auth_user_is_active` (trigger, management
      command, codice Python) per stimare l'impatto della generalizzazione
- [ ] 3.3 Censire tutte le view/API che oggi usano `EmittenteFiscaleScopeMixin`
      e quelle che filtrano manualmente per `auth_user`
- [ ] 3.4 Verificare che [token_monouso](/dbzero/config/tabelle/token_monouso)
      supporti l'aggiunta di nuovi `tipo_token` (INVITO_PORTALE, VERIFICA_EMAIL_SHOP)
      senza breaking change
- [ ] 3.5 Verificare che il ruolo DB applicativo (`zeroerp_app`) abbia i grant
      corretti per leggere `identita_digitali` (nuova tabella)
- [ ] 3.6 Valutare costo performance RLS sulle tabelle principali (fatture,
      ordini, DDT) — benchmark con 100k righe prima dell'attivazione
- [ ] 3.7 Redigere nota decisionale su: **l'admin di portale esiste?**
      (cioe': un cliente puo' gestire utenti-figli sul suo portale?)
      Decisione impatta §5.2 e §7.3
- [ ] 3.8 **Documentazione RLS — linee guida SQL**: aggiungere sezione
      "Row Level Security" in [linee-guida-sql.md](/linee-guida-sql). Contenuti:
      * Quando usarla (tabelle con scope multi-tenant/multi-cliente/multi-fornitore)
      * Naming policy: `rls_<tabella>_<scope>` (es. `rls_fatture_ba_ownership`)
      * Obbligo di logica in funzioni `script.fn_scope_*` (testabilita' pgTAP)
      * Bypass esplicito per ruoli DB di manutenzione (`zeroerp_admin`, `zeroerp_migration`)
      * Uso di `USING` vs `WITH CHECK`
      * Defense-in-depth: RLS si **somma** al filtro applicativo, non lo sostituisce
      * Riferimento obbligatorio ai GUC `app.*` come input
- [ ] 3.9 **Documentazione RLS — scheda PostgreSQL**: creare
      `docs/it/postgresql/row-level-security.md` con:
      * Sintassi `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `CREATE POLICY`
      * Differenza comportamentale `USING` vs `WITH CHECK`
      * Interazione con i GUC `app.*` (link a
        [parametri-personalizzati-(GUC)](/postgresql/parametri-personalizzati-(GUC)))
      * Troubleshooting: policy "silent" che nasconde righe senza errore,
        pattern di debugging (`SET ROLE` di test, `row_security = off` per superuser)
      * Performance: indici funzionali su colonne usate nella policy,
        impatto su `EXPLAIN`, `pg_stat_statements`
      * Convivenza con viste e funzioni `SECURITY DEFINER`
- [ ] 3.10 Le due schede §3.8 e §3.9 sono **prerequisito** per §4.9
      (attivazione RLS) — servono come riferimento quando si scrivono le prime
      policy, non dopo. Da evadere prima dell'inizio della Fase DB se il team
      non ha esperienza pregressa di RLS Postgres

---

## 4. Fase DB — Fondamenta (schema + funzioni)

### 4.1 ENUM nuovi / estensioni

- [ ] 4.1.1 Creare ENUM `config.ruolo_applicativo` con valori:
      `OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`,
      `API_CLIENT`, `DISABILITATO`
- [ ] 4.1.2 Creare ENUM `config.tipo_profilo_accesso` con valori:
      `REPARTO`, `PORTALE`, `AD_HOC`
- [ ] 4.1.3 Valutare estensione ENUM `config.tipo_token` con
      `INVITO_PORTALE`, `VERIFICA_EMAIL_SHOP`

### 4.2 Tabella bridge `identita_digitali`

- [ ] 4.2.1 Creare `anagrafiche.identita_digitali` con campi e UNIQUE come da guida §3.1
- [ ] 4.2.2 Audit trigger standard (`trgfn_audit_data_user_generic`)
- [ ] 4.2.3 Trigger guard `trgfn_identita_digitali_guard_coerenza`:
      * se `ruolo_applicativo = OPERATORE` -> `soggetto_ruolo` deve essere RIS_UMANA su PF pura
      * se `ruolo_applicativo = CLIENTE_PORTALE` -> tipo_ruolo CLIENTE
      * se `ruolo_applicativo = FORNITORE_PORTALE` -> tipo_ruolo FORNITORE
      * se `ruolo_applicativo = SHOP_CUSTOMER` -> tipo_ruolo CLIENTE
- [ ] 4.2.4 Trigger UNIQUE parziale: una sola identita' attiva per auth_user
      (indice `ON (auth_user_id) WHERE attivo = true`)
- [ ] 4.2.5 Policy ATTIVO (child/parent framework) — coerenza con pattern
      esistente (es. `trgfn_prevent_deactivate_if_children`)

### 4.3 Profili accesso generalizzati

- [ ] 4.3.1 Creare `config.profili_accesso` (id, tipo, codice, descrizione, attivo)
- [ ] 4.3.2 Creare `config.profili_accesso_aree` (rimpiazzo concettuale di `profili_reparto_aree`)
- [ ] 4.3.3 Creare `config.profili_accesso_azioni` (rimpiazzo concettuale di `profili_reparto_azioni`)
- [ ] 4.3.4 Creare `config.profili_accesso_bindings` con CHECK che **esattamente uno**
      tra `unita_organizzativa_id`, `identita_digitale_id`, `ruolo_applicativo` sia valorizzato
- [ ] 4.3.5 Migrazione dati: popolare `profili_accesso` con un record per ogni
      riga oggi in `profili_reparto_aree` (tipo=REPARTO)
- [ ] 4.3.6 Backfill `profili_accesso_bindings` con i binding reparto -> profilo
- [ ] 4.3.7 Seed iniziale profili portale:
      * `CLIENTE_PORTALE_STANDARD` (LETTURA su vendite, LETTURA su pagamenti)
      * `FORNITORE_PORTALE_STANDARD` (LETTURA su acquisti, LETTURA su pagamenti)
      * `SHOP_CUSTOMER_STANDARD` (LETTURA su storico ordini propri)
- [ ] 4.3.8 Binding dei profili seed al relativo `ruolo_applicativo`

### 4.4 Scope policy generalizzato

- [ ] 4.4.1 Creare `config.scope_policy` (id, codice, descrizione, funzione_db)
- [ ] 4.4.2 Creare `config.identita_scope_bindings` (bigint id, identita_digitale_id,
      scope_policy_id, parametri JSONB)
- [ ] 4.4.3 Seed `scope_policy`:
      * `EF_WHITELIST` -> `script.fn_scope_ef_whitelist`
      * `BA_OWNERSHIP` -> `script.fn_scope_ba_ownership`
      * `FORNITORE_OWNERSHIP` -> `script.fn_scope_fornitore_ownership`
      * `SELF_OWNERSHIP` -> `script.fn_scope_self_ownership` (shop)
- [ ] 4.4.4 Scrivere le 4 funzioni `fn_scope_*` in `script` schema
- [ ] 4.4.5 Backfill: per ogni riga in `user_emittenti_fiscali` creare binding
      `EF_WHITELIST` sulla corrispondente identita'

### 4.5 Generalizzazione sync `auth_user.is_active`

- [ ] 4.5.1 Riscrivere `fn_sync_auth_user_is_active` in modo che parta da
      `auth_user_id` e trovi il bridge attivo (identita_digitali)
- [ ] 4.5.2 Algoritmo nuovo come da guida §9 (gestisce tutti i ruoli applicativi)
- [ ] 4.5.3 Trigger `trg_identita_digitali_sync_auth_user_active` su INSERT/UPDATE
- [ ] 4.5.4 Compatibilita' con trigger esistenti su `risorse_umane_auth_user`
      (la funzione interna non cambia API, cambia solo implementazione)
- [ ] 4.5.5 Estendere `fn_sync_auth_user_expired` per coprire anche le identita'
      portale con `valido_al` scaduto
- [ ] 4.5.6 Test pgTAP sync per ogni tipo di identita' (operatore, cliente portale,
      fornitore portale, shop customer)

### 4.6 Vista di compatibilita'

- [ ] 4.6.1 Creare vista `anagrafiche.vw_risorse_umane_auth_user` che
      riproduce il vecchio layout di `risorse_umane_auth_user` leggendo
      da `identita_digitali WHERE ruolo_applicativo = 'OPERATORE'`
- [ ] 4.6.2 Verificare che tutto il codice che oggi scrive su
      `risorse_umane_auth_user` sia migrato a `identita_digitali` prima di
      sostituire la tabella con la vista
- [ ] 4.6.3 Rinominare `risorse_umane_auth_user` in `_legacy_risorse_umane_auth_user`
      e creare la vista con il nome originale (cutover)

### 4.7 GUC e propagazione identita'

- [ ] 4.7.1 Documentare i nuovi GUC in [docs/it/postgresql/parametri-personalizzati-(GUC).md](/postgresql/parametri-personalizzati-(GUC))
      * `app.current_identita_id`
      * `app.ruolo_applicativo`
      * `app.soggetto_ruolo_id`
- [ ] 4.7.2 Funzione di convenienza `script.fn_current_identita_context()`
      che legge tutti i GUC e restituisce un record composito

### 4.8 Funzioni risoluzione permessi

- [ ] 4.8.1 Generalizzare `fn_resolve_livello_area` per usare `profili_accesso`
      invece di `profili_reparto_aree` — mantenere la stessa firma esterna
- [ ] 4.8.2 Generalizzare `fn_resolve_livello_oggetto` stessa logica
- [ ] 4.8.3 Generalizzare `fn_check_azione_processo`
- [ ] 4.8.4 Test pgTAP: verificare che gli operatori esistenti mantengano lo
      stesso risultato (regression test)

### 4.9 Row Level Security (RLS) — prima ondata

> **Nota:** attivare RLS solo dopo che backend e frontend sono pronti a
> popolare i GUC per ogni tipo di utente. Altrimenti le query esistenti si bloccano.

- [ ] 4.9.1 Abilitare RLS su `vendite.fatture` con policy `BA_OWNERSHIP` per CLIENTE_PORTALE
- [ ] 4.9.2 Abilitare RLS su `vendite.ordini` con stessa policy
- [ ] 4.9.3 Abilitare RLS su `pagamenti.scadenze` con stessa policy
- [ ] 4.9.4 Abilitare RLS su `acquisti.ordini` con policy `FORNITORE_OWNERSHIP`
- [ ] 4.9.5 Abilitare RLS su `acquisti.ddt_ingresso` con stessa policy
- [ ] 4.9.6 Abilitare RLS su `anagrafiche.billing_account` (CLIENTE_PORTALE vede solo i propri)
- [ ] 4.9.7 Esenzione policy per ruolo DB `zeroerp_admin` / superuser (bypass RLS)
- [ ] 4.9.8 Benchmark performance pre/post su query chiave (list fatture, list ordini)

---

## 5. Fase Backend — Autenticazione e Authorization

### 5.1 Model ORM

- [ ] 5.1.1 Creare `IdentitaDigitale` (managed=False) su `apps/anagrafiche/models.py`
- [ ] 5.1.2 Creare `ProfiloAccesso`, `ProfiloAccessoArea`, `ProfiloAccessoBinding`
- [ ] 5.1.3 Creare `ScopePolicy`, `IdentitaScopeBinding`
- [ ] 5.1.4 Marcare `RisorseUmaneAuthUser` come deprecato (docstring + pre-commit warning)

### 5.2 Refactor `PermissionResolver`

- [ ] 5.2.1 Riscrivere `_get_livello_reparto` come `_get_livello_da_profilo_accesso`
      (parametrico per tipo di binding)
- [ ] 5.2.2 Aggiungere step "profilo da ruolo applicativo" nella catena di risoluzione
- [ ] 5.2.3 Aggiungere classificazione `ruolo_applicativo` nel resolver
      (bypass per OPERATORE+ADMIN resta come oggi; portale segue la catena standard)
- [ ] 5.2.4 Test unitari: regression + casi portale/shop

### 5.3 Estensione `JwtAuditAuthentication`

- [ ] 5.3.1 Dopo `super().authenticate()`, risolvere l'identita' digitale attiva
      dell'utente
- [ ] 5.3.2 Propagare i 3 nuovi GUC (`app.current_identita_id`,
      `app.ruolo_applicativo`, `app.soggetto_ruolo_id`)
- [ ] 5.3.3 Se nessuna identita' attiva -> fallire l'autenticazione con 401
      (edge case: utente orfano)
- [ ] 5.3.4 Cleanup dei nuovi GUC in `JwtAuditMiddleware.process_response`
      (simmetria con quelli esistenti)
- [ ] 5.3.5 Aggiornare `JwtMockedApiTest` per mockare anche i nuovi GUC

### 5.4 Namespace API

- [ ] 5.4.1 Creare `PortaleBasePermission` che ammette solo `ruolo_applicativo IN
      (CLIENTE_PORTALE, FORNITORE_PORTALE)`
- [ ] 5.4.2 Creare `ShopBasePermission` che ammette `SHOP_CUSTOMER` oppure
      utente anonimo (per endpoint catalogo)
- [ ] 5.4.3 Creare `PortaleAPIView` come base class sotto `apps/portale/api/base.py`
- [ ] 5.4.4 Creare `ShopAPIView` come base class sotto `apps/shop/api/base.py`
- [ ] 5.4.5 Registrare routing separato:
      * `/api/admin/*` (resta quello attuale con `ZeroERPPermission`)
      * `/api/portale/*` (nuovo)
      * `/api/shop/*` (nuovo, throttle aggressivo)
- [ ] 5.4.6 Middleware throttle per endpoint shop pubblici (anti-spam)

### 5.5 Service invito portale

- [ ] 5.5.1 Creare `apps/portale/services/invito_portale_service.py`
      simmetrico a `InvitoOperatoreService`
- [ ] 5.5.2 Nuovo tipo token `INVITO_PORTALE` in `token_monouso`
- [ ] 5.5.3 Template email dedicato `portale_invito.html` (personalizzabile per
      ruolo applicativo)
- [ ] 5.5.4 Endpoint `POST /api/admin/clienti/{id}/invita-portale/`
- [ ] 5.5.5 Endpoint `POST /api/admin/fornitori/{id}/invita-portale/`
- [ ] 5.5.6 Endpoint `POST /api/portale/attivazione/conferma/` (cambio password
      + attivazione identita_digitali)
- [ ] 5.5.7 Test API completi per entrambi i flussi

### 5.6 Service registrazione shop

- [ ] 5.6.1 Creare `apps/shop/services/registrazione_service.py` con transazione
      atomica (soggetto + ruolo + cliente + billing_account + auth_user + identita)
- [ ] 5.6.2 Validazione email unica tra `auth_user.email`
- [ ] 5.6.3 Tipo token `VERIFICA_EMAIL_SHOP` con scadenza 24h
- [ ] 5.6.4 Template email `shop_verifica_email.html`
- [ ] 5.6.5 Endpoint pubblico `POST /api/shop/register/` (throttle 3 req / 1h per IP)
- [ ] 5.6.6 Endpoint `GET /api/shop/verifica-email/{token}/`
- [ ] 5.6.7 Test end-to-end: registrazione -> email -> clic link -> login riuscito

### 5.7 API portale (primo slice)

Primo set di endpoint sufficienti per un MVP del portale cliente:

- [ ] 5.7.1 `GET /api/portale/me/` — profilo utente corrente
- [ ] 5.7.2 `GET /api/portale/billing-account/` — lista propri BA (filtrata RLS)
- [ ] 5.7.3 `GET /api/portale/fatture/` — lista proprie fatture
- [ ] 5.7.4 `GET /api/portale/fatture/{id}/` — dettaglio fattura
- [ ] 5.7.5 `GET /api/portale/fatture/{id}/pdf/` — download PDF
- [ ] 5.7.6 `GET /api/portale/scadenze/` — scadenzario proprio
- [ ] 5.7.7 Smoke test end-to-end con utente CLIENTE_PORTALE di test

### 5.8 API portale fornitori (primo slice)

- [ ] 5.8.1 `GET /api/portale/ordini-ricevuti/` — ordini ricevuti dal fornitore
- [ ] 5.8.2 `GET /api/portale/ordini-ricevuti/{id}/`
- [ ] 5.8.3 `GET /api/portale/pagamenti-verso-di-me/` — stato pagamenti
- [ ] 5.8.4 Smoke test end-to-end con utente FORNITORE_PORTALE di test

### 5.9 API shop (primo slice)

- [ ] 5.9.1 `GET /api/shop/catalogo/` — pubblico, no auth
- [ ] 5.9.2 `GET /api/shop/catalogo/{sku}/` — pubblico
- [ ] 5.9.3 `POST /api/shop/carrello/` — anonimo via session id o autenticato
- [ ] 5.9.4 `POST /api/shop/checkout/` — richiede SHOP_CUSTOMER autenticato
- [ ] 5.9.5 `GET /api/shop/ordini/` — storico ordini propri (RLS)
- [ ] 5.9.6 Smoke test end-to-end

### 5.10 Sicurezza e hardening

- [ ] 5.10.1 Rate limit su login portale (5 tentativi / 5 minuti per IP)
- [ ] 5.10.2 Rate limit su reset password shop (3 / 15 min per IP)
- [ ] 5.10.3 Email template di **sicurezza**: notifica all'utente ad ogni cambio password
- [ ] 5.10.4 Audit sessioni: estendere `dbops.sessioni_utente` con colonna `ruolo_applicativo`
- [ ] 5.10.5 Headers di sicurezza dedicati per `/api/shop/*` e `/api/portale/*`
      (CSP restrittivo, no-cache documenti sensibili)

---

## 6. Fase Frontend — Due app separate + bridge admin

### 6.1 Navigazione e build

- [ ] 6.1.1 Decisione: frontend unico con router guard per ruolo **oppure**
      build separati (admin / portale / shop). Valutazione bundle size + UX.
- [ ] 6.1.2 Se unico: aggiungere `ruolo_applicativo` al profilo store auth
- [ ] 6.1.3 Se separato: creare `frontend-portale/` e `frontend-shop/`
- [ ] 6.1.4 Aggiornare `src/core/navigation.js` in base alla decisione
- [ ] 6.1.5 Router guard che blocca OPERATORE sui path `/portale/*` e viceversa

### 6.2 Schermate admin (gestione invito portale)

- [ ] 6.2.1 Tab "Accesso Portale" nel `ClienteDrawer`
- [ ] 6.2.2 Tab "Accesso Portale" nel `FornitoreDrawer`
- [ ] 6.2.3 Pulsante "Invia invito portale" con conferma
- [ ] 6.2.4 Visualizzazione stato identita' (attiva / inattiva / scaduta)
- [ ] 6.2.5 Pulsante "Reinvia invito" (se scaduto)
- [ ] 6.2.6 Pulsante "Disattiva accesso" (soft, reversibile)
- [ ] 6.2.7 Badge su riga lista cliente/fornitore: "portale attivo"

### 6.3 Schermate admin — configurazione profili portale

- [ ] 6.3.1 Sezione "Profili di accesso" sotto Amm. Software
- [ ] 6.3.2 Lista profili con filtro per tipo (REPARTO / PORTALE / AD_HOC)
- [ ] 6.3.3 Drawer modifica profilo: matrice area x livello + azioni abilitate
- [ ] 6.3.4 Vista "Binding" del profilo: quali utenti/reparti/ruoli lo usano
- [ ] 6.3.5 Allerta modifica profilo: "impatta N utenti" come oggi per reparto

### 6.4 Portale cliente — UI

- [ ] 6.4.1 Layout dedicato semplificato (senza sidebar admin)
- [ ] 6.4.2 Dashboard: ultime fatture, scadenze in arrivo, saldo aperto
- [ ] 6.4.3 Pagina "Le mie fatture" con filtro periodo + export PDF
- [ ] 6.4.4 Pagina "Scadenzario"
- [ ] 6.4.5 Pagina "Profilo" con cambio password volontario
- [ ] 6.4.6 Tema visivamente distinto dall'admin (header, colori)
- [ ] 6.4.7 Supporto dark/light mode (coerente con `docs/it/dev/frontend/`)

### 6.5 Portale fornitore — UI

- [ ] 6.5.1 Layout dedicato (riusabile con portale cliente, differenziato per menu)
- [ ] 6.5.2 Dashboard: ordini ricevuti recenti, stato pagamenti
- [ ] 6.5.3 Pagina "Ordini ricevuti"
- [ ] 6.5.4 Pagina "Pagamenti ricevuti"
- [ ] 6.5.5 Pagina "Profilo"

### 6.6 Shop — UI pubblica

- [ ] 6.6.1 Layout shop (catalogo, carrello, checkout)
- [ ] 6.6.2 Pagina catalogo con filtri categoria
- [ ] 6.6.3 Pagina prodotto
- [ ] 6.6.4 Carrello (persistente per anonimi via session id)
- [ ] 6.6.5 Registrazione self-service (3 campi: email, password, dati base)
- [ ] 6.6.6 Email verifica + redirect a login
- [ ] 6.6.7 Pagina "I miei ordini"
- [ ] 6.6.8 Checkout con scelta metodo pagamento (collegato a `pagamenti` backend)

### 6.7 Flussi autenticazione condivisi

- [ ] 6.7.1 Login unificato con redirect post-login in base a `ruolo_applicativo`:
      * OPERATORE -> `/admin/`
      * CLIENTE_PORTALE / FORNITORE_PORTALE -> `/portale/`
      * SHOP_CUSTOMER -> `/shop/account/`
- [ ] 6.7.2 Pagina attivazione invito portale (analoga all'attivazione operatore)
- [ ] 6.7.3 Reset password universale
- [ ] 6.7.4 Verifica email shop (click da link -> conferma visiva + redirect login)

---

## 7. Fase Test e Documentazione

### 7.1 Test DB

- [ ] 7.1.1 pgTAP: trigger `trgfn_identita_digitali_guard_coerenza` (8 casi)
- [ ] 7.1.2 pgTAP: sync is_active per 4 tipi di identita'
- [ ] 7.1.3 pgTAP: scope policy EF_WHITELIST (regression rispetto a oggi)
- [ ] 7.1.4 pgTAP: scope policy BA_OWNERSHIP (con dati di test multi-cliente)
- [ ] 7.1.5 pgTAP: scope policy FORNITORE_OWNERSHIP
- [ ] 7.1.6 pgTAP: scope policy SELF_OWNERSHIP (shop)
- [ ] 7.1.7 pgTAP: RLS policy su fatture (cliente A non vede cliente B)
- [ ] 7.1.8 pgTAP: RLS bypass per operatore interno

### 7.2 Test Backend

- [ ] 7.2.1 Test `PermissionResolver` con profili_accesso generalizzati (regression)
- [ ] 7.2.2 Test `JwtAuditAuthentication` con propagazione GUC identita'
- [ ] 7.2.3 Test API portale cliente (list/get fatture, scadenze)
- [ ] 7.2.4 Test API portale fornitore
- [ ] 7.2.5 Test API shop (catalogo, registrazione, checkout)
- [ ] 7.2.6 Test cross-role: utente admin non accede a `/api/portale/`,
      utente portale non accede a `/api/admin/`
- [ ] 7.2.7 Test invito portale (admin invita cliente -> cliente attiva)
- [ ] 7.2.8 Test rate limit login e registrazione shop

### 7.3 Smoke test end-to-end

- [ ] 7.3.1 Script bash `smoke-test-multi-face-auth.sh` (coerente con il resto dei
      smoke test, con indice e cleanup proattivo)
- [ ] 7.3.2 Scenario 1: admin crea cliente -> invita portale -> cliente attiva ->
      cliente vede proprie fatture
- [ ] 7.3.3 Scenario 2: admin crea fornitore -> invita portale -> fornitore
      vede ordini ricevuti
- [ ] 7.3.4 Scenario 3: visitatore si registra shop -> verifica email -> ordine ->
      vede storico
- [ ] 7.3.5 Scenario 4: cliente portale tenta di accedere a fatture di altro
      cliente -> 403 / RLS blocca

### 7.4 Documentazione

- [ ] 7.4.1 Aggiornare [soggetti-e-ruoli-anagrafici](/guide/soggetti-e-ruoli-anagrafici)
      con riferimento al nuovo bridge
- [ ] 7.4.2 Aggiornare [architettura-permessi-e-autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
      con `profili_accesso` generalizzato
- [ ] 7.4.3 Aggiornare [risorse-umane-e-accessi](/guide/risorse-umane-e-accessi) con R4 ridisegnato
- [ ] 7.4.4 Creare nuova guida "Portale Clienti — Uso e Onboarding"
- [ ] 7.4.5 Creare nuova guida "Portale Fornitori — Uso e Onboarding"
- [ ] 7.4.6 Creare nuova guida "Shop Online — Registrazione e Acquisti"
- [ ] 7.4.7 Documentare i nuovi GUC in `docs/it/postgresql/parametri-personalizzati-(GUC).md`
- [ ] 7.4.8 Aggiornare [api.md](/backend/dev/api) con i namespace `/api/portale/*` e `/api/shop/*`

---

## 8. Fase deployment e cutover

- [ ] 8.1 Migrazione liquibase eseguita in staging con backup pre-apply
- [ ] 8.2 Smoke test staging OK
- [ ] 8.3 Verifica performance query post-RLS (no regression > 10%)
- [ ] 8.4 Piano di rollback documentato
- [ ] 8.5 Deploy backend con feature flag `ENABLE_MULTI_FACE_AUTH` (default off)
- [ ] 8.6 Attivazione progressiva per cliente pilota
- [ ] 8.7 Raccolta feedback pilota
- [ ] 8.8 Rimozione feature flag dopo 2 settimane stabili
- [ ] 8.9 Deprecazione formale di `risorse_umane_auth_user` (doc)
- [ ] 8.10 Rimozione fisica della tabella legacy (milestone +3 mesi)

---

## 9. Ordine consigliato di esecuzione

Sviluppo concentrico: si parte dal DB e si procede solo quando lo strato
inferiore e' completo e testato.

1. **Prerequisiti §3** — censimenti e decisioni aperte
2. **Fase DB §4.1-4.8** — tutto lo schema + funzioni, senza ancora attivare RLS
3. **Fase Backend §5.1-5.3** — resolver e GUC, senza ancora cambiare API pubbliche
4. **Fase Backend §5.4-5.6** — namespace nuovi + servizi invito/registrazione
5. **Fase DB §4.9** — attivazione RLS (dopo che backend popola GUC)
6. **Fase Backend §5.7-5.9** — API portale e shop
7. **Fase Frontend §6** — una linea alla volta (portale cliente -> portale
   fornitore -> shop)
8. **Fase Test §7** — in parallelo ad ogni fase, ma gate di chiusura
9. **Fase cutover §8** — deploy con pilota

---

## 10. Decisioni aperte da discutere

- [ ] 10.1 **Admin di portale?** Un cliente azienda con piu' referenti vuole
      un "amministratore" che gestisca gli utenti secondari? Se si', serve
      un sotto-modello `CLIENTE_ADMIN_PORTALE` + capability di invito
- [ ] 10.2 **Frontend separato o unico?** Un bundle unico con guard vs tre build
      separati. Impatto su deploy e autenticazione cross-domain
- [ ] 10.3 **Multi-lingua portale?** I clienti esteri vedono in inglese? Se si',
      i template email per `ruolo_applicativo + lingua`
- [ ] 10.4 **Scope per agenti di vendita?** Fuori scope iniziale ma il modello
      `scope_policy` permetterebbe di aggiungere `AGENTE_OWNERSHIP`. Quando?
- [ ] 10.5 **API pubbliche per integrazioni (ruolo `API_CLIENT`)?** Oggi o in
      una fase successiva?
- [ ] 10.6 **Notifiche in-app nel portale?** (nuova fattura emessa, scadenza
      in arrivo). Se si', richiede canale dedicato

---

## 11. Rischi noti

| Rischio | Mitigazione |
| --- | --- |
| RLS rallenta query critiche | Benchmark prima dell'attivazione + indici mirati su colonne scope |
| Bug di scope che leaka dati cross-cliente | Test pgTAP dedicati + RLS come rete di sicurezza |
| Rottura del flusso operatori durante migrazione | Vista di compatibilita' + feature flag + rollout graduale |
| Complessita' onboarding portale (admin non capisce) | UI guidata + documentazione utente + video tutorial |
| Spam registrazione shop | Rate limit + captcha + verifica email obbligatoria |
| Email invito che finiscono in spam | SPF/DKIM/DMARC corretti + monitoring deliverability |

---

## 12. Storico modifiche

* **2026-04-18**: Documento creato dopo analisi architetturale.
  Guida di riferimento: [architettura-multi-face-auth](/guide/architettura-multi-face-auth).

---

{% include-markdown "signature-core.md" %}
