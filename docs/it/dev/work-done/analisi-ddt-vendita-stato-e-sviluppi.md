# Analisi — DDT di vendita: stato attuale e piano di sviluppo

> **Tipo**: analisi + piano (da cui nascono i brief DB/BE/FE) · **Data**: 2026-07-09
> · **Owner**: Tid · **Target sviluppo**: DB (`dev/db-tid`) → BE/FE (`dev/backend-tid`).
> **Natura**: attivazione di uno *slot predisposto*, non fondazione da zero.
>
> **Vedi anche**:
> [Gestione Ordini](/guide/gestione-ordini) ·
> [Gestione Commesse](/guide/gestione-commesse) ·
> [Fatturazione end-to-end](/guide/fatturazione) ·
> [Genealogia & transiti vendite](/dev/work-done/brief-design-genealogia-transiti-vendite) ·
> [Lineage documenti vendite (brief DB)](/dev/work-done/brief-db-lineage-documenti-vendite) ·
> [Analisi ordini vendita](/dev/work-done/analisi-ordini-vendita) ·
> [Analisi commesse — stato e sviluppi](/dev/work-done/analisi-commesse-stato-e-sviluppi)

---

> ## 🟢 CHIUSA — 2026-08-05
>
> **Tutte e sei le fasi del §6 sono fatte**, comprese le due che questo documento
> ha portato aperte fino a oggi (Fase 4 lineage e slice RESI): erano state
> realizzate dentro altri cantieri e nessuno era tornato a spuntarle qui.
> Verifica del 2026-08-05 misurata sul database dal canale di sistema e sul
> codice, non dedotta dai documenti.
>
> | Fase | Stato | Rif. |
> | --- | --- | --- |
> | **1 — DB** (evasione + stati + gap + predisposizione PDF) | ✅ FATTO | [brief DB](brief-db-ddt-vendita-evasione-e-stati.md) |
> | **2 — BE** (service/repo/endpoint + evasione + push + note) | ✅ CHIUSO (11-13/07) | [brief BE](brief-be-ddt-vendita.md) §12–14 |
> | **3 — FE** (lista + drawer + evasione + navigazione) | ✅ CHIUSO (12-13/07) | [brief FE](brief-fe-ddt-vendita.md) §11–13 |
> | **3-bis — Standalone** (DDT senza sorgente, billing proprio) | ✅ FATTO | incluso in BE/FE |
> | **5 — PDF** (stampa DDT + valuta/emittente drawer + PDF data-driven capabilities) | ✅ FATTO (2026-07-11) | [[handoff_20260711_ddt_stampa_orfano_refactor]] |
> | **4 — Lineage** (accensione nodo DDT in `vw_documento_lineage`) | ✅ **FATTO** (verificato 2026-08-05) | §9.1 |
>
> **Slice minori** — tutte chiuse: editing `ddt_indirizzi` (✅ UX v2 pilota DDT +
> rollout 5 domini, 2026-07-12, brief design indirizzi §7), riepilogo IVA DDT
> (✅ 2026-07-12), export lista DDT (✅ 2026-07-11), colonna "Emittente" a
> catalogo (✅ 2026-07-12, brief
> [brief-db-ddt-colonna-emittente-catalogo](brief-db-ddt-colonna-emittente-catalogo.md)),
> PDF DDT con indirizzo di consegna (✅ 2026-07-12). **Slice RESI: ✅ chiusa**
> (§9.2). **Verifica visiva in-app** ✅ Tid (2026-07-13).
>
> ⚠️ La riga «tutto il lavoro FE/BE è su `dev/backend-tid` non committato» è
> **superata**: è mergiato da luglio. Restava scritta perché il documento si era
> fermato al 2026-07-13.
>
> **Un residuo, e non è quello che sembrava.** Scrivendone il manuale il team DB
> ha misurato `mv_ddt_ordini`: non le manca solo la pagina, è **un oggetto morto**
> — 0 righe, nessun lettore, nessun percorso che la aggiorni. Il livello 3 del
> §3.1 non ha mai funzionato, e gli altri due bastano. Raccomandazione:
> **ritirarla** — §9.4.
>
> ---

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
   🔴 **Questo livello non ha mai funzionato** (misurato il 2026-08-05): la MV è
   vuota e nessuno la aggiorna né la legge — vedi §9.4. I consumatori reali usano
   il livello 1 (il lineage, via `sorgente_uid`) e il livello 2 (il backend, che
   interroga `ordini_righe_fulfillment` direttamente). Raccomandazione: ritirarla.

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

Il grafo dei transiti ([genealogia](/dev/work-done/brief-design-genealogia-transiti-vendite))
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
- Design transiti: [genealogia](/dev/work-done/brief-design-genealogia-transiti-vendite),
  [lineage DB](/dev/work-done/brief-db-lineage-documenti-vendite).
- Codice: `backend/apps/vendite/services/commesse_source_handlers.py` (`HandlerDdt`),
  `backend/apps/vendite/db/ddt_repository.py` (minimale),
  `backend/apps/vendite/api/note_views.py` (note DDT da cablare).

---

## 9. Verifica di chiusura (2026-08-05)

> Misurata sul database dal canale di sistema (`system_process_context`: le
> tabelle documento hanno RLS, e senza GUC si legge zero e si conclude il falso)
> e sul codice. Le tabelle del §2 restano com'erano: sono la fotografia
> pre-sviluppo e non vanno riscritte, si legge questa sezione accanto.

### 9.1 Fase 4 — il nodo DDT nel lineage è acceso

| Prova | Esito |
| --- | --- |
| nodi in `vw_documento_lineage` | **29 DDT_VENDITA** (e 10 RESO_VENDITA) |
| view API | `ApiDdtPassaggi` e `ApiResoPassaggi` montate dalla factory `build_passaggi_view`, accanto agli altri cinque domini |
| frontend | lineage cablato in `DdtDrawer.vue` e `DdtSearchTable.vue` |

La fase era stata realizzata dentro il cantiere lineage, che ha acceso tutti i
nodi insieme invece che uno per volta: da qui la spunta mai riportata.

### 9.2 Slice RESI — chiusa

Tre brief in `work-done` (`brief-db-resi-vendita`, `brief-be-fe-resi-vendita`,
`brief-be-fe-ddt-resi-dashboard`), dominio frontend `vendite/resi` con rotta e
voce di navigazione, 10 nodi `RESO_VENDITA` nel lineage.

### 9.3 I gap del §2.1, ricontrollati uno per uno

| Voce del §2.1 | Allora | Oggi |
| --- | --- | --- |
| `fn_genera_ddt_da_ordine` | ❌ MANCANTE | ✅ esiste |
| `config.transizioni_stati_ddt` | ❌ MANCANTE | ✅ 9 righe |
| seed `config.causali_trasporto` | ⚠️ VUOTO | ✅ 8 righe (`aspetti_beni`: 10) |
| `trgfn_ddt_guard_transizione_approvazione` | ⚠️ NON WIRED | ✅ `trg_ddt_a10_guard_transizione_upd` |
| `trgfn_ddt_normalize` risolve per `codice` | ⚠️ FRAGILE | ✅ usa `codice_interno` |
| manual `ddt.md` con colonne inesistenti | ⚠️ STALE | ✅ corretto |
| doc MV `mv_ddt_ordini` | ⚠️ STALE | 🔴 **ancora assente** → §9.4 |

Anche il §2.3 («FE inesistente») è superato per intero: dominio, rotta, voce di
navigazione, e persino l'icona `app-nav-icon-ddt` che allora era definita e
inutilizzata ora è agganciata in `navigation.js`.

### 9.4 🔴 `mv_ddt_ordini` non è un buco di documentazione: è un oggetto morto

> ⚠️ **Correzione del 2026-08-05 (sera).** Questo paragrafo diceva «manca solo la
> pagina» e «la MV è viva». **Era sbagliato**, ed è istruttivo come: l'avevo
> dedotto dall'esistenza dell'oggetto (`relkind = 'm'`) senza guardarci dentro.
> Scrivendone il manuale, il team DB ha misurato il contenuto e ha trovato altro.

| Domanda | Risposta misurata (team DB, 2026-08-05) |
| --- | --- |
| righe contenute adesso | **0** |
| righe che la sua query produrrebbe | **15** |
| chi la legge | **nessuno** — l'unica citazione in `fn_genera_ddt_da_ordine` è dentro un commento |
| chi la aggiorna | `dbops.fn_refresh_mv_ddt_ordini`, che **nessuno chiama**: né una funzione, né un job pgagent |

Non è una vista rotta: è una vista **mai agganciata**, ferma allo stato in cui è
nata e destinata a restarci, perché non esiste un percorso che la aggiorni. Il
pgTAP `test-ddt-gate-emissione-mv-v1.sql` è verde ma esegue **lui stesso** il
`REFRESH`: prova che il meccanismo funziona, non che qualcuno lo azioni.

**Verifica applicativa (BE/FE, 2026-08-05)** — conferma il quadro dall'altro lato:

* `mv_ddt_ordini` e `fn_refresh_mv_ddt_ordini`: **zero occorrenze** in tutto il
  backend e il frontend. Nessuna vista del database la usa;
* il legame ordine↔DDT è **già derivato altrove, e funziona**: il backend
  interroga `ordini_righe_fulfillment` direttamente
  ([`ordini_repository.py:336`](../../../../backend/apps/vendite/db/ordini_repository.py#L336),
  `resi_repository.py:876`), cioè il **livello 2** del §3.1;
* il **lineage non la usa**: l'arco Ordine→DDT si regge su `sorgente_uid`, cioè
  il **livello 1**. Nessun rischio nascosto sulla genealogia, che è il consumatore
  più visibile di questo legame.

**Ne discende una raccomandazione, non una scelta aperta: ritirarla.** Delle tre
strade del §3.1 per legare ordine e DDT, le prime due sono vive e usate da
consumatori reali; la terza — questa MV — è ridondante rispetto a entrambe.
Agganciare il refresh significherebbe pagare una manutenzione per un fatto che
l'applicazione già ricava in due modi diversi. È la seconda delle due strade
oneste indicate dal DB («il giro diretto sulla tabella basta»), e il codice vivo
l'ha già scelta da sé.

⚠️ **La cosa da non fare** — parole del team DB, che vale la pena ripetere:
leggerla un giorno credendola aggiornata. Risponderebbe «questo DDT non ha
ordini» **con la stessa sicurezza con cui direbbe il vero**. È il difetto
peggiore di tutti, perché non somiglia a un errore.

Materiale per il cantiere dei riferimenti morti
([brief-be-bonifica-riferimenti-morti](brief-be-bonifica-riferimenti-morti.md)).
⚠️ Se si ritira, cadono con lei tre cose: la MV, `dbops.fn_refresh_mv_ddt_ordini`
e il pgTAP che le testa — più la riga «livello 3» del §3.1 di questa analisi, che
descrive un meccanismo che non ha mai funzionato.

### 9.5 ⚠️ Una cosa che i documenti non dicono: il transito non è mai stato percorso

Il meccanismo c'è tutto, ma **il percorso DDT → commessa → fattura è stato
attraversato una volta sola** nei dati di sviluppo:

| Misura | Valore |
| --- | --- |
| ordini per `fatturazione_trigger` | **89 su 89 = `CONFERMATO`** |
| righe `commesse_sorgenti` di tipo DDT_VENDITA | **1** |
| DDT nati da un ordine / righe di evasione | 15 / 20 |

Non è un difetto e non contraddice la chiusura: è la **regola XOR del §3.3** che
si vede nei dati — con `CONFERMATO` è l'ordine a pushare, e nessun ordine usa
ancora la fatturazione differita. L'evasione ordine→DDT è esercitata (15 DDT, 20
righe di fulfillment); è il transito a valle, cioè la ragione per cui questo
cantiere esiste (§3.2), ad avere un solo passaggio all'attivo.

⚠️ **Quindi il primo ordine messo a `SPEDITO` o `CONSEGNATO` è il caso da
guardare per primo**: sarà il primo giro reale su un percorso che finora ha visto
un solo documento.
