## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_check_coerenza`

> **Ultimo aggiornamento**: 15 novembre 2026
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
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — la stessa domanda, prima del render
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — con quale modello si stampa un documento

---

### 🎯 Scopo Principale

Trigger function `BEFORE INSERT` su `documenti.documenti_generati` che rifiuta una stampa incoerente con il suo
modello: la versione deve essere di quel modello, e il modello deve andare bene per il documento stampato.

La stampa ricopia sorgente, tipo di output e azienda, perché lo snapshot deve reggere anche se il modello cambia
dopo. Ricopiare apre la strada all'incoerenza: una stampa che dice di essere nata da un modello che non poteva
stamparla perde il suo valore di prova. Il controllo è la rete del database dietro alla scelta del modello che fa
il backend.

---

### Due domande, una sola sede per la seconda

* **La versione è del modello?** Il trigger legge il modello della versione indicata e lo confronta con
  `template_documento_id` della stampa.
* **Il modello va bene per il documento?** La risposta è di `documenti.fn_template_motivo_non_coerente`: stessa
  sorgente, stesso tipo di output, e la stessa azienda **oppure** un modello standard, che vale per tutte. È la
  stessa domanda che la risoluzione fa sul modello indicato prima del render: la regola sta in un punto solo.

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

Per la prima domanda il contesto porta il modello atteso e quello fornito. Per la seconda porta il **motivo** per
nome (`SORGENTE`, `TIPO`, `EMITTENTE`) e i valori della stampa; se più regole falliscono, il motivo è il primo
nell'ordine della regola (sorgente, tipo, azienda).

Fra i controlli sull'inserimento questo parla per primo: su una stampa incoerente e anche fuori forma, la frase
giusta è quella della coerenza, non quella della forma dei dati.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_COERENZA` (`DATO_ERRATO`) — la versione non è del modello, oppure il modello non va bene
  per il documento; il motivo è nel contesto.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — tipo di output e azienda incoerenti;
* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — il modello standard va bene per ogni azienda,
  quello di un'altra azienda no;
* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — la stessa regola vista dalla risoluzione;
* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — l'ordine dei controlli;
* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — cambiato il modello dopo la stampa, la stampa
  vecchia si modifica ancora.

---

### Note di migrazione

* 2026-05-01 — nasce il controllo.
* 2026-10-20 — un modello standard va bene per la stampa di qualunque azienda.
* 2026-10-21 — la seconda domanda passa alla regola comune con la risoluzione del modello, e il rifiuto dice il
  motivo per nome.
* 2026-11-15 — il controllo gira solo alla nascita: prima girava anche sulla modifica, e rifiutava ogni modifica
  di una stampa vecchia quando il suo modello era cambiato.

---

{% include-markdown "signature-core.md" %}
