# Multi-face auth — da completare (dominio portale/shop; la RLS è accesa)

> **Scopo.** Documento di lavoro che raccoglie in un punto solo **cosa manca**
> per chiudere lo sviluppo multi-face auth (portale clienti/fornitori + shop
> B2C). Nato il 2026-05-30 come piano per **accendere la RLS**: quella parte è
> **superata** — la RLS è accesa dal 2026-06-01 e oggi copre 95 tabelle — e
> il documento è stato riscritto per dire che cosa resta *davvero*.
>
> ⚠️ **Perché la versione precedente sbagliava.** Diceva «RLS dormiente per
> scelta deliberata, si accende solo dopo le API portale». Il giorno dopo
> (2026-06-01) il team DB l'ha accesa **per un altro asse** — lo scope emittente
> fiscale degli **operatori**, che un consumatore lo aveva già — e da lì è
> cresciuta per ondate fino a oggi. Il documento non è stato riletto per tre
> mesi e la memoria dell'agente ha continuato a ripeterlo. *Un documento che
> descrive un blocco superato non è neutro: rimanda lavoro che non è più
> bloccato.*
>
> **Fonti.** Estratto e riorganizzato da:
> - [sviluppo-multi-face-auth.md](../work-done/sviluppo-multi-face-auth.md) (in
>   `work-done` ma con checklist ancora aperte — è il vero WIP appeso)
> - [sviluppo-portale-shop.md](sviluppo-portale-shop.md)
> - [smoke-b1-invito-shop-checklist.md](smoke-b1-invito-shop-checklist.md)
> - **RLS, tre documenti di riferimento**:
>   [analisi-attivazione-rls-operatori.md](../work-done/analisi-attivazione-rls-operatori.md)
>   (le decisioni, §11) ·
>   [analisi-attivazione-rls-db.md](../work-done/analisi-attivazione-rls-db.md)
>   (il log DB, §15) ·
>   [architettura-multi-face-auth.md §6](../../guide/architettura-multi-face-auth.md)
>   (il modello)
> - **Il presidio vivo**: `dbops.vw_rls_perimetro_scoperto` +
>   `dbops.rls_perimetro_debito` (CSV in `80_data/sql/dbops/`), che dicono
>   *oggi* che cosa è scoperto e perché.
>
> I riferimenti `§x.y` puntano alle sezioni dei doc di origine. **Aggiornato:
> 2026-09-12** (stato letto dal catalogo di PostgreSQL di `dbdev` e dal codice,
> non a memoria).

---

## 0. Dove siamo (snapshot 2026-09-11)

**Fatto e stabile**

- PR-A (cutover DB+BE) e PR-B1..B4 (foundation auth + login multi-canale + FE
  profilo/stub shop) chiusi al 2026-04-21. Post-merge: **invito shop
  admin-driven** + stato/disattiva veste (`invita-portale`, `invita-shop`,
  `WebAccessiDrawer`, `PortaleAccessoPanel`).
- **Blocker di PR-C — RISOLTO 2026-04-21**: erano i 4 resolver ruolo-aware +
  `is_super_admin` (§13.7), non la RLS.
- ⭐ **RLS: ACCESA, non dormiente.** Attivata il **2026-06-01** per lo scope
  emittente fiscale (EF) degli OPERATORI — Ondata 1 SR (`20260601-38`), Ondata 2
  PK (`-39/-40/-41`) — e poi estesa **per ondate** fino al `20260911-02`:
  satelliti fattura (2026-07-29, brief «rls-satelliti-fattura-portale»),
  commesse, DDT, resi, lotti, listini, note, `event_log`, `pagamenti.*`,
  `config.email_*`, `documenti.*`, `pratiche.*`. Le policy `ef_whitelist` sono
  `FOR ALL` dal 2026-06-03 (brief «ondata2-insert-bloccati»: una `FOR SELECT`
  sola manda in deny-all le scritture).

**Stato letto dal catalogo (`pg_class`/`pg_policy`, 2026-09-11 — fatto datato)**

| Cosa | Valore |
| --- | --- |
| Tabelle con `ENABLE ROW LEVEL SECURITY` | **95** — `vendite` 68 · `pratiche` 10 · `anagrafiche` 6 · `pagamenti` 6 · `documenti` 3 · `config` 2 |
| `FORCE ROW LEVEL SECURITY` | **0**, per decisione (§9 del brief DB): owner `titodb` e superuser `postgres` (pgAgent) restano esenti → migrazioni e job non si bloccano |
| Ruolo applicativo `zeroerp_app` | `NOBYPASSRLS` ✅ — la RLS morde davvero |
| Ruoli batch | `zeroerp_batch_fatturazione` **BYPASSRLS**, creato dal provisioning per-job (brief «contesto-sistema-batch-fatturazione-rls», 2026-06-17); processi automatici con identità propria dal 2026-09-04 (brief «processi-automatici-identita-e-perimetro») |
| Tabelle con policy **e RLS spenta** (`POLICY_INERTE`) | **3**: `acquisti.ddt`, `acquisti.ordini`, `shop.ricevute` — tutte **a debito dichiarato** il 2026-09-09 (§1.4) |
| Figlie di tabelle protette senza copertura | **7**, tutte `DEBITO_DICHIARATO`; **zero `NON_DICHIARATO`** |

> **Nota 2026-11-04**: il ruolo `zeroerp_batch_fatturazione` della riga «Ruoli batch» è **ritirato
> dal 2026-10-15** e non esiste più; il suo nome sopravvive solo nell'elenco delle porte dichiarate
> di [dbops.vw_processi_che_bypassano](/dbzero/dbops/views/vw_processi_che_bypassano).

⭐ **Le branch portale/shop NON sono dry-run.** Sulle tabelle accese, le policy
`*_ba_ownership` (CLIENTE_PORTALE), `*_cliente_ownership` (CLIENTE_PORTALE),
`*_shop` (SHOP_CUSTOMER) sono policy permissive `FOR SELECT` che PostgreSQL
**applica già**, in OR con la `ef_whitelist`: `anagrafiche.billing_account`
(4 policy), `anagrafiche.clienti` (3), `vendite.fatture` + 12 satelliti (2
ciascuna), `vendite.ordini` + 5 satelliti (3 ciascuna), `vendite.note`,
`note_fatture`, `note_ordini`. Una sessione che entrasse con
`app.ruolo_applicativo = 'CLIENTE_PORTALE'` **oggi verrebbe filtrata** — lo prova
il caso 12 di `db/pgtap/rls/test-rls-fatture-satelliti-functional.sql` (veste
non proprietaria → zero righe). ⇒ **Manca il consumatore, non l'accensione.**

**Il vero blocco a monte — è lo stesso di maggio, ma è l'unico rimasto**

Le **API di dominio del portale/shop non esistono** (verificato su
`backend/apps/portale/api/urls.py` e `backend/apps/shop/api/urls.py`): il
portale espone attivazione + `profile/activate-shop/` (stub 501), lo shop
attivazione + `register/check-email/` (stub). Nessuna rotta legge fatture,
ordini, catalogo. La RLS le aspetta armata; il rischio di lockout di cui parlava
la versione precedente **non esiste**, perché la faccia OPERATORE ha la sua
branch `FOR ALL` su ogni tabella accesa.

---

## 1. RLS — che cosa è chiuso e che cosa resta

### 1.1 Prerequisiti dell'accensione (erano «non saltabili»: sono passati)

- [x] **GUC di sessione propagati** (PR-A): `set_jwt_gucs` in
      `backend/apps/core/api/jwt_audit_authentication.py`, 5 GUC, invariante
      tutto-o-niente.
- [x] **R-GUC — reset per richiesta, fail-closed** (2026-06-02, Stream A del
      piano BE/FE): senza questo i GUC session-scoped con `CONN_MAX_AGE`
      avrebbero perso fra richieste. Era il gate dell'`ENABLE`.
- [x] `zeroerp_app` = `NOBYPASSRLS` — verificato sul catalogo 2026-09-11.
- [ ] **Un consumatore portale/shop** che legga le tabelle sotto la veste
      corretta. ⚠️ Non era un prerequisito dell'accensione (lo si credeva): è il
      prerequisito della **prova end-to-end** delle branch portale (§2.7).

### 1.2 Attivazione (team DB — CHIUSA per l'asse operatore)

> Azioni DDL/policy/migration: **mai eseguite dal backend agent**. Brief al team
> DB su `dev/db-tid` (regola `feedback_db_actions_passaggio_team`).

- [x] `ENABLE` **per famiglia di join atomica**, mai per tabella isolata (R9);
      changeset **kill-switch gemello** `DISABLE` per ogni ondata, policy
      preservate (mai `DROP POLICY` come rollback).
- [x] **No `FORCE`** — decisione §9 del brief DB, confermata dal catalogo.
- [x] ~~`BYPASSRLS` a `zeroerp_admin`/`zeroerp_migration`~~ → quei ruoli non
      esistono; il problema è risolto altrimenti: owner esente (no FORCE),
      pgAgent come `postgres`, ruoli **batch per-job** `zeroerp_batch_*`
      `BYPASSRLS` dal provisioning (`scripts/sql/provision_db_role_batch_*.sql`,
      mai da changeSet — regola in AGENTS.md).
- [x] **pgTAP**: 37 file `test-*rls*.sql` (`db/pgtap/rls/` + per schema),
      strutturali e funzionali; dal **2026-08-07 l'intera suite gira come
      l'applicazione** (`zeroerp_app` + contesto operatore, brief
      «pgtap-runner-rls-baseline»), quindi **ogni pgTAP passa sotto RLS**, non
      solo quelli che la nominano.
- [x] **Smoke operatore** `backend/scripts/tests/smoke-test-rls-emittente-operatore.sh`:
      lista filtrata, dettaglio fuori scope → 404, controprova in scope → 200.
- [~] ~~**§4.9.8 Benchmark formale** pre/post `ENABLE` (soglia ≤ 10%)~~ —
      **RITIRATO dal team DB il 2026-09-11** (`f7169c956`), non chiuso: la RLS
      operatori è in esercizio dal 02-06 senza che sia mai stato eseguito, e la
      premessa era falsa — il predicato RLS è una **chiamata di funzione per
      riga** (`fn_check_user_emittente_scope`, plpgsql), opaca al planner, non
      un confronto indicizzabile. Lo script `benchmark-rls-ondata1.sql` è
      **cancellato**. ⭐ La regola che lo sostituisce (`linee-guida-sql` §10.9):
      per la FK della colonna emittente una **decisione dichiarata** in
      `dbops.fk_index_policy` (seed CSV con `true`/`false` e il perché), e un
      indice si decide sulla **query dell'applicazione** che entra da quella
      colonna — mai sulla policy, mai a mano (`90_end` lo rimuoverebbe al
      primo migrate, com'è successo a 4 indici su 6 di `20260601-34`).

### 1.3 Decisioni di rilascio (erano aperte: chiuse)

- [x] Tutte insieme o a tranche? → **per ondate, una famiglia di join per
      volta**, ognuna con kill-switch.
- [x] Kill switch → changeset gemello `DISABLE ROW LEVEL SECURITY`.

### 1.4 Che cosa resta della RLS *per il multi-face* — tutto a debito dichiarato

Il presidio è `dbops.vw_rls_perimetro_scoperto`, con due criteri letti dal
catalogo; ciò che resta scoperto **per decisione** sta in
`dbops.rls_perimetro_debito`, che è un registro del debito e **deve calare**.
Al 2026-09-11 nessuna riga è `NON_DICHIARATO`. Le voci che toccano questo
cantiere:

| Tabella | Criterio | Perché è ferma | Chi la chiude |
| --- | --- | --- | --- |
| `shop.ricevute` | `POLICY_INERTE` + figlia di BA/ordine | Policy `SHOP_CUSTOMER FOR SELECT` c'è; accenderla costa **una riga** e non toglie niente a nessuno (`zeroerp_app` non ha GRANT sulla tabella). Ferma perché la decisione è del cantiere shop | **Stage D shop** (§3) |
| `acquisti.ordini`, `acquisti.ddt` | `POLICY_INERTE` | Policy `FORNITORE_PORTALE FOR SELECT` sola: accesa oggi chiuderebbe le tabelle all'OPERATORE, che ci scrive (`SELECT/INSERT/UPDATE/DELETE`). **Manca la colonna emittente**, quindi manca la branch operatore, quindi manca il modello — non l'accensione | **Cantiere `acquisti`** — 🔵 il prossimo, per decisione di Tid del 2026-09-11 (`PROJECT_CONTEXT.md`). Le due si armano insieme |
| `anagrafiche.emittenti_fiscali_billing_account`, `resellers_billing_account` | figlia di BA | Definiscono il legame da cui la whitelist si deriva: una policy si appoggerebbe a sé stessa. Domanda di modello (catalogo o dato di perimetro?) | decisione di Tid, fuori da questo cantiere |
| `anagrafiche.pdp`, `magazzino.assets`, `pagamenti.sepa_mandati` | figlia di BA/clienti/contratto | FK **nullable**: una policy su chiave nullable ha un buco esatto dove passa il NULL. Prima si decide il verso del perimetro | cantieri magazzino / pagamenti |
| `config.email_allegato` | figlia di `email_log`/`email_outbox` | Il perimetro lì è l'**ambito**, non l'emittente: policy a due rami | cantiere email |

E due lavori adiacenti, **non** di questo cantiere ma che lo toccano:

- [x] [brief-db-rls-storico-scope-congelato.md](../work-done/brief-db-rls-storico-scope-congelato.md)
      — lo storico porta il proprio perimetro e non lo ricalcola: **APPLICATO
      il 2026-09-11** (passi 1-7, 37 shadow armate con `scope_emittente_fiscale_id`
      congelato alla scrittura e policy `FOR SELECT` generate da
      `dbops.fn_storico_arma_scope`; `audit_log` §8 applicato). ⏳ Restano la
      decisione §8.3 (registro tecnico o di dominio, di Tid) e i debiti §4d.
      ⇒ Per il portale conta: **la storia di una riga protetta è protetta come
      la riga** — le shadow delle tabelle con branch portale seguono la madre,
      non serve una policy a parte.
- [x] Utenti tecnici con emittente e `system_process_context` per i processi
      headless — chiuso 2026-09-04/06 (brief «processi-automatici-*»).

---

## 2. Sviluppo residuo (per chiudere PR-C / PR-D)

La RLS c'è. Perché serva al portale va costruito il dominio portale/shop
sopra. Raggruppato per livello; le caselle sono state **riverificate sul codice
il 2026-09-11**.

### 2.1 DB — modello identità/profili (§5.1, §13.3-13.4) — CHIUSO

- [x] `identita_digitali` è la tabella; `risorse_umane_auth_user` è una **vista**
      che ci legge sopra e la tabella vecchia è archiviata come
      `anagrafiche._legacy_risorse_umane_auth_user` (cutover 2026-04-19,
      §13.3.2). ✅ Il **drop fisico** è stato fatto il 12-09-2026 (§2.9).
- [x] Tabelle profili: `config.profili_accesso`, `profili_accesso_aree`,
      `profili_accesso_azioni`, `profili_accesso_bindings`, `scope_policy`,
      `identita_scope_bindings` (doc auto-gen in `docs/it/dbzero/config/tabelle/`).

### 2.2 BE — auth, resolver, GUC, permission (§5.2-5.4, §13.4) — quasi chiuso

- [x] Resolver ruolo-aware + `is_super_admin` GUC-aware (blocker PR-C, 2026-04-21).
- [x] `JwtAuditAuthentication`: identità attiva → 5 GUC, 401 senza identità,
      **reset per richiesta** (2026-06-02).
- [x] `PortaleAPIView` / `ShopAPIView` (`apps/core/api/base_views.py`),
      `PortaleBasePermission` / `ShopBasePermission`
      (`apps/core/api/permissions.py`); routing `/api/portale/*` e `/api/shop/*`
      montato.
- [ ] Throttle **dedicati** agli endpoint shop pubblici: oggi esistono
      `LoginRateThrottle` e `PasswordResetRateThrottle` generici
      (`apps/core/api/throttling.py`); il register shop (§2.3) porterà il suo.
- [ ] Cleanup writer/repo amm_software ruolo-aware (§13.4.15-13.4.18) — *non
      riverificato in questa revisione*.

### 2.3 BE — servizi inviti/registrazione (§5.5-5.6)

- [x] Portale: `InvitoPortaleService`, token `INVITO_PORTALE` /
      `ATTIVAZIONE_PORTALE_CROSS`, `clienti/<id>/invita-portale/`,
      `fornitori/<id>/invita-portale/`, `attivazione/validate/<token>/` +
      `attivazione/conferma/`.
- [x] Shop **admin-driven**: `clienti/<id>/invita-shop/` + attivazione shop
      (`/api/shop/attivazione/*`), post-merge PR-B.
- [ ] Shop **self-register** pubblico: `registrazione_service` (transazione
      atomica), email unica sui 3 mondi, token `VERIFICA_EMAIL_SHOP` (24h),
      `register` (throttle 3/1h per IP) + `verifica-email`. Oggi esiste solo lo
      stub `ShopRegisterCheckEmailView` (il commento in `urls.py` lo dichiara).
- [ ] `profile/activate-shop/` dal portale: stub **501** «finché PR-C».

### 2.4 BE — API di dominio (§5.7-5.9) — **il blocco reale, nulla iniziato**

> ⭐ Non sono più «prerequisito della RLS»: sono il **consumatore** che la RLS
> armata sta aspettando. Ogni rotta qui sotto nasce già filtrata dal DB per la
> veste che la chiama; il backend non deve riscrivere nessun filtro di scope.

- [ ] **Portale cliente**: `me`, `billing-account`, `fatture` (lista/dettaglio/PDF),
      `scadenze`. Le tabelle sono tutte accese con branch `CLIENTE_PORTALE`
      (fatture + 12 satelliti, scadenze incluse).
- [ ] **Portale fornitore**: `ordini-ricevuti` (lista/dettaglio),
      `pagamenti-verso-di-me`. ⚠️ `acquisti.ordini`/`ddt` sono le due tabelle a
      **policy inerte**: questa parte dipende dal cantiere `acquisti` (§1.4).
- [ ] **Shop**: `catalogo` (pubblico) + `{sku}`, `carrello`, `checkout`
      (SHOP_CUSTOMER), `ordini`. Branch `SHOP_CUSTOMER` accese su BA, clienti,
      ordini + satelliti, note; `shop.ricevute` da accendere nello stesso gesto.
- [ ] Export PDF fattura per il portale: il motore documentale e la **ristampa
      fedele** (`GET .../documenti/<id>/ristampa/`, 6 domini) esistono lato
      operatore — la decisione è se il portale riusa quella rotta sotto
      `PortaleAPIView` o ne ha una sua (§3.3).

### 2.5 BE — hardening (§5.10)

- [ ] Rate limit login portale (5/5min IP) e reset password shop (3/15min IP)
      — oggi valori generici in `throttling.py`.
- [ ] Email di sicurezza ad ogni cambio password (§2.2 portale-shop).
- [ ] Audit sessioni con la veste: `dbops.sessioni_utente` **non** ha una
      colonna `ruolo_applicativo` (ha `dettaglio jsonb`; se la veste finisce lì
      non è stato verificato). Tracciamento LOGIN/LOGOUT/REFRESH per veste →
      brief DB.
- [ ] Headers di sicurezza dedicati `/api/shop/*` e `/api/portale/*` (CSP,
      no-cache documenti sensibili).

### 2.6 FE (§6, §13.5)

- [ ] **Decisione architetturale**: bundle unico con router guard per ruolo
      **oppure** build separate portale/shop (§6.1.1 / §10.2). ⚠️ *De facto* i
      flussi auth stanno già nel bundle unico (`/attivazione-portale/:token`,
      `/attivazione-shop/:token`, `portale/profile`, stub `shop`); la decisione
      per il **dominio** non è registrata da nessuna parte. Sblocca il resto.
- [x] Store auth: `ruoloApplicativo`, `isSuperAdmin`, router guard per
      namespace (PR-B3).
- [x] Admin: pannello accessi web su Cliente/Fornitore
      (`PortaleAccessoPanel.vue`, `WebAccessiDrawer.vue`,
      `AttivaAccessoShopButton.vue`, `portaleAdminApi.js`: invito, stato,
      reinvia, disattiva veste).
- [x] Auth flow: login multi-canale, pagina attivazione invito portale e shop,
      `ProfileView` portale con card «Accessi» (PR-B4).
- [ ] Portale cliente: layout dedicato, dashboard, «Le mie fatture»,
      scadenzario, tema distinto (§6.4). ⛔ Le liste passano da
      `<ListaConfigurabile>` come tutto il resto (AGENTS.md).
- [ ] Portale fornitore: layout, ordini ricevuti, pagamenti (§6.5).
- [ ] Shop: catalogo, prodotto, carrello, registrazione, verifica email, «I miei
      ordini», checkout (§6.6).
- [ ] Sezione «Profili di accesso» sotto Amm. Software (§6.3) — *non
      riverificato*.

### 2.7 Test (§7)

- [x] pgTAP RLS: 37 file, funzionali inclusi; la veste `CLIENTE_PORTALE` non
      proprietaria è provata (caso 12 di `test-rls-fatture-satelliti-functional`,
      `test-rls-ordini-multipolicy`, `test-fn-scope-ba-ownership-ruolo-aware`).
- [x] Smoke RLS lato operatore (`smoke-test-rls-emittente-operatore.sh`).
- [ ] Unit/integration BE: API portale/shop, cross-role, register, rate limit
      (§7.2) — nascono con §2.3/§2.4.
- [ ] Smoke e2e multi-face (`smoke-test-multi-face-auth.sh`, **non esiste**):
      invito cliente, invito fornitore, register shop, **leak cross-user → con
      la RLS accesa deve dare ZERO righe, non 403**. ⚠️ Richiede §2.4: senza
      una rotta che legga, non c'è niente da provare end-to-end.

### 2.8 Doc (§7.4)

- [ ] Guide: «Portale Clienti», «Portale Fornitori», «Shop Online».
- [x] GUC documentati: `docs/it/guide/contratto-guc-app.md`,
      `guc_reference.md`, `parametri-personalizzati-(GUC).md`.
- [x] `api.md` con i namespace `/api/portale/*` e `/api/shop/*` (base view e
      permission class dedicate).
- [ ] La nota «Aggiornamento giugno 2026 — RLS a due velocità» in
      `architettura-multi-face-auth.md` **§14** («Stato portale e shop») dice
      ancora «branch portale/shop dry-run/dormienti»: va riscritta come in §0
      qui — *armate, senza consumatore*; dormienti solo le tre `POLICY_INERTE`.

### 2.9 Rollout (§8) — *fuori scope finché non in produzione*

> ZeroErp non è in produzione (`project_no_produzione_solo_sviluppo`): niente
> staging/feature-flag/pilota, niente gradient di rilascio.

- [x] Drop fisico di `anagrafiche._legacy_risorse_umane_auth_user` — ✅
      **fatto il 12-09-2026** (`90_end/20260912-10`, con shadow `-08` e
      registrazioni `-09`; decisione Tid: «senza produzione è sporcizia», quindi
      non aspetta il rollout). ⚠️ Stava qui «fuori scope finché non in
      produzione»: era la ragione sbagliata, perché la tabella non era inerte
      (due FK `ON DELETE RESTRICT`, `storicizza` che la riarmava a ogni
      `ci_apply`). Storia in `work-done/brief-db-rls-storico-scope-congelato.md`
      §10. *(Il «benchmark post-RLS > 10%» che stava qui è ritirato — §1.2.)*

---

## 3. Decisioni di dominio da chiudere prima di implementare (§3 portale-shop)

Nessuna di queste risulta decisa al 2026-09-11.

- [ ] **3.1 Catalogo shop**: flag `vendibile_shop` vs listino dedicato; pricing
      B2C (iva inclusa?); controllo stock real-time?
- [ ] **3.2 Checkout**: ricevuta non-fiscale (`shop.ricevute`) vs fattura con CF a
      scelta; integrazione `pagamenti` (il giro incassi esiste dal 2026-08-28:
      distinte, abbinamento, registrazione); resi/rimborsi (oggi fuori modello).
- [ ] **3.5 Brand shop**: tema dedicato vs look admin; multilingua IT+EN da subito?
- [ ] **10.x questioni aperte**: frontend separato/unico, multilingua portale,
      scope agenti di vendita, API pubbliche `API_CLIENT`, notifiche in-app,
      collegamento `identita_digitali → anagrafiche.contatti`.

---

## 4. Ordine consigliato (riscritto: la RLS non è più un passo)

1. **API portale cliente (§2.4)** — è il consumatore che manca. Le policy
   `CLIENTE_PORTALE` sono già accese su fatture, satelliti, scadenze e BA: la
   prima rotta `GET /api/portale/fatture/` sotto `PortaleAPIView` è **già
   filtrata dal DB** il giorno in cui nasce.
2. **Decisione bundle FE (§2.6)** e poi portale cliente a video — «Le mie
   fatture» è la vetrina naturale, e usa liste e drawer che esistono già lato
   operatore.
3. **Smoke leak cross-user (§2.7)** appena esiste la prima rotta: zero righe,
   non 403. È la prova che il §0 promette e che nessun pgTAP può dare.
4. **Portale fornitore** → dopo il cantiere `acquisti` (colonna emittente su
   `acquisti.ordini`/`ddt`, branch operatore, `ENABLE`).
5. **Shop** → prima le decisioni §3, poi Stage D con `shop.ricevute` accesa
   nello stesso gesto; il self-register (§2.3) e l'hardening (§2.5) vivono lì.

> Suggerimento doc sorgente: ogni blocco §2.x può diventare uno **sprint
> dedicato con WIP figlio**. Con la RLS accesa, il portale cliente non ha più
> nessuna dipendenza esterna: è il primo candidato.

---

## 5. Registro delle revisioni

| Data | Che cosa |
| --- | --- |
| 2026-05-30 | Prima stesura: piano per accendere la RLS «dopo le API portale» |
| 2026-09-12 | Integrato il merge DB #1563: benchmark RLS **ritirato** (§1.2, §2.9), storico-scope **applicato** (§1.4) |
| 2026-09-11 | Riscritto sullo stato reale: RLS accesa dal 2026-06-01 (asse operatore) e cresciuta a 95 tabelle; branch portale/shop **armate** sulle tabelle accese; 3 `POLICY_INERTE` a debito dichiarato; §2 riverificato sul codice; §4 riordinato. Stato letto dal catalogo di `dbdev` e da `urls.py`, non dai changeSet |
