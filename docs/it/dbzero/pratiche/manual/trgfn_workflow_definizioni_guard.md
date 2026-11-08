## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_workflow_definizioni_guard`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — la tabella sorvegliata: le edizioni del workflow
>
> Approfondimento funzioni:
>
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — la strada che usa le due transizioni ammesse
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) — la struttura dell'edizione, cioè i template
> * [pratiche.trgfn_pratiche_guard_pin_immutabile](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_pin_immutabile) — l'edizione fissata su una pratica
> * [pratiche.trgfn_flussi_guard_definizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_definizione) — i flussi restano nell'edizione della loro pratica

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_workflow_definizioni_guard` protegge il ciclo di vita di
un'edizione di workflow: ammette solo i due passaggi di stato previsti e, fuori dalla bozza, rende
immutabile l'intestazione.

---

### Le due regole

| Regola | Che cosa dice | Errore |
| --- | --- | --- |
| Transizioni | Lo stato cambia solo da `BOZZA` a `PUBBLICATA` e da `PUBBLICATA` a `RITIRATA` | `E_DEFINIZIONE_TRANSIZIONE_NON_AMMESSA` |
| Intestazione | Fuori da `BOZZA`, non cambiano tipo di prestazione, emittente, versione, preset di origine e versione di origine | `E_DEFINIZIONE_PUBBLICATA_IMMUTABILE` |

Ogni altro passaggio è vietato: da bozza a ritirata, da pubblicata a bozza, qualunque uscita da
ritirata. Una bozza da scartare si cancella, non si ritira.

---

### Le regole del montaggio

* Scatta `BEFORE UPDATE`, riga per riga, su `pratiche.workflow_definizioni`, solo quando l'aggiornamento
  tocca lo stato o una colonna dell'intestazione.
* `descrizione` e `meta` restano fuori dall'evento: sono display, correggibili sempre, anche su
  un'edizione pubblicata. Un aggiornamento che tocca solo quelle non fa scattare il trigger.
* L'inserimento non è vincolato: bootstrap e backfill creano edizioni già `PUBBLICATA`. La matrice delle
  transizioni vale sugli aggiornamenti.
* Qui si protegge l'intestazione; la struttura dell'edizione, i template e i loro figli, la proteggono
  `pratiche.trgfn_template_flussi_guard_immutabile` e
  `pratiche.trgfn_template_flussi_figli_guard_immutabile`.

---

### Codici errore

* `E_DEFINIZIONE_TRANSIZIONE_NON_AMMESSA` — passaggio di stato fuori dai due ammessi.
* `E_DEFINIZIONE_PUBBLICATA_IMMUTABILE` — modifica dell'intestazione di un'edizione non in bozza.

---

### Test

* `pratiche/test-workflow-definizioni-fase1` — le transizioni ammesse e vietate, e l'intestazione
  immutabile fuori dalla bozza.

---

### Note di migrazione

* 2026-07-03 — nasce come primo presidio delle edizioni versionate: protegge intestazione e
  transizioni, mentre l'immutabilità dei template arriva il giorno dopo con i guard sulla struttura.

---

{% include-markdown "signature-core.md" %}
