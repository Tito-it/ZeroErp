# Multi-face auth — da completare (RLS + sviluppo residuo)

> **Scopo.** Documento di lavoro che raccoglie in un punto solo **cosa manca**
> per chiudere lo sviluppo multi-face auth (portale clienti/fornitori + shop
> B2C) e, in particolare, per **attivare la RLS** oggi parcheggiata in dry-run.
>
> **Fonti.** Estratto e riorganizzato da:
> - [sviluppo-multi-face-auth.md](../work-done/sviluppo-multi-face-auth.md) (in
>   `work-done` ma con checklist ancora aperte — è il vero WIP appeso)
> - [sviluppo-portale-shop.md](sviluppo-portale-shop.md)
> - [smoke-b1-invito-shop-checklist.md](smoke-b1-invito-shop-checklist.md)
>
> I riferimenti `§x.y` puntano alle sezioni di quei due doc, così ogni voce qui
> resta tracciabile alla fonte. Aggiornato: 2026-05-30.

---

## 0. Dove siamo (snapshot)

**Fatto e stabile**
- PR-A (cutover DB+BE) e PR-B1..B4 (foundation auth + login multi-canale + FE
  profilo/stub shop) chiusi al 2026-04-21.
- **Blocker di PR-C — RISOLTO 2026-04-21**: erano i 4 resolver ruolo-aware +
  `is_super_admin` (§13.7), **non** l'attivazione RLS. Da non confondere: il
  blocker chiuso ha sbloccato lo smoke guard FE §8.3.9, ma la RLS resta da
  accendere.
- **RLS: fase DRY-RUN completata** (policy create il 19-04, ondata shop il
  20-04). Le policy esistono ma le tabelle **non** hanno `ENABLE ROW LEVEL
  SECURITY` → sono **dormienti per scelta deliberata**, non un lavoro lasciato
  a metà.

**Il vero blocco a monte**
Le **API di dominio del portale/shop non esistono ancora** (fatture viste dal
cliente, ordini del fornitore, catalogo B2C, checkout). La regola del doc è
esplicita: attivare RLS (`ENABLE`+`FORCE`) **solo dopo** che backend e frontend
portale sono pronti a popolare i GUC per ogni tipo di utente — altrimenti le
query esistenti si bloccano (fail-closed). Senza un consumatore esterno reale,
accendere la RLS non serve e anzi rischia il lockout.

**Nota di precisione (verificata sui doc)**
- Le tabelle della **prima ondata RLS sono 6**, non 8:
  `vendite.fatture`, `vendite.fatture_scadenze`, `vendite.ordini`,
  `acquisti.ordini`, `acquisti.ddt`, `anagrafiche.billing_account`.
- C'è poi una **seconda ondata shop** (3 policy dry-run, file `20260420-07`):
  `rls_shop_ricevute` (tabella nuova `shop.ricevute`), `rls_billing_account_shop`
  (billing_account, già contata), `rls_ordini_shop` (vendite.ordini, già
  contata). Tabelle **distinte** totali = **7** (le 6 + `shop.ricevute`).
- Le policy `billing_account` e `vendite.ordini` esistono in **doppia variante**
  (portale CLIENTE_PORTALE vs shop SHOP_CUSTOMER, split `20260420-08`): vanno
  attivate insieme.

---

## 1. Completamento RLS (focus)

Riferimento: `sviluppo-multi-face-auth.md §4.9.7-4.9.9` + `sviluppo-portale-shop.md §2.1, §3.4`.

### 1.1 Prerequisiti per poter accendere (non saltabili)
La RLS fa fail-closed: senza GUC popolati, le query non vedono nulla. Prima di
attivare servono **tutti** questi:

- [x] **GUC di sessione già propagati** dal backend (PR-A): `set_jwt_gucs` in
      `backend/apps/core/api/jwt_audit_authentication.py` popola i 5 GUC
      (`app.jwt_user`, `app.current_user_id`, `app.current_identita_id`,
      `app.ruolo_applicativo`, `app.soggetto_ruolo_id`) subito dopo l'auth, con
      invariante "tutto o niente" (identità orfana → stringhe vuote → fail-closed).
      **Questo strato c'è già**, non va rifatto.
- [ ] Almeno un set di **API portale/shop** che legge le tabelle target sotto la
      veste corretta (§1.1/§1.3 portale-shop), così la RLS ha un consumatore
      reale che esercita i GUC end-to-end.
- [ ] Verifica grant: `zeroerp_app` deve essere `NOBYPASSRLS` (§3.5).

### 1.2 Attivazione (checklist DB — passaggio team DB)
> Azioni DDL/policy/migration: **mai eseguite dal backend agent**. Brief scritto
> al team DB su `dev/db-tid` (regola `feedback_db_actions_passaggio_team`).

- [ ] **§4.9.7** Migration dedicata: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
      + `FORCE ROW LEVEL SECURITY` sulle 6 tabelle prima ondata **+** sulle
      tabelle shop (`shop.ricevute`, e le varianti shop su billing_account /
      vendite.ordini).
- [ ] Concessioni `BYPASSRLS` ai ruoli tecnici `zeroerp_admin` /
      `zeroerp_migration` (via `ALTER ROLE`), così gli operatori interni non
      vengono filtrati. Verifica preventiva `zeroerp_app` = `NOBYPASSRLS`.
- [~] **§4.9.8** Benchmark pre/post su query chiave — **ritirato il 2026-09-11**:
      la RLS operatori è in esercizio dal 02-06 senza benchmark, e la voce
      «≤ 10%» è uscita da linee-guida-sql §10.9 perché il predicato RLS è una
      chiamata di funzione per riga, non un confronto indicizzabile. Per le
      tabelle portale/shop vale la regola nuova di §10.9: decisione dichiarata
      in `dbops.fk_index_policy` per la FK di scope, non una misura.
- [ ] **§4.9.9** pgTAP per ogni policy attivata: utente visibile, utente non
      autorizzato, senza GUC (fail-closed), bypass ruolo tecnico. File in
      `db/pgtap/rls/<schema>_<tabella>_rls.sql`.

### 1.3 Decisioni di rilascio ancora aperte (§3.4)
- [ ] Attivare le tabelle **tutte insieme** o **tranche per tranche**?
- [ ] Kill switch documentato in caso di regressione: `ALTER TABLE ... DISABLE
      ROW LEVEL SECURITY` + rollback plan (collegato a §8.4).

---

## 2. Sviluppo residuo (per chiudere PR-C / PR-D)

La RLS è solo l'ultimo strato. Perché serva a qualcosa va costruito tutto il
dominio portale/shop sopra. Raggruppato per livello.

### 2.1 DB — modello identità/profili (§5.1, §13.3-13.4)
- [ ] Rinominare/deprecare `risorse_umane_auth_user` → `identita_digitali`
      (changeset Liquibase §13.3.2-13.3.5; rimozione doppia verifica OPERATORE,
      drop trigger legacy).
- [ ] Tabelle profili: `ProfiloAccesso`, `ProfiloAccessoArea`,
      `ProfiloAccessoBinding`, `ScopePolicy`, `IdentitaScopeBinding` (modelli
      `managed=False` lato Django §5.1.2-5.1.3).

### 2.2 BE — auth, resolver, GUC, permission (§5.2-5.4, §13.4)
- [ ] Resolver: `_get_livello_da_profilo_accesso`, step "profilo da ruolo
      applicativo", classificazione `ruolo_applicativo`, `get_ruolo_applicativo`
      (§5.2 / §13.4.4).
- [ ] `JwtAuditAuthentication`: dopo `authenticate()` risolvere identità attiva e
      **propagare i 3 GUC**; 401 se nessuna identità attiva; cleanup GUC nel
      middleware response (§5.3 / §13.4.8-13.4.10).
- [ ] Permission/base view: `PortaleBasePermission`, `ShopBasePermission`,
      `PortaleAPIView`, `ShopAPIView`; routing separato `/api/portale/*` e
      `/api/shop/*`; throttle endpoint shop pubblici (§5.4 / §13.4.12-13.4.14).
- [ ] Cleanup writer/repo amm_software ruolo-aware (§13.4.15-13.4.18).

### 2.3 BE — servizi inviti/registrazione (§5.5-5.6)
- [ ] Portale: `invito_portale_service`, token `INVITO_PORTALE`, template email,
      endpoint `invita-portale` cliente/fornitore + `attivazione/conferma`.
- [ ] Shop self-register: `registrazione_service` (transazione atomica),
      validazione email unica sui 3 mondi, token `VERIFICA_EMAIL_SHOP` (24h),
      endpoint pubblico `register` (throttle 3/1h per IP) + `verifica-email`.
      Oggi esiste solo lo stub `ShopRegisterCheckEmailView` (§1.4.6 portale-shop).

### 2.4 BE — API di dominio (§5.7-5.9) — *prerequisito RLS*
- [ ] **Portale cliente**: `me`, `billing-account`, `fatture` (lista/dettaglio/PDF),
      `scadenze`.
- [ ] **Portale fornitore**: `ordini-ricevuti` (lista/dettaglio),
      `pagamenti-verso-di-me`.
- [ ] **Shop**: `catalogo` (pubblico) + `{sku}`, `carrello`, `checkout`
      (SHOP_CUSTOMER), `ordini`.
- [ ] Export PDF fattura: decisione BE (reportlab/weasyprint) + cache (§3.3).

### 2.5 BE — hardening (§5.10)
- [ ] Rate limit login portale (5/5min IP) e reset password shop (3/15min IP).
- [ ] Email di sicurezza ad ogni cambio password (§2.2 portale-shop).
- [ ] Audit sessioni: colonna `ruolo_applicativo` su `dbops.sessioni_utente` +
      tracciamento LOGIN/LOGOUT/REFRESH con la veste (brief DB).
- [ ] Headers di sicurezza dedicati `/api/shop/*` e `/api/portale/*` (CSP,
      no-cache documenti sensibili).

### 2.6 FE (§6, §13.5)
- [ ] **Decisione architetturale**: bundle unico con router guard per ruolo
      **oppure** build separate portale/shop (§6.1.1 / §10.2). Sblocca tutto il
      resto FE.
- [ ] Store auth: `ruoloApplicativo`, `isSuperAdmin`, helper ortogonali; rimozione
      `RUOLO_SISTEMA`; router guard cross-ruolo (§13.5).
- [ ] Admin: tab "Accesso Portale" su Cliente/Fornitore drawer (invito, stato,
      reinvia, disattiva, badge lista); sezione "Profili di accesso" sotto Amm.
      Software (§6.2-6.3).
- [ ] Portale cliente: layout dedicato, dashboard, "Le mie fatture", scadenzario,
      profilo, tema distinto, dark/light (§6.4).
- [ ] Portale fornitore: layout, ordini ricevuti, pagamenti (§6.5).
- [ ] Shop: catalogo, prodotto, carrello, registrazione, verifica email, "I miei
      ordini", checkout (§6.6).
- [ ] Auth flow: login unificato con redirect per `ruolo_applicativo`, pagina
      attivazione invito, reset password universale, verifica email shop (§6.7).

### 2.7 Test (§7)
- [ ] Unit/integration: resolver con profili generalizzati, GUC identità, API
      portale/shop, cross-role, invito, rate limit (§7.2).
- [ ] Smoke e2e `smoke-test-multi-face-auth.sh`: 4 scenari (invito cliente,
      invito fornitore, register shop, **leak cross-user → con RLS attiva deve
      dare ZERO righe, non 403**) (§7.3 / §13.7).
- [ ] pgTAP RLS policy attive (vedi §1.2 sopra, §7.1.7-7.1.8).

### 2.8 Doc (§7.4)
- [ ] Guide: "Portale Clienti", "Portale Fornitori", "Shop Online".
- [ ] Documentare i nuovi GUC in
      `docs/it/postgresql/parametri-personalizzati-(GUC).md`.
- [ ] Aggiornare `api.md` con i namespace `/api/portale/*` e `/api/shop/*`.

### 2.9 Rollout (§8) — *fuori scope finché non in produzione*
> ZeroErp non è in produzione (`project_no_produzione_solo_sviluppo`): la parte
> staging/feature-flag/pilota è da riconsiderare, niente gradient di rilascio.
- [ ] Smoke staging, rollback plan, deprecazione + drop fisico
      `risorse_umane_auth_user` (milestone +3 mesi). *(Il «benchmark post-RLS
      >10%» che stava qui è ritirato — vedi §4.9.8.)*

---

## 3. Decisioni di dominio da chiudere prima di implementare (§3 portale-shop)

- [ ] **3.1 Catalogo shop**: flag `vendibile_shop` vs listino dedicato; pricing
      B2C (iva inclusa?); controllo stock real-time?
- [ ] **3.2 Checkout**: ricevuta non-fiscale (`shop.ricevute`) vs fattura con CF a
      scelta; integrazione `pagamenti`; resi/rimborsi (oggi fuori modello).
- [ ] **3.5 Brand shop**: tema dedicato vs look admin; multilingua IT+EN da subito?
- [ ] **10.x questioni aperte**: frontend separato/unico, multilingua portale,
      scope agenti di vendita, API pubbliche `API_CLIENT`, notifiche in-app,
      collegamento `identita_digitali → anagrafiche.contatti`.

---

## 4. Ordine consigliato

1. **API portale cliente (§2.4) + GUC backend (§2.2)** — prerequisito reale della
   RLS: senza consumatore non si accende nulla.
2. **§2.3 inviti/registrazione** in parallelo dove possibile.
3. **FE (§2.6)** — prima la decisione bundle unico/separato, poi portale cliente.
4. **Attivazione RLS (§1)** — quando esiste almeno un flusso portale end-to-end
   che popola i GUC; tranche-by-tranche con benchmark e kill switch pronto.
5. **§2.7 test e2e** (incluso leak cross-user con RLS attiva) → **PR-D**.

> Suggerimento doc sorgente: ogni blocco §2.x può diventare uno **sprint dedicato
> con WIP figlio**. Il portale fornitore (§2.4 fornitore) e il self-register shop
> (§2.3 shop) sono i più rinviabili.
