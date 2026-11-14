## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_guard_versione_contesto`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa che si controlla
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la forma dei dati che la versione legge
>
> Approfondimento funzioni:
>
> * [documenti.fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto) — la regola, in un posto solo
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — come è fatto un modello

---

### 🎯 Scopo Principale

Trigger function `BEFORE INSERT` su `documenti.documenti_generati` che rifiuta una stampa il cui contesto congelato
non ha la forma che la versione di template legge, qualunque strada l'abbia prodotta.

Legge la forma che il contesto dichiara e la passa a `documenti.fn_guard_versione_contesto`, che la confronta con
quella della versione. È la rete dietro al controllo che il backend fa prima del render: protegge da una strada di
stampa che lo dimentica.

---

### La forma la dichiara il contesto

La forma sta nel contesto, alla voce `context_version` di `_meta`, scritta come **numero intero**. Qualunque altra
cosa (la voce assente, un testo, un decimale, un valore vuoto) vale «forma non dichiarata»: il trigger passa un
valore vuoto, e la regola risponde che la stampa non si può verificare. Il trigger non converte il testo in numero:
un testo che non è un numero darebbe un errore generico al posto del codice di catalogo.

---

### Solo all'inserimento

Il contesto e la versione di una stampa non cambiano dopo (li ferma il blocco dello snapshot), e la ristampa fedele
non scrive una riga nuova: non c'è niente da ricontrollare.

Fra i controlli sull'inserimento parla dopo la coerenza col modello, il perimetro dell'azienda e la provenienza: su una stampa
incoerente la frase giusta è quella della coerenza, non quella della forma.

---

### Codici errore

Li solleva la regola, `documenti.fn_guard_versione_contesto`:

* `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` — la forma del contesto non è quella della versione;
* `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` — il contesto non dichiara la sua forma come numero intero.

---

### Test

* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — stessa forma, forma diversa, forma assente, forma
  scritta come testo, e l'ordine dei controlli.

---

### Note di migrazione

* 2026-09-30 — nasce il controllo.

---

{% include-markdown "signature-core.md" %}
