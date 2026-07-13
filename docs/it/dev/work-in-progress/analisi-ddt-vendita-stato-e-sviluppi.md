# Analisi — DDT di vendita: stato attuale e piano di sviluppo

> **Tipo**: analisi + piano (da cui nascono i brief DB/BE/FE) · **Data**: 2026-07-09
> · **Owner**: Tid · **Target sviluppo**: DB (`dev/db-tid`) → BE/FE (`dev/backend-tid`).
> **Natura**: attivazione di uno *slot predisposto*, non fondazione da zero.
>
> **Vedi anche**:
> [Gestione Ordini](/guide/gestione-ordini) ·
> [Gestione Commesse](/guide/gestione-commesse) ·
> [Fatturazione end-to-end](/guide/fatturazione) ·
> [Genealogia & transiti vendite](/dev/work-in-progress/brief-design-genealogia-transiti-vendite) ·
> [Lineage documenti vendite (brief DB)](/dev/work-in-progress/brief-db-lineage-documenti-vendite) ·
> [Analisi ordini vendita](/dev/work-done/analisi-ordini-vendita) ·
> [Analisi commesse — stato e sviluppi](/dev/work-done/analisi-commesse-stato-e-sviluppi)

---

> ## ⏱️ Stato avanzamento (aggiornato 2026-07-11)
>
> Le tabelle §2 sono la **fotografia iniziale** (pre-sviluppo). Avanzamento reale sulle fasi del §6:
>
> | Fase | Stato | Rif. |
> |---|---|---|
> | **1 — DB** (evasione + stati + gap + predisposizione PDF) | ✅ FATTO | [brief DB](../work-done/brief-db-ddt-vendita-evasione-e-stati.md) |
> | **2 — BE** (service/repo/endpoint + evasione + push + note) | 🟢 slice principale FATTA · backlog ⬜ | [brief BE](brief-be-ddt-vendita.md) §12–14 |
> | **3 — FE** (lista + drawer + evasione + navigazione) | 🟢 slice principale FATTA · backlog ⬜ | [brief FE](brief-fe-ddt-vendita.md) §11–13 |
> | **3-bis — Standalone** (DDT senza sorgente, billing proprio) | ✅ FATTO | incluso in BE/FE |
> | **5 — PDF** (stampa DDT + valuta/emittente drawer + PDF data-driven capabilities) | ✅ FATTO (2026-07-11) | [[handoff_20260711_ddt_stampa_orfano_refactor]] |
> | **4 — Lineage** (accensione nodo DDT in `vw_documento_lineage`) | ⬜ APERTO | segue brief lineage esistente |
>
> **Slice minori** — chiuse: editing `ddt_indirizzi` (✅ UX v2 pilota DDT + rollout
> 5 domini, 2026-07-12, brief design indirizzi §7), riepilogo IVA DDT (✅ 2026-07-12,
> brief dedicato CHIUSO), export lista DDT (✅ 2026-07-11), colonna "Emittente"
> a catalogo (✅ 2026-07-12, seed DB applicato — opt-in, mai nei preset, brief
> [brief-db-ddt-colonna-emittente-catalogo](brief-db-ddt-colonna-emittente-catalogo.md)),
> PDF DDT con indirizzo di consegna (✅ 2026-07-12, builder v2 + template v2
> PUBBLICATA, brief design indirizzi §7-F10). Aperta: **slice RESI** (brief DB §12).
> **Verifica visiva in-app** ✅ fatta da Tid (2026-07-13): drawer DDT + 4 drawer
> rollout indirizzi, tutto ok.
> Tutto il lavoro FE/BE è su `dev/backend-tid` **non committato** (commit → Tid).

## 1. Scopo e perimetro

Attivare il **ciclo DDT di vendita**, oggi presente a livello DB ma dormiente lato
applicativo. Due modalità di nascita del DDT, entrambe destinate a **transitare in
commessa** per la **fatturazione differita**:

- **DDT da ordine (evasione)** — il DDT nasce dalle righe di un ordine confermato,
  quando la fatturazione è legata a spedizione/consegna (non alla conferma);
- **DDT standalone (libero)** — DDT senza ordine, con `billing_account` proprio.

### 1.1 Decisioni prese (Tid, 2026-07-09)

| # | Decisione |
|---|---|
| D-1 | **Prima slice = DDT da ordine (evasione)**; lo **standalone** segue come slice immediata successiva (stesso motore di push, testata senza sorgente). |
| D-2 | **Macchina a stati DDT data-driven**: nuova `config.transizioni_stati_ddt` coerente con ordini/contratti/commesse → azioni FE data-driven "gratis". |
| D-3 | **Stampa PDF in seconda battuta**, MA **modello dati e BE predisposti** (snapshot completi, campi di trasporto, indirizzi, note-stampa) così la fase PDF è "solo frontend o poco più". Concentrico, no-YAGNI ([[feedback_concentrico_no_yagni]]). |
| D-4 | **BE/FE seguono lo stile di preventivi/ordini/contratti** (logica diversa, impronta identica): in particolare **liste personalizzabili** `<ListaConfigurabile>`, drawer master-detail, azioni data-driven, pannello componenti condiviso. Omogeneità UI, mai varianti locali ([[feedback_vue_reuse]], [[feedback_lista_pattern_standard]]). |
| A-1 | **Multi-DDT per ordine = SÌ** (consegne parziali): si rimuove l'unicità `un DDT per sorgente` dalla testata; l'unicità resta sul fulfillment riga↔riga. |
| A-2 | **Prezzi nel DDT da ordine = copia snapshot ordine** (no ri-risoluzione resolver): il prezzo è già negoziato sull'ordine. |
| A-3 | **Stati DDT = `DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO`** (+`ANNULLATO`): il **RESO è previsto** nella prima matrice. |

### 1.2 Fuori perimetro (confermato dal design lineage, G-5)

- **Solo gli ordini** generano DDT: preventivi / offerte / contratti **no**.
- Il **DDT non genera mai un ordine** (direzione unica ordine → DDT).
- **DDT non-vendita** (trasferimento, conto lavorazione, reso, campioni): nessuna
  fatturazione, fuori da questo asse (vivono su `magazzino`).
- **Ramo logistico puro** dell'ordine (tracking spedizioni end-to-end) non è
  obiettivo di questa analisi: qui il DDT serve come **nodo di fatturazione**.

---

## 2. Stato attuale — mappa FATTO / PREDISPOSTO / MANCANTE

### 2.1 DB — ricco e in gran parte coerente

| Elemento | Stato | Note |
|---|---|---|
| Tabelle `vendite.ddt`, `ddt_righe`, `ddt_righe_componenti`, `ddt_indirizzi`, `note_ddt` | ✅ FATTO | Vedi [/dbzero/vendite/tabelle/ddt](/dbzero/vendite/tabelle/ddt) e correlate |
| `storico.ddt` / `storico.ddt_righe` (audit temporale) | ✅ FATTO | Trigger `_z90_storico` attivi su testata+righe |
| Campi billing su testata (`billing_account_id`, `utility_id`, `valuta_id`) | ✅ FATTO | Ereditati dall'ordine via `trgfn_ddt_normalize` |
| Campi trasporto/logistica (causale, aspetto, vettore, porto, colli/pesi, targa, tracking) | ✅ FATTO | Predisposti per il PDF (D-3) |
| BoM CASO A su righe DDT (`ddt_righe_componenti` + init/preview + guard PENDING) | ✅ FATTO | Riusa il modello componenti unificato |
| Numerazione, normalize, gen-codice, no-hard-delete, guard fulfillment | ✅ FATTO | Trigger di dominio attivi |
| `config.sorgenti` id **8 = DDT_VENDITA** (attivo, scope `PUSH_COMMESSA`, target `vendite.ddt`) | ✅ PREDISPOSTO/ATTIVO | Lo slot del transito è **acceso** |
| `fn_list_ddt_da_pushare` (elenca righe DDT eleggibili al push) | ✅ FATTO | Non crea nulla: **elenca** soltanto |
| **Funzione che *genera* il DDT dall'ordine (evasione)** | ❌ MANCANTE | Nessuna fn crea `ddt`+`ddt_righe`+`ordini_righe_fulfillment` |
| **`config.transizioni_stati_ddt`** (macchina a stati data-driven) | ❌ MANCANTE | Esiste per ordini/contratti/preventivi/commesse, non per DDT |
| Seed `config.causali_trasporto` | ⚠️ VUOTO | CSV con solo header; dominio referenziato ma senza valori |
| `trgfn_ddt_guard_transizione_approvazione` agganciata alla testata DDT | ⚠️ NON WIRED | Funzione definita, trigger non registrato su `vendite.ddt` |
| `trgfn_ddt_normalize` risolve sorgente per `codice` (mutabile) | ⚠️ FRAGILE | `fn_list_ddt_da_pushare` usa `codice_interno` (immutabile): allineare |
| Doc MV `mv_ddt_ordini` + manual `ddt.md` | ⚠️ STALE | MV non documentata; manual con colonne inesistenti (`data_documento`, ecc.) |

### 2.2 BE — quasi vuoto

| Elemento | Stato |
|---|---|
| `HandlerDdt` nel push commesse + `_SORGENTE_FN_MAP["DDT_VENDITA"]` | ✅ FATTO (ma **mai alimentato**: nessun DDT viene creato) |
| `DdtRepository` (solo lettura componenti via mixin) | ⚠️ MINIMALE |
| `ddt_service` (CRUD testata/righe/componenti/indirizzi, emissione, stati) | ❌ MANCANTE |
| Endpoint `/ddt`, `/ddt/<id>`, `/ddt/da-pushare`, azione "genera DDT da ordine" | ❌ MANCANTE |
| Cablaggio note DDT in `note_views.py` | ❌ MANCANTE (~3 righe: il BB è pronto, whitelist include già `DDT`) |

### 2.3 FE — inesistente

Nessuna vista lista, nessun drawer, nessuno store, nessun api client, nessuna rotta,
nessuna voce di navigazione (l'icona CSS `app-nav-icon-ddt` esiste ma è inutilizzata),
nessuna azione "genera DDT" nel drawer ordine.

---

## 3. Come si collega tutto

### 3.1 Ordine ↔ DDT — tre livelli (nessuna FK diretta DDT→ordine)

1. **Testata (soft):** `ddt.sorgente_tipo_id` = **ORDINE_VENDITA** (id 6, la sorgente *a monte*
   del DDT) + `ddt.sorgente_uid = ordini.uid`. È questo il valore letto da `trgfn_ddt_normalize`
   per ereditare `billing_account`/`utility`/`valuta` (la fn richiede `codice = 'ORDINE_VENDITA'`).
   ⚠️ **Non** `DDT_VENDITA` (id 8): quello è il tipo-sorgente *a valle*, usato quando il DDT
   pusha in commessa (`fn_list_ddt_da_pushare`, §2.1), non la sorgente della testata. Con id 8
   l'eredità billing non scatterebbe (bug silenzioso). La UNIQUE storica
   `(sorgente_tipo_id, sorgente_uid)` "un DDT per ordine" viene **rimossa** da A-1 (multi-DDT):
   l'unicità resta sul fulfillment riga↔riga.
2. **Riga ↔ riga (fonte di verità) = l'evasione:**
   `vendite.ordini_righe_fulfillment(ordine_riga_id, ddt_riga_id, qta_evasa)`,
   UNIQUE `(ordine_riga_id, ddt_riga_id)`, FK `ON DELETE RESTRICT`, guard
   consistenza (match articolo, no over-shipping). Le righe DDT **non** hanno FK
   diretta a `ordini_righe`.
3. **Testata ↔ testata (derivata):** MV `mv_ddt_ordini(ddt_id, ordine_id)` =
   `DISTINCT` sul fulfillment, refresh via `dbops.fn_refresh_mv_ddt_ordini`.

### 3.2 DDT → commessa → fattura (il transito)

Il DDT pusha le sue righe in `vendite.commesse_attivita` con segment_key
deterministica `DDT:{uid}:R:{riga_id}` → `attivita_fatturabili` → pipeline lotto →
fattura. **Stesso binario di tutte le altre sorgenti**: `HandlerDdt` è già
registrato, manca solo che esista un DDT reale da pushare.

### 3.3 Regola XOR ordine/DDT — `ordini.fatturazione_trigger`

| `fatturazione_trigger` | Chi pusha in commessa |
|---|---|
| `CONFERMATO` (default) | **l'ordine** (flusso vivo oggi, nessun DDT) |
| `SPEDITO` | **il DDT** quando spedito — l'ordine NON pusha |
| `CONSEGNATO` | **il DDT** quando consegnato — l'ordine NON pusha |

> ⚠️ **Invariante da presidiare (rischio doppia fatturazione):** ordine e DDT sono
> in **XOR** sul push. Quando c'è il DDT è **il DDT** ad andare in commessa, non
> l'ordine. `fn_list_ddt_da_pushare` è già eleggibile solo quando
> `ordini.fatturazione_trigger == stato_ddt` (≠ CONFERMATO); simmetricamente
> `fn_list_ordini_da_pushare` deve escludere gli ordini con trigger SPEDITO/CONSEGNATO.
> Il trigger è ereditato da `billing_account.fatturazione_ordini`, sovrascrivibile
> per singolo ordine.

### 3.4 Lineage — il nodo DDT si "accende"

Il grafo dei transiti ([genealogia](/dev/work-in-progress/brief-design-genealogia-transiti-vendite))
prevede già il nodo **DDT_VENDITA** come slot predisposto. Attivare i DDT lo riempie:
la `vw_documento_lineage` mostrerà `Ordine → DDT → Commessa → Att.fatt. → Fattura`.
**È qui che "si collega tutto" visivamente** nelle liste vendite.

---

## 4. Regole di business (per i brief)

1. **Provenienza:** DDT da ordine **oppure** standalone. Mai da preventivo/offerta/contratto. Mai DDT→ordine.
2. **Quando un ordine genera DDT:** quando `fatturazione_trigger ∈ {SPEDITO, CONSEGNATO}` (fatturazione differita). Con `CONFERMATO` l'ordine chiude il giro senza DDT.
3. **Evasione parziale e multi-DDT:** un ordine può generare **più DDT** (consegne parziali); `qta_evasa` accumula sul fulfillment; serve il **residuo per riga** (`ordinato − evaso`) come gate. La UNIQUE `un DDT per sorgente` sulla testata va **riconsiderata** per il multi-consegna → decisione aperta A-1 (§7).
4. **Standalone:** richiede `billing_account_id` proprio; eleggibile al push a `SPEDITO`/`CONSEGNATO`.
5. **Emissione:** transizione `DRAFT → EMESSO` gate su componenti CASO A non PENDING e prezzi valorizzati (guard oggi non wired → §5).
6. **No hard-delete:** annullo/storno, mai DELETE fisica (policy già a trigger).

---

## 5. Gap, rischi e predisposizione PDF

**Bloccanti (DB, prima slice):**
- **Funzione di evasione mancante** → costruire `vendite.fn_genera_ddt_da_ordine`
  riusando il pattern di [`fn_push_preventivo_a_ordine`](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)
  (copia righe MERCE, snapshot, idempotenza di riga, transizione atomica, link
  sorgente): crea `ddt` + `ddt_righe` + `ordini_righe_fulfillment` con `qta_evasa`,
  gate sul residuo.
- **`config.transizioni_stati_ddt`** (D-2): tabella + seed + guard `child` sulle transizioni.

**Da chiudere nello stesso brief DB (rifinitura):**
- Seed `config.causali_trasporto` (+ verificare seed `config.aspetti_beni` per il PDF).
- Wiring `trgfn_ddt_guard_transizione_approvazione` sulla testata DDT (simmetria col preventivo).
- Allineare `trgfn_ddt_normalize` a `codice_interno` (robustezza lookup sorgente).
- Documentare `mv_ddt_ordini`; correggere manual `ddt.md` disallineato.

**Predisposizione PDF (D-3) — cosa garantire ora perché il PDF sia "solo FE":**
- Snapshot completi già presenti: `ddt_indirizzi.snapshot`, campi trasporto in testata,
  `note_ddt.solo_stampa`. Verificare completezza snapshot mittente/destinatario/vettore
  ed eventuale riepilogo colli/pesi calcolato.
- Causali e aspetti beni **seedati** (senza, il PDF non ha i valori da stampare).
- La generazione userà il **motore documentale esistente** ([api_documenti_templates](/backend/documenti/manual/api_documenti_templates)):
  la fase PDF diventa un template + una view, non un rifacimento.

---

## 6. Piano concentrico e brief da generare

| Fase | Contenuto | Brief da scrivere | Target |
|---|---|---|---|
| **1 — DB** | `fn_genera_ddt_da_ordine` (evasione) + `transizioni_stati_ddt` + chiusura gap + predisposizione PDF | `brief-db-ddt-vendita-evasione-e-stati.md` | `dev/db-tid` |
| **2 — BE** | `ddt_service` + `ddt_repository` (testata/righe) + endpoint CRUD/emissione/stati + `genera-da-ordine` + `da-pushare` + note DDT (~3 righe) | `brief-be-ddt-vendita.md` | `dev/backend-tid` |
| **3 — FE** | Lista DDT + drawer master-detail (righe + pannello componenti condiviso + indirizzi + note) + azione "genera DDT" nel drawer ordine + navigazione/rotta/store | `brief-fe-ddt-vendita.md` | `dev/backend-tid` |
| **3-bis — Standalone** | Testata DDT senza sorgente + billing proprio (slice immediata su BE/FE già fatti) | incluso nei brief BE/FE come variante | — |
| **4 — Lineage** | Accensione nodo DDT nella `vw_documento_lineage` (già progettata) | segue il brief lineage esistente | `dev/db-tid` → BE/FE |
| **5 — PDF** | Template DDT accompagnatorio sul motore documentale (predisposto in Fase 1) | `brief-ddt-vendita-pdf.md` | `dev/backend-tid` |

**Building block da riusare (regola del 2, no duplicazione):**
- DB: pattern `fn_push_preventivo_a_ordine` (doc→doc), matrice `transizioni_stati_*`,
  `fn_ddt_riga_componenti_init/preview` (già pronte).
- BE: `PayloadValidator`, `PartitionedNoteService`/`make_note_views` (note DDT),
  gate pricing componenti, `handle_post_json`, envelope/paginazione core.
- FE: `ListaConfigurabile`, drawer master-detail inline, **pannello componenti
  condiviso** (già usato da preventivi, predisposto per DDT), note BB, azioni
  data-driven `DrawerActionsBar`/`availableActions`.

**Gate DB-first:** BE/FE partono solo a viste/funzioni applicate ([[feedback_be_fe_attende_prerequisiti_db]]);
le azioni DB passano per brief al team DB ([[feedback_db_actions_passaggio_team]]).

---

## 7. Decisioni chiuse (2026-07-09) → confluiscono nel brief DB Fase 1

Le tre decisioni aperte sono state chiuse con Tid (vedi A-1/A-2/A-3 in §1.1) e sono
il capitolato del `brief-db-ddt-vendita-evasione-e-stati.md`:

- **A-1 Multi-DDT = SÌ** → rimuovere la UNIQUE `uq_ddt_v_sorgente_fk` dalla testata
  (resta indice non-unique per lookup); unicità garantita dal fulfillment riga↔riga.
- **A-2 Copia snapshot ordine** → `fn_genera_ddt_da_ordine` copia prezzi/componenti
  dall'ordine, nessuna ri-risoluzione resolver.
- **A-3 Matrice con RESO** → `DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO` (+`ANNULLATO`)
  in `config.transizioni_stati_ddt`.

---

## 8. Riferimenti

- Tabelle: [/dbzero/vendite/tabelle/ddt](/dbzero/vendite/tabelle/ddt),
  [ddt_righe](/dbzero/vendite/tabelle/ddt_righe),
  [ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti),
  [ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment),
  [commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti).
- Funzioni: [fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare),
  [fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init),
  [fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine).
- Config/seed: `config.sorgenti` (id 8), `config.stati_doc_ddt`,
  `config.modalita_addebito_trasporto`, `config.causali_trasporto` (vuoto).
- Guide: [gestione-ordini §Fatturazione: ordine vs DDT](/guide/gestione-ordini),
  [gestione-commesse](/guide/gestione-commesse), [fatturazione](/guide/fatturazione).
- Design transiti: [genealogia](/dev/work-in-progress/brief-design-genealogia-transiti-vendite),
  [lineage DB](/dev/work-in-progress/brief-db-lineage-documenti-vendite).
- Codice: `backend/apps/vendite/services/commesse_source_handlers.py` (`HandlerDdt`),
  `backend/apps/vendite/db/ddt_repository.py` (minimale),
  `backend/apps/vendite/api/note_views.py` (note DDT da cablare).
</content>
</invoke>
