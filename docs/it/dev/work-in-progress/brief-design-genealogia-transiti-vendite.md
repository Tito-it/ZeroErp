# Brief Design — Genealogia & transiti dei documenti vendite (nr. pratica + stato di transito nelle liste)

> **Tipo**: brief di design · **Data**: 2026-07-08 · **Owner**: Tid
> **Target sviluppo**: DB (`dev/db-tid`) → BE/FE (`dev/backend-tid`).
> **Origine**: discussione Tid 2026-07-08 — le liste vendite non dicono *dove è
> finito il lavoro* di un documento né *quale pratica lo orchestra*. Mappa dei
> transiti ricostruita dal modello vivo e validata con Tid.
>
> **Vedi anche**:
> [Gestione Preventivi](/guide/gestione-preventivi) ·
> [Offerte commerciali](/guide/gestione-offerte-commerciali) ·
> [Gestione Ordini](/guide/gestione-ordini) ·
> [Gestione Contratti](/guide/gestione-contratti) ·
> [Gestione Commesse](/guide/gestione-commesse) ·
> [Fatturazione end-to-end](/guide/fatturazione) ·
> [Cruscotti fatturazione](/guide/cruscotti-fatturazione) (riusa la stessa fase normalizzata)

---

## 1. Il problema

Oggi, guardando una lista di vendite (preventivi, ordini, offerte, contratti),
l'operatore **non sa**:

1. se il documento è **collegato a una pratica** (workflow) e quale;
2. se e **dove è transitato** a valle — il suo lavoro è ancora sul documento, o è
   già diventato un ordine / una commessa / una fattura? E **dov'è adesso** il
   fronte del lavoro?

Il modello **contiene già** tutta l'informazione (chi ha generato chi), ma è
sparsa fra tabelle di link e non è esposta alle liste.

## 2. Le due richieste (Tid)

- **R1 — nr. pratica collegato in lista**: mostrare, se presente, il numero della
  pratica che orchestra il documento. Legame **1:1** (deciso: una pratica genera
  al più un preventivo / un'offerta / un ordine / un contratto).
- **R2 — stato di transito**: rendere visibile, dalla lista, se il documento ha
  transitato e **verso quale documento più prossimo in esecuzione**; e, entrando
  nel singolo movimento, mostrare l'**elenco reale dei passaggi**.

Entrambe sono **due proiezioni della stessa cosa**: la *genealogia* del documento
(il grafo dei transiti + il link pratica). Si progetta il grafo una volta, le due
richieste sono due render.

## 3. La mappa dei transiti (validata sul modello vivo)

Vocabolario tipi-sorgente: `config.sorgenti` (2=PREVENTIVO, 6=ORDINE_VENDITA,
4=CONTRATTO, 14=OFFERTA_COMMERCIALE, 13=COMMESSA, **8=DDT_VENDITA** predisposto,
1=ATTIVITA).

### 3.1 Nodi (documenti) — fase normalizzata riusata dalla Situazione aperta

| Documento | Stati → fase (⚪APERTO 🔵IN_ATTESA 🟠IN_CORSO 🟢CHIUSO) |
|---|---|
| Preventivo | DRAFT⚪ · EMESSO🔵 · ACCETTATO🟠 · RIFIUTATO/SCADUTO/ANNULLATO/EVASO🟢 |
| Offerta | BOZZA⚪ · EMESSA🔵 · ACCETTATA🟠 · RIFIUTATA/SUPERATA/ANNULLATA🟢 |
| Ordine | DRAFT⚪ · CONFERMATO/ALLOCATO/SPEDITO/CONSEGNATO🟠 · ANNULLATO/FATTURATO/EVASO🟢 |
| Contratto | DRAFT⚪ · ATTIVO🟠 · CESSATO/ANNULLATO🟢 |

### 3.2 Archi (chi genera chi)

| # | Da → A | Cardinalità | Meccanismo |
|---|---|---|---|
| A | Preventivo → **Ordine** | 1:1 (parte merce) | smistamento (`righe merce → ordine`) |
| B | Preventivo → **Commessa** | 1:1 (parte servizi) | smistamento (`servizi una-tantum → commessa`) |
| C | Offerta → **Contratto** | 1:1 | accettazione offerta (ricorrente) |
| D | Offerta → **Ordine** | 1:1 | accettazione offerta (una-tantum / merce) — **confermato** |
| E | Ordine → **Commessa** | 1:1 | "invio a commessa dell'ordine merce confermato" |
| F | Contratto → **Commessa** | **1:N** | push ricorrente (una commessa per periodo) |
| G | Commessa → **Att. fatturabili → Fattura** | 1:N | emissione + pipeline fatturazione |
| (P) | **DDT_VENDITA** → Commessa/Fattura | *predisposto* | fattura differita — **slot pronto, non attivo** |

```text
                       ┌── merce ────> ORDINE ──conferm.──> COMMESSA ─┐
   PREVENTIVO ─split──>┤                                              ├─> ATT.FATT ─> FATTURA
                       └── servizi ─────────────────────> COMMESSA ─┘
   OFFERTA ──accett.──> CONTRATTO ══ ricorrente (1:N) ══> COMMESSA ──┘
           └─una tantum─> ORDINE ──> COMMESSA ─┘
   (DDT_VENDITA) ┈┈ predisposto (fattura differita) ┈┈> COMMESSA/FATTURA
```

### 3.3 Fuori perimetro

- **Ramo logistico dell'ordine** (ALLOCATO → SPEDITO → CONSEGNATO → DDT logistico):
  non è asse fatturazione.
- **DDT non-vendita** (trasferimento, conto lavorazione, reso, campioni): nessuna
  fatturazione. Un DDT **non genera mai un ordine** (o l'ordine genera il DDT, o il
  DDT standalone salta l'ordine verso la fattura differita).

## 4. Modello dati riusato (niente dato nuovo)

Il grafo è interamente ricostruibile da:

- `vendite.vw_stato_sorgente_{preventivo,offerta,ordine,contratto}` — stato
  proiettato a valle della sorgente;
- `vendite.commesse_sorgenti` (`sorgente_tipo_id`/`sorgente_uid`/`ruolo_link`) —
  archi verso commessa;
- `vendite.ordini.documento_origine_tipo/id` — archi preventivo/offerta → ordine;
- `vendite.contratti.offerta_id` / `sorgente_uid` — arco offerta → contratto;
- `pratiche.pratiche_sorgenti` (`sorgente_tipo_id`/`sorgente_uid`) — link **1:1**
  documento ↔ pratica;
- `config.sorgenti` — vocabolario (include già `DDT_VENDITA` id 8).

## 5. Concetti chiave del design

- **Frontiera** = "documento più prossimo in esecuzione" = il **discendente più a
  valle ancora attivo** — fase ≠ 🟢 CHIUSO **e non ANNULLATO/abortito** (G-10).
  Nelle catene lineari è univoca (Preventivo → **Ordine ORD0000163 (DRAFT)**).
  L'arco **F** (contratto → N commesse) è l'unico fan-out: in lista si mostra la
  **commessa più prossima attiva** (G-9); il pannello "Passaggi" le elenca tutte.
- **Fase normalizzata riusata** dalla Situazione aperta (`faseDocumentoSeverity`):
  una sola scala di stato in tutta l'app (omogeneità UI).
- **Pratica 1:1**: numero singolo, non ambiguo, cliccabile per aprire la pratica.
- **DDT predisposto**: `DDT_VENDITA` è già un tipo-sorgente; la lineage prevede lo
  **slot** ma il DDT resta vuoto finché la fattura differita non è implementata
  (concentrico, no-YAGNI: un nodo in più non rifà il modello).

## 6. Backbone DB-first — vista di lineage unificata

Una **vista** (es. `vendite.vw_documento_lineage`) come **single source of truth**
del grafo, che per ogni documento (le 4 aree + estensibile a DDT) espone:

- il **link pratica** (numero, id) da `pratiche_sorgenti`;
- i **discendenti diretti** (tipo, codice, stato, fase, data) — 0..N;
- la **frontiera** (discendente più a valle attivo) — 1 valore o insieme per il
  fan-out F;
- un flag/segnale di **transito** (ha discendenti? completamente transitato?).

La vista è **bidirezionale** (G-11): lo stesso grafo letto **in avanti** (documento
→ destinazioni) e **all'indietro** (commessa → sorgenti che l'hanno generata).
Costa ~zero al DB (sono gli stessi archi).

Tutta la logica di grafo vive **nel DB**; BE espone endpoint sottili; FE rende.
La vista è materia del **team DB** (regola azioni DB).

## 7. Le due feature FE (render sottili)

### 7.1 Colonna lista (R1 + R2 compatto) — sulle 4 liste vendite

Due-tre segnali per riga, dalla lineage view:

- **Pratica**: numero cliccabile (1:1), "—" se assente;
- **Fase** propria del documento (Tag + `faseDocumentoSeverity`);
- **Transito / frontiera**: chip col documento a valle più prossimo in esecuzione
  — es. `→ Ordine ORD0000163 · DRAFT`; per il fan-out F → `→ N commesse (ultima …)`;
  "—" se non ancora transitato.

### 7.2 Pannello "Passaggi" nel drawer (R2 dettaglio)

Nel drawer del singolo documento, un'area **"Passaggi / Genealogia"**: la **catena
reale** dei transiti con i loro stati (documento → ordine → commessa → att.
fatturabile → fattura), come timeline/albero. Per il fan-out (contratto → N
commesse) è semplicemente una **lista di N righe**. Zero dati persi, resa uniforme.

### 7.3 Lista commesse — genealogia inversa (follow-on)

Sulla lista commesse la stessa lineage letta **all'indietro**: la commessa mostra
le **sorgenti** che l'hanno generata (es. `commessa 186 ← PRV0000183, PRV0000184`),
e il pannello "Passaggi" ne elenca l'origine. **Follow-on immediato** dopo le 4
liste documento (non fase 2 lontana) — la vista bidirezionale lo rende quasi
gratis (G-11).

## 8. Decisioni prese (con Tid, 2026-07-08)

| # | Decisione |
|---|---|
| G-1 | Pratica ↔ documento **1:1** (una pratica genera al più un documento delle 4 aree) |
| G-2 | Arco **D (Offerta → Ordine)** confermato come path di design (offerta una-tantum/merce) |
| G-3 | Arco **F (Contratto → Commessa) 1:N** — unico fan-out; aggregato in lista, esploso nel pannello |
| G-4 | **DDT predisposto**: `DDT_VENDITA` slot-sorgente pronto, non attivo (fattura differita futura) |
| G-5 | **Fuori perimetro**: ramo logistico ordine + DDT non-vendita; DDT non genera mai un ordine |
| G-6 | **Frontiera** = discendente più a valle con fase ≠ CHIUSO |
| G-7 | **Riuso** della fase normalizzata (Situazione aperta) come stato in lista |
| G-8 | **Backbone DB-first**: una lineage view unica; FE render sottili |
| G-9 | **Fan-out F in lista**: si mostra la **commessa più prossima attiva** (non l'ultima); il pannello le elenca tutte |
| G-10 | **Frontiera "attivo"**: discendente con fase ≠ CHIUSO **e** non ANNULLATO/abortito |
| G-11 | **Lineage bidirezionale**: vista unica letta avanti (documento→destinazioni) e indietro (commessa→sorgenti). FE prima 4 liste, poi lista commesse (follow-on) |

## 9. Invarianti / non-obiettivi

- **Nessuna logica di grafo nel FE**: la lineage vive nel DB (proiezione read-only).
- **DDT fatturazione non implementata**: solo lo slot-sorgente predisposto.
- **DDT logistico / non-vendita**: fuori dall'asse fatturazione.
- Non si tocca il modello dati dei documenti: la lineage è **additiva** (una vista).

## 10. Piano di sviluppo (concentrico)

1. **DB** — `vw_documento_lineage` (grafo + frontiera + link pratica), su
   `vw_stato_sorgente_*` + link. Prerequisito, → team DB (brief DB dedicato).
2. **BE** — endpoint sottili: colonna lista (arricchimento delle 4 liste con
   pratica/fase/frontiera) + dettaglio passaggi per documento.
3. **FE-a** — colonna lista (pratica cliccabile + fase riusata + chip frontiera)
   sulle 4 liste vendite.
4. **FE-b** — pannello "Passaggi" nel drawer dei 4 documenti.
5. **FE-c** — lista **commesse** con genealogia inversa (sorgenti) — follow-on
   immediato (stessa vista letta all'indietro).

## 11. Punti chiusi (2026-07-08/09)

- **Fan-out F in lista** → **commessa più prossima attiva** (G-9).
- **Quali liste** → 4 liste documento (avanti) + **lista commesse** con genealogia
  inversa come **follow-on**; vista DB **bidirezionale** (G-11).
- **"Attivo" per la frontiera** → fase ≠ CHIUSO **e** non ANNULLATO/abortito (G-10).

Tutti i punti sono chiusi → design fissato, si passa al **brief DB** della
`vw_documento_lineage`.
