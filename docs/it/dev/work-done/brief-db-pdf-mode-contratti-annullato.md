# Brief DB — `pdf_mode` contratti ANNULLATO: NONE → ARCHIVE

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16 · **Owner**: Tid
> **Stato**: ✅ CHIUSO (2026-07-16) — **superato in meglio dalla revisione del team DB**:
> il presupposto "asimmetria = svista solo contratti" era errato (il `NONE` su ANNULLATO era
> un pattern verbatim su 3 domini: contratti, ordini, DDT). Decisione Tid: regola unica sui
> 5 domini — *annullare non cancella la storia* — `ANNULLATO: NONE → ARCHIVE` anche su
> ordini e DDT (pgTAP 17/19/22 aggiornati). Verificato live su DB dev: ANNULLATO=ARCHIVE
> su contratti/ordini/ddt, `NONE` non più usato da alcuno stato. FE data-driven: recepito
> senza modifiche. Fonte: revisione 2026-07-16 in [[brief-db-pdf-mode-contratti-annullato-archive]].
> **Contesto**: rimozione delle aree inline "Documenti generati" dai drawer
> Preventivi e Contratti (doppione del pulsante PDF in testata, che apre lo
> stesso BB `DocumentiGeneratiSorgenteList` via `PdfDocumentiSorgenteDialog`,
> con in più expand automatico e append allegati). FE già allineato.

## 1. Cosa serve (NON come)

Il pulsante PDF è data-driven da `config.stati_doc_*.pdf_mode`. Oggi:

- **Preventivi**: tutti gli stati post-DRAFT (inclusi RIFIUTATO / SCADUTO /
  **ANNULLATO** / EVASO) hanno `pdf_mode = ARCHIVE` → l'archivio PDF resta
  consultabile in ogni stato terminale. ✔
- **Contratti**: `ANNULLATO` ha `pdf_mode = NONE` → pulsante disabilitato.
  Con l'area inline rimossa, un contratto annullato che aveva PDF generati
  (mentre era ATTIVO) non avrebbe più accesso ai documenti dal drawer.

Serve quindi che lo stato **`ANNULLATO` dei contratti** (`config.stati_doc_contratti`,
`codice_interno = 'ANNULLATO'`) passi a **`pdf_mode = ARCHIVE`**
(`pdf_allow_allegati` resta `f`): consultare i PDF di un documento annullato è
legittimo, e allinea i contratti alla simmetria già in vigore sui preventivi.
L'asimmetria attuale appare una svista, non una scelta di dominio.

## 2. Impatto

- Nessun oggetto DB nuovo: solo il valore `pdf_mode` dello stato.
- FE: nessuna modifica ulteriore (il pulsante è già data-driven: recepisce da solo).
- In ANNULLATO il pulsante tornerà attivo in modalità "scarica archivio";
  se l'archivio è vuoto (contratto mai emesso? caso non raggiungibile: il PDF
  nasce all'attivazione) il dialog mostra l'empty-state standard.

## 3. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | `stati_doc_contratti.ANNULLATO`: `pdf_mode` NONE → ARCHIVE | ✅ (esteso dal team DB anche a ordini e DDT — regola unica sui 5 domini) |
| 2 | Apply su DB dev + verifica pulsante PDF su contratto annullato | ✅ apply verificato live (ANNULLATO=ARCHIVE su contratti/ordini/ddt, `NONE` non più usato); verifica visiva in-app al prossimo giro |
