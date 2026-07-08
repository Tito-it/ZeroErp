# Brief Design — GUIDA (D4): avanzamento milestone su esito proiettato

> **Tipo**: brief di design autorevole (modello + deliverable DB → team + piano BE) · **Data**: 2026-07-06
> **Owner**: Tid · **Stato**: 🟢 **PILOTA PREVENTIVI IMPLEMENTATO + E2E VERDE (2026-07-07)**.
> DB (G1-G5 + trigger + reconcile + grant/resilienza), BE/FE (inversione handler→proiezione,
> cutover step 9011), binding G2 = **NULL** (inversione piena: accept **e** reject auto-avanzano
> il milestone). Smoke E2E `backend/scripts/tests/smoke-test-guida-inversione-preventivi.sh`
> **7/7 verde** (Accetta→POSITIVO, Rifiuta→NEGATIVO). Residui: cleanup handler dormiente,
> roll-out altri domini. Vedi §12.
> **Origine**: §6 (le due direzioni) e §8-**D4** di
> [brief-design-proiezione-stato-dominio.md](../work-in-progress/brief-design-proiezione-stato-dominio.md)
> (MOSTRA già implementato: Fase 0 DB ✅ · Fase 1 BE ✅ · Fase 2 FE ✅). Salda il
> **debito §5.3** di [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md)
> (handler accetta/push oggi per-pratica PREVENTIVI → generalizzare prima del 2° dominio).
> **Correlati**: editor definizioni versionate (config di questi binding) —
> [brief-fe-fase3-editor-definizioni-workflow.md](../work-in-progress/brief-fe-fase3-editor-definizioni-workflow.md) (FE-3.3 handler-eventi).

---

## 1. Problema — la pratica MOSTRA lo stato del documento, ma non lo GUIDA

MOSTRA (fasi 0-2, fatte) ha reso la pratica capace di **proiettare** lo stato vivo del
documento (`doc_fase`/`doc_esito`/`doc_terminale` da `fn_stato_sorgente`). Ma l'**avanzamento
del milestone** è ancora pilotato all'antica, con due difetti:

1. **Per-dominio (debito §5.3)**: l'accettazione è un **handler dedicato per tipo documento**
   (`vendita.accetta_preventivo`) bindato su `template_flussi_handler_eventi`. Un handler per
   preventivi, un altro per offerte, un altro per ordini… **non scala**.
2. **Divergenza dallo standalone** (la radice del brief proiezione): oggi il milestone avanza
   **solo** se l'operatore completa il flusso *dentro* la pratica. Se il documento viene
   accettato dal suo **drawer standalone** (fuori pratica), il milestone resta **aperto** e la
   pratica va cieca — la proiezione lo *mostra* come "Accettato", ma il flusso non è
   COMPLETATO. La macchina pratica e la macchina documento **divergono**.

**GUIDA** chiude entrambi: un **unico meccanismo config-driven** che avanza il milestone
**quando il documento proietta il verdetto**, per qualsiasi dominio, indipendentemente da dove
è avvenuta la transizione.

## 2. Come funziona OGGI (mappa del codice — non divergere da questa)

- **Dispatch handler-eventi** (Python, non trigger): `pratiche_service.dispatch_handler_eventi()`
  ([pratiche_service.py:888-923](../../../../backend/apps/pratiche/services/pratiche_service.py))
  gira **dentro la transazione** di completamento flusso
  ([`_completa_flusso_validato`:628-650](../../../../backend/apps/pratiche/services/pratiche_service.py)):
  dopo `update_stato_flusso(...,'COMPLETATO',esito)` chiama i binding di
  `template_flussi_handler_eventi` per `evento='COMPLETATO'` il cui `esito_richiesto` matcha
  (query in [pratiche_repository.py:1251-1268](../../../../backend/apps/pratiche/db/pratiche_repository.py),
  `esito_richiesto IS NULL OR = esito`). Risoluzione `handler_key → callable` via
  `HANDLER_MAP` ([handler_registry.py](../../../../backend/apps/pratiche/services/handler_registry.py));
  vendite registra i propri handler in [vendite/apps.py:29-40](../../../../backend/apps/vendite/apps.py).
- **`vendita.accetta_preventivo`** ([accetta_preventivo_handler.py:26-89](../../../../backend/apps/vendite/handlers/accetta_preventivo_handler.py))
  **non tocca la pratica**: risolve il preventivo ROOT e chiama
  `preventivi_service.cambia_stato(pid,'ACCETTATO',…)`. Spinge **solo il documento**; il
  milestone lo ha già completato il FE (che ha dispatchato l'handler).
- **Primitiva di avanzamento**: `completa_flusso`/`avvia_e_completa_flusso` → `update_stato_flusso`
  + dispatch. BB cross-dominio **`completa_step_pratica(pratica_id, template_codice, esito, user)`**
  ([pratiche_service.py:741-760](../../../../backend/apps/pratiche/services/pratiche_service.py)),
  **idempotente** sui flussi terminali (`_STATI_FLUSSO_TERMINALI`).
- **Resolver della proiezione (D1-D3, già in produzione per PREVENTIVI)**:
  `pratiche.fn_stato_sorgente(sorgente_tipo_id, sorgente_uid)` +
  `script.vw_stato_sorgente` (UNION per-dominio; **niente `resolver_key`** — il dispatch è
  "il tipo ha un ramo UNION o no"). Descrittore: `risolto, stato_codice, fase, esito, terminale`,
  con **`esito` sempre verdetto** (`is_verdetto=true`, guardato da
  `trgfn_stati_doc_guard_esito_verdetto`) o NULL. L'àncora ROOT/link è già promossa a vista
  condivisa **`script.vw_pratica_doc_sorgente`** (pratica-level, accende anche i COLLEGATO con
  `flusso_id` NULL).
- **Direzione OGGI**: *milestone → documento* (l'operatore completa in pratica → push del doc).
  Il `doc_esito` proiettato è oggi **solo display**, mai consumato per avanzare.

## 3. Principio GUIDA — inverti la direzione, generalizza il meccanismo

**Projection-driven advancement**: quando il documento raggiunge un **verdetto proiettato**
(`doc_esito ∈ {POSITIVO,…}` o `doc_terminale`), un meccanismo **generico** avanza il milestone
corrispondente — *ovunque* sia avvenuta la transizione (in-pratica **o** standalone). Il
**documento guida**, la pratica **segue la proiezione**.

Conseguenze:
- **Un solo meccanismo per tutti i domini**: niente più un handler accetta/push per tipo
  documento (smaterializza `vendita.accetta_preventivo`).
- **Salda la divergenza standalone**: accettato il preventivo dal suo drawer, il milestone
  avanza comunque.
- Il pulsante "Accetta" **in pratica** diventa un semplice invocatore del **servizio standalone
  del documento** (`preventivi_service.cambia_stato → ACCETTATO`); l'avanzamento del milestone
  **non è più** nel dominio, è nel motore su proiezione. Coerente col principio "non divergere
  dallo standalone".

## 4. Il meccanismo generico — tre pezzi

### 4.1 Mappa step → sorgente *(nuova — non esiste)*
Il motore deve sapere **quale milestone** è "in attesa del verdetto di quale tipo documento".
Oggi non c'è (il commento [pratiche_repository.py:70](../../../../backend/apps/pratiche/db/pratiche_repository.py)
la nomina come *futuro di GUIDA*). Serve per i COLLEGATO (`flusso_id` NULL) dove l'àncora
per-flusso non basta.
**Proposta**: dichiarazione **dominio-owned** sul template step — es. colonna
`template_flussi.attende_sorgente_tipo_id` (FK `config.sorgenti`), oppure una tabella-binding
dedicata se un milestone può attendere più sorgenti. Additiva; senza mappa → nessun
avanzamento automatico (comportamento di oggi).

### 4.2 Config di avanzamento *(binding)*
"Questo step avanza quando il documento atteso proietta esito ∈ {verdetti} → completa con
quell'esito." **Vocabolario compatibile**: `handler_eventi.esito_richiesto` e il `doc_esito`
proiettato sono **entrambi** ristretti ai 4 verdetti (`config.esiti_flussi_pratiche` con
`is_verdetto=true`) → il match proiezione↔condizione è omogeneo.
**Decisione (§9.2)**: binding **dedicato leggero** (semantica «avanza-su-proiezione» distinta
da «handler server-side su evento di flusso») **vs** riuso di `template_flussi_handler_eventi`
con un nuovo `evento='PROIEZIONE'` (estende `chk_tfhe_evento`) + handler generico
`pratiche.avanza_su_proiezione`. *Proposta: dedicato* (non sovraccarica la CHECK evento né la
semantica del binding handler; ma valutare il riuso per non moltiplicare tabelle).

### 4.3 Motore di riconciliazione *(il punto d'innesco — decisione centrale §9.1)*
La proiezione è **read-time**; il cambio stato documento avviene nel dominio. Serve un innesco:

- **A) Push generico dal dominio** *(proposta)*: dopo `cambia_stato` del doc, il dominio chiama
  **un** entrypoint generico `pratiche.reconcile_sorgente(sorgente_tipo_id, sorgente_uid)` —
  **una riga, zero logica di dominio** (come oggi vendite *registra* un handler). Il motore:
  risolve il descrittore via `fn_stato_sorgente` → trova le `pratiche_sorgenti` agganciate →
  per gli step con binding di avanzamento (4.2) il cui esito matcha il verdetto proiettato →
  `completa_step_pratica(pratica_id, codice, esito, SISTEMA)` (idempotente sui terminali).
  Event-driven, niente write-on-read, dominio agnostico.
- **B) Trigger DB** sulle tabelle documento → chiama la fn generica. Più automatico ma accoppia
  a DB-level e richiede un trigger per-dominio (contro "additivo per dominio").
- **C) Pull read-time**: ❌ scrittura su lettura (anti-pattern).

*Proposta: **A***. Coerente col pattern handler (dispatch in Python) e col principio "il motore
consuma un descrittore normalizzato". L'avanzamento gira in **contesto SISTEMA** (RLS/audit;
giornale `DOMINIO_*` riusando il frammento condiviso — debito §5.3).

## 5. Cosa esiste già — è *normalizzare*, non greenfield

| Pezzo | Stato |
|---|---|
| `fn_stato_sorgente` / `vw_stato_sorgente` (descrittore verdetto-typed) | ✅ (PREVENTIVI) |
| `vw_pratica_doc_sorgente` (àncora pratica-level, accende COLLEGATO NULL) | ✅ |
| `completa_step_pratica` idempotente sui terminali | ✅ |
| dispatch handler-eventi (Python, esito-aware) | ✅ |
| vocabolario esito compatibile (4 verdetti) proiezione↔binding | ✅ |
| **mappa step→sorgente (4.1)** | ❌ nuovo (G1) |
| **binding di avanzamento (4.2)** | ❌ nuovo (G2) |
| **entrypoint `reconcile_sorgente` (4.3)** | ❌ nuovo (G3) |

## 6. Deliverable DB *(→ brief separato al team DB su `dev/db-tid`)*

Le azioni DB (colonne/tabelle/fn/trigger/pgTAP) **non** le esegue l'agent: brief scritto al
team (`feedback_db_actions_passaggio_team`).

- **G1 — mappa step→sorgente** (§4.1): colonna/tabella dominio-owned che lega il template step
  al `sorgente_tipo` atteso. Additiva.
- **G2 — binding di avanzamento** (§4.2): dedicato, oppure `evento='PROIEZIONE'` su
  `template_flussi_handler_eventi` + `chk_tfhe_evento` esteso (secondo §9.2).
- **G3 — `pratiche.fn_reconcile_sorgente(sorgente_tipo_id, sorgente_uid)`** (o service BE): risolve
  il descrittore + avanza i milestone matching. `SECURITY DEFINER` se invocata in contesto
  sistema/batch.
- **Note di roll-out** (review 2026-07-02, stato aggiornato):
  - **(a)** indice a espressione `((uid::text))` per dominio — ⚠️ **ancora aperto** (non presente):
    la pushdown della LATERAL non usa il btree su `uid` → voce DB per il roll-out per volumi.
  - **(b)** COLLEGATO senza `flusso_id`: risolto da **G1 (step→sorgente) + àncora pratica-level**.
    *Proposta*: NON forzare `flusso_id` sui COLLEGATO; usare la mappa step→sorgente.
  - **(c)** àncora condivisa `vw_pratica_doc_sorgente` — ✅ **GIÀ FATTO** (de-scoped).

## 7. Piano BE

- **Entrypoint generico** `reconcile_sorgente` nel service pratiche, invocato dai domini dopo
  `cambia_stato` (una riga per dominio). Contesto SISTEMA per l'avanzamento automatico.
- **Ritiro `vendita.accetta_preventivo`**: il pulsante "Accetta" in-pratica chiama
  `preventivi_service.cambia_stato → ACCETTATO` (servizio standalone) + `reconcile_sorgente`; il
  milestone avanza per proiezione. Rimuovere il binding handler dedicato quando il generico è
  validato.
- **Estrazione frammento condiviso** (debito §5.3): risoluzione ROOT/sorgenti + scrittura
  giornale `DOMINIO_*`, riusabile dal motore generico.
- **Test**: smoke E2E **"accetta standalone → milestone avanza"** e **"accetta in-pratica →
  milestone avanza"** (i due percorsi devono convergere).

## 8. Vincoli e non-obiettivi

- Il motore **non nomina stati di dominio**: ragiona su `fase`/`esito` normalizzati.
- **Read-time** per la proiezione, **event-driven** (push generico) per l'avanzamento — mai
  scrittura su lettura.
- **Additivo**: senza mappa/binding, comportamento di oggi. Roll-out per dominio.
- **Idempotente**: `completa_step_pratica` è no-op sui flussi terminali → reconcile ripetuti
  innocui.
- **Niente mirror**: non si copiano gli stati del documento in flussi (§2 brief proiezione).

## 9. Decisioni aperte (per l'owner)

1. **Innesco** (§4.3): **A) push generico dal dominio** *(proposta)* vs **B) trigger DB**.
2. **Binding** (§4.2): **dedicato** *(proposta)* vs **evento `PROIEZIONE` su handler_eventi**.
3. **Mappa step→sorgente** (§4.1): **colonna su `template_flussi`** vs **tabella dedicata**
   (se un milestone può attendere più sorgenti).
4. **`accetta_preventivo`**: **ritiro completo** (inversione piena) *(proposta)* vs
   **coesistenza transitoria** durante il roll-out.
5. **Dominio pilota**: **PREVENTIVI** (ROOT, ha `flusso_id`, workflow E2E già validato) → poi
   OFFERTA.

## 11. Decisioni adottate (owner, 2026-07-06)

- **§9.1 Innesco** → **trigger DB generico, best-effort**. Detection = trigger DB generico sulla
  colonna-stato del documento (scatta su ogni percorso di scrittura, **standalone incluso**) →
  `pratiche.fn_reconcile_sorgente(tipo,uid)`; avanzamento **DB-side**; **best-effort**: un errore
  lato pratiche **non** annulla il cambio-stato del documento (documento **sovrano**; log +
  segnalazione, non rollback). *Vincolo*: i milestone auto-avanzati portano solo effetti
  **DB-side** (la generazione è già trigger DB) — niente handler-eventi Python su quello step.
  Idempotenza garantita da `completa_step_pratica` (no-op sui terminali).
- **§9.2 Binding** → **dedicato leggero** (semantica «avanza-su-proiezione» separata da
  `template_flussi_handler_eventi`; non si sovraccarica `chk_tfhe_evento`).
- **§9.3 Mappa step→sorgente** → *(proposta confermata salvo diverso avviso)* colonna su
  `template_flussi` se un milestone attende **una** sorgente; tabella dedicata solo se serve N.
- **§9.4 `accetta_preventivo`** → **ritiro completo (inversione)**: «Accetta» in-pratica chiama
  il servizio standalone del doc + il reconcile avanza il milestone per proiezione; rimosso il
  binding handler dedicato una volta validato il generico.
- **§9.5 Pilota** → **PREVENTIVI** → poi OFFERTA.

## 10. Gate & sequenza

**Gate**: l'implementazione parte **solo dopo** la validazione E2E in-app di **MOSTRA** su
PREVENTIVI (oggi aperta nel brief proiezione). Il **design** (questo documento) procede ora.

**Sequenza**: design (questo) → **decisioni §9 (Tid)** → **brief DB team** (G1-G3 + nota a) →
DB → **BE** (reconcile + ritiro handler + frammento condiviso) → **smoke E2E** (standalone +
in-pratica) → **roll-out domini** (offerta/ordine/contratto).

## 12. Consuntivo pilota PREVENTIVI (2026-07-07) — ✅ CHIUSO

- **DB** (team, committato): G1 colonna `attende_sorgente_tipo_id` · G2 tabella
  `template_flussi_avanzamento_proiezione` · G3 `fn_reconcile_sorgente` + trigger generico
  best-effort su `vendite.preventivi` · G5 `reconcile_errori` · cutover step 9011 · binding
  **NULL** (inversione piena) · fix GRANT (`reconcile_errori` + `template_flussi_avanzamento_proiezione`)
  + log best-effort resiliente (nested-guard). pgTAP `test-guida-avanza-esito-proiettato.sql`.
- **BE** (committato): `preventivi_service.cambia_stato_da_pratica` + endpoint
  `POST /vendite/preventivi/da-pratica/<pratica_id>/stato/` + flag `template_attende_sorgente_tipo_id`
  sul flusso. Handler `vendita.accetta_preventivo` **dormiente** (binding off).
- **FE** (committato): `flussoCompletionRegistry.APPROVAZIONE_CLIENTE` (`esitoToStato` + `docAction`
  lazy) + gate `FlussoDrawer` su `template_attende_sorgente_tipo_id != null` (discrimina i tipi
  ancora su handler: deprecati 9002/9003 + altre edizioni 9004).
- **Smoke E2E**: `backend/scripts/tests/smoke-test-guida-inversione-preventivi.sh` — **7/7**
  (Accetta→ACCETTATO/POSITIVO, Rifiuta→RIFIUTATO/NEGATIVO), idempotente. Ha scoperto i 2 GRANT
  mancanti (invisibili al pgTAP, che gira come owner).
- **Residui**: (a) cleanup file/test handler `accetta_preventivo`; (b) verificare `cambia_stato_preventivi`
  sui profili operatori-pratica; (c) **roll-out** offerta/ordine/contratto (binding G1/G2 +
  trigger reconcile + indice `((uid::text))` + voce registry + endpoint da-pratica; motore già
  generico).

---

*Brief vivo: a chiusura aggiornare §8-D4 e la nota GUIDA in
[brief-design-proiezione-stato-dominio.md](../work-in-progress/brief-design-proiezione-stato-dominio.md) e la riga
V10 di [analisi-pratiche-valutazione-stato.md](../work-in-progress/analisi-pratiche-valutazione-stato.md).*
