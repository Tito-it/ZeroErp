# Collaudo in-app · le due voci residue di V2 — DL-23 `CONFERMATO` e l'area RESI

> **Cos'è.** Il copione a video delle **ultime due** voci di **V2** del
> [brief fan-out](brief-be-fan-out-isolato-e-esito-parziale.md) §13.2. Il *perché*
> sta lì; qui c'è cosa fare, cosa deve succedere, cosa fare se non succede.
>
> **Stato**: 🔴 **APERTO**. · **Ambiente**: sviluppo (`dbdev`). · **Pagine**:
> `Vendite → Situazione aperta` e `Vendite → Backlog fatturazione`.
>
> **Sono due prove indipendenti**: la **A** vuole un ordine da costruire, la
> **B** si guarda e basta (tranne il suo secondo ramo). Si possono fare in
> qualunque ordine e in due sedute.
>
> ⛔ **Niente numerazione in nessuna prova.** E la fattura **2263 non va
> numerata**, comunque vada.

---

## A · DL-23 — con trigger `CONFERMATO` il serbatoio mostra il **pieno**

**Il ramo gemello è già verde** (2026-08-17, `ORD0018587`: trigger `SPEDITO`,
10 ordinati evasi per 4 → ORDINI mostra **6**, DDT mostra **4**, somma 10, la
merce compare una volta sola). Qui si prova l'altro verso: con
`fatturazione_trigger = CONFERMATO` la fatturazione avviene alla conferma,
quindi il serbatoio ORDINI deve mostrare il **pieno** — non il residuo.

⚠️ **Il soggetto non esiste e non nascerà da sé** (ricontrollato 2026-08-31): i
soli due ordini `PARZIALMENTE_EVASO` sono entrambi a trigger `SPEDITO`, cioè il
ramo già provato. Chi lavora con `CONFERMATO` fattura alla conferma e non passa
dall'evasione parziale: **va costruito**.

### Come costruirlo

1. `Vendite → Ordini → Nuovo`. Cliente a piacere, **una riga sola** da **10
   pezzi** con un prezzo tondo — annota `10 × prezzo = <pieno>`;
2. ⚠️ **il trigger si imposta DOPO il salvataggio della testata** (è la stessa
   trappola del gemello): apri l'ordine salvato e porta
   `fatturazione_trigger` a **`CONFERMATO`**;
3. conferma l'ordine, poi generane un **DDT di 4 pezzi** → l'ordine passa a
   `PARZIALMENTE_EVASO`.

- [ ] l'ordine è `PARZIALMENTE_EVASO` e il suo trigger è **`CONFERMATO`**.

### Cosa deve succedere

**Dove**: `Vendite → Situazione aperta`, aree **ORDINI** e **DDT**.

- [ ] l'ordine compare nell'area **ORDINI** con il **valore pieno** (`10 ×
      prezzo`), **non** il residuo di 6;
- [ ] il drill-down apre l'ordine.

⛔ **Si legge dal VALORE, non da `unita_totali`.** Quella colonna vale `1`
perché conta le **righe documento**, non i pezzi. È l'errore facile da fare
guardando la lente a video. *(Riferimento misurato il 2026-08-31 sul ramo già
verde: `ORD0018587` = **86,70** cioè 6 × 14,45 — il residuo; `DDT0010841` =
**57,80** cioè 4 × 14,45.)*

⚠️ **Se ORDINI mostra il residuo** invece del pieno: il ramo `CONFERMATO` sta
applicando la regola del ramo `SPEDITO`. È il difetto che DL-23 esiste per
escludere — annota i due valori e segnala.

### E adesso guarda l'area DDT — è la domanda vera

L'invariante di DL-23 è uno solo: **la merce vale 10, una volta sola.** Sul ramo
`SPEDITO` torna così: ordine 6 + DDT 4. Sul ramo `CONFERMATO` l'ordine porta già
il pieno, quindi il DDT **non può portare altri 4** o sarebbero 14 pezzi a
fronte di 10 — esattamente il doppio conteggio del §13.2.

⚠️ **Non do per scontato cosa vedrai**, perché il caso non è mai esistito e la
lente «Situazione aperta» è uno stock di documenti aperti, non un serbatoio di
fatturazione. Annota quale delle due:

- [ ] il DDT **non compare** nell'area DDT → ✅ l'invariante regge;
- [ ] il DDT **compare**: annota il suo **valore** e il **motivo fermo**.
      Se il valore è quello dei suoi 4 → 🔴 **10 + 4 = 14**, è il doppio
      conteggio e va segnalato. Se il motivo è `FATTURA_DA_ORDINE` (il DDT
      dichiarato non-pushabile perché fattura l'ordine) la riga è una
      *presenza*, non un *addebito*: annotalo comunque, perché è una lettura
      che nessuno ha ancora dato.

---

## B · L'area RESI del Backlog — non è più vuota

Era vuota **per progetto** fino al 2026-08-26: il motivo `MERCE_RESA_GIA_FATTURATA`
era `FISIOLOGICO` con `azione = NULL`, e il Backlog elenca solo ciò che è fermo
**e recuperabile**. Con la nota di credito quel motivo ha un rimedio, e il seed
lo porta a `RECUPERABILE`.

### B1 · L'area compare, con l'azione *(si guarda e basta)*

**Dove**: `Vendite → Backlog fatturazione`.

- [ ] l'area **RESI** c'è fra le card (le altre tre sono DDT, ORDINI,
      PREVENTIVI);
- [ ] entrando, la riga è **`RESO0005123`** con motivo
      **`RICONSEGNA_NON_ESEGUITA`**, classe **`RECUPERABILE`** e azione
      *«Genera il DDT di ri-consegna»*;
- [ ] ⭐ il **`valore_fermo` è vuoto**, non `0,00`: è un'area a **conteggi**, e
      DL-11 prescrive il vuoto — uno zero direbbe «vale niente» invece di «qui
      non si misura in denaro»;
- [ ] il **drill-down** apre il drawer del reso.

⚠️ **Il drill-down è l'unica parte non garantita a tavolino.** Le whitelist a
valle ammettono `RESI` su entrambi i lati (`DASH_FATTURAZIONE_AREE` nel BE,
`DASH_AREA_CONFIG` nel FE, con `drawerTipo = RESO_VENDITA`) — ma la whitelist è
condizione **necessaria**, non sufficiente. Se il drawer non si apre, è lì che
guarda il difetto.

### B2 · Il motivo gemello — quello per cui l'area è stata sbloccata

⛔ **Il soggetto che il brief indicava non c'è più**: `RESO0005122` è stato
**accreditato** durante il collaudo nota di credito, il residuo è sceso a zero e
la riga è uscita dalla coda. Il ramo `MERCE_RESA_GIA_FATTURATA` è di nuovo senza
materia e **va ricostruita**.

**Come**: serve un reso **confermato** su merce **già fatturata**, e **non
accreditato**. Il giro è quello del §13.2: DDT consegnato → fatturato → reso
confermato sulle sue righe, e ci si ferma prima di accreditare.

- [ ] la riga compare in **coda accrediti** con accredito **dovuto**;
- [ ] nel **Backlog**, area RESI, compare una **seconda** riga col motivo
      **`MERCE_RESA_GIA_FATTURATA`**, classe **`RECUPERABILE`**, azione
      *«Emetti la nota di credito dalla coda accrediti»*;
- [ ] ⛔ **non accreditarla**: lasciandola lì il soggetto resta per la prossima
      volta. È esattamente ciò che è mancato questa volta.

⚠️ **Se la riga non compare** ma la coda accrediti sì: guarda la classe del
motivo a catalogo — se `MERCE_RESA_GIA_FATTURATA` è tornato `FISIOLOGICO`, il
filtro `classe <> 'FISIOLOGICO'` della vista la scarta ed è quello il punto.

---

## Verbale

**Chiuso il**: — · **Da**: — · **Ambiente**: sviluppo (`dbdev`)

| # | Prova | Costruisce | Esito | Note |
| --- | --- | --- | --- | --- |
| A.1 | Ordine da 10, trigger `CONFERMATO`, DDT di 4 | **sì** | | |
| A.2 | ORDINI mostra il **pieno**, non il residuo | no | | |
| A.3 | Area DDT: la merce resta contata **una volta sola** | no | | |
| B.1 | L'area RESI c'è, con azione e `valore_fermo` vuoto | no | | |
| B.2 | Il drill-down apre il drawer del reso | no | | |
| B.3 | Reso ricostruito → `MERCE_RESA_GIA_FATTURATA` nel Backlog | **sì** | | |

### Che cosa ha trovato

> Da compilare. Se non trova niente, si scrive che non ha trovato niente.

---

## Quando questo verbale è chiuso

Restano solo le **23 caselle** di
[collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md)
(V1). Chiuse quelle, il [brief fan-out](brief-be-fan-out-isolato-e-esito-parziale.md)
va in `work-done` e la linea chiude per intero.
