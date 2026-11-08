## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_chiusura_pratica`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — gli step della definizione della pratica
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — i prerequisiti, anche condizionati all'esito
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le istanze eseguite
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — dice se uno step è ancora percorribile
> * [pratiche.fn_check_pratica_chiudibile](/dbzero/pratiche/funzioni/fn_check_pratica_chiudibile) — ne usa il predicato «nessun obbligatorio bloccante»
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — il guard sulla transizione a `CHIUSA`

---

### 🎯 Scopo Principale

`pratiche.fn_check_chiusura_pratica` è un controllo puro che fotografa gli step della pratica ai fini
della chiusura: per ogni template attivo della definizione della pratica dice se è stato eseguito, se è
ancora percorribile e se blocca la transizione a `CHIUSA`. Non solleva errori.

È anche la fonte del backend per rendere il percorso a bivi: da «eseguito» e «percorribile» si ricava lo
stato visuale di ogni step (completato, eseguibile, ramo chiuso).

---

### Le tre risposte

* `completato` — esiste un'istanza `COMPLETATO` dello step, con qualunque esito: uno step eseguito con
  esito negativo è comunque stato fatto. Le istanze annullate non contano.
* `percorribile` — tutti i prerequisiti dello step sono soddisfatti, tenendo conto dell'esito
  richiesto. Il **ramo morto** di un bivio, dove il predecessore ha dato l'esito opposto a quello
  richiesto, risulta non percorribile.
* `bloccante` — lo step è obbligatorio, non eseguito e ancora percorribile: blocca la chiusura.

---

### ⭐ Obbligatorio vincola solo se il suo percorso è attivabile

* Il ramo morto di un bivio non blocca mai.
* Uno step a valle di un predecessore non eseguito non blocca: se il predecessore è obbligatorio, blocca
  già lui.

---

### Gli step sono quelli della definizione della pratica

La funzione considera i template della definizione **fissata sulla pratica** (`definizione_id`), non
quelli del tipo di prestazione: quando più definizioni condividono lo stesso tipo, una pratica guarda
solo gli step della propria edizione.

---

### Chi la usa

* Il guard sulla transizione a `CHIUSA`.
* `pratiche.fn_check_pratica_chiudibile`, e attraverso di lei l'autochiusura e il controllo prima del
  completamento.
* Il percorso del backend, per la resa a bivi.

---

### Test

* `pratiche/test-bivi-condizionali` — ramo morto, percorribilità ed esito.
* `pratiche/test-fork-chiusura-per-definizione` — gli step si leggono dalla definizione della pratica.

---

### Note di migrazione

* 2026-07-03 — gli step si leggono dalla definizione fissata sulla pratica invece che dal tipo di
  prestazione, per i fork delle definizioni.

---

{% include-markdown "signature-core.md" %}
