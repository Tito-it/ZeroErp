## 📘 Documentazione Concettuale – Trigger `script.trgfn_doc_stato_iniziale()`

> 👀 **Vedi anche**
>
> [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) ·
> brief `brief-modello-documento-vendita` (§4-bis, §4-ter)

### 🎯 Scopo
(24-10-2026 — brief `brief-modello-documento-vendita`, decisioni N-1 … N-3 e P-1 … P-3 di Tid)

**Un documento nasce nel suo stato iniziale.** Un preventivo, un ordine, una
bolla o una fattura nuovi nascono in bozza; gli altri stati si raggiungono con
i passaggi del documento (emetti, conferma, accetta…), che controllano le loro
condizioni. Prima di questa regola un documento poteva nascere già avanti e
saltare quei controlli: una bolla nasceva emessa, numerata e senza righe.

| Lo stato scritto alla creazione | Che cosa succede |
| --- | --- |
| nessuno | il database mette lo stato iniziale |
| lo stato iniziale | passa |
| un altro stato | errore `E_DOC_STATO_INIZIALE_NON_VALIDO` |

Chi ha bisogno di un documento già avanti lo crea in bozza e lo porta avanti
coi passaggi, nella stessa transazione.

### Dove si dichiara lo stato iniziale

Nel vocabolario degli stati di ogni documento, colonna `iniziale`: uno stato
solo per vocabolario, ed è attivo. Il valore sta nel CSV del vocabolario.
Nessuno scrive più `'DRAFT'` o `'BOZZA'` per dire «lo stato in cui si nasce»:
lo legge `script.fn_stato_iniziale_id`.

### Dove è montato

Su ogni testata che ha un vocabolario degli stati: preventivo, offerta,
contratto, ordine, DDT, reso, commessa e fattura di vendita; ordine e DDT
d'acquisto. Il trigger si chiama `trg_<tabella>_a05_stato_iniziale_ins` ed è il
primo dei trigger che scattano alla creazione, perché alcuni altri leggono lo
stato (il numero della bolla e del reso, lo snapshot di categoria del
contratto). Il montaggio dice due cose: la colonna di stato e il vocabolario.

### Regole

* L'errore è **TECNICO**: nessuna maschera crea un documento già avanti, quindi
  lo commette solo chi scrive il documento, non l'operatore.
* La frase nomina il documento e gli stati come li legge una persona: «Il
  documento Preventivo non può nascere nello stato Emesso: un documento nuovo
  nasce in Bozza.».
* Un montaggio sbagliato, o un vocabolario che non dichiara lo stato
  iniziale, ferma ogni creazione di quel documento con
  `E_SCRIPT_CHIAMATA_NON_VALIDA`, che nomina il vocabolario: è un difetto del
  seed, e si vede subito.
* Le righe dell'ordine hanno uno stato loro e non sono testate: il trigger non
  le copre, e chi le crea legge lo stato iniziale con `script.fn_stato_iniziale_id`.

### Presidio

`db/pgtap/script/test-trgfn-doc-stato-iniziale-v1.sql`: il montaggio si ricava
dal catalogo (ogni testata con una chiave verso un vocabolario che ha la
colonna `iniziale`), quindi una testata nuova senza il trigger fa rosso.
