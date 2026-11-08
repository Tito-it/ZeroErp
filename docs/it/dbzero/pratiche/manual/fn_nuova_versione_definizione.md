## 📘 Documentazione Concettuale – Funzione `pratiche.fn_nuova_versione_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni di una definizione, e i loro stati
>
> Approfondimento funzioni:
>
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — il motore di copia che questa funzione chiama
> * [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) — la copia verso un altro emittente
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — pubblica la bozza e ritira la pubblicata precedente

---

### 🎯 Scopo Principale

`pratiche.fn_nuova_versione_definizione` crea una nuova versione in `BOZZA` di un'edizione di workflow
`PUBBLICATA`, nello stesso perimetro (tipo di prestazione ed emittente, preset compreso). Restituisce
l'id della nuova bozza.

È il modo di modificare in sicurezza un'edizione pubblicata, che è immutabile: si crea la bozza, la si
modifica, la si pubblica, e `pratiche.fn_pubblica_definizione` ritira la pubblicata precedente. Le
pratiche in volo restano sull'edizione con cui sono nate.

---

### Le regole

* **La sorgente deve essere `PUBBLICATA`.** La nuova versione si deriva dall'edizione pubblicata del
  perimetro, non da una bozza o da un'edizione ritirata.
* **Una sola bozza per perimetro.** Se il perimetro ha già una bozza aperta la funzione si ferma: è la
  stessa invariante che un indice unico garantisce sulla tabella.
* La copia la fa `pratiche.fn_copia_definizione`, nello stesso perimetro dell'emittente della sorgente
  e senza provenienza: non è un fork.

⚠️ **Nuova versione e fork non sono la stessa cosa.** Il fork porta la definizione verso un altro
emittente e ne ricorda la provenienza, per il confronto col preset; la nuova versione resta nello
stesso perimetro, col numero di versione successivo.

---

### Accesso

La funzione è `SECURITY DEFINER` con un `search_path` fisso: le scritture interne girano come
proprietario, e il ruolo applicativo la esegue senza permessi di scrittura diretti sulle tabelle della
configurazione. L'esecuzione è concessa al solo ruolo applicativo; il backend la riserva al super
admin.

---

### Codici errore

* `E_VALORE_MANCANTE` — la definizione sorgente non esiste.
* `E_DEFINIZIONE_NO_PUBBLICATA` — la sorgente è in bozza o ritirata.
* `E_DEFINIZIONE_BOZZA_ESISTENTE` — il perimetro ha già una bozza aperta.

---

### Test

* `pratiche/test-workflow-definizioni-fase2` — la nuova versione e la pubblicazione che ritira la
  precedente.
* `pratiche/test-definizione-bozza-unica` — i due guard sulla sorgente pubblicata e sulla bozza unica.

---

### Note di migrazione

* 2026-07-03 — nasce con le definizioni versionate, `SECURITY DEFINER` dallo stesso giorno
  (brief-db-step-dominio-e-definizioni-versionate).
* 2026-07-04 — arrivano i guard sulla sorgente pubblicata e sulla bozza unica per perimetro.

---

{% include-markdown "signature-core.md" %}
