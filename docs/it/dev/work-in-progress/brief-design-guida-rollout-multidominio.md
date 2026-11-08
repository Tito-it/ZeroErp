# Brief Design — GUIDA roll-out multi-dominio (OFFERTA / ORDINE / CONTRATTO)

> **Tipo**: brief di design autorevole (modello + sequenza + decisioni → poi brief DB per dominio) · **Data**: 2026-07-07
> ⚠️ **Allineamento al modello della provenienza (2026-11-08).** Dove questo documento descrive la sorgente
> della pratica come `(sorgente_tipo_id, sorgente_uid)` testuale, con la chiave nativa castata a testo e il
> `key_selector` passato come letterale al trigger del reconcile, oggi vale il modello unico di
> `brief-db-sorgente-documento-e-riga` (lotto P): `pratiche.pratiche_sorgenti` e `pratiche.reconcile_errori` hanno
> le colonne tipizzate (`sorgente_id` bigint o `sorgente_uid` uuid, secondo il tipo, e `sorgente_riga`),
> `pratiche.fn_stato_sorgente` prende tipo, `sorgente_id` e `sorgente_uid`, e il trigger del reconcile riceve il
> solo codice del tipo: la chiave la risolve il catalogo. Il meccanismo è nella guida
> [Sorgente polimorfa](../../guide/sorgente-polimorfa.md). Il resto del modello di proiezione resta valido.
>
> **Owner**: Tid · **Stato**: 🟢 **DECISO (owner, 2026-07-07)** — le 4 decisioni (§6) sono adottate; pronto per
> i brief DB per dominio, **si parte da OFFERTA**. Il pilota PREVENTIVI è chiuso ed E2E-verde
> ([brief-design-guida-avanza-esito-proiettato](../work-done/brief-design-guida-avanza-esito-proiettato.md),
> [brief-db-guida-avanza-esito-proiettato](../work-done/brief-db-guida-avanza-esito-proiettato.md)). Questo brief
> pianifica l'estensione del meccanismo a OFFERTA, ORDINE, CONTRATTO.
>
> **Documento padre**: [analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md) — è il
> documento *padre* da cui derivano i brief della Gestione Pratiche (voce **V10** §4, processo §6 «come
> nascono i brief»). Questo brief è un **figlio** della voce V10 e ne va aggiornata la riga a chiusura.
>
> **Gerarchia dei documenti** (dalla radice a qui):
> 1. [analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md) — **padre** (V10 §4;
>    Problema 1 §2.1 + radice §2.4 «due macchine a stati»).
> 2. [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) — design MOSTRA/GUIDA
>    (§6 le due direzioni · §8 deliverable · **D4** GUIDA).
> 3. [brief-design-guida-avanza-esito-proiettato](../work-done/brief-design-guida-avanza-esito-proiettato.md) +
>    [brief-db-guida-avanza-esito-proiettato](../work-done/brief-db-guida-avanza-esito-proiettato.md) —
>    **pilota PREVENTIVI** (design-of-record + DB, chiusi in work-done).
> 4. **Questo brief** — roll-out del meccanismo agli altri domini (OFFERTA/CONTRATTO/ORDINE).
>
> **Origine**: la domanda dell'owner (2026-07-07): *«il roll-out non è solo offerta, riguarda anche ordini e
> contratti; e prima andrebbero definite le pratiche»*. Entrambe le osservazioni sono corrette e sono il
> perno di questo brief.
>
> **Correlati**: [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) (padre
> MOSTRA/GUIDA), [analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md) (V10 + Problema 2
> «variazione per azienda»), [brief-design-workflow-definizioni-versionate](../work-done/brief-design-workflow-definizioni-versionate.md)
> (edizioni versionate — lo strumento con cui si *definiscono* le pratiche), il cantiere editor
> [brief-fe-fase3-editor-definizioni-workflow](../work-done/brief-fe-fase3-editor-definizioni-workflow.md).

---

## 1. Tesi in una frase — il roll-out è *definizione + wiring*, non greenfield

Contro-intuitivamente rispetto a come era inquadrato nel brief-padre («MOSTRA implementato solo su
PREVENTIVI»), la ricognizione DB (2026-07-07) mostra che **il livello di lettura e il motore sono già
generici su tutti e 4 i domini**. Ciò che manca per OFFERTA/ORDINE/CONTRATTO è solo il **livello di
definizione+wiring**: (a) una **pratica-definizione** con un milestone da far avanzare, e (b) il
**cablaggio GUIDA** (binding di avanzamento + trigger reconcile sul documento). Il collo di bottiglia è
**definire le pratiche**: senza uno step-milestone concreto non c'è nulla su cui mettere il binding.

## 2. Mappa verificata — cosa c'è / cosa manca (ricognizione 2026-07-07)

Legenda: **PREV** preventivi · **OFF** offerte_commerciali · **ORD** ordini · **CON** contratti.

| Capacità | PREV | OFF | ORD | CON | Note |
|---|:--:|:--:|:--:|:--:|---|
| Riga `config.sorgenti` | ✅ | ✅ | ✅ | ✅ | id 2 / 14 / 6 / 4. **`key_selector`**: PREV+OFF=`uid`, ORD+CON=`id` |
| Normalizzazione `stati_doc_*` (`fase`/`esito`/`terminale`) — D1 | ✅ | ✅ | ✅ | ✅ | `is_abortito` solo PREV+CON; `is_bozza` solo CON |
| Resolver lettura `vw_stato_sorgente_*` (ramo UNION) — D3 | ✅ | ✅ | ✅ | ✅ | 4 rami reali in `script.vw_stato_sorgente` |
| `fn_available_actions_*` | ✅ | ✅ | ✅ | ✅ | schema `script` |
| **Pratica-definizione** (`tipi_prestazione` + `template_flussi`) | ✅ (9004) | ❌ | ❌ | ❌ | catena unica 9009→9014 sul tipo 9004 |
| **Binding avanzamento** (`TFAP` + `attende_sorgente_tipo_id`) | ✅ (9011) | ❌ | ❌ | ❌ | seedato solo sullo step 9011 |
| **Trigger reconcile** sul documento — D4 write-side | ✅ | ❌ | ❌ | ❌ | wired **solo** su `vendite.preventivi` |

**Motore già generico** (nessun hardcode di dominio): `pratiche.fn_stato_sorgente`,
`pratiche.fn_reconcile_sorgente`, `template_flussi_avanzamento_proiezione` (UNIQUE
`(template_flusso_id, esito_richiesto) NULLS NOT DISTINCT`), `template_flussi.attende_sorgente_tipo_id`
(FK `config.sorgenti`), `pratiche.reconcile_errori`, `pratiche_sorgenti.flusso_id` (nullable).

## 3. Cosa resta davvero — due pezzi per dominio (+ 2 di contorno)

Poiché lettura+motore ci sono, per portare GUIDA su un dominio servono **solo**:

- **(A) Definire la pratica** del dominio: `tipi_prestazione` + catena `template_flussi` con lo step che
  fa da **milestone** (il punto di responsabilità/attesa che proietta il verdetto del documento).
- **(B) Cablare GUIDA** sullo step-milestone:
  1. `template_flussi.attende_sorgente_tipo_id = <id sorgente del dominio>` (G1);
  2. riga in `template_flussi_avanzamento_proiezione` per lo step (G2), `esito_richiesto` NULL per
     l'inversione piena accept+reject (come il pilota) o valorizzato se si vuole un solo verso;
  3. trigger `AFTER UPDATE` sulla tabella documento →
     `trgfn_documento_reconcile_proiezione('<sorgente_tipo_id>','<key_selector>')` (D4 write-side).

Di contorno, per dominio:
- **FE**: una voce in `flussoCompletionRegistry` (mappa `esito → stato di dominio` + `docAction` lazy) +
  il gate `FlussoDrawer` già data-driven sul flag `template_attende_sorgente_tipo_id != null` (non serve
  toccarlo: discrimina da solo).
- **BE**: un endpoint `POST /vendite/<dominio>/da-pratica/<pratica_id>/stato/` (mirror di
  `ApiPreventivoStatoDaPratica` → `<dominio>_service.cambia_stato_da_pratica`), se il dominio ha un
  «Accetta/Rifiuta» in-pratica che deve agire sul documento standalone.
- **Perf (su evidenza di volumi)**: indice a espressione sulla `key_selector` castata a text del predicato
  LATERAL — `((uid::text))` per OFF (come PREV), `((id::text))` per ORD/CON. **Non** bloccante; voce DB.

## 4. Il bivio centrale — pratica standalone *vs* milestone COLLEGATO

Qui sta la parte non meccanica. Oggi ORDINE e CONTRATTO **non hanno una pratica propria**: nascono come
**documenti generati a valle** della catena PREVENTIVI (step `CONFERMA_ORDINE` 9013 → ordine,
`INVIO_COMMESSA` 9014 → commessa), agganciati come **`pratiche_sorgenti` con `ruolo_link=COLLEGATO` e
`flusso_id` NULL**. Ci sono quindi **due forme** di roll-out, non mutuamente esclusive:

- **Forma S — pratica standalone**: il dominio ha un proprio ciclo di vita-pratica (come PREVENTIVI), con
  un milestone `APPROVAZIONE_*`/`ATTIVAZIONE_*`. Richiede una **nuova pratica-definizione** (è il «definire
  le pratiche» dell'owner). GUIDA binda quel milestone. Àncora **ROOT con `flusso_id`** → nessun problema.
- **Forma C — milestone COLLEGATO in una pratica esistente**: lo step 9013/9014 della catena PREVENTIVI è
  un traguardo che dovrebbe **auto-avanzare** quando l'ordine/commessa collegato raggiunge un verdetto.
  **Non** serve una nuova pratica, ma GUIDA deve risolvere l'àncora per un link **`flusso_id` NULL**.

⚠️ **Nodo tecnico della Forma C** (caveat (b) del brief-padre, tuttora aperto): `fn_reconcile_sorgente`
fa tie-break via `pratiche_sorgenti.flusso_id`; con più candidati **senza** `flusso_id` **salta e logga
`E_RECONCILE_AMBIGUO`** (per design, no avanzamento a caso). Quindi la Forma C **non funziona** finché non
si decide l'àncora dei COLLEGATO: o **valorizzare `flusso_id`** sul link al momento della generazione
(lo step che genera il documento conosce il proprio `flusso_id`), o dare a `fn_reconcile_sorgente` un
**fallback pratica-level** (àncora allo step per `attende_sorgente_tipo_id` quando il link è NULL).
*Proposta*: valorizzare `flusso_id` sul COLLEGATO alla generazione — è la correzione più pulita e rende la
proiezione per-flusso (MOSTRA) coerente anche sui passi a valle.

## 5. Lettura per dominio — non sono simmetrici

- **OFFERTA** — *gemello di PREVENTIVI*. Verdetto cliente netto (`ACCETTATA`/`RIFIUTATA`), `key_selector=uid`.
  **Forma S**: merita una pratica standalone (offerta commerciale → APPROVAZIONE_CLIENTE → push contratto).
  Binding NULL (accept+reject) come il pilota. **Roll-out più pulito → primo candidato.**
- **CONTRATTO** — ciclo `DRAFT → ATTIVO → CESSATO`. `ATTIVO` è **data-driven** (`valido_dal`), non un
  click-verdetto; `CESSATO` è terminale data-driven. Il modello «avanza-su-**esito**» ci calza a metà:
  bisogna **decidere quale transizione è il milestone** e se il suo avanzamento è un *esito* (POSITIVO su
  attivazione?) o una *transizione temporale*. Verosimilmente **Forma S**, ma con semantica da definire.
- **ORDINE** — tre grane: (a) **niente verdetto-cliente** — un ordine nasce *già* da un'accettazione a
  monte; i suoi "esiti" utili sono **fulfillment** (`EVASO`/`FATTURATO` = POSITIVO terminale, `ANNULLATO` =
  NEGATIVO); (b) oggi è **COLLEGATO senza `flusso_id`** nella catena PREVENTIVI → **Forma C** con il nodo
  del §4 da sciogliere. Da affrontare **dopo** la decisione sull'àncora; (c) ⚠️ **il milestone ORDINE
  avanza già oggi in modo imperativo** — `ordini_service._completa_flusso_ordine_pratica`
  ([ordini_service.py:262](../../../../backend/apps/vendite/services/ordini_service.py)) completa
  `CONFERMA_ORDINE`/`INVIO_COMMESSA` (POSITIVO) all'azione standalone. Quindi per ORDINE la reconcile
  dichiarativa **non riempie un vuoto: converte imperativo→dichiarativo** (il valore aggiunto è coprire i
  versi mancanti — `ANNULLATO`=NEGATIVO — e i cambi-stato standalone non passati dall'azione-pratica). Serve
  un **cutover esplicito** (vedi §9-R2): il guard di mutua esclusione D-B10 **non** intercetta la spinta
  imperativa (è codice BE, non un `handler_eventi COMPLETATO`), perciò non protegge dal doppio scatto.

## 6. Decisioni adottate (owner, 2026-07-07)

- **D-A — Forma per OFFERTA e CONTRATTO → Forma S (standalone) per entrambi.** Ognuno ha una pratica
  propria con uno step-milestone che aspetta il verdetto del documento; àncora **ROOT con `flusso_id`**,
  nessun nodo tecnico. Gemelli del preventivo.
- **D-B — Àncora dei COLLEGATO → Fix 1: valorizzare `flusso_id` alla generazione.** Lo step che genera il
  documento a valle (es. `CONFERMA_ORDINE`) scrive il proprio `flusso_id` sul link `pratiche_sorgenti`.
  `fn_reconcile_sorgente` risolve il traguardo esatto senza ambiguità; allinea anche MOSTRA sui passi a
  valle. Additivo (colonna già esistente, oggi NULL). Sblocca ORDINE (Forma C).
- **D-C — Traguardo di CONTRATTO (e ORDINE) → Option A: avanzamento su FASE, non solo su esito.**
  Generalizzare il binding: un traguardo può avanzare quando il documento **raggiunge una fase**
  (`IN_CORSO` = attivato/confermato) o diventa **terminale**, oltre che su un **verdetto** (`esito`). Il
  descrittore espone già `fase`/`terminale`: si allarga solo la condizione di
  `template_flussi_avanzamento_proiezione`. Copre «contratto attivato» **e** «ordine confermato» (entrambi
  `IN_CORSO` senza esito nel modello attuale).
- **D-D — Ordine di attacco → OFFERTA → CONTRATTO → ORDINE.** Dal più pulito al più carico: offerta
  (gemello, zero estensioni), contratto (primo utente dell'avanza-su-fase), ordine (avanza-su-fase +
  àncora `flusso_id` + collegato a valle).

**Conseguenza sul modello (aggiornamento §4-§5)**: con D-A, OFFERTA e CONTRATTO sono **Forma S**; ORDINE
resta **Forma C** (milestone collegato nella catena, sbloccato da D-B). Con D-C il motore non è più
«avanza-su-esito» ma **«avanza-su-descrittore»** (esito **o** fase **o** terminale) — estensione generica
che vale per tutti i domini presenti e futuri.

## 7. Sequenza e deliverable

**Passo 0 — base condivisa (una volta sola, poi vale per tutti i domini)** → **brief DB al team**
(`feedback_db_actions_passaggio_team`):

- **G-est.1 (da D-C)** — generalizzare `template_flussi_avanzamento_proiezione` e `fn_reconcile_sorgente`
  perché un traguardo possa avanzare su **fase**/**terminale** oltre che su **esito** (condizione sul
  descrittore, non solo `esito_richiesto`). Retro-compatibile col binding esito del pilota.
- **G-est.2 (da D-B)** — valorizzare `pratiche_sorgenti.flusso_id` sui link **COLLEGATO** al momento della
  generazione a valle (lo step generatore conosce il proprio `flusso_id`). Serve a ORDINE ma è additivo e
  innocuo sugli altri. ⚠️ **Non è un changeset a sé**: l'INSERT del link COLLEGATO vive dentro le funzioni
  di push (`fn_push_preventivo_a_ordine` oggi inserisce `(pratica_id, sorgente_tipo_id, sorgente_uid,
  ruolo_link)` **senza** `flusso_id`) — le stesse funzioni che
  [analisi-fix-transazioni](../work-done/analisi-fix-transazioni.md) rifonde in **funzioni madre** (finding #4/#5/#10).
  G-est.2 va **incorporato in quelle madri**, non scritto in parallelo (vedi §9-R1).

Entrambe **additive** e non regressive sul pilota PREVENTIVI (che continua a bindare su `esito` NULL con
àncora ROOT).

**Passo N — per ogni dominio** (ordine D-D: OFFERTA → CONTRATTO → ORDINE). ⚠️ **OFFERTA non dipende dal
Passo 0** (Forma S, binding `esito` NULL come il pilota: non usa né G-est.1 né G-est.2) → può partire **in
parallelo** alla base. Il Passo 0 è prerequisito solo per **CONTRATTO** (primo utente di avanza-su-fase) e
**ORDINE** (avanza-su-fase + `flusso_id`). Per ogni dominio:

1. **Design/seed pratica** (Forma S): `tipi_prestazione` + `template_flussi` con lo step-milestone. → è
   lavoro di **definizione workflow** (cantiere edizioni versionate / editor): può nascere da seed
   Liquibase (come PREVENTIVI) o dall'editor quando disponibile.
2. **Brief DB al team** (`feedback_db_actions_passaggio_team`): binding G1/G2 sullo step + trigger reconcile
   sulla tabella documento (`trgfn_documento_reconcile_proiezione(<tipo>,<key>)`) + (opz.) indice a
   espressione. Additivo, `attivo=false`-friendly.
3. **BE**: endpoint `da-pratica` per il dominio (mirror preventivi) — **solo se** c'è un «Accetta/Rifiuta»
   in-pratica.
4. **FE**: voce `flussoCompletionRegistry` per il tipo-step del dominio. Il gate `FlussoDrawer` è già
   data-driven.
5. **Smoke E2E** per dominio (mirror di `smoke-test-guida-inversione-preventivi.sh`): accept **e** reject →
   milestone avanza; **come ruolo app** (gli smoke E2E hanno scoperto i GRANT mancanti invisibili al pgTAP).

**Le azioni DB (colonne/tabelle/trigger/seed/pgTAP) non le esegue l'agent**: brief scritto al team su
`dev/db-tid`.

## 8. Vincoli e non-obiettivi

- Il motore **non nomina stati di dominio**: ragiona su `fase`/`esito` normalizzati (già così).
- **Additivo**: senza binding/trigger → comportamento di oggi (milestone manuale). Roll-out per dominio.
- **Idempotente**: `completa_step_pratica` è no-op sui flussi terminali → reconcile ripetuti innocui.
- **Best-effort documento-sovrano**: un errore lato pratiche **non** rollbacka il cambio-stato del
  documento (lezione dei GRANT del pilota).
- **Niente mirror**: non si copiano gli stati del documento in flussi.
- **Non** è questo brief a definire i *contenuti* dei workflow di offerta/ordine/contratto (quali step,
  SLA, prerequisiti): quello è il cantiere edizioni versionate. Qui si definisce **dove** e **come** GUIDA
  si aggancia una volta che la pratica esiste.

---

## 9. Analisi critica e correzioni operative (verifica codice, 2026-07-07)

Verifica delle affermazioni del brief contro il **codice vivo** (doc auto-gen dbzero, funzioni, trigger,
seed) e contro i documenti padre/pilota. Esito: la ricognizione §2 **regge in ogni cella**; le correzioni
sotto riguardano il *framing* e il *coordinamento con altre attività*, non errori di merito.

### Cosa è confermato ✓

- **§2 accurata**: `config.sorgenti` id 2/14/6/4, `key_selector` PREV+OFF=`uid` / ORD+CON=`id`;
  `vw_stato_sorgente` ha **4 rami reali**; normalizzazione D1 (`fase`/`esito`/`terminale`) presente su
  **tutti e 4** i `stati_doc_*`; flag asimmetrici esatti (`is_abortito` solo PREV+CON, `is_bozza` solo CON).
- **Nodo Forma C (§4) esatto**: `fn_reconcile_sorgente` usa `flusso_id` come filtro di restrizione
  (`r_ps.flusso_id IS NULL OR f.id = r_ps.flusso_id`) e, con più candidati COLLEGATO senza `flusso_id`,
  **logga `E_RECONCILE_AMBIGUO` e fa `CONTINUE` (skip)** — resiliente (il log fallito degrada a `WARNING`).
- **«Nota di correzione al brief-padre» giustificata**: il livello di lettura DB è davvero generico e
  completo sui 4 domini (refuta il «MOSTRA solo su PREVENTIVI» del padre).

### Correzioni di framing

- **F1 — «solo definizione+wiring» sottostima il Passo 0.** Verificato:
  `template_flussi_avanzamento_proiezione` ha **solo** `esito_richiesto`, **nessuna** colonna
  `fase`/`terminale`; `fn_reconcile` matcha solo su verdetto. Quindi **D-C (avanza-su-fase) è una modifica
  di schema+logica al motore condiviso** — CONTRATTO e ORDINE la richiedono *prima* di poter essere
  cablati. Il §1/§6 lo ammette a valle («avanza-su-descrittore»), ma va detto nell'incipit: **due domini su
  tre non sono «solo cablaggio»**.
- **F2 — D-B inverte la proposta del pilota (tracciabilità).** Il pilota
  [brief-design-guida-avanza-esito-proiettato](../work-done/brief-design-guida-avanza-esito-proiettato.md)
  §6(b) proponeva **l'opposto** («NON forzare `flusso_id` sui COLLEGATO; usare la mappa step→sorgente»).
  D-B sceglie il forcing — legittimo e **compatibile col motore attuale** (che già legge `flusso_id` come
  restrizione, quindi *nessuna* modifica al motore per D-B) — ma è un ribaltamento da annotare.
- **F3 — CONTRATTO ha un predecessore aperto.** D-C generalizza il *motore*, ma **non decide quale
  transizione contratto è il milestone** (attivazione? cessazione?) né se è esito o temporale (§5 lo
  ammette). Lo stato «DECISO» vale per le 4 decisioni trasversali, **non** per la prontezza di CONTRATTO: il
  suo brief-DB ha una decisione-di-dominio a monte.
- **F4 — MOSTRA display fuori scope, da verificare.** Il livello di *lettura DB* è generico, ma
  l'esposizione BE nei payload e il consumo FE del descrittore per offerta/ordine/contratto potrebbero
  essere ancora preventivi-only. GUIDA senza MOSTRA-display = l'operatore «guida» un documento di cui non
  vede lo stato. Verificare per dominio.

### Correzioni operative (da recepire prima dei brief-DB per dominio)

- **R1 — Coordinamento con la fix-transazioni (stesso branch, stesse funzioni).** ✅ **RECEPITO sul lato
  firma — verificato in DB il 2026-07-16.** G-est.2 (`flusso_id` sul
  COLLEGATO) va **dentro le funzioni madre** dei finding **#4/#5/#10** di
  [analisi-fix-transazioni](../work-done/analisi-fix-transazioni.md) — che *già* riscrivono l'INSERT su
  `pratiche_sorgenti`. Progettare **da subito** la firma della madre per ricevere/risolvere il `flusso_id`
  (oggi `fn_push_preventivo_a_ordine` riceve `p_pratica_id` ma non il flusso): aggiungerlo dopo = seconda
  modifica di firma → `DROP FUNCTION` (regola `RETURNS TABLE`). **#3 escluso** (link ROOT: `flusso_id` già
  gestito). Invarianti già allineati (`SECURITY INVOKER` + GRANT-a-`zeroerp_app` + documento-sovrano).

  ➡️ **Stato 2026-07-16 — il rischio strutturale che motivava R1 è scongiurato**: la parentesi «oggi
  `fn_push_preventivo_a_ordine` … non riceve il flusso» **non è più vera**. La firma viva è
  `fn_push_preventivo_a_ordine(p_preventivo_id, p_righe_ids, p_pratica_id, p_fatturazione_trigger,
  p_flusso_id bigint DEFAULT NULL)` e il corpo scrive il parametro sul link COLLEGATO
  (`INSERT INTO pratiche.pratiche_sorgenti (…, ruolo_link, flusso_id) VALUES (…, 'COLLEGATO', p_flusso_id)`).
  **Nessun secondo `DROP FUNCTION` sarà necessario**: R1, come formulata, è chiusa.

  ⚠️ **Ma G-est.2 NON è operativo — capability dormiente, da sapere prima dei brief-DB per dominio**
  (analisi BE 2026-07-19; *una revisione precedente di questa nota indicava `push_a_ordine` come sede
  dell'INSERT: era imprecisa, vedi sotto*). **Riscontro sui dati**: `pratiche.pratiche_sorgenti` ha
  **40 link COLLEGATO, 0 con `flusso_id`** (ROOT: 14/46) — link nuovi continuano a nascere vuoti.

  - **Dove nasce davvero il link**: sul percorso pratica `crea_ordine_da_preventivo` invoca la fn con
    `pratica_id=None`, quindi il blocco INSERT **interno alla fn non viene mai eseguito**. Il vero
    autore è `PostSmistamentoHandler` → `PraticheRepository.upsert_pratica_sorgente`, che **accetta
    già** `flusso_id`. Il `p_flusso_id` della fn DB è dormiente **due volte**.
  - **Il cablaggio ingenuo sarebbe SBAGLIATO**: l'handler ha il `flusso_id` di **SMISTAMENTO (9012)**,
    non di **CONFERMA_ORDINE (9013)**; con l'ancora `ps.flusso_id = f.id` il documento si accenderebbe
    sulla card sbagliata. La via corretta è **D4 — pinning per-step, mappa step→sorgente condivisa con
    GUIDA**: design, non due righe di cablaggio.
  - **Il fallback pratica-level è già stato implementato** (`script.vw_pratica_doc_sorgente`): dettaglio
    e lista accendono già i COLLEGATO senza `flusso_id`. Scoperto solo l'aggancio **per-flusso**
    (percorso/coda). Dettaglio nelle note **(b)** e **(c)** del
    [brief-padre proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md).
  - 🔴 **ATTENZIONE sul primo dominio del roll-out — OFFERTA**: `vendite.fn_push_offerta_a_contratto`
    ha firma `(p_offerta_id, p_pratica_id, p_chiudi_contratto_esistente)` — **nessun `p_flusso_id`**.
    Il rischio che R1 voleva evitare (seconda modifica di firma → `DROP FUNCTION`) è scongiurato per i
    **preventivi**, ma per **offerta è ancora tutto da pagare**: se G-est.2 dovrà valere anche lì, la
    firma va progettata **ora**, nello stesso brief-DB, non dopo. Stessa verifica da fare su
    `vendite.fn_link_commessa_sorgente` (altro scrittore di COLLEGATO).
- **R2 — ORDINE: cutover esplicito imperativo→dichiarativo.** Aggiungere alla checklist Passo N per ORDINE
  un passo «**neutralizza `_completa_flusso_ordine_pratica`**» (mirror del pilota che ha disattivato
  l'handler `accetta_preventivo`). Senza, binding G2 e spinta imperativa scattano entrambi su 9013/9014
  (idempotente, ma ridondante) e il guard D-B10 **non** intercetta la spinta BE. Nel pilota preventivi le
  due vie coesistono solo perché colpiscono step *diversi*; per ORDINE colpiscono lo **stesso** step.
- **R3 — Sequenza: OFFERTA parte subito.** Recepito in §7: OFFERTA non dipende dal Passo 0 → in parallelo;
  il Passo 0 gate solo CONTRATTO/ORDINE.

### Note minori

- **`9009→9014` vs `9011`**: non è contraddizione — `9009→9014` è la *campata* della catena, `9011` è il
  milestone APPROVAZIONE_CLIENTE (binding del pilota), `9013/9014` sono gli step che generano i COLLEGATO.
- **`is_verdetto`**: non esiste in nessuno `stati_doc_*` (il brief non lo cita — corretto).

---

## Nota di correzione al brief-padre

Il brief-padre [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) inquadra
MOSTRA come «implementato solo su PREVENTIVI». La ricognizione 2026-07-07 mostra che il **livello di
lettura DB (D1 norm + D3 resolver)** è in realtà **generico e completo su tutti e 4 i domini**; ciò che è
PREVENTIVI-only è la **definizione di pratica** (e quindi i *dati*: solo la pratica preventivi crea link
verso un documento) e il **wiring GUIDA**. Aggiornare la nota di stato del brief-padre di conseguenza a
chiusura di questo cantiere.

*Brief vivo: a chiusura per dominio, aggiornare la tabella §2 e la riga V10 di
[analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md).*
