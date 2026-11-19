## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preset_riga_tocca_preset`

> **Ultimo aggiornamento**: 18 novembre 2026
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
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la stessa data, mossa dalla testata
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il flag «preset aggiornato» delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — il flag delle dashboard

---

### 🎯 Scopo Principale

`ui.trgfn_preset_riga_tocca_preset` sposta `contenuto_aggiornato_il` di un preset all'ora della
transazione quando una sua riga di composizione si aggiunge, si toglie o cambia: una colonna di un
preset di lista, un widget di un preset di dashboard. Una riga cambiata è un cambio del preset, e
il banner «preset aggiornato» lo deve vedere.

---

### Una funzione, due famiglie

È montata come trigger `AFTER INSERT OR UPDATE OR DELETE`, riga per riga, su
[lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) e su
[dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget). L'argomento del trigger è la
tabella del preset da aggiornare; la riga figlia porta il preset nella colonna `preset_id`.

---

### Quale preset si tocca

* Una riga aggiunta tocca il suo preset; una riga tolta, il preset da cui è tolta.
* Una riga spostata su un altro preset li tocca **tutti e due**: tutti e due cambiano contenuto.
* Una riga riscritta **uguale** non tocca niente. Il confronto è sulla riga intera, perché le
  tabelle figlie non hanno colonne d'audit che lo sporcherebbero; il seed riscrive ogni riga a
  ogni giro, e altrimenti accenderebbe il banner a tutti.
* Se il preset stesso si cancella, le righe se ne vanno per cascata: l'aggiornamento trova zero
  righe e non fa niente.

L'aggiornamento della testata passa dai trigger della testata: l'audit registra chi ha cambiato la
composizione.

---

### ⚠️ Che cosa oggi non copre

* **Cancellare e reinserire non è «uguale».** Il servizio di amministrazione salva la composizione
  di un preset di lista cancellando tutte le righe e reinserendole: per il trigger è un cambio
  vero, anche quando la composizione salvata è identica, e il banner si accende a chi ha una
  preferenza su quel preset.
* **Le righe che il resolver non mostra.** Una riga che cita una colonna o un widget spenti sposta
  la data lo stesso, anche se il resolver non la mostrerà.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — colonna di un preset di
  lista riscritta uguale, cambiata, aggiunta e tolta; i due trigger delle liste sulle funzioni
  condivise.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — lo stesso per i widget
  di un preset di dashboard.
* Non è costruito lo spostamento di una riga da un preset a un altro.

---

### Note di migrazione

* 2026-11-01 — nasce per la preferenza per chiave, al posto della sola data della testata.
* 2026-11-08 — scrive la colonna nuova `contenuto_aggiornato_il` invece dell'audit.

---

{% include-markdown "signature-core.md" %}
