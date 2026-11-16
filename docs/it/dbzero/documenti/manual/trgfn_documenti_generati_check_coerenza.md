## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_check_coerenza`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa che si controlla
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello con cui si confronta
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la versione, che deve essere di quel modello
>
> Approfondimento funzioni:
>
> * [documenti.fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente) — la regola: il modello va bene per il documento?
> * [documenti.fn_template_motivo_non_stampabile](/dbzero/documenti/funzioni/fn_template_motivo_non_stampabile) — la regola: il modello stampa oggi, con questa versione?
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la stessa domanda, prima del render
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — con quale modello si stampa un documento

---

### 🎯 Scopo Principale

Trigger function `BEFORE INSERT` su `documenti.documenti_generati` che rifiuta una stampa incoerente con il suo
modello: la versione deve essere di quel modello, il modello deve andare bene per il documento stampato, e deve
poter stampare oggi proprio con quella versione.

La stampa ricopia sorgente, tipo di output e azienda, perché lo snapshot deve reggere anche se il modello cambia
dopo. Ricopiare apre la strada all'incoerenza: una stampa che dice di essere nata da un modello che non poteva
stamparla perde il suo valore di prova. Il controllo è la rete del database dietro alla scelta del modello che fa
il backend.

---

### Tre domande, una sede sola per le ultime due

* **La versione è del modello?** Il trigger legge il modello della versione indicata e lo confronta con
  `template_documento_id` della stampa.
* **Il modello va bene per il documento?** La risposta è di `documenti.fn_template_motivo_non_coerente`: stessa
  sorgente, stesso tipo di output, e la stessa azienda **oppure** un modello standard, che vale per tutte. È la
  stessa domanda che la risoluzione fa sul modello indicato prima del render: la regola sta in un punto solo.
* **Il modello stampa oggi, e con questa versione?** La risposta è di
  `documenti.fn_template_motivo_non_stampabile`: il modello è acceso, ha una versione in vigore alla data
  operativa, ed è proprio quella della stampa. Anche questa è la domanda della risoluzione, che sceglie il
  modello un istante prima.

La terza domanda c'è perché una stampa non tiene accesi i suoi padri: modello, versione, tipo, sorgente e azienda
si spengono anche quando hanno stampato. Lo stesso registro che lo permette toglie il controllo opposto, «il padre
è acceso quando il figlio nasce», e senza questa domanda una stampa potrebbe nascere da un modello spento, da una
bozza o da una versione già superata. Sorgente e azienda non si guardano: la risoluzione non le guarda, e la stampa
segue il suo documento, che esiste.

Il trigger non corregge niente: rifiuta. Correggere in silenzio nasconderebbe il difetto di chi ha scritto la
riga.

---

### ⭐ Si giudica alla nascita, e solo lì

La coerenza è una domanda sul momento in cui la stampa nasce, e lì si fa, sul modello com'è allora. Dopo, le
colonne della stampa che la decidono le tiene ferme lo snapshot
(`documenti.trgfn_documenti_generati_protect_snapshot`), e il modello può cambiare sorgente, tipo o azienda
senza toccare le stampe già fatte: una stampa vecchia resta modificabile nel suo `meta`. Il modello non porta
nessun lucchetto per questo.

---

### Che cosa dice il rifiuto

Il contesto porta sempre il **motivo** per nome: `VERSIONE_DI_ALTRO_MODELLO` per la prima domanda, col modello
atteso e quello fornito; `SORGENTE`, `TIPO`, `EMITTENTE` per la seconda, coi valori della stampa;
`MODELLO_SPENTO`, `NESSUNA_VERSIONE_VALIDA`, `VERSIONE_NON_IN_USO` per la terza. Le domande si fanno in
quest'ordine, e dentro ciascuna vale il primo motivo della sua regola.

Fra i controlli sull'inserimento questo parla per primo: su una stampa incoerente e anche fuori forma, la frase
giusta è quella della coerenza, non quella della forma dei dati.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_COERENZA` (`DATO_ERRATO`) — la versione non è del modello, il modello non va bene per il
  documento, oppure oggi non stampa con quella versione; il motivo è nel contesto.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — tipo di output e azienda incoerenti;
* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — il modello standard va bene per ogni azienda,
  quello di un'altra azienda no;
* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — la stessa regola vista dalla risoluzione;
* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — l'ordine dei controlli;
* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — cambiato il modello dopo la stampa, la stampa
  vecchia si modifica ancora;
* `db/pgtap/documenti/test-documenti-risoluzione-scarto-asset-v1.sql` — la stampa non nasce da una versione
  superata, da una bozza, dalla versione di un altro modello, da un modello spento; nasce da quella in uso.

---

### Note di migrazione

* 2026-05-01 — nasce il controllo.
* 2026-10-20 — un modello standard va bene per la stampa di qualunque azienda.
* 2026-10-21 — la seconda domanda passa alla regola comune con la risoluzione del modello, e il rifiuto dice il
  motivo per nome.
* 2026-11-15 — il controllo gira solo alla nascita: prima girava anche sulla modifica, e rifiutava ogni modifica
  di una stampa vecchia quando il suo modello era cambiato.
* 2026-11-16 — il controllo chiede anche che il modello stampi oggi con la versione della stampa: dal giorno
  prima, quando le stampe hanno smesso di tenere accesi i padri, nessuno lo verificava più.

---

{% include-markdown "signature-core.md" %}
