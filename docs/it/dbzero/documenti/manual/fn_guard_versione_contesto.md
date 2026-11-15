## 📘 Documentazione Concettuale – Funzione `documenti.fn_guard_versione_contesto`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la forma dei dati che ogni versione legge
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe, controllate all'inserimento
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_guard_versione_contesto](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_versione_contesto) — il controllo sulla stampa
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — il controllo alla pubblicazione
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — come è fatto un modello

---

### 🎯 Scopo Principale

Funzione che tiene il patto fra una versione di template e la forma dei dati che legge: se la versione indicata non
legge i dati nella forma indicata, rifiuta, e nessun PDF nasce.

La forma indicata è quella che i dati **hanno**: la forma dichiarata dal contesto, per una stampa, oppure quella che
il codice che prepara i dati produce, prima del render e alla pubblicazione. Quest'ultima è un fatto del codice: il
database non la conosce, e la riceve da chi chiama.

---

### Tre chiamanti, una regola

* il **backend**, prima del render, con la forma che il suo codice produce: così una stampa incompatibile si ferma
  prima di produrre un PDF da buttare;
* il **controllo sull'inserimento della stampa**, con la forma dichiarata dal contesto congelato;
* la **pubblicazione** di una versione in bozza, con la forma che il backend dichiara.

Una versione in bozza si controlla solo quando si pubblica o si stampa.

---

### È un guard, non una capability

La funzione rifiuta, e non risponde con un sì o un no: non c'è un pulsante da accendere o spegnere sullo schermo,
perché la forma prodotta dal codice non è un dato del database e una capability non la potrebbe comporre.

Legge la versione con i diritti di chi chiama: una versione fuori dal perimetro di chi legge è, per lei, una
versione che non c'è.

---

### Codici errore

* `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` (`CONFLITTO_STATO`) — le due forme non coincidono. La frase dice la
  versione, il nome del modello, la forma della versione e quella dei dati. Rimedia chi amministra i modelli,
  pubblicando una versione che legga la forma di oggi;
* `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` (`TECNICO`) — manca la versione o manca la forma dei dati: lo
  produce solo un chiamante che non dichiara ciò che deve;
* `E_DOCUMENTI_VERSIONE_NOT_FOUND` (`NON_TROVATO`) — la versione non c'è, o non è nel perimetro di chi legge.

Nessuno porta un bersaglio: un modello non è fra i tipi di entità che il catalogo degli errori sa indicare.

---

### Test

* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — la regola e il controllo sulla stampa;
* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — la pubblicazione;
* `db/pgtap/documenti/test-documenti-template-versioni.sql` — la forma ferma su una versione pubblicata, libera in
  bozza.

---

### Note di migrazione

* 2026-09-30 — nasce la funzione, con la forma dei dati dichiarata su ogni versione.

---

{% include-markdown "signature-core.md" %}
