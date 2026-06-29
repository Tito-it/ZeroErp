# 📘 Operativo Magazzino — Trasferimenti, Rettifiche, Inventari

> Scopo: regole funzionali di utilizzo dei documenti interni e di **posting** sul ledger `magazzino.movimenti`.
> Valgono per l’attuale progetto (senza trigger lock).

---

## 1) Trasferimenti

**Obiettivo:** spostare stock da un magazzino A ad un magazzino B con tracciabilità completa.

### Regola chiave

* Per **ogni riga** di `magazzino.trasferimenti_righe` si generano **due movimenti**:

  1. **OUT (−)** dal `magazzino_id_from` con **causale `TRASF_OUT`**
  2. **IN (+)** nel `magazzino_id_to` con **causale `TRASF_IN`**
* Le **due righe** del ledger sono accoppiate tramite **`transfer_uid` (UUID)** uguale su entrambe.

### Invarianti/controlli (logica applicativa)

* Per ogni `transfer_uid` vale: somma **qta = 0**; stessi `articolo_id` e (se presenti) stessi `lotto/seriale`.
* La riga OUT può valorizzare `magazzino_id_dest` a **B** (campo informativo utile per query/riconciliazioni).

### Errori tipici

* OUT registrata senza IN → segnalazione su `transfer_uid` orfano.
* Seriali mancanti quando richiesti → blocco posting della riga.

---

## 2) Rettifiche

**Obiettivo:** adeguare la giacenza (per differenze inventariali, rotture, perdite, sovrapprezzi di accertamento, allineamenti iniziali, ecc.).

### Documento

* `magazzino.rettifiche` (testata) + `magazzino.rettifiche_righe` (righe).
* Ogni **riga** contiene **`qta_delta`** (può essere **positiva** o **negativa**), oltre a `articolo_id`, eventuali `lotto`/`seriale` e **motivo** (testo/codice).

### Regola chiave

* **Non servono due causali diverse in riga**: la **causale effettiva di posting** si **deriva dal segno** di `qta_delta`:

  * `qta_delta > 0` → **RETT_POS** (carico di rettifica)
  * `qta_delta < 0` → **RETT_NEG** (scarico di rettifica)
* Il posting avviene quando lo **stato documento = POSTED**.

### Algoritmo di posting (concettuale)

Per ogni riga `r` di una rettifica `R` in stato POSTED:

1. **Valida**: se la causale selezionata richiede `seriale/lotto`, verifica presenza valori; opzionalmente verifica che lo stock negativo sia consentito per il magazzino/categoria.
2. **Determina segno**: `segno = sign(qta_delta)` → mappa in `RETT_POS` / `RETT_NEG`.
3. **Valorizzazione**:

   * In **fase 1 (CMP)**: su **carichi (RETT_POS)** aggiorni il costo medio; su **scarichi (RETT_NEG)** usi il **costo corrente medio**.
   * Se la rettifica è puramente quantitativa (senza impatto valore), si può usare causale con `impatto_valorizzazione = 'none'` (caso raro).
4. **Scrivi ledger**: una riga su `magazzino.movimenti` con: `magazzino_id` della rettifica, `qta = qta_delta`, `causale_id` risolta, `lotto/seriale` se presenti, riferimenti `doc_*` (o `sorgente_*`).

### Esempi

* **Mancano 3 pezzi** di un articolo: `qta_delta = -3` → una riga ledger con `qta = -3`, causale **RETT_NEG**.
* **Trovo 2 pezzi in più**: `qta_delta = +2` → una riga ledger con `qta = +2`, causale **RETT_POS**.

### Buone pratiche

* Raccogliere **motivo** standard (es. `ROTTURA`, `SMARRIMENTO`, `INVENTARIO_DIFF`, `ALLINEAMENTO_INIZIALE`) per report.
* Se l’articolo è **serializzato**, **una riga per seriale** (o usa `qta_delta` = 1/−1 per unità singola con seriale obbligatorio).

---

## 3) Inventari

**Obiettivo:** contabilizzare il conteggio fisico e allineare lo stock ai valori reali.

### Documento

* `magazzino.inventari` (testata) + `magazzino.inventari_righe` (conteggi).
* In riga si memorizza **`qta_contata`** (≥ 0), ed opzionalmente **`qta_sistema`** (snapshot informativo della giacenza al momento del confronto). `lotto/seriale` se applicabili.

### Flusso operativo

1. **DRAFT** → creazione documento e definizione ambito (magazzino, area, lista articoli, data cut-off).
2. **COUNTING** → inserimento conteggi (`qta_contata`), anche multi-pass (più versioni/contatori; si può sovrascrivere o tracciare in `meta`).
3. **CONFIRM** → chiusura conteggi e calcolo differenze vs giacenza di sistema.
4. **POSTED** → generazione **automatica di rettifiche** sul ledger (una riga di rettifica per ogni riga inventario con differenza ≠ 0).

### Calcolo differenze

* Per ogni riga inventario si calcola:
  **`qta_delta = qta_contata - giacenza_sistema_attuale`**
* La **giacenza di sistema** si ricava dal ledger fino al **cut-off** (es. `data` dell’inventario) e, se vuoi, “freeza” le movimentazioni successive fino a `POSTED`.
* Regole di posting come nelle **Rettifiche**:

  * `qta_delta > 0` → **RETT_POS** (carico)
  * `qta_delta < 0` → **RETT_NEG** (scarico)

### Dettagli importanti

* **Seriali**: il conteggio deve indicare i seriali presenti. La differenza genera **una riga di rettifica per seriale** mancante/eccedente.
* **Lotti**: stessa logica; le differenze sono **per lotto**.
* **Soglie**: puoi usare tolleranze (es. differenze minime ignorate) gestite via `meta` o regole applicative.
* **Aree/zone**: per inventari parziali, filtra `magazzino_id` o subset di ubicazioni (se gestite); l’algoritmo è identico sul sottoinsieme.
* **Valorizzazione**: segue le regole CMP di cui sopra.

### Esempi

* Conto **100** pezzi, il sistema riporta **98** → `qta_delta = +2` → rettifica **RETT_POS** `+2`.
* Conto **95**, il sistema dice **100** → `qta_delta = -5` → rettifica **RETT_NEG** `-5`.

---

## 4) Posting, idempotenza e riconciliazione

* Ogni riga di documento interno (trasferimenti/rettifiche/inventari) posta **esattamente una riga ledger** (o due nel caso del trasferimento).
* L’idempotenza si garantisce tramite la **chiave sorgente** sul ledger (campi `doc_*`/`sorgente_*` + UNIQUE) per evitare doppi posting.
* **Report utili**:

  * “Trasferimenti con coppie OUT/IN incomplete” → raggruppo per `transfer_uid`.
  * “Rettifiche non postate” → documenti in stato non `POSTED` o righe con errori (seriale/lotto mancanti quando obbligatori).
  * “Inventari differenze attese vs ledger” → confronto `qta_delta` teorica e righe ledger generate.

---

## 5) Riepilogo operativo

* **Trasferimenti** → 2 righe ledger per riga doc, accoppiate da `transfer_uid` (− OUT da A, + IN su B).
* **Rettifiche** → una riga ledger per riga doc; usa `qta_delta` con segno per derivare **RETT_POS/RETT_NEG**; rispetta seriali/lotti e politiche stock negativo.
* **Inventari** → conti fisico (`qta_contata`), calcoli **`qta_delta`** vs sistema, e **posti rettifiche** automatiche al passaggio a **POSTED**.

> Nota: se in futuro vorrai dominare gli **stati documento** con tabelle `config.*`, il flusso non cambia; si sostituiscono solo le `VARCHAR` con FK ai domini di stato.
