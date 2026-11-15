## 📘 Documentazione Concettuale – Funzione `documenti.fn_risolvi_template_applicabile`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello, standard o dell'azienda
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la versione con cui il modello stampa
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — la sede unica di «può stampare»
> * [documenti.vw_template_risoluzione_emittente](/dbzero/documenti/views/vw_template_risoluzione_emittente) — la stessa regola, letta dalla lista Modelli documento
>
> Approfondimento funzioni:
>
> * [documenti.fn_template_esito_risoluzione](/dbzero/documenti/funzioni/fn_template_esito_risoluzione) — la regola dei due livelli
> * [documenti.fn_template_motivo_non_coerente](/dbzero/documenti/funzioni/fn_template_motivo_non_coerente) — se il modello indicato va bene per il documento
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — passa da qui per sapere da quale versione parte una copia
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §3, con quale modello si stampa un documento

---

### 🎯 Scopo Principale

La porta unica della stampa: dice con quale modello, e con quale versione di quel modello, si stampa
un documento di una sorgente per un'azienda. Il backend la chiama prima del render e non ne riscrive
la regola.

Le strade sono due. Senza un modello indicato, il modello lo **sceglie** la regola dei due livelli.
Con un modello indicato, il modello si **verifica**: deve essere adatto al documento e deve poter
stampare oggi. In tutti e due i casi la risposta è una riga sola: il modello, il livello da cui viene
(`EMITTENTE`, `STANDARD` o `INDICATO`) e la versione.

---

### Conta solo un modello che può stampare

Un modello entra nella scelta solo se compare in `vw_template_versioni_stampabili`: è attivo e ha una
versione attiva, fuori bozza e valida alla data operativa. «Attivo» non vuol dire «pronto»: la copia
appena creata con «personalizza» ha solo una bozza, e finché non la si pubblica l'azienda continua a
stampare con lo standard. Lo stesso vale per una versione spenta e per una versione che parte da una
data futura.

La condizione vale per tutti i passi: la deduzione del tipo, il livello dell'azienda, il livello
standard e il modello indicato.

---

### ⭐ La versione esce con il modello

Insieme al modello la funzione restituisce la versione che lo rende stampabile. Chi stampa usa quella,
e non la cerca di nuovo con filtri suoi: se lo facesse, «può stampare» sarebbe scritto in due posti, e
il giorno che i due posti dicessero cose diverse la funzione sceglierebbe un modello che poi non si
riesce a stampare. Per ogni modello e ogni data la versione è al più una, perché le versioni attive
fuori bozza di uno stesso modello non si sovrappongono nel tempo.

---

### Senza modello indicato: la regola dei due livelli

La regola è di `fn_template_esito_risoluzione`; qui gli esiti negativi diventano errori.

1. **L'azienda ha almeno un modello suo che può stampare** per quel tipo e quella sorgente: si usa il
   suo predefinito, se anche lui può stampare. Altrimenti la stampa si ferma con
   `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`, e lo standard **non** entra: un modello pubblicato
   dell'azienda vuol dire «per questo documento uso i miei», e un predefinito dimenticato non deve far
   uscire il documento con la grafica sbagliata senza che nessuno se ne accorga.
2. **L'azienda non ha nessun modello suo che può stampare**: si usa il predefinito standard. Se manca o
   non può stampare, `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`.

Spegnere tutti i propri modelli di un tipo riporta allo standard: è voluto.

---

### Il tipo di documento si deduce solo se non c'è scelta

Il tipo si può omettere. In quel caso la funzione guarda i modelli della sorgente che l'azienda può
usare (i suoi e gli standard) e che possono stampare: se hanno un tipo solo, vale quello; se ne hanno
più d'uno, la funzione non sceglie a caso e solleva `E_DOCUMENTI_TEMPLATE_AMBIGUO`. Una bozza di un
altro tipo non conta.

---

### Con il modello indicato: si verifica, non si sceglie

1. **È un modello?** Un id che non è un modello è un chiamante rotto:
   `E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO`.
2. **È adatto al documento?** Lo dice `fn_template_motivo_non_coerente`: stessa sorgente, stesso tipo
   (se indicato), stessa azienda oppure standard. Se no, `E_DOCUMENTI_TEMPLATE_NON_COERENTE` con il
   motivo (`SORGENTE`, `TIPO`, `EMITTENTE`).
3. **Può stampare oggi?** Se no, `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE` con il motivo: `MODELLO_SPENTO`
   se il modello è disattivato, `NESSUNA_VERSIONE_VALIDA` se è attivo ma non ha una versione valida
   oggi.
4. Livello `INDICATO`, con la versione.

È la stessa regola che il trigger di coerenza applica alla scrittura del documento generato, detta
prima del render. Uno standard indicato è sempre adatto, anche per un'azienda che ha modelli suoi: la
regola dei due livelli vale per la scelta, non per una scelta già fatta da chi stampa.

---

### Chi la chiama, e con quali permessi

La chiamano il servizio di generazione dei documenti del backend e
`fn_personalizza_template_standard`. Gira con i permessi di chi la chiama e non rifà il perimetro
delle aziende: l'azienda è quella del documento, che il chiamante ha già letto con i suoi permessi, e
gli standard servono a tutti.

---

### ⚠️ Che cosa oggi non copre

* **Il tipo omesso su una sorgente senza modelli che stampano.** La deduzione non trova nessun tipo,
  la regola dei due livelli risponde `NON_RISOLTO`, e il messaggio di `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`
  nomina il documento come «?», perché il valore che porta è la descrizione del tipo, che non c'è.

---

### Codici errore

* `E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO` — sorgente o azienda assenti o non positive, tipo o
  modello non positivi, un id che non è un modello. Solo un chiamante rotto lo produce.
* `E_DOCUMENTI_TEMPLATE_AMBIGUO` — tipo omesso su una sorgente i cui modelli stampabili hanno più tipi.
* `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO` — l'azienda ha modelli suoi che stampano, nessuno predefinito
  o il predefinito non stampa. Rimedia l'operatore.
* `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` — né l'azienda né lo standard hanno un predefinito che stampa.
* `E_DOCUMENTI_TEMPLATE_NON_COERENTE` — il modello indicato non è adatto al documento.
* `E_DOCUMENTI_TEMPLATE_NON_STAMPABILE` — il modello indicato oggi non può stampare. Rimedia l'operatore.

---

### Test

* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — la regola dei due livelli, la
  deduzione del tipo, gli argomenti rotti, la versione restituita.
* `db/pgtap/documenti/test-documenti-template-standard-app-v1.sql` — la lettura come applicazione.
* `db/pgtap/documenti/test-documenti-template-porta-unica-v1.sql` — il modello indicato e la parità con
  la vista della lista.
* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — fra la pubblicazione di
  una versione futura e la sua partenza stampa ancora la versione superata.

---

### Note di migrazione

* 2026-10-20 — nasce: un'azienda senza modelli suoi stampa con lo standard. Lo stesso giorno conta solo
  un modello che può stampare, e la funzione restituisce anche la versione.
* 2026-10-21 — diventa la porta unica: accetta il modello indicato, e «può stampare» passa nella vista
  delle versioni stampabili.
* 2026-11-14 — per la vista una versione superata da una pubblicazione con partenza futura stampa fino
  alla vigilia della nuova.

---

{% include-markdown "signature-core.md" %}
