# Sviluppo Portale + Shop — continuazione post "predisposizione utenti"

> Questo WIP raccoglie il lavoro residuo dopo la chiusura dello scope
> **"predisposizione utenti/operatori per i 3 ambiti: operatore, portale,
> shop"** (completato 2026-04-21). Contiene **dominio applicativo**
> (cosa vedono gli utenti non-operatore una volta loggati) e **hardening
> di sicurezza** non ancora implementato.
>
> I 2 documenti WIP di origine (`pr-b-shop-b2c-cambio-modello.md` e
> `sviluppo-multi-face-auth.md`) sono stati spostati in `work-done/` per
> riflettere lo stato "foundation chiusa". Rimangono la fonte di verita'
> per architettura, decisioni storiche e changelog sprint PR-B.

---

## 0. Riepilogo foundation chiusa (predisposizione utenti)

Scope confermato chiuso end-to-end lato codice (smoke manuale in corso
con checklist dedicata). Include:

**Autenticazione multi-veste** (ex `sviluppo-multi-face-auth.md`)

- Nuovo bridge `anagrafiche.identita_digitali` (modello 1:N user → vesti)
- Namespace separati `/api/v1/admin/token/` + `/portale/token/` +
  `/shop/token/` con guard cross-veste
- JWT con claim `identita_id` + `ruolo_applicativo` propagato via 5 GUC
  PostgreSQL (`app.jwt_user`, `app.current_user_id`,
  `app.current_identita_id`, `app.ruolo_applicativo`,
  `app.soggetto_ruolo_id`)
- 4 resolver DB `fn_resolve_livello_area` / `fn_check_azione_processo` /
  `fn_get_user_permissions_map` / `fn_get_user_actions_map` +
  `fn_is_super_admin` **veste-aware** (filtrano la query in base a
  `app.ruolo_applicativo`)
- Profili accesso generalizzati (tipo REPARTO / PORTALE / AD_HOC /
  SUPER_ADMIN) + scope policy (EF_WHITELIST, BA_OWNERSHIP,
  FORNITORE_OWNERSHIP) — RLS in **DRY-RUN** (policy create, non ancora
  attivata con `ENABLE ROW LEVEL SECURITY`)

**Ciclo di vita utenti non-operatore** (ex `pr-b-shop-b2c-cambio-modello.md` + B1 §13.7)

- Invito admin-driven (clienti + fornitori per portale; clienti per shop)
  con branching automatico INVITO (email nuova → set password) vs CROSS
  (email gia' nota → one-click no password)
- Attivazione self-service via link email (portale + shop simmetrici)
- Cross-veste self-service: cliente portale loggato attiva shop sul
  proprio `auth_user` con un click (no email/token)
- Stato accessi admin-side: `NESSUNO / PENDING / ATTIVO / DISATTIVO` con
  badge nel `PortaleAccessoPanel`
- Disattivazione soft-revoke con invalidazione token pendenti; riattivazione
  implicita via nuovo invito

**Frontend**

- LoginView con switch canale persistito in localStorage
- Router guard cross-namespace (grace redirect admin↔portale↔shop)
- View attivazione portale + shop simmetriche (`AttivazionePortaleView`,
  `AttivazioneShopView`)
- Panel admin `PortaleAccessoPanel` in ClienteDrawer + FornitoreDrawer
  (invia/reinvia/disattiva/stato)
- ProfileView portale con bottone "Attiva accesso shop"

**Manual di riferimento attivi** (restano validi):

- [api.md](../api.md) + [api_invito_portale_shop.md](../../backend/core/manual/api_invito_portale_shop.md)
- [api_multi_veste_token.md](../../backend/core/manual/api_multi_veste_token.md)
- [catalogo-building-block-backend.md](../backend/catalogo-building-block-backend.md) sezione "Portale + Shop — Invito veste"
- [architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md)

**WIP originali archiviati in** [work-done/](../work-done/):

- [pr-b-shop-b2c-cambio-modello.md](../work-done/pr-b-shop-b2c-cambio-modello.md) — piano sprint PR-B + changelog §8.9
- [sviluppo-multi-face-auth.md](../work-done/sviluppo-multi-face-auth.md) — architettura, storico modifiche, blocker risolti

**Smoke e2e** in corso — checklist operativa in
[smoke-b1-invito-shop-checklist.md](smoke-b1-invito-shop-checklist.md).

---

## 1. Residuo dominio applicativo

Cosa gli utenti **fanno** una volta loggati, oltre al profilo. Tutto
fuori dallo scope foundation — ciascuna linea richiede analisi
dominio dedicata.

### 1.1 Portale cliente — API dati

Riferimento originale: `sviluppo-multi-face-auth.md §5.7` + `§6.4`.

- [ ] 1.1.1 `GET /api/portale/me/` — profilo esteso (oggi c'e' `/core/me/`
      base, da valutare se serve una versione portale-specific)
- [ ] 1.1.2 `GET /api/portale/billing-account/` — lista propri BA
      (filtrata via RLS `BA_OWNERSHIP` o scope applicativo)
- [ ] 1.1.3 `GET /api/portale/fatture/` — lista proprie fatture (periodo,
      stato, export PDF)
- [ ] 1.1.4 `GET /api/portale/fatture/{id}/` — dettaglio
- [ ] 1.1.5 `GET /api/portale/fatture/{id}/pdf/` — download PDF fattura
- [ ] 1.1.6 `GET /api/portale/scadenze/` — scadenzario proprio

### 1.2 Portale fornitore — API dati

Riferimento: `sviluppo-multi-face-auth.md §5.8` + `§6.5`.

- [ ] 1.2.1 `GET /api/portale/ordini-ricevuti/` — ordini acquisto ricevuti
- [ ] 1.2.2 `GET /api/portale/ordini-ricevuti/{id}/` — dettaglio
- [ ] 1.2.3 `GET /api/portale/pagamenti-verso-di-me/` — stato pagamenti

### 1.3 Shop — API commerciali

Riferimento: `sviluppo-multi-face-auth.md §5.9` + `§6.6`. **Richiede
analisi dominio** prima di implementare (vedi §3 sotto).

- [ ] 1.3.1 `GET /api/shop/catalogo/` — pubblico, no auth
- [ ] 1.3.2 `GET /api/shop/catalogo/{sku}/` — dettaglio prodotto pubblico
- [ ] 1.3.3 `POST /api/shop/carrello/` — anonimo via session id o autenticato
- [ ] 1.3.4 `POST /api/shop/checkout/` — richiede `SHOP_CUSTOMER` autenticato
- [ ] 1.3.5 `GET /api/shop/ordini/` — storico ordini propri (filtrato RLS)

### 1.4 Shop — Self-register pubblico

Riferimento: `sviluppo-multi-face-auth.md §5.6`. Il flow admin-driven e'
gia' attivo (B1 §13.7); la registrazione self-service resta da fare.

- [ ] 1.4.1 Service `apps/shop/services/registrazione_service.py` con
      transazione atomica (soggetto + ruolo + cliente + BA
      `canale_origine='SHOP'` + auth_user + identita SHOP_CUSTOMER
      `attivo=false`)
- [ ] 1.4.2 Validazione email unica tra `auth_user.email` (distinguere 3
      casi: email nuova / gia' auth_user / gia' SHOP_CUSTOMER)
- [ ] 1.4.3 Token `VERIFICA_EMAIL_SHOP` scadenza 24h + template email
      dedicato
- [ ] 1.4.4 Endpoint pubblico `POST /api/shop/register/` (throttle 3
      req/h per IP)
- [ ] 1.4.5 Endpoint `GET /api/shop/verifica-email/{token}/` che attiva
      identita
- [ ] 1.4.6 Stub attuale `ShopRegisterCheckEmailView` (`POST /shop/register/check-email/`)
      da sostituire con logica reale
- [ ] 1.4.7 Seed template email + test e2e

### 1.5 UI dominio portale + shop

- [ ] 1.5.1 Layout portale dedicato (no sidebar admin, dashboard
      semplificata — §6.4)
- [ ] 1.5.2 Pagine portale cliente: fatture, scadenzario
- [ ] 1.5.3 Pagine portale fornitore: ordini ricevuti, pagamenti
- [ ] 1.5.4 Layout shop pubblico (catalogo, carrello, checkout — §6.6)
- [ ] 1.5.5 Form registrazione shop (collegato a §1.4)

### 1.6 Admin UI — gestione accessi web (drawer dedicato)

Sostituisce il pannello `PortaleAccessoPanel` inline dentro
`ClienteDrawer` / `FornitoreDrawer` con un **drawer autonomo**
`WebAccessiDrawer.vue` aperto via pulsante toolbar `pi-globe` accanto
a Contatti / Indirizzi / Conti.

- [x] 1.6.1 ~~BE endpoint dedicato `/portale/admin/accessi/`~~ — non
      necessario: esteso invece `PortaleRepository.get_stato_identita`
      con JOIN `django.auth_user` per includere `username` + `email`
      nella response. L'endpoint esistente `GET /api/v1/anagrafiche/
      {clienti|fornitori}/<id>/stato-accessi/` risponde ora con
      `{stato, identita_id, auth_user_id, username, email,
      invito_inviato_at, token_scade_at}` per ogni veste. 1600 test OK.
- [x] 1.6.2 FE `WebAccessiDrawer.vue` generico
      (`entitaTipo: 'cliente' | 'fornitore'`), wrapper autonomo che
      incapsula `PortaleAccessoPanel` (portale + shop sezioni). Il
      pannello e' stato aggiornato per mostrare username + email
      dell'auth_user collegato sotto ogni sezione (no tab dedicata
      "utenti", l'info sta nelle card di stato).
- [x] 1.6.3 Pulsante `pi-globe` "Web" aggiunto in
      `SoggettoPreviewBadges.vue` (gated da prop `entitaTipoWeb` +
      `entitaIdWeb`), affiancato ai pulsanti Indirizzi/Contatti/Conti.
      Badge count = vesti ATTIVE (0-2 per cliente, 0-1 per fornitore).
- [x] 1.6.4 Rimozione `PortaleAccessoPanel` inline da `ClienteDrawer`
      e `FornitoreDrawer`. Il componente resta usato dentro
      `WebAccessiDrawer`. Vite build 982ms, full suite BE 1600 OK.
- [ ] 1.6.5 **Forza logout / invalida session utente** — NON in questo
      scope. Deferred: operazione distruttiva che richiede policy
      (admin-only? solo super_admin? audit dedicato?). Da pianificare
      con `dbops.sessioni_utente` + SimpleJWT blacklist bulk. Nota
      parcheggiata qui per memoria, sprint dedicato dopo §1.6.1-4.
- [ ] 1.6.6 **i18n en.json** — chiavi `portale.accessi_web.*` aggiunte
      solo in `it.json`; `en.json` ha sezione `portale` incompleta
      (fallback a `it`). Da completare in sprint i18n dedicato (scope
      cross-feature, non blocker).
- [ ] 1.6.7 **Riuso da lista** — il `WebAccessiDrawer` e' gia' pronto
      per essere invocato da `ClientiListView` / `FornitoriListView`
      via row-action menu (passa `entitaTipo` + `entitaId` +
      `emailIniziale`, zero dipendenze dal drawer padre). Da integrare
      nei row-action delle due liste per consentire gestione accessi
      senza aprire il drawer completo.

---

## 2. Residuo hardening (security)

Riferimento: `sviluppo-multi-face-auth.md §5.10` + `§4.9.7-9.9` (RLS).

- [ ] 2.1 **Attivazione RLS** su 6 tabelle (`vendite.fatture`,
      `vendite.ordini`, `vendite.fatture_scadenze`,
      `acquisti.acquisti_ordini`, `acquisti.acquisti_ddt_ingresso`,
      `anagrafiche.billing_account`). Policy gia' DRY-RUN, serve
      `ENABLE ROW LEVEL SECURITY` + `FORCE` + `BYPASSRLS` per ruolo DB
      `zeroerp_admin`. ~~Benchmark pre/post (<10% degrado query)~~ —
      ⚠️ voce ritirata il 2026-09-11: il predicato RLS è una chiamata di
      funzione per riga, non un confronto indicizzabile; per le FK di scope
      vale la decisione dichiarata in `dbops.fk_index_policy`
      (linee-guida-sql §10.9).
- [ ] 2.2 Notifica email all'utente ad ogni cambio password (§5.10.3)
- [ ] 2.3 Audit sessioni: estendere `dbops.sessioni_utente` con colonna
      `ruolo_applicativo` + tracciare tutti gli eventi LOGIN/LOGOUT/REFRESH
      con la veste utilizzata (§5.10.4)
- [ ] 2.4 Headers di sicurezza dedicati per `/api/shop/*` e `/api/portale/*`
      (CSP restrittivo, no-cache documenti sensibili — §5.10.5)
- [ ] 2.5 Smoke test `smoke-test-multi-face-auth.sh` end-to-end con 3
      utenti fixture (operatore, portale, shop) — oggi abbiamo checklist
      manuale [smoke-b1-invito-shop-checklist.md](smoke-b1-invito-shop-checklist.md),
      automazione in sprint dedicato

---

## 3. Analisi da perfezionare successivamente

Le seguenti decisioni di design sono **rimandate**: richiedono analisi
dominio dedicata prima di implementare i task §1. Scrivere qui pro/contro
man mano che emergono nelle discussioni.

### 3.1 Catalogo shop — quali articoli sono vendibili?

Aperto:

- Introdurre flag `catalogo.articoli.vendibile_shop` oppure derivarlo da
  listino dedicato?
- Pricing consumer (B2C): listino unico "shop" con prezzi iva inclusa,
  oppure applicazione sconti/markup su listino standard?
- Scorte: lo shop richiede controllo stock real-time? Oggi l'ERP gestisce
  giacenze ma non magazzino "consumer-facing".

### 3.2 Checkout shop — emissione documento

Aperto:

- Il cliente B2C riceve una **ricevuta non-fiscale** (tabella
  `shop.ricevute` gia' presente) o una **fattura con CF richiesto** a
  scelta utente?
- Integrazione con `pagamenti` backend per registrazione incasso shop.
- Gestione resi/rimborsi: attualmente fuori modello.

### 3.3 Portale cliente — export PDF fatture

Aperto:

- Generazione PDF lato BE (reportlab / weasyprint) o delega a servizio
  esterno?
- Cache PDF per fattura emessa (evitare rigenerazione ogni download)?

### 3.4 RLS attivazione — ordine di rilascio

Aperto:

- Attivare tutte le 6 tabelle insieme o tranche per tranche? Il
  benchmark §2.1 va misurato su carico realistico — richiede dati
  production-like.
- Fallback in caso di regressione performance: `ALTER TABLE ... DISABLE
  ROW LEVEL SECURITY` come kill switch?

### 3.5 Layout shop — brand dedicato?

Aperto:

- Lo shop usa lo stesso look&feel dell'admin o richiede tema dedicato
  (colori, logo, tipografia) per differenziarsi?
- Multilingua (vue-i18n) — shop in IT+EN da subito o IT only MVP?

---

## 4. Come proseguire

Ogni task §1.x o §2.x puo' diventare uno **sprint dedicato** con il
proprio WIP figlio. Suggerimento di raggruppamento:

- **Sprint successivo (suggerito)**: §2.1 attivazione RLS — sblocca
  tutto il dominio portale/shop perche' garantisce isolamento dati a
  livello DB. Task DB principalmente, BE impatto minimo.
- Poi **§1.1 + §1.3** in parallelo (2 persone): API portale cliente e
  API shop. La UI (§1.5) segue di 1 sprint.
- §1.2 portale fornitore: rinviabile finche' non arrivano i primi
  fornitori reali.
- §1.4 self-register shop: rimandabile fino a quando il flow admin-driven
  B1 §13.7 non soddisfa piu' l'esigenza (oggi basta per onboarding
  controllato).

Gli item §3 vengono **chiusi progressivamente** all'interno degli
sprint §1/§2 appena le decisioni diventano bloccanti.
