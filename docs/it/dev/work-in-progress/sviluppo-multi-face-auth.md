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
- [x] 3.2 Censire chi chiama `fn_sync_auth_user_is_active` (trigger, management
      command, codice Python) per stimare l'impatto della generalizzazione
      — **esito**: 8 chiamanti (3 trigger DB, 1 pgAgent daily, 1 management
      command, 3 metodi `AmmSoftwareRepository`). Firma attuale:
      `fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)`.
- [x] 3.2.b **Verifica coerenza firma vs chiamanti Python** (2026-04-18):
      **bug confermato**. `fn_sync_auth_user_is_active(p_risorsa_umana_id)`
      riceve `auth_user_id` dai 3 metodi `AmmSoftwareRepository`. Impatto
      pratico nullo grazie ai trigger AFTER su `risorse_umane_auth_user`
      che coprono il sync con il parametro corretto. **Risoluzione scelta
      (opzione 3)**: fix incorporato nel refactor §4.5 — la nuova firma
      `fn_sync_auth_user_is_active(p_auth_user_id)` rende le 3 chiamate
      Python corrette senza toccare il codice chiamante. Dettaglio
      invariante e anti-pattern: callout in §4.5.
- [ ] 3.3 Censire tutte le view/API che oggi usano `EmittenteFiscaleScopeMixin`
      e quelle che filtrano manualmente per `auth_user`
- [ ] 3.4 Verificare che [token_monouso](/dbzero/config/tabelle/token_monouso)
      supporti l'aggiunta di nuovi `tipo_token` (INVITO_PORTALE, VERIFICA_EMAIL_SHOP)
      senza breaking change
- [ ] 3.5 Verificare che il ruolo DB applicativo (`zeroerp_app`) abbia i grant
      corretti per leggere `identita_digitali` (nuova tabella)
- [ ] 3.6 Valutare costo performance RLS sulle tabelle principali (fatture,
      ordini, DDT) — benchmark con 100k righe prima dell'attivazione
- [x] 3.7 Redigere nota decisionale su: **l'admin di portale esiste?**
      — **decisione 2026-04-18**: rimandato a Fase 2 post-MVP. Motivazioni:
      (1) modello `identita_digitali` + `profili_accesso_bindings` +
      `scope_policy` gia' compatibile, l'aggiunta futura di
      `CLIENTE_ADMIN_PORTALE` e' un enum value + un profilo + un set di
      endpoint, **zero refactor strutturale**; (2) MVP con un solo account
      per cliente e' sufficiente per raccogliere feedback pilota senza
      scope creep su §5.4-5.5; (3) in §4.1.1 non aggiungere ancora lo slot
      enum, lasciare gancio in §10.1. Vedi §10.1 per dettaglio.
- [x] 3.8 **Documentazione RLS — linee guida SQL**: sezione 10 "Row Level
      Security (RLS)" in [linee-guida-sql.md](/linee-guida-sql), suddivisa
      in sotto-sezioni 10.1-10.9 (quando usarla, naming policy, funzioni
      `fn_scope_*`, GUC, bypass ruoli, USING vs WITH CHECK, defense-in-depth,
      test, checklist). Riferimento helper `fn_current_identita_context`
      aggiunto in §10.4 (2026-04-19).
- [x] 3.9 **Documentazione RLS — scheda PostgreSQL**: file
      [row-level-security.md](/postgresql/row-level-security) completo con
      sintassi, USING/WITH CHECK, PERMISSIVE/RESTRICTIVE, interazione GUC,
      ruoli `BYPASSRLS` e `FORCE`, troubleshooting, performance
      (funzioni STABLE, indici, EXPLAIN, pg_stat_statements), convivenza
      con viste `security_invoker` e `SECURITY DEFINER`. Riferimento a
      `fn_current_identita_context` aggiunto (2026-04-19).
- [x] 3.10 Le due schede sono disponibili come riferimento per §4.9
      (attivazione RLS) — prerequisito soddisfatto.

### 3.bis Esiti censimenti (sintesi 2026-04-18)

**3.1 Trigger su `risorse_umane_auth_user`** (7 trigger censiti):

* 2 guard: `guard_persona_fisica` (CF obbligatorio / P.IVA vietata) e
  `require_active_parent` su `risorse_umane.attivo`
* 1 sync: `sync_auth_user_active` (AFTER INS + AFTER UPD OF attivo)
* 2 audit generici: `audit_data_user_generic` e `tx_id_managed`
* 1 storico: `storico_generic` su `risorse_umane_auth_user_id`
* **Impatto §4.2**: il guard `persona_fisica` va incorporato come ramo
  condizionale sul ruolo dentro `trgfn_identita_digitali_guard_coerenza`
  (§4.2.3), valido solo per `ruolo_applicativo = OPERATORE`. I trigger
  audit/tx_id/storico sono riusabili as-is sulla nuova tabella.

**3.2 Callers `fn_sync_auth_user_is_active`**: vedi checkbox sopra.

**3.3 Superficie scope attuale**:

* `EmittenteFiscaleScopeMixin` definito in `apps/core/mixins.py` ma
  **non usato** in alcun viewset. Enforcement attuale = DB-first:
  repository chiamano `script.fn_get_emittenti_scope_sr_ids(auth_user_id)`
* 6 punti di scoping nei repository (`vendite_repository`,
  `preventivi_repository`, `amm_software_repository`,
  `permissions_resolver`, `parameter_repository`)
* `JwtAuditAuthentication` popola oggi solo `app.jwt_user` e
  `app.current_user_id` (session-scoped, reset nel middleware response).
  L'aggiunta dei 3 nuovi GUC (§4.7.1) e' incrementale, zero breaking.
* Stima RLS: ~11 tabelle operazionali. Policy `EF_WHITELIST` -> RLS
  semplice (un'unica clausola su array GUC). Permessi area/oggetto/azione
  restano in Python per ora (3 livelli di override, porting feasible ma
  non prioritario — defense-in-depth via DB-first via repository resta).

**3.4 `token_monouso` estendibilita'**: vedi §4.1.3 aggiornato. Non-breaking.

---

## 4. Fase DB — Fondamenta (schema + funzioni)

### 4.1 ENUM nuovi / estensioni

- [x] 4.1.1 Creare ENUM `config.ruolo_applicativo` con valori:
      `OPERATORE`, `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`,
      `API_CLIENT`, `DISABILITATO`
      — implementato in `20260418-01-create-ruolo-applicativo-enum-mctit.yaml`
- [x] 4.1.2 Creare ENUM `config.tipo_profilo_accesso` con valori:
      `REPARTO`, `PORTALE`, `AD_HOC`
      — implementato in `20260418-02-create-tipo-profilo-accesso-enum-mctit.yaml`
- [x] 4.1.3 ~~Valutare estensione ENUM `config.tipo_token`~~ — **non
      applicabile**: `config.token_monouso.tipo` e' un `varchar(50)`, non
      un ENUM PostgreSQL. Nessun CHECK, nessun switch esaustivo in codice.
      Le nuove costanti `INVITO_PORTALE` e `VERIFICA_EMAIL_SHOP` si
      definiscono solo a livello Python nei nuovi service (vedi §5.5.2 e
      §5.6.3). Zero DDL.

### 4.2 Tabella bridge `identita_digitali`

- [x] 4.2.1 Creare `anagrafiche.identita_digitali` con campi e UNIQUE come da guida §3.1
      — DDL `20260418-10-create-identita-digitali-mctit.yaml`;
      storico `20260418-23-create-storico-identita-digitali-mctit.yaml`.
      Nota: l'indice parziale UNIQUE e' stato implementato su
      `(soggetto_ruolo_id) WHERE attivo = true` (vincolo "una sola identita
      attiva per soggetto_ruolo"); la UNIQUE su `auth_user_id` e' totale
      (un auth_user e' sempre legato a una sola identita). Vedi §4.2.4.
- [x] 4.2.2 ~~Audit trigger standard (`trgfn_audit_data_user_generic`)~~
      — delegato ad automation (pattern ZeroErp: i trigger framework
      audit/tx_id/storico sono applicati automaticamente dai processi di
      infrastruttura sulle nuove tabelle).
- [x] 4.2.3 Trigger guard `trgfn_identita_digitali_guard_coerenza`:
      * `OPERATORE` -> `RIS_UMANA` + soggetto PF pura (delega a
        `script.fn_guard_soggetto_pf_pura`)
      * `CLIENTE_PORTALE` / `SHOP_CUSTOMER` -> `CL`
      * `FORNITORE_PORTALE` -> `FO`
      * `API_CLIENT` / `DISABILITATO` -> nessun vincolo
      * ramo ELSE anti-bypass (`E_RUOLO_APPLICATIVO_NON_GESTITO`)
      — implementato in `20260418-22-create-trgfn-identita-digitali-guard-coerenza-mctit.yaml`.
      Nuova funzione riusabile `script.fn_guard_soggetto_pf_pura`
      (`20260418-20-...`) + refactor del vecchio trigger PF pura su RUA
      (`20260418-21-...`) per eliminare la duplicazione di logica.
- [x] 4.2.4 Indice parziale UNIQUE implementato come
      `uq_identita_digitali_soggetto_ruolo_attivo ON (soggetto_ruolo_id)
      WHERE attivo = true` (una sola identita attiva per soggetto_ruolo).
      La UNIQUE su `auth_user_id` e' totale.
- [x] 4.2.5 ~~Policy ATTIVO (child/parent framework)~~ — non applicabile
      in questa fase: `anagrafiche.soggetti_ruoli` non ha colonna `attivo`.
      Il gating sull'attivita del parent passa da `soggetti.attivo`, gia'
      verificato via trigger esistente su `soggetti_ruoli`. Nessun trigger
      aggiuntivo necessario su `identita_digitali`.

### 4.3 Profili accesso generalizzati

- [x] 4.3.1 Creare `config.profili_accesso` (id, tipo, codice, descrizione, attivo)
      — `20260418-30-create-profili-accesso-mctit.yaml` +
      storico `20260418-34-...`.
- [x] 4.3.2 Creare `config.profili_accesso_aree`
      — `20260418-31-create-profili-accesso-aree-mctit.yaml` +
      storico `20260418-35-...`.
- [x] 4.3.3 Creare `config.profili_accesso_azioni`
      — `20260418-32-create-profili-accesso-azioni-mctit.yaml` +
      storico `20260418-36-...`.
- [x] 4.3.4 Creare `config.profili_accesso_bindings` con CHECK xor a 3 vie
      + 3 indici parziali UNIQUE per entita (uo / identita / ruolo)
      + guard coerenza tipo profilo <-> tipo binding
      — DDL `20260418-33-create-profili-accesso-bindings-mctit.yaml` +
      guard `20260418-40-create-trgfn-profili-accesso-bindings-guard-coerenza-mctit.yaml` +
      storico `20260418-37-...`.
- [x] 4.3.5 Migrazione dati: un profilo REPARTO per ogni `unita_organizzativa`
      con permessi configurati, codice `REPARTO_<codice_interno>`
      — `80_data/changelog/20260418-42-migrate-profili-reparto-to-profili-accesso-mctit.yaml`
      (idempotente via `ON CONFLICT DO NOTHING`).
- [x] 4.3.6 Backfill `profili_accesso_bindings` REPARTO coperto dallo
      stesso changeset §4.3.5 (step 4 del DO block).
- [x] 4.3.7 Seed profili portale via CSV + `loadUpdateData`:
      * `CLIENTE_PORTALE_STANDARD` (LETTURA su vendite + pagamenti)
      * `FORNITORE_PORTALE_STANDARD` (LETTURA su acquisti + pagamenti)
      * `SHOP_CUSTOMER_STANDARD` (LETTURA su vendite + pagamenti) — aggiunto
        `pagamenti` oltre a vendite su richiesta
      — CSV: `profili_accesso.csv`, `profili_accesso_aree.csv`,
      `profili_accesso_bindings.csv`; changeset
      `20260418-43-upsert-profili-accesso-portale-mctit.yaml` con `setval`
      sequenze finale. Range id seed dedicato 9001-9006.
- [x] 4.3.8 Binding dei profili seed al relativo `ruolo_applicativo`
      — incluso nel CSV `profili_accesso_bindings.csv` e nel changeset
      `20260418-43-...`.

### 4.4 Scope policy generalizzato

- [x] 4.4.1 Creare `config.scope_policy` con colonna singola `funzione_db`
      (formato `schema.nome`) — `20260418-50-create-scope-policy-mctit.yaml`
      + storico `20260418-52-...`.
- [x] 4.4.2 Creare `config.identita_scope_bindings` con UNIQUE
      `(identita_digitale_id, scope_policy_id)` e `parametri` JSONB default
      `{}` (vuoto per seed iniziale: le policy risolvono i dati dai
      riferimenti anagrafici)
      — `20260418-51-create-identita-scope-bindings-mctit.yaml` +
      storico `20260418-53-...`.
- [x] 4.4.3 Seed `scope_policy` (3 policy, `SELF_OWNERSHIP` unificato con
      `BA_OWNERSHIP` perche' cliente portale e shop condividono il ruolo CL):
      * `EF_WHITELIST` -> `script.fn_scope_ef_whitelist`
      * `BA_OWNERSHIP` -> `script.fn_scope_ba_ownership`
      * `FORNITORE_OWNERSHIP` -> `script.fn_scope_fornitore_ownership`
      — CSV `scope_policy.csv` + `20260418-70-upsert-scope-policy-mctit.yaml`.
- [x] 4.4.4 Scrivere le funzioni `fn_scope_*` in schema `script`, tutte
      `LANGUAGE sql STABLE` (inlineable), fail-closed su identita inattiva:
      * `fn_scope_ef_whitelist` — `20260418-60-...`
      * `fn_scope_ba_ownership` — `20260418-61-...`
      * `fn_scope_fornitore_ownership` — `20260418-62-...`
- [x] 4.4.5 Backfill: per ogni identita `OPERATORE` attiva con righe in
      `user_emittenti_fiscali` creato un binding `EF_WHITELIST` (parametri
      `{}`, la funzione risolve dai dati legacy)
      — `80_data/changelog/20260418-71-backfill-identita-scope-bindings-ef-whitelist-mctit.yaml`
      idempotente, `runOnChange: true`. Durante la transizione §4.5 -> §4.6
      `identita_digitali` puo' essere vuota; il changeset si applica senza
      errori e crea i bindings man mano che le identita vengono popolate.

### 4.5 Generalizzazione sync `auth_user.is_active`

> **Nota — bug latente da non riprodurre** (verifica 2026-04-18, §3.2.b):
> la firma attuale e' `fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)`
> e la funzione cerca il bridge con `WHERE rau.risorsa_umana_id = p_param`.
> I tre metodi `AmmSoftwareRepository.update_operatore /
> disabilita_operatore / riattiva_operatore` le passano invece un
> `auth_user_id`. Il bug e' coperto dai trigger AFTER su
> `risorse_umane_auth_user` (che passano il parametro corretto), quindi il
> sync avviene comunque, ma in modo non deterministico e con rischio di
> agire temporaneamente sulla risorsa sbagliata in caso di collisione di id.
>
> **Invariante per il refactor**: la nuova firma deve essere
> `fn_sync_auth_user_is_active(p_auth_user_id bigint)` — quel `bigint` e' un
> `auth_user.id`, NON un `risorsa_umana.id`. Il lookup del bridge/identita'
> avviene **dentro** la funzione partendo da `auth_user_id`. Cosi' le tre
> chiamate Python esistenti diventano corrette senza modifiche al codice
> chiamante.
>
> **Da NON fare**: mantenere una firma ambigua o due overload
> (`bigint, bigint`) che si distinguono solo per semantica del parametro.

- [x] 4.5.1 Nuova firma `fn_sync_auth_user_is_active(p_auth_user_id integer)`
      che parte da `auth_user_id`, risolve internamente il bridge (priorita'
      al nuovo `identita_digitali`, fallback legacy su
      `risorse_umane_auth_user` durante transizione §4.5 -> §4.6)
      — `20260418-72-update-fn-sync-auth-user-is-active-mctit.yaml`.
      Firma precedente `(bigint)` droppata e ricreata con `(integer)`.
      I 3 metodi `AmmSoftwareRepository` diventano automaticamente corretti
      (fix implicito del bug latente §3.2.b).
- [x] 4.5.2 Algoritmo gestisce tutti i ruoli applicativi:
      * `DISABILITATO` -> `false` immediato
      * altri ruoli -> identita attiva + finestra + soggetto attivo
      * `OPERATORE` in piu' -> doppia verifica su `risorse_umane.attivo` +
        finestra RU (vincolo legacy mantenuto finche' non si fa il cutover
        §4.6; rimovibile in changeset dedicato dopo il cutover).
- [x] 4.5.3 Nuovo trigger + trigger function
      `trg_identita_digitali_z90_sync_auth_user_active_ins/upd` +
      `trgfn_identita_digitali_sync_auth_user_active`
      — `20260418-75-create-trgfn-identita-digitali-sync-auth-user-active-mctit.yaml`.
      `UPDATE OF attivo, valido_dal, valido_al, ruolo_applicativo,
      auth_user_id` per evitare scatti inutili.
- [x] 4.5.4 Compatibilita' con trigger esistenti: le 2 trigger function
      `trgfn_risorse_umane_auth_user_sync_active` e
      `trgfn_risorse_umane_sync_auth_user_active` aggiornate in
      `20260418-73-update-trgfn-sync-active-callers-mctit.yaml` per passare
      `auth_user_id` alla nuova firma (la prima usa direttamente
      `NEW.auth_user_id`, la seconda lo risolve dal bridge RUA).
      Trigger installati invariati (stesso nome, fase, eventi).
- [x] 4.5.5 `fn_sync_auth_user_expired` estesa per coprire UNION di
      `risorse_umane` legacy + tutte le `identita_digitali` con `valido_al`
      scaduto; `SELECT DISTINCT auth_user_id` evita double-sync
      — `20260418-74-update-fn-sync-auth-user-expired-mctit.yaml`.
- [x] 4.5.6 Test pgTAP sync per identita operatore (caso fallback legacy)
      — aggiornato `db/pgtap/anagrafiche/test-sync-auth-user-is-active.sql`
      per la nuova firma `(p_auth_user_id integer)`. 18 casi coprono
      fn_sync + trigger su RUA/RU + fn_sync_auth_user_expired. Per i
      nuovi ruoli (portale, shop) il fallback legacy copre il caso
      operatore; i test dedicati per identita portale/shop andranno
      aggiunti in §7.1.2 (segnalati quando il cutover §4.6 sara' completato
      e `identita_digitali` popolata con dati di test).

### 4.6 Cutover operatori — da `risorse_umane_auth_user` a `identita_digitali`

> **Design deciso 2026-04-19**: ADMIN modellato come profilo `SUPER_ADMIN`
> (nuovo valore in `config.tipo_profilo_accesso`) + binding su
> `identita_digitali`, NON come colonna boolean. Il bypass e' un privilegio
> bindato che riusa l'infrastruttura §4.3 (audit, storico, guard coerenza,
> finestra temporale). DISABILITATO legacy assorbito da
> `ruolo_applicativo = DISABILITATO` OPPURE `identita_digitali.attivo = false`.
> OPERATIVO legacy = default implicito (assenza di binding SUPER_ADMIN).
>
> `identita_digitali` viene esteso con 4 colonne stateful cross-ruolo
> (`tentativi_falliti`, `bloccato_fino_a`, `totp_obbligatorio`, `storicizza`)
> che oggi vivono solo sul bridge legacy. La vista di compatibilita'
> ricostruisce dinamicamente `ruolo_sistema` e `risorsa_umana_id`.
>
> **Split PR**:
>
> * **PR1 DB** (branch `dev/db-tid`): §4.6.A-F (schema, refactor resolver,
>   writer DB, backfill, vista, test)
> * **PR2 Backend** (branch `dev/backend-tid`, **FUORI scope di questa fase
>   DB**): §4.6.G (PermissionResolver, repository, UI). Non verra' iniziato
>   finche' PR1 non e' mergiata su `Tito-dev`.
> * **PR3 Cutover** (branch `dev/db-tid`, dopo che PR2 gira stabile): §4.6.H
>   (rinomina tabella legacy + promozione vista).

#### 4.6.A — Estensione modello (PR1 DB)

- [x] 4.6.A.1 `ALTER TABLE identita_digitali` aggiungere 4 colonne stateful:
      `tentativi_falliti` (smallint, default 0), `bloccato_fino_a`
      (timestamptz, nullable), `totp_obbligatorio` (boolean, default false),
      `storicizza` (boolean, default true — gia' presente, idempotente)
      — `20260419-01-alter-identita-digitali-add-stateful-cols-mctit.yaml`
- [x] 4.6.A.2 `ALTER TYPE config.tipo_profilo_accesso ADD VALUE 'SUPER_ADMIN'`
      — `20260419-02-alter-tipo-profilo-accesso-add-super-admin-mctit.yaml`
- [x] 4.6.A.3 Update `trgfn_profili_accesso_bindings_guard_coerenza` per
      gestire `tipo = SUPER_ADMIN`: bindable **solo** su
      `identita_digitale_id` (privilegio personale, non di reparto ne' di
      ruolo applicativo)
      — `20260419-03-update-trgfn-profili-accesso-bindings-guard-coerenza-mctit.yaml`
- [x] 4.6.A.4 Seed profilo `SUPER_ADMIN` (id 9100) via INSERT
      idempotente + setval sequenza. No righe in `profili_accesso_aree`:
      il bypass e' totale, risolto nel resolver. Nota limite: l'indice
      `uq_profili_accesso_bindings_identita` impone **un solo binding
      diretto per identita**, quindi SUPER_ADMIN e AD_HOC sono
      mutualmente esclusivi per la stessa identita (SUPER_ADMIN comunque
      bypassa AD_HOC, quindi semanticamente coerente).
      — `20260419-04-seed-profilo-super-admin-mctit.yaml`

#### 4.6.B — Funzioni resolver (PR1 DB)

- [x] 4.6.B.0 Creare helper DRY
      `script.fn_has_identita_attiva(auth_user_id, ruolo_applicativo)`
      `RETURNS boolean LANGUAGE sql STABLE`. Incapsula il check
      "identita attiva nella finestra temporale" riusato da 7+ funzioni.
      Parametrizzato sul ruolo_applicativo per riuso futuro §4.8
      (resolver generalizzato su profili_accesso).
      — `20260419-09-create-fn-has-identita-attiva-mctit.yaml`
- [x] 4.6.B.1 Creare `script.fn_is_super_admin(p_auth_user_id integer)`
      — `20260419-10-create-fn-is-super-admin-mctit.yaml`
- [x] 4.6.B.2 Update `fn_resolve_livello_area`
      — `20260419-11-update-fn-resolve-livello-area-mctit.yaml`
- [x] 4.6.B.3 Update `fn_resolve_livello_oggetto`
      — `20260419-12-update-fn-resolve-livello-oggetto-mctit.yaml`
- [x] 4.6.B.4 Update `fn_check_azione_processo`
      — `20260419-13-update-fn-check-azione-processo-mctit.yaml`
- [x] 4.6.B.5 Update `fn_check_user_emittente_scope`
      — `20260419-14-update-fn-check-user-emittente-scope-mctit.yaml`
- [x] 4.6.B.6 Update `fn_get_emittenti_scope_sr_ids`
      — `20260419-15-update-fn-get-emittenti-scope-sr-ids-mctit.yaml`
- [x] 4.6.B.7 Update `fn_get_emittenti_scope` (firma slegata da RUA)
      — `20260419-16-update-fn-get-emittenti-scope-mctit.yaml`
- [x] 4.6.B.8 Update `fn_get_user_permissions_map` (JOIN diretto)
      — `20260419-17-update-fn-get-user-permissions-map-mctit.yaml`
- [x] 4.6.B.9 Update `fn_get_user_actions_map`
      — `20260419-18-update-fn-get-user-actions-map-mctit.yaml`
- [x] 4.6.B.10 Update `fn_check_operatore_invitabile` + `fn_get_setup_status`
      (entrambe leggevano `ruolo_sistema` via JOIN diretto)
      — `20260419-19-update-fn-check-operatore-invitabile-mctit.yaml`
      + `20260419-20-update-fn-get-setup-status-mctit.yaml`
- [x] 4.6.B.11 Update `fn_get_user_profile` (refactor query iniziale su
      identita_digitali + aggiunta output `is_super_admin`, `ruolo_applicativo`)
      — `20260419-21-update-fn-get-user-profile-mctit.yaml`

#### 4.6.C — Wrapper deprecato (PR1 DB)

- [x] 4.6.C.1 Update `script.fn_get_ruolo_sistema` come wrapper
      retrocompatibile. Firma e tipo di ritorno invariati.
      — `20260419-22-update-fn-get-ruolo-sistema-wrapper-mctit.yaml`

#### 4.6.D — Writer DB (PR1 DB)

- [x] 4.6.D.1 Update `script.fn_registra_tentativo_login`: scrive su
      `identita_digitali` (fonte primaria) + doppio UPDATE su
      `risorse_umane_auth_user` durante transizione expand-align-contract.
      — `20260419-23-update-fn-registra-tentativo-login-mctit.yaml`
- [x] 4.6.D.2 Update `script.fn_check_blocco_login`: legge da
      `identita_digitali`; auto-unlock su entrambe durante transizione.
      — `20260419-24-update-fn-check-blocco-login-mctit.yaml`
- [x] 4.6.D.3 Update `anagrafiche.fn_crea_risorsa_umana`: doppio INSERT
      (RUA legacy + identita_digitali OPERATORE). Traduce
      `p_ruolo_sistema`: ADMIN -> binding SUPER_ADMIN (profilo 9100);
      DISABILITATO -> identita inattiva; OPERATIVO -> default. Firma
      esterna invariata (fn_crea_operatore / amm_software_repository
      non cambiano).
      — `20260419-25-update-fn-crea-risorsa-umana-mctit.yaml`

#### 4.6.E — Backfill dati (PR1 DB)

- [x] 4.6.E.1 Backfill identita OPERATORE per ogni RUA esistente.
      Idempotente via NOT EXISTS (niente ON CONFLICT: il constraint
      `uq_identita_digitali_auth_user` e' totale ma NOT EXISTS e'
      equivalente e piu' leggibile).
      — `20260419-80-backfill-identita-digitali-operatori-mctit.yaml`
- [x] 4.6.E.2 Backfill bindings SUPER_ADMIN per operatori con
      `ruolo_sistema='ADMIN'` legacy. Idempotente via NOT EXISTS.
      — `20260419-81-backfill-bindings-super-admin-mctit.yaml`

Aggiunta 2026-04-19 **§4.6.D.4 — Trigger-ponte temporaneo** (non
previsto nel piano iniziale ma necessario per transizione expand-align-
contract senza rompere test esistenti + backend legacy pre-PR2):

- [x] 4.6.D.4 `trgfn_risorse_umane_auth_user_sync_identita`: AFTER
      INSERT/UPDATE su RUA propaga stato a `identita_digitali` OPERATORE
      (UPSERT) e sincronizza binding SUPER_ADMIN col ruolo_sistema.
      Rimovibile al cutover §4.6.H.3.
      — `20260419-26-create-trgfn-rua-sync-identita-digitale-mctit.yaml`

#### 4.6.F — Vista compatibilita' (PR1 DB, corrisponde al vecchio §4.6.1)

- [x] 4.6.F.1 Vista `anagrafiche.vw_risorse_umane_auth_user` creata con
      prefisso vw_ per convivere con la tabella omonima fino al cutover
      §4.6.H.2. Colonna `ruolo_sistema` ricostruita via CASE dinamico;
      `risorsa_umana_id` via JOIN `soggetti_ruoli -> risorse_umane`.
      Read-only.
      — `20260419-30-create-vw-risorse-umane-auth-user-mctit.yaml`

#### 4.6.G — Backend Python + UI (PR2 — **FUORI scope fase DB**)

> Branch `dev/backend-tid`. Non iniziare finche' PR1 non e' mergiata.

- [ ] 4.6.G.1 `PermissionResolver.get_ruolo_sistema` -> rinomina in
      `is_super_admin(user)` + wrapper temporaneo retrocompatibile.
      Aggiungere `is_disabilitato(user)` se serve esplicito.
- [ ] 4.6.G.2 `auth_repository.set_invito_inviato_at` e
      `set_deve_cambiare_password` -> switch scrittura su
      `identita_digitali` (colonne gia' esistenti dal 2026-04-18).
- [ ] 4.6.G.3 `amm_software_repository.update_operatore` -> input cambia
      da `ruolo_sistema: str` a `is_super_admin: bool`. Traduce in
      INSERT/UPDATE del binding SUPER_ADMIN via API di gestione profili.
- [ ] 4.6.G.4 `amm_software_repository.disabilita_operatore` /
      `riattiva_operatore` -> toccano solo `identita_digitali.attivo`
      (oltre al parent `risorse_umane.attivo` come oggi). Niente piu'
      UPDATE diretta del bridge legacy.
- [ ] 4.6.G.5 UI `OperatoreDrawer.vue`: radio ADMIN/OPERATIVO/DISABILITATO
      -> toggle "Concedi accesso SUPER ADMIN" (binding) +
      toggle/pulsante separato "Disabilita accesso".
- [ ] 4.6.G.6 Test Django: aggiornare `test_permissions.py`,
      `test_emittente_fiscale_scope.py`, `test_me_view.py`,
      `test_permissions_audit.py` per mockare `is_super_admin` invece di
      `ruolo_sistema`.

#### 4.6.H — Cutover fisico (PR3, dopo PR2 stabile)

> Branch `dev/db-tid`, solo quando tutti i writer Python sono migrati su
> `identita_digitali`.

- [ ] 4.6.H.1 Verificare assenza di writer residui su
      `risorse_umane_auth_user` (corrisponde al vecchio §4.6.2). Grep su
      backend Python + DB functions + trigger. Report di check-list in
      PR description.
- [ ] 4.6.H.2 Rinominare `risorse_umane_auth_user` in
      `_legacy_risorse_umane_auth_user` (corrisponde al vecchio §4.6.3).
      Promuovere la vista `vw_risorse_umane_auth_user` al nome
      originale `risorse_umane_auth_user` (DROP vista vecchia, CREATE
      vista col nome originale).
- [ ] 4.6.H.3 Changeset dedicato: rimuovere la doppia verifica OPERATORE
      in `fn_sync_auth_user_is_active` (vincolo legacy §4.5.2 ora
      ridondante, il sync gira su `identita_digitali`).
- [ ] 4.6.H.4 Changeset dedicato: rimuovere fallback legacy su
      `risorse_umane_auth_user` in `fn_sync_auth_user_is_active` (§4.5.1
      dead code post-cutover).

#### 4.6.I — Test pgTAP (distribuiti tra PR1 e PR3)

- [x] 4.6.I.1 Test `test-fn-is-super-admin.sql` (8 casi): NULL, utente
      inesistente, binding attivo/inattivo, identita inattiva, profilo
      inattivo, finestra scaduta
      — `db/pgtap/script/test-fn-is-super-admin.sql`
- [x] 4.6.I.2 Test `test-vw-risorse-umane-auth-user.sql` (5 casi):
      ricostruzione ruolo_sistema OPERATIVO/ADMIN/DISABILITATO +
      verifica trigger-ponte §4.6.D.4
      — `db/pgtap/anagrafiche/test-vw-risorse-umane-auth-user.sql`
- [ ] 4.6.I.3 ~~Aggiornare ~25 fixture nei test esistenti~~ **rimandato**:
      il trigger-ponte §4.6.D.4 mantiene i test legacy funzionanti
      (INSERT/UPDATE RUA si propaga automaticamente a identita_digitali).
      Aggiornamento esplicito rinviato a post-PR2, quando il backend
      cesserà di usare RUA e il trigger-ponte potrà essere rimosso (§4.6.H.3).
- [ ] 4.6.I.4 Test regression: operatore non-ADMIN mantiene esattamente
      lo stesso livello_area / livello_oggetto / azione_processo prima
      e dopo il refactor (fixture legacy + nuova per confronto). **Coperto
      implicitamente** dal trigger-ponte durante PR1; test esplicito
      rinviato a PR3 (pre-cutover) come smoke regression.

### 4.7 GUC e propagazione identita'

- [x] 4.7.1 Documentati i 3 nuovi GUC `app.current_identita_id`,
      `app.ruolo_applicativo`, `app.soggetto_ruolo_id` in
      [parametri-personalizzati-(GUC).md](/postgresql/parametri-personalizzati-(GUC))
      (nuova sezione "GUC di sessione `app.*`") + riga aggiunta in
      [guc_reference.md](/postgresql/guc_reference).
      Invariante "tutto o niente": il middleware popola tutti e 3 insieme
      o nessuno.
- [x] 4.7.2 Creata `script.fn_current_identita_context()` `RETURNS TABLE`
      (LANGUAGE sql STABLE): lettura tipizzata dei 3 GUC con pattern
      `NULLIF(current_setting(name, true), '')::<tipo>` (fail-soft su
      GUC mancanti). Manual + 6 test pgTAP.
      — `20260419-40-create-fn-current-identita-context-mctit.yaml`
      + [fn_current_identita_context.md](/dbzero/script/funzioni/fn_current_identita_context)
      + `db/pgtap/script/test-fn-current-identita-context.sql`

### 4.8 Funzioni risoluzione permessi

> **Nota implementativa (2026-04-19)**: le funzioni refactorate
> `fn_resolve_livello_area` (20260419-11) e `fn_check_azione_processo`
> (20260419-13) sono gia' state pushate come parte della PR1 §4.6.B.
> Gli update §4.8 qui sotto sono **nuovi changeset successivi** (-51, -52)
> sullo stesso branch `dev/db-tid`, per non violare la regola "mai
> modificare changelog pushati". Liquibase esegue in ordine alfabetico:
> la versione finale della funzione e' quella del file piu' recente.

- [x] 4.8.0 Helper `script.fn_get_profili_accesso_applicabili(auth_user_id)`
      `RETURNS TABLE (profilo_accesso_id, priorita)`: risolve i profili
      applicabili via identita + bindings (AD_HOC prio 1, PORTALE/REPARTO
      prio 2). `LANGUAGE sql STABLE` inlineable.
      — `20260419-50-create-fn-get-profili-accesso-applicabili-mctit.yaml`
      + manual + test pgTAP (5 casi)
- [x] 4.8.1 Update `fn_resolve_livello_area`: ramo 4 "profilo reparto"
      via `profili_reparto_aree` sostituito con lookup su
      `profili_accesso_aree` via helper.
      — `20260419-51-update-fn-resolve-livello-area-via-profili-accesso-mctit.yaml`
- [x] 4.8.2 `fn_resolve_livello_oggetto` non tocca `profili_reparto_*`
      direttamente; fa fallback a `fn_resolve_livello_area` che ora usa
      il nuovo modello. **Generalizzato implicitamente** — nessun nuovo
      file necessario.
- [x] 4.8.3 Update `fn_check_azione_processo`: ramo 4 "profilo reparto
      azione" sostituito con lookup su `profili_accesso_azioni` via helper.
      — `20260419-52-update-fn-check-azione-processo-via-profili-accesso-mctit.yaml`
- [x] 4.8.4 Test pgTAP regression end-to-end operatore (11 asserzioni):
      seed 'tid' spostato temporaneamente in UO test + profilo REPARTO
      dedicato con 2 aree (LETTURA/TUTTO) + 1 azione abilitata. Verifica
      che `fn_resolve_livello_area`, `fn_check_azione_processo`,
      `fn_get_user_permissions_map` e `fn_get_user_actions_map`
      restituiscano i livelli configurati. ROLLBACK finale ripristina
      stato iniziale. Skip graceful se seed 'tid' assente (CI minimale).
      — `db/pgtap/script/test-fn-resolve-regression-operatore.sql`

**Pendenza coordinamento backend**: il backend amministrativo scrive
ancora su `profili_reparto_aree`/`profili_reparto_azioni`. Il backfill
§4.3.5 (`runOnChange: true`) ri-sincronizza al deploy successivo. Non
real-time ma accettabile in dev. PR2 backend spostera' i writer sul nuovo
modello.

- [x] 4.8.5 Update `fn_get_user_permissions_map` e `fn_get_user_actions_map`
      per coerenza: CTE `best_per_area` / `best_per_azione` su
      `fn_get_profili_accesso_applicabili` invece di JOIN diretto a
      `profili_reparto_*`. Rimossa variabile `v_uo_id` non piu' necessaria
      (il helper incapsula il lookup UO).
      — `20260419-53-update-fn-get-user-permissions-map-via-profili-accesso-mctit.yaml`
      + `20260419-54-update-fn-get-user-actions-map-via-profili-accesso-mctit.yaml`

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

- [x] 7.1.1 pgTAP: trigger `trgfn_identita_digitali_guard_coerenza` (10 casi)
      — `db/pgtap/anagrafiche/test-identita-digitali-guard-coerenza.sql`:
      dispatch CASE completo (OPERATORE ok/ko, CLIENTE_PORTALE ok/ko,
      SHOP_CUSTOMER, FORNITORE_PORTALE ok/ko, API_CLIENT early-exit) +
      guard riusabile `fn_guard_soggetto_pf_pura` coperto da
      `db/pgtap/script/test-fn-guard-soggetto-pf-pura.sql` (8 casi).
- [ ] 7.1.2 pgTAP: sync is_active per 4 tipi di identita'
      — parziale: test legacy (operatore via RUA) coperto da
      `test-sync-auth-user-is-active.sql` aggiornato (18 casi).
      Dedicati per CLIENTE_PORTALE / FORNITORE_PORTALE / SHOP_CUSTOMER
      aperti (vanno scritti post cutover §4.6 con dati di test
      identita_digitali popolati).
- [x] 7.1.3 pgTAP: scope policy EF_WHITELIST (8 casi)
      — `db/pgtap/script/test-fn-scope-ef-whitelist.sql`: identita
      inesistente/inattiva/attiva senza whitelist/con whitelist e target
      dentro/fuori. Regression sul comportamento legacy verificata.
- [x] 7.1.4 pgTAP: scope policy BA_OWNERSHIP (6 casi incluso leak test)
      — `db/pgtap/script/test-fn-scope-ba-ownership.sql`: identita
      cliente A non vede BA di cliente B + fail-closed su identita
      inattiva/inesistente.
- [x] 7.1.5 pgTAP: scope policy FORNITORE_OWNERSHIP (7 casi)
      — `db/pgtap/script/test-fn-scope-fornitore-ownership.sql`: match,
      leak test, check ruolo applicativo (defense-in-depth), fail-closed
      su inattivo.
- [x] 7.1.6 ~~pgTAP: scope policy SELF_OWNERSHIP (shop)~~ — **non applicabile**:
      SELF_OWNERSHIP unificato con BA_OWNERSHIP in §4.4 (CLIENTE_PORTALE
      e SHOP_CUSTOMER condividono il ruolo anagrafico CL). Copertura in
      §7.1.4.
- [x] 7.1.9 pgTAP: CHECK xor + guard coerenza
      `trgfn_profili_accesso_bindings_guard_coerenza` (9 casi)
      — `db/pgtap/config/test-profili-accesso-bindings-guard-coerenza.sql`:
      xor violato (0/2 colonne), ogni combinazione tipo profilo ↔ tipo
      binding (REPARTO/PORTALE coerenti e incoerenti).
- [ ] 7.1.7 pgTAP: RLS policy su fatture (cliente A non vede cliente B)
      — rimandato a §4.9 (RLS non ancora attivate).
- [ ] 7.1.8 pgTAP: RLS bypass per operatore interno — rimandato a §4.9.

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

- [x] 10.1 **Admin di portale?** — *Decisione 2026-04-18*: rimandato a
      Fase 2 post-MVP. Il modello architetturale supporta nativamente
      l'aggiunta futura del ruolo `CLIENTE_ADMIN_PORTALE` (enum value +
      profilo standard + endpoint `POST /api/portale/utenti/invita`)
      senza refactor strutturali. MVP: un solo account per cliente.
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
* **2026-04-18 (stesso giorno, sessione implementativa)**: completate le
  prime 5 sotto-fasi DB.
  * **§4.1 ENUM** (2 file): `ruolo_applicativo`, `tipo_profilo_accesso`.
    `config.tipo_token` risulta varchar, nessun DDL necessario.
  * **§4.2 Bridge `identita_digitali`** (7 file): tabella + storico +
    guard coerenza ruolo + nuova funzione riusabile
    `script.fn_guard_soggetto_pf_pura` + refactor del vecchio trigger
    guard su RUA per delegare alla funzione riusabile.
  * **§4.3 Profili accesso** (15 file): 4 tabelle nuove +
    4 storiche + guard tipo profilo <-> tipo binding + migrazione dati
    REPARTO idempotente + seed 3 profili PORTALE via CSV +
    loadUpdateData + aggiornamento `messaggi_errore.csv` (2 nuovi codici).
  * **§4.4 Scope policy** (10 file): 2 tabelle + 2 storiche + 3 funzioni
    `fn_scope_*` (`LANGUAGE sql STABLE`, fail-closed) + seed CSV +
    backfill EF_WHITELIST. `SELF_OWNERSHIP` unificato con `BA_OWNERSHIP`
    (cliente portale e shop condividono il ruolo CL).
  * **§4.5 Generalizzazione sync** (4 file): nuova firma
    `fn_sync_auth_user_is_active(p_auth_user_id integer)` con algoritmo
    expand-align-contract (priorita identita nuova, fallback legacy) +
    fix implicito del bug latente §3.2.b + doppia verifica OPERATORE
    temporanea + aggiornamento 2 trigger function esistenti + nuovo
    trigger su `identita_digitali` + estensione `fn_sync_auth_user_expired`
    a UNION di RU legacy + identita nuove.
  * **Doc concettuale**: 19 nuovi manual + 4 manual esistenti aggiornati
    (sync auth_user family).
  * **pgTAP §7.1 (recupero debito)**: 1 file aggiornato + 6 nuovi file,
    totale ~50 casi di test. Coperture: guard coerenza identita, guard
    bindings, funzione riusabile PF pura, 3 scope policy. Aperti: sync
    per identita portale/shop (post cutover §4.6) e RLS (§4.9).
  * **Aperto**: §4.6 vista compatibilita, §4.7 GUC, §4.8 resolve_livello_*,
    §4.9 RLS.
* **2026-04-19 (sessione implementativa — PR1 DB estesa)**: completate
  §4.6, §4.7, §4.8 DB-side. Backend PR2 ora puo' partire in parallelo.
  * **§4.6 Cutover operatori** (25 file): decisione di design "ADMIN come
    profilo SUPER_ADMIN" (non boolean). Estensione `identita_digitali`
    con 4 colonne stateful (tentativi_falliti, bloccato_fino_a,
    totp_obbligatorio, storicizza). Nuovo tipo ENUM `SUPER_ADMIN` +
    seed profilo 9100 + guard bindings aggiornato. Helper DRY
    `fn_has_identita_attiva(auth_user_id, ruolo_applicativo)` e
    `fn_is_super_admin(auth_user_id)`. Refactor 11 funzioni resolver
    (fn_resolve_livello_*, fn_check_*, fn_get_emittenti_*,
    fn_get_user_profile, fn_check_operatore_invitabile, fn_get_setup_status),
    wrapper retrocompatibile `fn_get_ruolo_sistema`. Writer DB:
    fn_registra_tentativo_login, fn_check_blocco_login, fn_crea_risorsa_umana
    aggiornate. Trigger-ponte TEMPORANEO
    `trgfn_risorse_umane_auth_user_sync_identita` (rimovibile al cutover
    §4.6.H.3). Backfill 80_data (identita OPERATORE per RUA esistenti +
    bindings SUPER_ADMIN per ADMIN legacy). Vista di compatibilita'
    `anagrafiche.vw_risorse_umane_auth_user` (prefisso `vw_` fino al
    rename §4.6.H.2) con sub-query pre-aggregata LEFT JOIN per
    evitare N+1 su fn_is_super_admin.
  * **§4.7 GUC e propagazione identita** (2 file): documentati i 3 GUC
    di sessione `app.current_identita_id`, `app.ruolo_applicativo`,
    `app.soggetto_ruolo_id` in parametri-personalizzati-(GUC).md +
    guc_reference.md. Creato helper
    `script.fn_current_identita_context()` RETURNS TABLE (lettura
    tipizzata fail-soft con `NULLIF(current_setting(..., true), '')::tipo`).
    Manual + test pgTAP (6 casi).
  * **§3.8 + §3.9 docs RLS**: verificati e completati. Aggiunto
    riferimento a `fn_current_identita_context` in entrambi i file.
  * **§4.8 Resolver generalizzato su `profili_accesso`** (5 file):
    nuovo helper `fn_get_profili_accesso_applicabili(auth_user_id)`
    che risolve i profili applicabili via 3 UNION (AD_HOC prio 1,
    PORTALE prio 2, REPARTO prio 2). Update fn_resolve_livello_area
    (-51), fn_check_azione_processo (-52), fn_get_user_permissions_map
    (-53), fn_get_user_actions_map (-54) per leggere dal nuovo modello
    via helper. fn_resolve_livello_oggetto generalizzato
    implicitamente (fallback area). Manual helper + test pgTAP helper
    (5 casi) + test regression end-to-end operatore (11 casi con seed
    'tid' spostato temporaneamente in UO test).
  * **Criticita' gestite in-session**:
    * Bug `fn_crea_risorsa_umana` doppio INSERT conflittante col
      trigger-ponte -> rimosso doppio INSERT, delegato al trigger.
    * Performance vista `vw_risorse_umane_auth_user` N+1 su
      fn_is_super_admin -> sostituito con LEFT JOIN sub-query
      pre-aggregata.
    * Violazione DRY (7 funzioni duplicavano lo stesso EXISTS identita)
      -> introdotto helper `fn_has_identita_attiva` parametrizzato,
      refactor 8 funzioni.
    * Ordering preCondition Liquibase (sqlCheck su risorse create in
      file processati dopo) -> rimossi check runtime, documentata
      dipendenza semantica.
    * Tentativa di modifica in-place di file Liquibase gia' pushati
      (fn_resolve_livello_area -11, fn_check_azione_processo -13) ->
      ripristino con git restore + creazione nuovi file successivi
      (-51, -52) con CREATE OR REPLACE.
  * **Pendenze residue DB**: §4.9 RLS (richiede GUC popolati da
    backend PR2), §4.6.H cutover (rinomina tabella legacy + rimozione
    trigger-ponte, richiede PR2 stabile), rimozione doppia verifica
    OPERATORE in `fn_sync_auth_user_is_active` (post cutover).

---

{% include-markdown "signature-core.md" %}
