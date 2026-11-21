## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_dashboard_widget_guard_in_uso`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool su cui il guard è montato
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i widget che i preset propongono
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — i preset nominati nel rifiuto

---

### 🎯 Scopo Principale

`ui.trgfn_ui_dashboard_widget_guard_in_uso` impedisce di togliere dal pool di una dashboard un widget che
un preset di quella dashboard propone. Il rifiuto nomina i preset.

---

### Prima si toglie dai preset, poi dal pool

Un preset di dashboard può proporre solo widget del pool della sua dashboard. Se il widget uscisse dal
pool, il preset ne proporrebbe uno che la dashboard non ha. Per toglierlo si toglie prima il widget dai
preset che lo propongono (o si cancellano i preset), poi dal pool. Un preset cancellato porta via la sua
composizione, e da quel momento non blocca più.

⭐ Il vincolo fra la composizione e il pool rifiuterebbe comunque la cancellazione, ma con un errore di
vincolo e il suo nome. Il guard parla prima, con un codice di dominio e i codici dei preset nel messaggio,
così chi toglie il widget sa da dove cominciare. Il vincolo resta come rete.

È la stessa regola delle colonne delle liste: una colonna che un preset nomina non si cancella.

---

### Codici errore

* `E_UI_WIDGET_IN_USO` — il widget è proposto da uno o più preset della dashboard; il messaggio dice il
  codice del widget e quelli dei preset.

---

### Test

* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — togliere dal pool un widget proposto è rifiutato col nome
  del preset; tolto dal preset, esce dal pool.

---

### Note di migrazione

* 2026-11-21 — nasce. Prima togliere un widget dal pool non toccava i preset che lo proponevano: il preset
  continuava a nominarlo, e la risoluzione lo toglieva.

---

{% include-markdown "signature-core.md" %}
