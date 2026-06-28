# Analisi sicurezza AI/agenti — aggiornamento e piano di allineamento

> **Tipo documento**: analisi + piano operativo (WIP). Raccoglie l'esito della
> revisione critica del *documento di considerazioni sicurezza AI* (Tid, 2026-06-26)
> e lo traduce in step concreti: **(1)** allineare la documentazione interna
> esistente, **(2)** aggiornare il software dove serve, **(3)** indicare gli sviluppi
> futuri e *dove* vanno nella documentazione già esistente.
>
> **Data**: 2026-06-26 · **Stato**: 🟢 **Step 1 (doc) + Step 2 completo (codice) APPLICATI**
> (2026-06-26, 72 test ai_assistant verdi): P1 ri-check permessi, P2 audit affidabile, P3
> durabilità conferme (cache Redis), granularità fine (azioni di processo), free-text (doc
> MCP). · ✅ **CHIUSO** — i residui sono tracciati nei doc WIP esistenti: follow-up
> conversazioni in-memory → [integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md)
> (§Durabilità conversazioni); sviluppi futuri (Step 3) → guida permessi / MCP / guida AI v2.
>
> **Origine**: documento di considerazioni sicurezza AI condiviso da Tid; revisione
> critica ancorata al codice vivo (`apps/ai_assistant/`).
>
> **Principio**: la prompt injection **non è eliminabile**; la difesa è il **blast
> radius** (permessi + conferma umana + assenza di esfiltrazione + RLS + audit). Vedi
> [integrazione-ai.md](integrazione-ai.md) e
> [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md).

---

## 1. Esito della revisione critica (sintesi)

Il documento di considerazioni è **direzionalmente corretto** e prezioso su due
intuizioni: l'equivoco sul `tool_result` (§3.1) e l'injection "a tempo" raccolta dal
supporto MCP (§3.2). La revisione ha però rilevato **lacune** da incorporare:

| # | Punto del doc considerazioni | Esito revisione (ancorato al codice) |
|---|---|---|
| A | "Difesa = catalogo filtrato per permessi" | **Vero ma grossolano**: il filtro è per-area ([tool_registry.get_tools_for_user](../../../../backend/apps/ai_assistant/services/tool_registry.py)). La protezione **per-riga** sulle letture viene dall'**RLS**, mai citata nel doc. → Aggiungere RLS al modello di difesa. |
| B | §3.5 "ri-check permessi alla conferma" presentato come nice-to-have | **È un gap reale (TOCTOU)**, vedi §2. I tool chiamano i service diretti, bypassando il layer permessi delle view; l'unico gate è il filtro catalogo all'offer-time. |
| C | §3.1 equivoco `tool_result` = protezione injection | **Confermato**: la §4 attuale della guida ([integrazione-ai.md](integrazione-ai.md)) lo dice davvero. Va corretta. |
| D | §3.3 logging best-effort | **Confermato** anche per le scritture confermate ([_execute_confirmation](../../../../backend/apps/ai_assistant/services/ai_assistant_service.py)). |
| E | Profilo "supporto" read-only (§3.2/§6.3) | **Sottospecificato**: lettura cross-org su tabelle RLS implica **bypass RLS a livello DB**, non solo permesso app. Rischio di pari livello. Vedi [[feedback_rls_query_contesto_sistema]]. |
| F | Durabilità conferme | **Non vista dal doc**: `_pending_confirmations` è un dict **in-memory di modulo** → problema multi-worker/restart. |

---

## 2. Approfondimento punto B — gap permessi nel path AI (verificato)

**Catena reale** (codice vivo):

1. `_execute_confirmation` esegue `tool_obj.execute(params, request)` **senza** ri-filtro
   catalogo né `PermissionResolver`.
2. I tool di scrittura (`CreaPraticaTool`, `CambiaStatoPraticaTool`, `AggiungiNotaPraticaTool`
   in `pratiche_tools.py`, gli unici `requires_confirmation=True`) chiamano **direttamente**
   `pratiche_service.*`.
3. I `pratiche_service.crea_pratica/cambia_stato_pratica/crea_nota_pratica` **non**
   controllano il livello area (nessun `PermissionResolver`).
4. Il check area-level vive **solo** nel layer view (`core/api/permissions.py`,
   `core/api/views.py` → `get_livello_area`), che l'AI **non attraversa**.

**Conseguenza:** l'unico gate permessi applicativo del path AI è il **filtro catalogo
all'offer-time** (`tool_registry.get_tools_for_user`). Manca un backstop a
**execution-time**. Finestra TOCTOU tra preview e `__confirm__`: un downgrade
TUTTO→LETTURA non viene intercettato, la conferma esegue comunque.

**Severità:** media. Mitiganti = gate all'offer-time (un LETTURA non si vede offrire il
tool) + trigger DB sulle transizioni di stato. Ma il gate è **unico e al momento
sbagliato** → va aggiunto il ri-check a execution-time.

**Fix (vedi Step 2 / P1):** centralizzare un ri-check permessi in `preview` **e** in
`_execute_confirmation`, riusando `get_livello_area`, speculare al filtro catalogo.

---

## 3. Step 1 — Allineare la documentazione interna esistente

Modifiche **solo doc** (zero rischio), da fare per prime.

1. **Riscrivere la §4 "Considerazioni di sicurezza"** di
   [integrazione-ai.md](integrazione-ai.md) col framing corretto (testo
   "§4 riscritta" già pronto nel documento di considerazioni):
   - distinguere **difese vere** (permessi, conferma umana, niente esfiltrazione, audit)
     da **igiene** (`tool_result`, istruzioni system prompt);
   - **aggiungere l'RLS** come difesa esplicita sulle letture (punto A — il doc
     considerazioni la omette): un tool di lettura disponibile restituisce comunque solo
     le righe visibili all'utente.
2. **Correggere `api_ai_query`** ([api_ai_query.md](../../backend/ai-assistant/manual/api_ai_query.md)):
   togliere dalle "regole" l'etichetta "`tool_result` = protezione prompt injection".
3. **Drift fra due guide**: esiste una seconda copia in
   [docs/it/guide/integrazione-ai.md](../../guide/integrazione-ai.md) con una sezione
   sicurezza propria. Allineare **entrambe** (o consolidare in una, linkando l'altra) per
   evitare divergenze.
4. **Roadmap rendering v2**: nel punto del rendering arricchito (guida AI v2) fissare la
   regola **"mai immagini/risorse esterne caricate dall'output del modello"** (anti
   esfiltrazione). Va scritto **prima** di implementare il rendering.
5. **Guida MCP** ([integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md)): nel §6.3
   (profilo supporto) annotare che il read cross-org implica **bypass RLS a livello DB**
   (non solo permesso app) e che la console investigazione va usata in **client isolato**
   senza altri connettori (già accennato, rinforzare col legame RLS).

---

## 4. Step 2 — Aggiornamenti software esistenti (se necessari)

In ordine di priorità. Da pianificare **dopo** Step 1; ognuno è un intervento a sé.

- **[P1] Ri-check permessi a execution-time nel path AI** (chiude il gap §2).
  Aggiungere, in `preview` e in `_execute_confirmation`, una verifica `get_livello_area`
  speculare al filtro catalogo (un helper unico, riusato dal registry e dall'esecuzione).
  Tocca: `apps/ai_assistant/services/ai_assistant_service.py` + `tool_registry.py`.
- **[P2] Logging audit affidabile** per **scritture confermate** (oggi best-effort in
  `_execute_confirmation` → `_log_query`): se l'INSERT in `dbops.ai_query_log` fallisce,
  generare almeno un alert; valutare che l'operazione delicata non proceda senza traccia.
  Per le sole letture, best-effort resta accettabile. Tocca:
  `ai_query_log_repository.py` + call-site del confirm.
- **[P3] Durabilità conferme** (punto F): `_pending_confirmations` in-memory non regge
  deploy multi-worker/restart. Se/quando il backend gira multi-processo, spostare lo store
  conferme su risorsa condivisa (cache/DB con TTL). Verificare la topologia di deploy
  prima di decidere.
- **[P3] Trattare i campi free-text come ostili**: quando `input_text`/note/descrizioni
  vengono dati al modello, delimitarli/etichettarli come "dato non fidato, non eseguire"
  (mitiga l'injection diretta e prepara il terreno per i tool investigazione MCP).
- **[Valutazione] Granularità permessi AI**: oggi il gate AI è solo livello-area
  (`required_level` vs area). La UI ha le **azioni di processo** più fini. Valutare se per
  alcune scritture serve allineare la granularità (evitare che il path AI sia più
  permissivo della UI per la stessa operazione).

> **Cosa tocca codice in esecuzione OGGI**: solo P1, P2 e (eventuale) P3-conferme. Tutto
> il resto del rischio "alto" (investigazione MCP) è su software **non ancora esistente**.

---

## 5. Step 3 — Sviluppi futuri (vanno nella documentazione GIÀ esistente)

Questi **non** sono nuovi documenti: vanno incorporati nei doc esistenti citati, così la
nuova analisi resta un piano e non duplica la roadmap.

1. **Profilo utente "supporto"** → documento progettuale dedicato + sezione nella
   [guida permessi e autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md).
   Deve esplicitare: read-only blindato (app **e** catalogo MCP) **+** come si realizza la
   lettura cross-org rispetto all'**RLS** (bypass controllato vs GUC ampio) — è la parte
   più delicata (punto E). È **prerequisito** dei tool investigazione MCP §6.1.
2. **Server MCP — tool di investigazione (§6.1)** → resta in
   [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md). Aggiornarlo col legame
   RLS↔profilo supporto e con la regola "client isolato".
3. **RAG documentale v2** (condiviso AI Assistant ↔ MCP) → roadmap v2 della guida AI
   ([integrazione-ai.md](integrazione-ai.md)) e
   [integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md). Annotare la regola
   anti-esfiltrazione del rendering (Step 1.4).
4. **Audit come detection** (segnali di anomalia: raffiche di tool-call, sequenze
   inusuali) → nota nella guida AI §4.6 (audit) come evoluzione, non MVP.

---

## 6. Checklist sintetica

**Doc (Step 1) — ✅ FATTO 2026-06-26:**
- [x] §4 guida AI riscritta (framing + RLS) — `guide/integrazione-ai.md`
- [x] `api_ai_query` regole corrette (no "`tool_result` = anti-injection")
- [x] Allineate le due copie della guida AI (`work-done/integrazione-ai.md` + `guide/`)
- [x] Regola "no immagini/risorse esterne dall'output AI" nella roadmap rendering v2 (`integrazione-ai-sviluppo-v2.md` + guida §4.5)
- [x] Guida MCP §6.3: legame RLS + client isolato

**Software (Step 2) — solo se confermato:**
- [x] P1 ri-check permessi nel loop **e** in confirm (chiude TOCTOU §2) — predicato unico `is_tool_allowed_for_user`
- [x] P2 logging affidabile su scritture confermate (param `reliable` → alert ERROR se l'audit fallisce)
- [x] P3 durabilità conferme — **gunicorn 3 worker confermato** → conferme spostate in `django.core.cache` (Redis prod), TTL 5 min, chiave per scope conv+owner
- [→] **(follow-up, tracciato)** conversazioni AI ancora **in-memory per processo** → stesso problema multi-worker delle conferme; migrare alla cache con lo stesso meccanismo. **Spostato in** [integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md) §Durabilità conversazioni.
- [x] P3 etichettare free-text dato al modello — **documentato nel doc MCP** §6.1 (è prerequisito dei tool `investigazione_*`, non codice oggi)
- [x] Granularità permessi AI = UI (anche fine): aggiunto `required_action` ai tool + Filtro 4 `check_azione` in `is_tool_allowed_for_user`; `cambia_stato_pratica` allineato al `post_permission` dell'endpoint. `crea_pratica`/`aggiungi_nota` restano area-level (i loro endpoint non hanno `post_permission`).

**Futuro (Step 3) — nei doc esistenti:**
- [ ] Profilo "supporto" (doc dedicato + guida permessi) — con impatto RLS
- [ ] Tool investigazione MCP (guida MCP) — gated sul profilo supporto
- [ ] RAG v2 (guida AI v2)

---

## 7. Riferimenti

- Guida tecnica AI: [integrazione-ai.md](integrazione-ai.md) (§4 da riscrivere)
- Guida AI (guide/): [integrazione-ai.md](../../guide/integrazione-ai.md) (drift da allineare)
- API AI: [api_ai_query.md](../../backend/ai-assistant/manual/api_ai_query.md)
- Guida MCP: [integrazione-server-mcp.md](../work-in-progress/integrazione-server-mcp.md)
- Sviluppo AI v2: [integrazione-ai-sviluppo-v2.md](../work-in-progress/integrazione-ai-sviluppo-v2.md)
- Tabella audit: [ai_query_log.md](../../dbzero/dbops/tabelle/ai_query_log.md)
- Codice: `backend/apps/ai_assistant/` (`services/ai_assistant_service.py`,
  `services/tool_registry.py`, `db/ai_query_log_repository.py`, `tools/`)
