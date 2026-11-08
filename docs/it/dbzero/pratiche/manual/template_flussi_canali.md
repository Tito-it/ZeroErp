## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_canali`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — lo step esposto
> * [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche) — il catalogo dei canali
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — protegge i collegamenti di un'edizione emessa

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi_canali` collega gli step di workflow ai canali su cui sono
esposti fuori dal gestionale (per esempio il portale clienti o l'app dei tecnici): una riga per coppia
(template, canale).

---

### Le regole

* Un template può stare su nessuno, uno o più canali; la stessa coppia non si ripete.
* Un canale nuovo si aggiunge a catalogo in `config.canali_pratiche` e si collega qui, senza toccare il
  codice.
* La visibilità esterna è una proprietà dello step, non della singola pratica: la dicono questa tabella
  e la `direzione` del template.
* Il collegamento si spegne con `attivo`. Un collegamento attivo vuole il template e il canale attivi,
  e un template con collegamenti attivi non si spegne.
* Cancellando il template i suoi collegamenti spariscono con lui; un canale collegato non si cancella.

---

### ⛔ I collegamenti seguono l'edizione

Il template appartiene a un'edizione di workflow, e i suoi collegamenti con lui: la copia di un'edizione
li porta con sé. Su un'edizione di un emittente già pubblicata o ritirata i collegamenti non si
inseriscono né si modificano, e su una pubblicata non si cancellano: la correzione passa da una nuova
versione.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — modifica di un collegamento di un'edizione emessa.

---

### Test

* `pratiche/test-canali-flussi` — collegamento, unicità della coppia, chiave esterna verso il canale.
* `pratiche/test-definizione-ritirata-edit-freeze` — la protezione dei figli di un'edizione ritirata, provata su prerequisiti e formule.

---

### Note di migrazione

* 2026-03-07 — ritirata la colonna `solo_interna` di `pratiche.pratiche`: la visibilità esterna si governa dallo step (questa
  tabella e la `direzione`), non dalla pratica.
* 2026-06-18 — la tabella, nata con l'audit del solo inserimento, riceve l'audit degli aggiornamenti.

---

{% include-markdown "signature-core.md" %}
