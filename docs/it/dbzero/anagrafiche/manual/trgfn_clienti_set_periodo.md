## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_set_periodo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella di cui scrive `periodo`
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — lo stato annullato, che non ha periodo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) — i controlli sulle date
> * [anagrafiche.fn_check_pdp_occupato](/dbzero/anagrafiche/funzioni/fn_check_pdp_occupato) — chi legge il periodo per lo stato del PDP
> * [anagrafiche.fn_clienti_stessa_chiave](/dbzero/anagrafiche/funzioni/fn_clienti_stessa_chiave) — chi lo legge per la chiave del cliente manuale
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — il subentro, che chiude il cliente uscente
> * [script.fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente) — la disdetta, che scrive la data di chiusura

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_set_periodo` scrive il periodo del cliente, dalla data di attivazione alla data di
chiusura, con il giorno di chiusura escluso. Chi scrive il cliente non lo passa: la colonna è il riflesso delle
due date.

---

### ⭐ Il periodo è la misura di «cliente presente»

Una sola colonna dice in quali giorni il cliente c'è, e la leggono tutti quelli che hanno bisogno di saperlo:

* il vincolo di esclusione `ex_clienti_no_overlap_stesso_pdp`, per cui un PDP ha un solo cliente alla volta;
* `anagrafiche.fn_check_pdp_occupato`, da cui lo stato tecnico del PDP;
* `anagrafiche.fn_clienti_stessa_chiave`, la chiave del cliente manuale.

Il periodo non guarda lo stato, salvo l'annullato: un sospeso ha il periodo e occupa. Chi vuole distinguere gli
stati lo fa da sé (la chiave del cliente manuale, per esempio, non conta il pre-contrattuale).

---

### Come lo calcola

* **Con la data di attivazione**: dall'attivazione alla chiusura, che è esclusa; senza chiusura il periodo è
  aperto.
* **Senza data di attivazione**: nessun periodo.
* **Annullato**: il trigger toglie le date di attivazione e di chiusura e il periodo. Un annullato non è mai
  esistito come fornitura, e non deve occupare niente.

Il calcolo si rifà a ogni scrittura del cliente. Il trigger non solleva errori: che le date ci siano e siano in
ordine lo controlla `anagrafiche.trgfn_clienti_guard_stato_date`, che per nome viene prima e quindi vede ancora
le date dell'annullato.

Con la chiusura esclusa, un cliente chiuso libera il PDP e la chiave **dal giorno della sua chiusura**: la
fornitura nuova può partire quel giorno.

---

### ⚠️ Che cosa oggi non copre

* **La data di chiusura ha due significati.** Il trigger la tratta come estremo escluso. I commenti delle
  colonne `data_chiusura` («inclusiva: cliente attivo fino a questo giorno») e `periodo` («fino a
  `data_chiusura+1`») dicono il contrario. `script.fn_subentro_cliente` chiude il cliente uscente al giorno
  prima dell'attivazione del nuovo, come se la chiusura fosse inclusa: con la regola del trigger, quel giorno il
  PDP non ha cliente. `script.fn_disdetta_cliente` scrive la data di cessazione così com'è, e il cliente smette
  di occupare quel giorno.
* **Un cliente chiuso il giorno stesso dell'attivazione** ha un periodo vuoto: non occupa né il PDP né la
  chiave in nessun giorno.

---

### Test

* `db/pgtap/script/test-fn-disdetta-cliente.sql` — il periodo dopo la disdetta, dall'attivazione alla data di
  cessazione esclusa.
* `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — il chiuso che libera la chiave dalla data
  di chiusura, l'annullato che non la occupa.

---

### Note di migrazione

* 2026-10-14 — i controlli sulle date (l'attivo senza attivazione, il chiuso con la chiusura prima
  dell'attivazione) passano a `anagrafiche.trgfn_clienti_guard_stato_date`, per tutti gli stati. Questo trigger
  resta il solo calcolo del periodo.

---

{% include-markdown "signature-core.md" %}
