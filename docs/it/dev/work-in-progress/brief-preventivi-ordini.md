# Brief — `preventivo → ordine`: modello a split di riga (NON 1:1 di testata)

> **Stato**: 🟡 **DECISIONI RATIFICATE — IMPLEMENTAZIONE NON AVVIATA**. Le scelte
> aperte (modello idempotenza, natura di riga, accoppiamento pratica, EVASO,
> link di riga, scope) sono chiuse: vedi §0. Resta da scrivere il changeSet DB.
> Nessun codice BE/FE/DB toccato finora.
>
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data**: 2026-06-07 — decisioni ratificate 2026-06-08.
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

Tutte verificate contro lo schema attuale: **niente** di quanto segue è ancora
implementato a DB (`fn_push_preventivo_a_ordine`, colonna link di riga, UNIQUE
parziale per `PREVENTIVO`, azione `genera_ordine` sulla fn preventivo, flusso
`CONFERMA_VENDITA`). L'unico precedente a terra è la UNIQUE parziale **offerta**
(`uq_ordini_v_documento_origine_offerta`), che è il modello *opposto* e **non**
si replica sul preventivo.

| # | Tema | Decisione |
| --- | --- | --- |
| **D1** | Livello idempotenza | **RIGA** (non testata): ogni riga di preventivo → max 1 ordine; un preventivo genera **0..N ordini** via smistamento incrementale. **Supera anello3 §5.3.3** (UNIQUE di testata su `sorgente_uid`), che è incoerente con §5.3.1/§5.3.2 della stessa anello3. |
| **D2** | Tappabuchi attuale | **Disabilitare** il bottone copia-tutto `crea_ordine_da_preventivo` (modello sbagliato 1:1 di tutte le righe). Endpoint/servizio BE restano dormienti. *Non implementato in questo giro* (è un brief DB). **Nota design:** nella modalità split "copia tutto" torna come **utility UI** (preseleziona tutte le righe = `p_righe_ids` = tutte), non come azione separata. |
| **D3 (A)** | Natura di riga | Nuova **`config.nature_vendita`** (`MERCE` / `SERVIZIO_UNA_TANTUM` / `SERVIZIO_RICORRENTE`), dedicata al routing — niente riuso di `listino_tipologia` (anello3 §5.3.2). La natura è **proprietà intrinseca dell'articolo**: `catalogo.articoli.natura_vendita_id` **obbligatoria** (NOT NULL + backfill articoli esistenti). La riga di preventivo la **eredita e congela** (snapshot all'inserimento, come i prezzi). **Nessun override operatore** (protezione da errore umano sullo smistamento). Articolo senza natura → non smistabile: la NOT NULL su articoli lo previene a monte. |
| **D4 (B)** | Accoppiamento pratica | **`p_pratica_id` opzionale** (NULL ammesso): la fn crea ordine + link riga + idempotenza standalone, e aggancia `pratiche_sorgenti` **solo se** la pratica esiste. → ramo ordine **spedibile a DB subito**, prima dell'engine `CONFERMA_VENDITA`. |
| **D5 (C)** | Riga già allocata | **Skip** silenzioso delle righe già allocate (l'ordine si crea con le sole residue); **errore semantico solo se TUTTE** già allocate. Più ergonomico del "errore propagato" di anello3 v1. |
| **D6 (D)** | Stato `EVASO` | Ridefinito **"nessun residuo smistabile"** (qualunque destinazione), resta terminale. Correggere `push_a_commessa`: **non** evade più se restano righe-merce non portate a ordine (oggi lo fa — incoerenza da chiudere). |
| **D7 (E)** | Link di riga | **FK tipizzata** `vendite.ordini_righe.preventivo_riga_id` → `vendite.preventivi_righe` + **UNIQUE parziale** (àncora hard dell'idempotenza). Testata resta polimorfica `documento_origine_*` per la provenienza. Asimmetria voluta: link di riga è solo-preventivo, testata è multi-sorgente. |
| **D8 (F)** | Scope v1 | Solo **ramo ordine**. `push_a_commessa` esiste già; ramo **contratto** rimandato (handler futuro / smistamento manuale). |

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
preventivo ACCETTATO ────┼── righe SERVIZIO una-tantum → COMMESSA (push_a_commessa, già esistente)
                         └── righe RICORRENTI ───────→ CONTRATTO (handler futuro)
```

Caratteristiche chiave del modello (testuali dal documento):

- **Una sorgente, 0..N destinazioni** — ciascuna corrisponde al **sottoinsieme
  di righe** del preventivo con natura corrispondente. *"Nessuna destinazione è
  speciale: tutte sono casi normali."*
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

1. Decidere §6 (tappabuchi) con Tid.
2. Quando si affronta lo split: aprire un workstream `CONFERMA_VENDITA` che
   includa `fn_push_preventivo_a_ordine(p_righe_ids)` + legame/idempotenza di
   riga §4 + riconciliazione `EVASO` §5 + aggancio pratica. Riprendere
   [analisi-pratiche-domini-anello3.md §5.3](analisi-pratiche-domini-anello3.md)
   come specifica di partenza (in particolare la *decisione aperta* §5.3.2 sulla
   natura come proprietà di riga).

---

*Documento di indirizzo — preventivo→ordine segue il modello a split di riga
(anello3 §5.3), NON il 1:1 di testata dell'offerta. L'offerta è trattata in
[brief-db-univocita-offerta-ordine.md](../work-done/brief-db-univocita-offerta-ordine.md).*
