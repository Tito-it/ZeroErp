## 📘 Documentazione Concettuale – Funzione `pratiche.fn_copia_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — l'edizione copiata e quella nuova
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — gli step di template, rimappati per codice
>
> Approfondimento funzioni:
>
> * [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) — copia verso un altro emittente, con provenienza
> * [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) — copia nello stesso perimetro
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — pubblica la bozza nata qui
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — rimappa per codice, a runtime, la destinazione delle regole di generazione

---

### 🎯 Scopo Principale

`pratiche.fn_copia_definizione` è il motore di copia di un'edizione di workflow: replica la testata,
gli step di template e tutta la loro configurazione in una nuova edizione in `BOZZA`, rimappando gli
step per codice. Restituisce l'id della nuova edizione.

La usano `pratiche.fn_fork_definizione` e `pratiche.fn_nuova_versione_definizione`.

---

### ⭐ L'unico punto che elenca che cosa si copia

Il perimetro della copia è scritto qui e in nessun altro posto: aggiungere al modello una tabella di
configurazione posseduta da uno step vuol dire aggiungerla qui, e basta.

| Che cosa | Come si rimappa |
| --- | --- |
| Gli step di template | Codice conservato, id nuovo, edizione nuova; compreso il tipo di documento atteso |
| Canali, handler sugli eventi, competenze, collegamenti di avanzamento su proiezione | Lo step, per codice |
| Prerequisiti, formule di tempo | Entrambi i lati, che sono step della stessa edizione |
| Regole di generazione | Lo step di origine per codice; la destinazione resta quella della sorgente, e `pratiche.fn_genera_pratica_da_flusso` la rimappa per codice a runtime nell'edizione della pratica figlia |

Non si copiano le istanze (flussi, calcoli di tempo) né i valori generati e di audit.

⭐ **Il codice è la chiave del rimappaggio** perché è unico per edizione: ogni riga copiata ritrova il
suo step nuovo cercando, nella nuova edizione, lo stesso codice dello step vecchio.

---

### Le regole della nuova edizione

* Nasce sempre in `BOZZA`, quindi non collide con l'edizione pubblicata del perimetro.
* La versione è la successiva nel perimetro di destinazione (tipo di prestazione ed emittente).
* Descrizione e metadati della testata vengono dalla sorgente.
* L'emittente di destinazione vuoto indica il preset; valorizzato, l'edizione di quella società.
* Con la provenienza attiva (il fork) la testata ricorda l'edizione sorgente e la sua versione, per il
  confronto col preset; senza (la nuova versione) non ricorda niente.

La funzione non controlla lo stato della sorgente né l'unicità della bozza: lo fanno i due wrapper, ognuno
con la sua regola.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — sorgente assente o non positiva.
* `E_VALORE_MANCANTE` — la sorgente non esiste.

---

### Test

* `pratiche/test-workflow-definizioni-fase2` — il fork e il rimappaggio doppio di prerequisiti e
  formule.

---

### Note di migrazione

* 2026-07-03 — nasce con le definizioni versionate (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}
