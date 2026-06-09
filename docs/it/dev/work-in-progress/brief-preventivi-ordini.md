# Brief — `preventivo → ordine`: modello a split di riga (NON 1:1 di testata)

> **Stato**: 🟢 **RAMO ORDINE IMPLEMENTATO A DB (2026-06-09)**. Le decisioni (§0)
> sono chiuse; il ramo merce→ordine è a terra e testato. Restano fuori scope DB
> l'orchestratore `CONFERMA_VENDITA` (BE), il gate EVASO (BE, primitiva DB pronta)
> e il filtro catalogo FE/BE. Dettaglio in §8 (log implementazione).
>
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data**: 2026-06-07 — decisioni ratificate 2026-06-08 — DB implementato 2026-06-09.
>
> **Perché esiste questo documento**: durante l'analisi dell'univocità
> offerta→ordine ([brief-db-univocita-offerta-ordine.md](../work-done/brief-db-univocita-offerta-ordine.md))
> è emerso che il preventivo **non** segue lo stesso modello dell'offerta. Tid ha
> ricordato che *«non era previsto che il preventivo diventasse ordine ma
> direttamente commessa»* — ed è confermato dal design iniziale: il preventivo va
> **smistato per riga** verso 0..N destinazioni (ordine, commessa, contratto),
> orchestrato dalla pratica. Mettere un UNIQUE 1:1 di testata sul preventivo
> **murerebbe** questo modello. Da qui un documento separato.
>
> **Fonte autorevole del modello**:
> [analisi-pratiche-domini-anello3.md §5.3](analisi-pratiche-domini-anello3.md)
> (flusso `CONFERMA_VENDITA`).

---

## 0. Decisioni ratificate (Tid, 2026-06-08)

Tutte verificate contro lo schema attuale. **Stato implementazione: ramo ordine a
DB (2026-06-09), vedi §8.** Restano da fare l'orchestratore `CONFERMA_VENDITA` e
il gate EVASO (lato BE). La UNIQUE parziale **offerta**
(`uq_ordini_v_documento_origine_offerta`) è il modello *opposto* e **non** si
replica sul preventivo (sul preventivo l'idempotenza è di riga, §3).

| # | Tema | Decisione |
| --- | --- | --- |
| **D1** | Livello idempotenza | **RIGA** (non testata): ogni riga di preventivo → max 1 ordine; un preventivo genera **0..N ordini** via smistamento incrementale. **Supera anello3 §5.3.3** (UNIQUE di testata su `sorgente_uid`), che è incoerente con §5.3.1/§5.3.2 della stessa anello3. |
| **D2** | Tappabuchi attuale | **Disabilitare** il bottone copia-tutto `crea_ordine_da_preventivo` (modello sbagliato 1:1 di tutte le righe). Endpoint/servizio BE restano dormienti. *Non implementato in questo giro* (è un brief DB). **Nota design:** nella modalità split "copia tutto" torna come **utility UI** (preseleziona tutte le righe = `p_righe_ids` = tutte), non come azione separata. |
| **D3 (A)** | Natura di riga | Nuova **`config.nature_vendita`** (`MERCE` / `SERVIZIO_UNA_TANTUM` / `SERVIZIO_RICORRENTE`), dedicata al routing — niente riuso di `listino_tipologia` (anello3 §5.3.2). La natura è **proprietà intrinseca dell'articolo**: `catalogo.articoli.natura_vendita_id` **obbligatoria** (NOT NULL + backfill articoli esistenti). La riga di preventivo la **eredita e congela** (snapshot all'inserimento, come i prezzi). **Nessun override operatore** (protezione da errore umano sullo smistamento). Articolo senza natura → non smistabile: la NOT NULL su articoli lo previene a monte. |
| **D4 (B)** | Accoppiamento pratica | **`p_pratica_id` opzionale** (NULL ammesso): la fn crea ordine + link riga + idempotenza standalone, e aggancia `pratiche_sorgenti` **solo se** la pratica esiste. → ramo ordine **spedibile a DB subito**, prima dell'engine `CONFERMA_VENDITA`. |
| **D5 (C)** | Riga già allocata | **Skip** silenzioso delle righe già allocate (l'ordine si crea con le sole residue); **errore semantico solo se TUTTE** già allocate. Più ergonomico del "errore propagato" di anello3 v1. |
| **D6 (D)** | Stato `EVASO` | Ridefinito **"nessun residuo smistabile"** (qualunque destinazione), resta terminale. Correggere `push_a_commessa`: **non** evade più se restano righe-merce non portate a ordine (oggi lo fa — incoerenza da chiudere). |
| **D7 (E)** | Link di riga | **FK tipizzata** `vendite.ordini_righe.preventivo_riga_id` → `vendite.preventivi_righe` + **UNIQUE parziale** (àncora hard dell'idempotenza). Testata resta polimorfica `documento_origine_*` per la provenienza. Asimmetria voluta: link di riga è solo-preventivo, testata è multi-sorgente. |
| **D8 (F)** | Scope v1 | Solo **ramo ordine**. `push_a_commessa` esiste già; ramo **contratto NON esiste sul preventivo** (vedi D9). |
| **D9** | Natura ricorrente sul preventivo | **MODALITÀ A — blocco vero (ratificata Tid 2026-06-09).** Un articolo la cui natura ha `destinazione_tipo = 'CONTRATTO'` (oggi `SERVIZIO_RICORRENTE`) **non può essere messo su un preventivo**: la ricorrenza viaggia solo su **offerta→contratto**. Blocco **fail-fast all'inserimento riga** (trigger `trgfn_preventivi_righe_set_natura_vendita`, guard data-driven su `destinazione_tipo`), **non** a CONFERMA, con `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`. Scartata la modalità B (ricorrente come destinazione valida ma «non smistata automaticamente» di anello3 §5.3.1). Difesa in profondità: + filtro catalogo BE/FE (non propone nature CONTRATTO sul preventivo) — fuori scope DB. Supera la prosa di anello3 §5.3.1/§5.3.2 (smistamento manuale / override operatore). |

**Conseguenza sulla capability:** `genera_ordine` (o "smista vendita") appare su
`fn_available_actions_preventivo` finché **restano righe di natura `MERCE` non
ancora allocate** (residuo a livello riga, non "esiste un ordine").

> anello3 §5.3.3 va marcata **deprecata** (idempotenza di riga, non di testata) e
> il substrato colonne va allineato al reale `documento_origine_*` — non al
> `sorgente_tipo_id`/`sorgente_uid` di anello3, mai implementato. Da riportare in
> anello3 quando si riapre quel documento.

---

## 1. Il bug attuale e lo stato di fatto (verificato)

Stesso sintomo dell'offerta: da un preventivo `ACCETTATO`, premere "Genera
ordine" più volte crea ordini duplicati, senza errore.

Ma il codice attuale è un **tappabuchi** che *contraddice* il design:

- [`crea_ordine_da_preventivo`](../../../../backend/apps/vendite/services/ordini_service.py)
  controlla solo `stato = ACCETTATO` e **copia in blocco tutte le righe attive**
  (rename `sconto_percentuale`→`sconto_perc`, componenti BoM re-init). Endpoint
  `POST /api/v1/vendite/preventivi/<id>/genera-ordine/`. Non passa per la
  pratica, non smista per natura, non registra `pratiche_sorgenti`. (Realizzato
  2026-06-04, vedi [analisi-ordini-vendita.md §7.4](analisi-ordini-vendita.md).)
- Il bottone "Genera ordine" è **hardcoded** su `stato = ACCETTATO` in
  [`PreventiviDrawer.vue`](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue).
- `documento_origine` su `vendite.ordini` è **senza UNIQUE** (A1).

Verificato che il modello previsto **non è implementato**:

- `vendite.fn_push_preventivo_a_ordine` **non esiste** a DB (solo progettata).
- Il flusso `CONFERMA_VENDITA` / handler `vendita.push_preventivo` / lo split per
  natura di riga **non sono cablati** nel BE (nessun riferimento in `apps/`).

Esiste invece già la strada **preventivo → commessa**:
[`preventivi_service.push_a_commessa`](../../../../backend/apps/vendite/services/preventivi_service.py),
che a push completato porta il preventivo `ACCETTATO → EVASO` (stato terminale).

## 2. Il modello previsto (design iniziale — anello3 §5.3)

Una volta accettato dal cliente, il preventivo viene tradotto dal flusso
`CONFERMA_VENDITA` (handler `vendita.push_preventivo`) in **destinazioni
operative**, **smistando le righe per natura**:

```
                         ┌── righe MERCE ───────────→ ORDINE   (fn_push_preventivo_a_ordine)
preventivo ACCETTATO ────┴── righe SERVIZIO una-tantum → COMMESSA (push_a_commessa, già esistente)

   righe RICORRENTI ──✗── NON AMMESSE sul preventivo (bloccate all'inserimento, D9)
                          → la ricorrenza si avvia da offerta→contratto, non da preventivo
```

> **Modalità A (D9):** il ramo CONTRATTO **non parte dal preventivo**. Un articolo
> ricorrente non può proprio entrare in una riga di preventivo (blocco a monte,
> all'inserimento). Le sole destinazioni del preventivo sono ORDINE e COMMESSA.

Caratteristiche chiave del modello (testuali dal documento):

- **Una sorgente, 0..N destinazioni** — ciascuna corrisponde al **sottoinsieme
  di righe** del preventivo con natura corrispondente. Le destinazioni del
  preventivo sono **ORDINE e COMMESSA**: il CONTRATTO è escluso a monte (D9, le
  righe ricorrenti non entrano nel preventivo). La frase di anello3 *"nessuna
  destinazione è speciale"* va letta in questo perimetro ristretto.
- Funzione DB prevista (*"da scrivere"*):
  `vendite.fn_push_preventivo_a_ordine(p_preventivo_id, p_righe_ids, p_pratica_id, p_fatturazione_trigger)`
  — copia **il sottoinsieme di righe** (`p_righe_ids`) e componenti BoM
  mantenendo lo snapshot prezzi, e registra il legame in `pratiche_sorgenti`.
- Il preventivo passa a **`EVASO` solo se TUTTE le righe sono state smistate**.
  Se ne resta anche una sola non smistata, **resta `ACCETTATO`**.
- È già prevista una sezione *"§5.3.3 — Idempotenza dell'azione
  push preventivo→ordine"* e *"§5.3.2 — preventivi misti: natura come proprietà
  di riga (**decisione aperta**)"*.

La macchina di "esecuzione parziale" che §5.1 voleva evitare **non** sta dentro
il preventivo: la regge la **pratica** (che traccia quali righe sono andate
dove) + i legami a livello riga. Per questo il preventivo resta semplice.

## 3. Perché NIENTE UNIQUE 1:1 di testata sul preventivo

Un indice `UNIQUE (documento_origine_tipo, documento_origine_id) WHERE tipo =
'PREVENTIVO'` (come quello dell'offerta) sarebbe **sbagliato**:

1. **Romperebbe lo split multi-destinazione**: un preventivo deve poter generare
   *contemporaneamente* un ordine (merce) **e** una commessa (servizi) **e/o** un
   contratto (ricorrenza). Un vincolo 1:1 testata-ordine non lo impedirebbe da
   solo, ma incardina la logica sbagliata (il preventivo come "padre di un solo
   ordine").
2. **Bloccherebbe il 0..N ordini** se la natura merce è a sua volta spezzata in
   più tranche di evasione.
3. **Vincolerebbe sul layer sbagliato**: l'invariante vero non è "un preventivo →
   un ordine", è **"la stessa riga di preventivo non può finire su due ordini"**
   (idempotenza di riga, §5.3.3).

→ Sul preventivo l'idempotenza è **a livello di riga**, non di testata.

## 4. Cosa servirà davvero a DB (quando si farà)

Non un indice di testata, ma un **legame a livello riga** + vincolo:

- una colonna su `vendite.ordini_righe` che punta alla **riga di preventivo**
  origine (es. `preventivo_riga_id bigint NULL` FK `vendite.preventivi_righe`, o
  un `documento_origine_riga_*` polimorfico coerente con la testata);
- un **vincolo di non-doppia-allocazione**: ogni riga di preventivo può finire su
  **al massimo un** ordine → `UNIQUE` parziale sul link di riga. (Niente
  conteggio di quantità: lo split per quantità è fuori scope — il frazionamento
  per quantità vive a valle, ordine→DDT via `ordini_righe_fulfillment`. Chi vuole
  "6 ora e 4 dopo" fa due preventivi/righe distinte, coerente con la regola
  decisa per l'offerta.)
- la valorizzazione del link dentro `fn_push_preventivo_a_ordine(p_righe_ids)`,
  che è anche il punto naturale dove vive l'idempotenza (§5.3.3): se una riga è
  già allocata, l'azione la salta o solleva.
- aggancio `pratiche_sorgenti` (preventivo ROOT + ordine COLLEGATO).

Capability data-driven: `genera_ordine` (o l'equivalente "smista vendita")
disponibile su `fn_available_actions_preventivo` finché **restano righe non
ancora smistate** (residuo a livello riga, non "esiste un ordine").

## 5. Interazione con lo stato `EVASO` (da tenere presente)

`EVASO` oggi è impostato dal **push a commessa** quando completa, ed è
**terminale** (nessuna transizione in uscita — vedi
[brief-db-stato-preventivo-evaso.md](../work-done/brief-db-stato-preventivo-evaso.md)).
Nel modello a split, `EVASO` va ridefinito come *"tutte le righe smistate"*
(qualunque destinazione), non *"pushato a commessa"*. Va riconciliato quando si
implementa `CONFERMA_VENDITA`: oggi `push_a_commessa` evade il preventivo anche
se esistono righe-merce non ancora portate a ordine — comportamento da rivedere.

## 6. Decisione aperta — cosa fare del tappabuchi attuale

Il modello corretto (split anello3) è un lavoro grande, legato alle pratiche.
Nel frattempo `crea_ordine_da_preventivo` (copia-tutto) resta in piedi col suo
bug. Opzioni, **da decidere con Tid**:

- **(a) Lasciarlo com'è** finché non si costruisce lo split — accettando il bug
  del doppio click sul preventivo (basso rischio: ambiente non in produzione).
- **(b) Guard soft non strutturale** (il bottone si nasconde / chiede conferma
  dopo il primo ordine), marcato esplicitamente come provvisorio — ma è in
  tensione col futuro 0..N e va rimosso quando arriva lo split.
- **(c) Disabilitare temporaneamente** `crea_ordine_da_preventivo` (copia-tutto
  in blocco non è il modello voluto), riattivando solo con lo split corretto.

> Raccomandazione: **(a)** se la priorità è chiudere subito l'offerta senza
> aprire cantieri; **(c)** se si preferisce non lasciare in giro un'azione che
> contraddice il modello. Evitare di "consolidare" il copia-tutto con un UNIQUE
> di testata (§3).

## 7. Prossimi passi

1. **Orchestratore `CONFERMA_VENDITA` (BE)** che invochi `fn_push_preventivo_a_ordine`
   per le righe merce e `push_a_commessa` per i servizi una-tantum.
2. **Gate `EVASO` (BE)** che consumi `vendite.fn_preventivo_ha_residuo_ordine` (§8):
   `push_a_commessa` non deve evadere se restano righe merce non ordinate (D6).
3. **Filtro catalogo FE/BE**: non proporre nature `CONTRATTO` (ricorrenti) sul
   preventivo (difesa in profondità del blocco DB).
4. Disattivare il tappabuchi `crea_ordine_da_preventivo` copia-tutto (§6 / D2).

## 8. Log implementazione DB (2026-06-09)

Modalità A ratificata (D9: ricorrente bloccata sul preventivo). Tutto applicato e
testato (pgTAP), salvo `20260609-07/08` da applicare:

| Migration | Cosa |
| --- | --- |
| `20260609-01/02` | Blocco fail-fast ricorrente all'inserimento riga (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`, guard data-driven `destinazione_tipo='CONTRATTO'` nel trgfn set-natura). |
| `20260609-03/04` | `catalogo.articoli.natura_vendita_id` backfill NULL→MERCE + `DEFAULT` MERCE + `NOT NULL` (D3). DML/DDL splittati per pending trigger events. |
| `20260609-05` | Codici errore push ordine (`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`, `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE`). |
| `20260609-06` | **`vendite.fn_push_preventivo_a_ordine`** (D1/D4/D5/D7/D8): split righe ORDINE→ordine DRAFT `documento_origine=PREVENTIVO`, snapshot prezzi, BoM via `fn_ordine_riga_componenti_init`, idempotenza di riga `ordini_righe.preventivo_riga_id`, pratica opzionale. |
| `20260609-07` | `vendite.fn_preventivo_ha_residuo_ordine` — predicato residuo merce, condiviso capability + gate EVASO. |
| `20260609-08` | Capability/azione `genera_ordine` in `script.fn_available_actions_preventivo` (additivo). |
| `20260609-09` | `fn_list_preventivi_da_pushare` **natura-aware**: il push commessa include solo righe `destinazione_tipo='COMMESSA'` (natura NULL = pregresso, inclusa), esclude la merce → niente doppio routing. Prerequisito dell'orchestratore. Vedi [brief-db-fn-list-preventivi-natura-aware.md](brief-db-fn-list-preventivi-natura-aware.md). |

Fuori scope DB: orchestratore `CONFERMA_VENDITA`, gate `EVASO`, filtro catalogo (BE/FE).

---

*Documento di indirizzo — preventivo→ordine segue il modello a split di riga
(anello3 §5.3), NON il 1:1 di testata dell'offerta. L'offerta è trattata in
[brief-db-univocita-offerta-ordine.md](../work-done/brief-db-univocita-offerta-ordine.md).*
