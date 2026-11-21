## 📘 Documentazione Concettuale – Tabella `ui.dashboard_widget`

> **Ultimo aggiornamento**: 21 novembre 2026
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
> * [ui.trgfn_ui_dashboard_widget_guard_in_uso](/dbzero/ui/funzioni/trgfn_ui_dashboard_widget_guard_in_uso) — un widget proposto da un preset non esce dal pool
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

### ⛔ Un widget proposto da un preset non esce dal pool

Un preset di dashboard può proporre solo widget del pool della sua dashboard (un vincolo composto sulla
composizione lo chiede). Togliere dal pool un widget che un preset propone è rifiutato con
`E_UI_WIDGET_IN_USO`, e il messaggio nomina i preset
([trgfn_ui_dashboard_widget_guard_in_uso](/dbzero/ui/funzioni/trgfn_ui_dashboard_widget_guard_in_uso)): si
toglie prima il widget dai preset, o si cancellano i preset, poi dal pool. È la stessa regola delle
colonne delle liste citate da un preset. Le preferenze non bloccano: una preferenza che nomina un widget
uscito dal pool lo perde alla risoluzione.

---

### Una parte, non un'entità

La riga non ha `attivo`, e le due FK sono in eccezione alla regola ATTIVO: un widget nel pool si spegne
lo stesso, e una dashboard non si ferma sul suo pool. Spegnere il widget lo toglie dalla dashboard alla
risoluzione. Un widget nel pool non si cancella (FK senza azione), e nemmeno la dashboard.

---

### ⚠️ Che cosa oggi non copre

* **L'ordine di default può essere uguale per due widget.** Nessun vincolo lo impedisce, e l'ordine fra i
  due non è determinato.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

* `E_UI_WIDGET_IN_USO` — si toglie dal pool un widget che un preset della dashboard propone.
* La coppia ripetuta arriva come violazione della chiave primaria.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — il catalogo del pool, il widget nuovo aggiunto
  invisibile e contato.
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — togliere dal pool un widget proposto è rifiutato col nome
  del preset; tolto dal preset, esce.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella.
* 2026-11-08 — le due FK entrano in eccezione alla regola ATTIVO.
* 2026-11-21 — un widget proposto da un preset non esce più dal pool: prima il preset continuava a
  nominarlo.

---

{% include-markdown "signature-core.md" %}
