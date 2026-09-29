# Brief DB + BE — Documenti: il patto fra la versione di un template e la forma dei dati che legge

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-29. **A chi:** team DB e backend
> (`dev/backend-tid`); Tid per le decisioni di §7.
> **Origine:** §9.8.4 di [brief-db-liste-righe-documento.md](brief-db-liste-righe-documento.md)
> (la stampa della fattura dalla lista delle righe).
> **Stato:** ⏸️ **in attesa del via di Tid per partire.** ✅ **Decisione di Tid (2026-09-29): si fa
> tutto, per TUTTI i documenti, appena possibile** (non siamo in produzione). ✅ **D-C1 → D-C4
> accettate da Tid il 2026-09-29** (§7). Nessuna riga scritta.
>
> **In una riga:** oggi una versione di template può leggere dati di una forma diversa da quella
> che il backend le prepara, e stampare un documento **incompleto senza nessun errore**. Ogni
> versione dichiara la forma che legge, e il sistema rifiuta di stampare se la forma non torna.

---

## 1. Il problema, in parole semplici

Un PDF nasce da due pezzi:

* il **template**, il modello grafico, salvato a DB e **versionato**
  (`documenti.template_documenti_versioni`);
* il **contesto**, i dati che un builder del backend prepara (testata, righe, totali…).

Il template legge i dati **aspettandosi una certa forma**. Se la forma cambia e il template no,
Jinja non si lamenta: le chiavi che non trova diventano vuote. Il PDF esce, e mancano dei pezzi.

**Il caso che l'ha fatto emergere** (brief liste, §9.8.4): la versione 3 del template «Fattura»
scorre le righe **in fila** e riconosce un componente di kit da `tipo_riga`. La lista delle righe
della fattura oggi le dà **ad albero** (il kit con i componenti dentro). Se il PDF passasse a
quella forma, la versione 3 stamperebbe la fattura **senza i componenti dei kit**: un documento
fiscale incompleto, senza un segnale.

⚠️ **Non è un caso isolato, è il modello.** Il preventivo è già passato una volta dalla forma 1
alla forma 2 (gli indirizzi a slot, `work-done/brief-db-template-preventivo-slot.md`), e
l'allineamento fra builder e template l'ha fatto una persona, a mano. Con i template
**personalizzati per azienda** ogni installazione avrà le sue versioni, scritte sulla forma di
quando sono nate: il caso diventa la norma.

## 2. Cosa c'è oggi — letto dalla struttura (2026-09-29)

* Ogni builder scrive `_meta.context_version` nel contesto (`apps/vendite/services/*_document_context_builder.py`):
  la **forma che produce**. Fatto datato: fattura `1`; preventivo, ordine, DDT, contratto,
  offerta `2`.
* `template_documenti_versioni.context_schema jsonb NOT NULL DEFAULT '{}'`, con il solo
  `CHECK` «è un oggetto». **Nessuno lo legge né lo controlla.**
* ⚠️ **Una regola decisa e mai costruita**: le decisioni 35-36 del 2026-04-29
  (`work-done/sviluppo-documenti.md`) volevano `context_schema` «contratto leggero delle
  variabili attese», **validato prima della pubblicazione** di una versione. Non esiste la
  validazione, e il campo è vuoto su tutte le versioni.
* `documenti.documenti_generati` congela per ogni stampa `context_json` (col suo `_meta`) e
  `template_versione_id`: la **ristampa fedele** rilegge quelle due cose, quindi è coerente per
  costruzione se lo era la prima stampa.

## 3. Il patto

1. Ogni **versione di template dichiara la forma che legge**: un numero, «versione del contesto».
2. Il **builder dichiara la forma che produce** (lo fa già: `_meta.context_version`).
3. **Si stampa solo se i due numeri coincidono.** Altrimenti un errore parlante — «questa
   versione del template legge la forma N, i dati sono nella forma M» — e **nessun PDF**.
4. Lo stesso controllo **alla pubblicazione** di una versione: non si pubblica una versione che
   dichiara una forma che il builder non produce.

Vale per **tutti** i tipi di documento, anche per quelli che oggi non cambiano forma.

## 4. Lato DB (proposta)

* **Una colonna tipizzata, non una chiave nel jsonb**: `template_documenti_versioni.versione_contesto
  integer NOT NULL`, `CHECK (versione_contesto >= 1)`. Un numero che decide se si stampa deve
  potersi vincolare e leggere con una query, non stare dentro un oggetto libero.
* **La regola in un posto solo**: una `documenti.fn_check_versione_contesto(template_versione_id,
  versione_contesto)` che risponde, e la chiamano **tutti e due**:
  - il **backend**, prima del render (niente PDF da buttare);
  - un **guard** sull'INSERT di `documenti_generati`, che confronta il
    `_meta.context_version` del contesto congelato con la versione del template: una stampa
    incoerente non si registra, qualunque strada l'abbia prodotta.
* **Il codice d'errore**, registrato (nome da decidere, p.es. `E_DOC_VERSIONE_CONTESTO_DIVERSA`).
* ⛔ **Il backfill non è «le vecchie valgono 1»** (la proposta di §9.8.4): cinque builder su sei
  producono già la forma 2, e le versioni pubblicate che la leggono diventerebbero
  **non stampabili** il giorno dopo. Il valore di ogni versione esistente va **stabilito
  leggendola** (quali chiavi usa), versione per versione: è un dato di catalogo, non una regola.
  Chi lo stabilisce è una decisione (§7).
* `context_schema` resta dov'è; se la validazione delle variabili (decisione 35-36) si fa, si
  appoggia sullo stesso momento della pubblicazione (§7, D-C3).

## 5. Lato BE (per sapere cosa serve)

* il controllo prima del render e alla pubblicazione, chiamando la funzione del DB;
* il campo nell'amministrazione delle versioni di template (a video: «legge la forma N»);
* la versione del builder resta nel codice del builder (è un fatto del codice): una costante per
  builder, da cui escono sia `_meta.context_version` sia il confronto;
* poi, **per la fattura**: il contesto in forma 2 dalla lettura completa di
  `vw_fattura_righe_lista`, la **versione 4 del template** che scorre `riga.componenti`, e il
  ritiro di `VenditeRepository.list_fattura_righe` (l'ultima proiezione Python delle righe,
  brief liste §9.8.4, punto 3). Nello stesso giro, gli altri documenti le cui righe sono già
  liste (preventivo, ordine, DDT, reso, contratto) passano alla stessa lettura se la loro forma
  cambia — con il loro numero di forma.

## 6. L'ordine

1. DB: colonna, funzione, guard, codice; backfill **verificato** delle versioni esistenti.
2. BE: controllo al render e alla pubblicazione; campo a video.
3. Da lì in poi ogni cambio di forma è: forma N+1 nel builder **e** versione nuova del template
   che la dichiara, nello stesso giro. La ristampa dei documenti già emessi non cambia.
4. Fattura: forma 2 + template versione 4 + ritiro di `list_fattura_righe`.

## 7. Decisioni per Tid

✅ **Tutte e quattro accettate da Tid il 2026-09-29, come proposte.**

| # | Domanda | Proposta |
| --- | --- | --- |
| D-C1 | Chi stabilisce la forma di ogni versione esistente (il backfill)? | Il team BE, leggendo ogni versione (sono poche), con la tabella nel brief prima del changeSet |
| D-C2 | Il controllo anche come guard sulle stampe registrate, o solo nel backend? | **Anche il guard**: una funzione sola, due chiamanti. Protegge da una strada di stampa che dimentica il controllo |
| D-C3 | La validazione delle variabili decisa ad aprile (35-36): si fa ora o resta fuori? | Fuori da questo giro, dichiarata: il numero di forma chiude il caso grave (pezzi mancanti in silenzio); la validazione delle singole variabili è un raffinamento |
| D-C4 | Una versione **in bozza** può dichiarare una forma che il builder non produce ancora? | Sì: è così che si prepara la versione 4 mentre il builder è ancora a 1. Il controllo vale alla pubblicazione e alla stampa |
