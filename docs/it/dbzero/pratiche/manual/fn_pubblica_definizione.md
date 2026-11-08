## 📘 Documentazione Concettuale – Funzione `pratiche.fn_pubblica_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — la definizione che si pubblica
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — gli step della definizione
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — il grafo che non deve avere cicli
>
> Approfondimento funzioni:
>
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) · [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) · [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) — le strade che producono una bozza
> * [pratiche.trgfn_workflow_definizioni_guard](/dbzero/pratiche/funzioni/trgfn_workflow_definizioni_guard) — il guard delle transizioni di stato della definizione

---

### 🎯 Scopo Principale

`pratiche.fn_pubblica_definizione` valida una definizione in `BOZZA` e la porta a `PUBBLICATA`, ritirando
nella stessa transazione la precedente pubblicata dello stesso perimetro. Restituisce l'id della
definizione pubblicata.

---

### Le validazioni

La pubblicazione si rifiuta, con `E_DEFINIZIONE_NON_PUBBLICABILE` e il motivo, se:

1. la definizione non è in `BOZZA`;
2. non ha nessuno step attivo;
3. il grafo dei prerequisiti dei suoi step ha un ciclo, anche lungo più passaggi. Il prerequisito di sé
   stesso lo esclude già un `CHECK` della tabella dei prerequisiti.

Che una definizione abbia al massimo uno step che chiude la pratica lo garantisce già un indice unico.

---

### ⭐ Una sola pubblicata per perimetro

Il perimetro è la coppia tipo di prestazione ed emittente fiscale: il preset (senza emittente) e i fork
di un emittente sono perimetri distinti, e non si toccano. Un indice unico parziale ammette una sola
`PUBBLICATA` per perimetro, e per questo la funzione **ritira prima** la vecchia e **poi** pubblica la
nuova: nell'ordine inverso le due righe colliderebbero sull'indice.

Le due transizioni, `PUBBLICATA → RITIRATA` sulla precedente e `BOZZA → PUBBLICATA` sulla nuova, passano
dal guard della definizione, che le ammette.

---

### Accesso

La funzione è `SECURITY DEFINER` con `search_path` fisso: gli aggiornamenti di stato girano come
proprietario, e il ruolo applicativo li esegue senza permessi di scrittura diretti sulla tabella delle
definizioni. L'esecuzione è concessa al solo ruolo applicativo; chi può pubblicare lo decide il backend,
che riserva l'operazione al super admin.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — id assente o non positivo.
* `E_VALORE_MANCANTE` — la definizione non esiste.
* `E_DEFINIZIONE_NON_PUBBLICABILE` — non in `BOZZA`, nessuno step attivo, oppure ciclo nei prerequisiti.

---

### Test

* `pratiche/test-workflow-definizioni-fase2` — pubblicazione atomica col ritiro della precedente; ciclo e
  definizione non in bozza rifiutati.

---

### Note di migrazione

* 2026-07-03 — nasce con le definizioni versionate, e lo stesso giorno diventa `SECURITY DEFINER` con
  l'esecuzione ristretta al ruolo applicativo.

---

{% include-markdown "signature-core.md" %}
