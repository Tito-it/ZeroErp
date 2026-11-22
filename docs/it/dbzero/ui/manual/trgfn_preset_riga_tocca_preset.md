## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preset_riga_tocca_preset`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — le colonne di un preset di lista
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset di lista di cui sposta la data
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i widget di un preset di dashboard
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il preset di dashboard di cui sposta la data
>
> Approfondimento funzioni:
>
> * [ui.fn_preset_impronta](/dbzero/ui/funzioni/fn_preset_impronta) — l'impronta della composizione
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la stessa data, mossa dalla testata
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il flag «preset aggiornato» delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — il flag delle dashboard

---

### 🎯 Scopo Principale

`ui.trgfn_preset_riga_tocca_preset` dice al preset che la sua composizione è cambiata: una colonna
di un preset di lista, un widget di un preset di dashboard, aggiunti, tolti o cambiati. Lo fa a
fine transazione, sull'**impronta** della composizione: una composizione riscritta uguale non è un
cambio, anche quando passa da un DELETE e da un INSERT separati.

---

### Perché a fine transazione

Il servizio di amministrazione salva la composizione di un preset cancellando tutte le righe e
reinserendole. Sono due istruzioni, e un trigger che guarda una riga, o un'istruzione, alla volta
vede «tolte tutte» e poi «aggiunte tutte»: non può sapere che alla fine la composizione è quella di
prima. Per questo la funzione è montata come **constraint trigger differito**
(`DEFERRABLE INITIALLY DEFERRED`), riga per riga, `AFTER INSERT OR UPDATE OR DELETE` su
[lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) e su
[dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget): scatta al commit, quando la
composizione è quella finale.

L'argomento del trigger è la tabella del preset; la riga figlia porta il preset in `preset_id`.

---

### L'impronta

Al commit la funzione calcola l'impronta della composizione del preset
([fn_preset_impronta](/dbzero/ui/funzioni/fn_preset_impronta)) e la confronta con
`composizione_impronta`, quella salvata sul preset. Se è diversa la scrive, e il trigger del preset
([trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato)) sposta
la chiave `colonne` (o `widget`) della data del contenuto. Se è uguale non scrive niente.

* Più righe cambiate sullo stesso preset danno più eventi: il primo scrive, gli altri trovano
  l'impronta già uguale.
* Una riga spostata su un altro preset guarda **tutti e due** i preset.
* Se il preset stesso si cancella, le righe se ne vanno per cascata e l'aggiornamento trova zero
  righe.

L'aggiornamento della testata passa dai trigger della testata: l'audit registra chi ha cambiato la
composizione, e il seed di primo impianto vede cambiare una colonna dell'installazione e registra
il preset come personalizzato. Una riscrittura uguale non lo personalizza.

---

### ⚠️ Coi vincoli immediati

Con `SET CONSTRAINTS … IMMEDIATE` (lo fanno i pgTAP) il trigger scatta a fine istruzione: un DELETE
seguito da un INSERT in due istruzioni sposta la data, perché fra le due la composizione è vuota.
Un evento in sospeso fa anche fallire, nella stessa transazione, un `ALTER TABLE` della tabella che
lo ha accodato: la composizione, non il preset. Chi scrive la composizione e poi la altera nello
stesso changeSet apre con `SET CONSTRAINTS ALL IMMEDIATE`.

---

### ⚠️ Che cosa oggi non copre

* **Le righe che il resolver non mostra.** Una riga che cita una colonna o un widget spenti cambia
  l'impronta lo stesso, anche se il resolver non la mostrerà.

---

### Codici errore

* `E_TRIGGER_ARGOMENTI_INVALIDI` — l'argomento non è `ui.lista_preset` né `ui.dashboard_preset`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — colonna di un preset di
  lista riscritta uguale, cambiata, aggiunta e tolta; coi vincoli differiti, DELETE + INSERT delle
  stesse righe non sposta niente, con un ordine cambiato sposta `colonne`.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — lo stesso per i widget
  di un preset di dashboard.
* `db/pgtap/ui/test-seed-primo-impianto-ui-installazione-v1.sql` — l'applicazione riscrive uguale la
  composizione di un preset di seed: il preset resta intatto.
* `db/pgtap/ui/test-seed-primo-impianto-ui-software-v1.sql` — il software toglie una riga dalla
  composizione di un preset personalizzato: l'impronta salvata è quella della composizione, e non
  finisce fra i valori scartati del seed.
* Non è costruito lo spostamento di una riga da un preset a un altro.

---

### Note di migrazione

* 2026-11-01 — nasce per la preferenza per chiave, al posto della sola data della testata.
* 2026-11-08 — scrive la colonna nuova `contenuto_aggiornato_il` invece dell'audit.
* 2026-11-20 — diventa un constraint trigger differito e scrive l'impronta della composizione solo
  se è cambiata: un DELETE + INSERT identico non sposta più la data.

---

{% include-markdown "signature-core.md" %}
