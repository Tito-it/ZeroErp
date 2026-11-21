## 📘 Documentazione Concettuale – Tabella `ui.dashboard_widget`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — la dashboard del pool
> * [ui.widget](/dbzero/ui/tabelle/widget) — il catalogo globale dei widget
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i widget che un preset propone
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — usa il pool come catalogo, per l'aggiunta dei nuovi e come filtro

---

### 🎯 Scopo Principale

`ui.dashboard_widget` è il **pool di una dashboard**: quali widget del catalogo globale può mostrare, e
in che ordine quando nessuno ha scelto. Una riga per coppia (dashboard, widget).

Il widget è globale ([ui.widget](/dbzero/ui/tabelle/widget)): questa tabella lo rende disponibile a più
dashboard senza ricopiarne la definizione.

---

### Il pool decide che cosa la dashboard può mostrare

La funzione di risoluzione legge il pool tre volte:

* **catalogo**: senza preferenza né preset, la dashboard mostra tutti i widget accesi del pool, visibili,
  nell'ordine di `ordine_default`;
* **widget nuovi**: un widget acceso del pool che la configurazione non nomina si aggiunge in coda,
  invisibile, e si conta in `widget_nuovi`;
* **filtro**: un widget fuori dal pool non compare, anche se una preferenza o un preset lo nominano.

Togliere un widget dal pool lo toglie quindi a tutti, preferenze comprese; aggiungerlo lo offre a tutti
come novità.

---

### Una parte, non un'entità

La riga non ha `attivo`, e le due FK sono in eccezione alla regola ATTIVO: un widget nel pool si spegne
lo stesso, e una dashboard non si ferma sul suo pool. Spegnere il widget lo toglie dalla dashboard alla
risoluzione. Un widget nel pool non si cancella (FK senza azione), e nemmeno la dashboard.

---

### ⚠️ Che cosa oggi non copre

* **Togliere un widget dal pool non tocca i preset che lo propongono.** Il preset continua a nominarlo, e la
  sua data del contenuto non si sposta.
* **L'ordine di default può essere uguale per due widget.** Nessun vincolo lo impedisce, e l'ordine fra i
  due non è determinato.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

La tabella non solleva codici propri. La coppia ripetuta arriva come violazione della chiave primaria.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — il catalogo del pool, il widget nuovo aggiunto
  invisibile e contato.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella.
* 2026-11-08 — le due FK entrano in eccezione alla regola ATTIVO.

---

{% include-markdown "signature-core.md" %}
