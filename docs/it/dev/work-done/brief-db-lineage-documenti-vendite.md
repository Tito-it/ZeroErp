# Brief DB — Vista di lineage dei documenti vendite (`vw_documento_lineage`)

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-09 · **Owner**: Tid
> **Design-of-record**:
> [brief-design-genealogia-transiti-vendite.md](brief-design-genealogia-transiti-vendite.md)
> (nodi, archi, decisioni G-1..G-11). **Gate**: BE/FE partono a viste applicate
> ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Natura**: **additivo, sola lettura** — nessun cambio al modello dati dei
> documenti (proiezione read-only, come i cruscotti fatturazione).
>
> **Aggiornamento nodo DDT (2026-07-13).** Alla stesura (09/07) il DDT era solo
> *predisposto*. Dal 10/07 la **slice DDT evasione è live**: esiste ora un **arco
> reale `Ordine → DDT`** (evasione ordine→DDT, multi-DDT). Va incluso alla
> costruzione della vista. Sorgente dell'arco: `vendite.ddt.sorgente_tipo_id`
> (= `ORDINE_VENDITA`) + `sorgente_uid` (= `ordini.uid`), indice
> `ix_ddt_v_sorgente`. Resta *predisposto/non attivo* solo l'arco **uscente**
> `DDT → Fattura differita` (la fattura differita da DDT non esiste ancora).
> Recepito nella tabella §2 (riga DDT) e nella nota §4 «DDT predisposto».

---

## ✅ STATO — DB COMPLETO (2026-07-15)

Il braccio **DB è chiuso, applicato e testato** su `dev/db-tid`. Deliverable:

- **Step 1 — Fondamenta** (`00_schema` `20260714-01..07`): colonne+seed `fase`/`is_abortito`
  su `stati_doc_ddt`/`stati_doc_fiscale`/`stati_doc_reso`/`stati_commessa` (`is_abortito`
  anche su `stati_doc_ordini`/`stati_doc_offerte`); scope `REVERSE_FLOW` + seed
  `config.sorgenti` `RESO_VENDITA(15)`.
- **Step 2–4 — Oggetti** (`20_code/vendite` `20260714-08..11`):
  `vw_documento_lineage_nodi` (dimensione nodo condivisa), `vw_documento_lineage_archi`
  (grafo archi A–H + R), `vw_documento_lineage` (summary: pratica + fase + frontiera
  forward con tie-break `pipeline_rank`), `fn_documento_lineage(tipo, uid, direzione)`
  (traversal avanti/indietro). Tutte `security_invoker=on`.
- **Step 5 — pgTAP**: `db/pgtap/vendite/test-documento-lineage-v1.sql` (`plan(26)`, verde).
- **Step 6 — Doc**: manuali concettuali dei 4 oggetti in `dbzero/vendite/manual/`.

Casi §5 validati sui dati reali (frontiera che segue la catena fino al nodo attivo più
profondo; genealogia inversa commessa → ROOT+COLLEGATO). **Downstream aperto**: BE/FE
(§7) — arricchimento liste + pannello "Passaggi".

---

## 0. Decisioni chiuse in analisi critica (2026-07-13)

Chiuse con Tid prima dello sviluppo; recepite nel piano §8.

- **Q1 — chiave nodo = chiave NATIVA polimorfa** (rivisto 2026-07-13). NON si
  "canonicalizza a uid": si usa la chiave che il sistema già parla,
  `(sorgente_tipo_id, sorgente_uid)` con `sorgente_uid` **secondo `config.sorgenti.key_selector`**
  (`uid` per preventivo/offerta, `id::text` per ordine/contratto/ddt/fattura/commessa/attività).
  È la stessa chiave di `pratiche_sorgenti`, `commesse_sorgenti`, `vw_stato_sorgente_*`
  → il grafo ci si aggancia senza tradurre e **senza toccare il modello**. Le sole
  **colonne tipizzate dirette** (`ddt.sorgente_uid`/`resi.sorgente_uid` uuid,
  `ordini.documento_origine_id`, `contratti.offerta_id`) si traducono su quella chiave
  con un join alla tabella target. **`key_selector` NON è un errore**: è portante
  (guard `trgfn_guard_sorgente_polimorfa` + resolver `vw_stato_sorgente_*`) — non
  ripulire. Convenzione + mappa + trappole: **`config.manual/sorgenti.md` §"Convenzione
  chiave sorgente"** (fonte di verità; leggere prima di ogni join tra documenti).
- **Q2 — colonna `fase` mancante**: `config.stati_doc_ddt`, `stati_doc_fiscale`,
  `stati_doc_reso` e `stati_commessa` **non hanno** la colonna `fase` (presente
  invece su preventivi/ordini/offerte/contratti). Si **aggiunge e si seeda** con la
  stessa scala ⚪APERTO/🔵IN_ATTESA/🟠IN_CORSO/🟢CHIUSO. → il brief non è più "solo
  vista": include un **seed fase** su questi cataloghi (comunque additivo).
- **Q3 — "attivo/abortito"**: non è un campo sul documento; è il flag `is_abortito`
  **sul catalogo stati**. La regola frontiera (fase ≠ CHIUSO ∧ ¬abortito) si legge
  da lì. Va garantita la presenza di `is_abortito` sui cataloghi attraversati
  (ddt/fiscale/reso/commessa): aggiungere+seed dove manca.
- **Q4 — Fattura è NODO** terminale del grafo (capolinea arco G): la frontiera può
  indicare «→ Fatturato / FT-xxxx». Non ha lista propria (nessuna colonna-lista).
- **Q5 — pratica 1:1 non garantita dal DB** (`pratiche_sorgenti` ammette più righe):
  default difensivo — si prende la pratica unica/attiva **+ si espone `n_pratiche`**
  (conteggio). *(default adottato; confermare in fase di build.)*
- **Resi = nodo "ramo inverso"** (2026-07-13, flusso LIVE): arco **`R` DDT → Reso
  (1:N)** — `vendite.resi.sorgente_tipo_id`(=DDT_VENDITA)/`sorgente_uid`(=`ddt.uid`),
  indice `ix_resi_sorgente`. Il reso **compare** nella genealogia (pannello
  "Passaggi") e nella sua lista (id 9), ma è **escluso dal calcolo della frontiera
  forward** (merce che torna, non avanzamento verso la fattura). Prerequisiti: seed
  `config.sorgenti` `RESO_VENDITA` (oggi assente) + `fase` su `config.stati_doc_reso`.
  Eventuali archi *uscenti* dal reso (riconsegna `resi_righe_riconsegne`, reso →
  nota di credito) si aggiungeranno poi con lo stesso meccanismo.
- **Liste che ricevono la colonna lineage**: **5** (preventivi, offerte, ordini,
  contratti, **DDT**) + follow-on lista commesse (§7.3); Fattura e Commessa restano
  **nodi** del grafo senza colonna-lista propria.

---

## 1. Scopo

Esporre il **grafo di genealogia/transito** dei documenti vendite come proiezione
read-only, per rispondere a due domande dalle liste:

1. a quale **pratica** (1:1) è collegato un documento;
2. **dove è transitato** e qual è il **documento più prossimo in esecuzione**
   (frontiera), più l'**elenco reale dei passaggi**.

Tutta la logica di grafo vive nel DB; il BE espone endpoint sottili; il FE rende.

## 2. Il grafo da modellare (dal design §3)

Archi (tutti già ricostruibili dal modello, nessun dato nuovo):

| # | Da → A | Card. | Fonte dell'arco |
|---|---|---|---|
| A | Preventivo → Ordine | 1:1 | `vendite.ordini.documento_origine_tipo='PREVENTIVO'/id` |
| B | Preventivo → Commessa | 1:1 | `vendite.commesse_sorgenti` (sorgente 2=PREVENTIVO) |
| C | Offerta → Contratto | 1:1 | `vendite.contratti.offerta_id` (/ `sorgente_uid`) |
| D | Offerta → Ordine | 1:1 | `vendite.ordini.documento_origine_tipo='OFFERTA'/id` |
| E | Ordine → Commessa | 1:1 | `vendite.commesse_sorgenti` (sorgente 6=ORDINE_VENDITA) |
| F | Contratto → Commessa | **1:N** | `vendite.commesse_sorgenti` (sorgente 4=CONTRATTO) |
| G | Commessa → Att. fatturabili → Fattura | 1:N | `commesse_attivita`/`attivita_fatturabili`/`fatture` |
| H | **Ordine → DDT** | **1:N** | `vendite.ddt.sorgente_tipo_id='ORDINE_VENDITA'/sorgente_uid` — **LIVE dal 10/07** (evasione, multi-DDT) |
| **R** | **DDT → Reso** (ramo **inverso**) | **1:N** | `vendite.resi.sorgente_tipo_id='DDT_VENDITA'/sorgente_uid` — **LIVE** (merce che torna). Nodo Reso incluso; **escluso dalla frontiera forward** (vedi §0). Prereq: seed `config.sorgenti` RESO_VENDITA + `fase` su `stati_doc_reso` |
| (P) | DDT → Fattura differita | *predisposto* | slot pronto (sorgente 8 come nodo), arco **uscente non attivo** (fattura differita da DDT futura) |

> **Nodo Fattura (Q4)**: la Fattura è nodo **terminale** del grafo (capolinea arco G,
> commessa → att. fatturabili → fattura). Ha `uid`; la sua `fase` arriva dal seed di
> Q2 su `stati_doc_fiscale`. La frontiera forward può quindi attestarsi su una fattura.

Vocabolario tipi: `config.sorgenti` (2 PREVENTIVO, 6 ORDINE_VENDITA, 4 CONTRATTO,
14 OFFERTA_COMMERCIALE, 13 COMMESSA, **8 DDT_VENDITA**). Chiave nodo consigliata:
`(sorgente_tipo_id, uid)` — `uid` UUID già presente su tutte le testate.

## 3. Cosa serve esporre

### 3.1 `vendite.vw_documento_lineage_archi` — vista ARCHI (grafo normalizzato)

Una riga per arco, uniforme e **bidirezionale per costruzione** (leggibile avanti
e indietro):

- `from_tipo_id, from_uid, from_codice`
- `to_tipo_id, to_uid, to_codice`
- `to_stato_codice, to_fase` (fase normalizzata del nodo target)
- `ruolo` (ROOT/COLLEGATO dove esiste, es. commesse_sorgenti)
- `arco` (A..G, per diagnostica)

È l'unione normalizzata degli archi A–G. Da qui derivano sia la summary sia il
traversal.

### 3.2 `vendite.vw_documento_lineage` — vista NODO/SUMMARY (per le liste)

Una riga per **documento** (le 4 aree + commesse), pensata per **arricchire le
liste** con un solo JOIN:

- chiave nodo: `tipo_id, uid, codice`
- **pratica**: `pratica_id, pratica_numero` (1:1, da `pratiche.pratiche_sorgenti`)
- **fase propria**: `fase` (dallo stato del documento)
- **frontiera** (documento più prossimo in esecuzione, avanti):
  `frontiera_tipo_id, frontiera_uid, frontiera_codice, frontiera_stato,
  frontiera_fase`
- `n_discendenti_diretti`, `n_discendenti_attivi` (per il fan-out F)
- `is_transitato` (ha almeno un discendente) e/o `is_transitato_completo`
- **inversa** (per la lista commesse, G-11): `n_sorgenti`, e/o la sorgente ROOT
  (`root_tipo_id, root_uid, root_codice`)

### 3.3 `vendite.fn_documento_lineage(p_tipo_id, p_uid, p_direzione)` — traversal (pannello "Passaggi")

Funzione ricorsiva (`WITH RECURSIVE` su `vw_documento_lineage_archi`) che ritorna
la **catena completa** con stati, per il pannello dettaglio. `p_direzione`:
`avanti` (documento → destinazioni, per le 4 liste) o `indietro` (commessa →
sorgenti, per la lista commesse). Ritorna livello/ordine per il rendering
timeline/albero.

## 4. Regole (dal design)

- **Frontiera** = discendente **più a valle ancora attivo** = fase ≠ `CHIUSO`
  **e** stato non ANNULLATO **e** non abortito (G-6/G-10). Traversal in avanti fino
  al nodo attivo più profondo.
- **Fan-out F** (contratto → N commesse): la summary espone la **commessa più
  prossima attiva** come frontiera (G-9); il conteggio (`n_discendenti_attivi`)
  segnala il fan-out; il traversal le elenca tutte.
- **Pratica 1:1** (G-1): un solo `pratica_numero` per documento; se il modello
  permettesse 0..N, prendere l'unica/attiva e (difensivo) esporre un conteggio.
- **Fase normalizzata**: riusare `config.stati_doc_*.fase` — **stessa scala** della
  Situazione aperta (⚪APERTO/🔵IN_ATTESA/🟠IN_CORSO/🟢CHIUSO). Per commessa/attività
  mappare a una fase coerente.
- **DDT nodo con arco entrante attivo** (G-4, agg. 2026-07-13): includere
  `DDT_VENDITA` come tipo-nodo **con l'arco reale `Ordine → DDT`** (evasione live
  dal 10/07, riga H §2). Resta senza arco **uscente** finché la fattura differita
  da DDT non esiste (nessun errore se 0 DDT). Un ordine può avere N DDT
  (evasione parziale/multipla): l'arco è 1:N, come Contratto→Commessa.
- **Scope emittente**: `security_invoker=on` sulle viste, come la famiglia
  `vw_dash_*` (RLS invoker; il BE non passa `auth_user_id`).

## 5. Dati di verifica (stato reale 2026-07-08/09, contesto RLS operatore)

Casi reali da usare come test di correttezza (super-admin per contesto RLS:
`SET app.ruolo_applicativo='OPERATORE'; SET app.current_user_id='1';`):

| Caso | Atteso |
|---|---|
| **PRV0000183** (EVASO, misto) | discendenti: **Ordine** + **Commessa 186**; frontiera = il più a valle attivo |
| **PRV0000184** (EVASO, servizi) | discendente: **Commessa 186** (arco B) |
| **PRV0000185** (EVASO, merce) | discendente: **Ordine ORD0000163 (DRAFT)** = frontiera; NESSUNA commessa (arco A) |
| **OFC-0000078** (ACCETTATA) | discendente: **Ordine ORD0000046** (arco D) |
| **Commessa 186** (inversa) | sorgenti: **PRV0000183 (ROOT) + PRV0000184 (COLLEGATO)** |
| Contratto con push ricorrente | **N commesse** (arco F 1:N): frontiera = commessa più prossima attiva |

Aggiungere **pgTAP**: presenza/forma delle 3 viste/fn, `security_invoker=on`, i casi
sopra, e l'invariante "frontiera sempre attiva (fase≠CHIUSO, non annullato/abortito)".

## 6. Note

- Le viste `vendite.vw_stato_sorgente_{preventivo,offerta,ordine,contratto}`
  esistenti già proiettano lo stato a valle di una sorgente: valutarne il riuso
  come mattoni della `vw_documento_lineage_archi`.
- Prestazioni: il traversal della frontiera è ricorsivo ma su catene corte
  (≤ ~5 hop); indicizzare i join sugli archi (`documento_origine_id`,
  `commesse_sorgenti.sorgente_uid`, `contratti.offerta_id`).
- Nessuna azione distruttiva; tutto additivo (`runOnChange` per le viste/fn con
  numerazione progressiva, [[feedback_db_actions_passaggio_team]]).

## 7. Downstream (dopo le viste)

BE: arricchimento delle 4 liste vendite (+ lista commesse) con `pratica_numero` +
`fase` + frontiera; endpoint dettaglio "Passaggi" per documento. FE: colonna
lista (pratica cliccabile + fase riusata + chip frontiera) + pannello "Passaggi".
Dettaglio nel design-of-record §7 e §10.
