## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset_widget`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il preset che la riga compone
> * [ui.widget](/dbzero/ui/tabelle/widget) — il widget proposto
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool della dashboard
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — il gemello delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — legge i widget del preset di base
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — una riga cambiata sposta la data del contenuto del preset

---

### 🎯 Scopo Principale

`ui.dashboard_preset_widget` è la **composizione di un preset di dashboard**: quali widget propone, in
che ordine, e quali mostra subito. Una riga per coppia (preset, widget).

---

### Visibile o solo disponibile

Con `visibile` vero il widget è una card della dashboard; con `visibile` falso il preset lo offre nella
personalizzazione senza mostrarlo. Così un preset può proporre molti widget e mostrarne pochi.

L'ordine è quello di `ordine`. I widget del pool che il preset non nomina la risoluzione li aggiunge in
coda, invisibili.

---

### Una riga cambiata è un preset cambiato

Una composizione cambiata sposta la chiave `widget` di `contenuto_aggiornato_il` del preset: è ciò che
accende il banner «preset aggiornato» a chi ha scelto i suoi widget partendo da quel preset. Lo giudica a
fine transazione un trigger differito
([trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset)), sull'impronta
della composizione: una riscrittura uguale non sposta niente, anche quando passa da un DELETE e da un
INSERT separati; una riga spostata da un preset all'altro guarda tutti e due.

---

### Una parte, non un'entità

La riga non ha `attivo`. Le due FK sono in eccezione alla regola ATTIVO: un preset ha sempre i suoi
widget, e contarli come figli vivi impedirebbe di spegnerlo; un widget proposto da un preset si spegne lo
stesso. Spegnere il widget lo toglie dal preset alla risoluzione. Cancellare il preset cancella le sue
righe; un widget proposto da un preset non si cancella (FK senza azione).

---

### ⚠️ Che cosa oggi non copre

* **Il widget può non essere nel pool della dashboard.** La FK punta al catalogo globale dei widget, non al
  pool della dashboard del preset, e nessun guard lo controlla: la risoluzione toglie il widget, ma il
  preset resta la base.
* **Un widget spento non cambia la data del contenuto.** Il preset perde una card senza che il banner si
  accenda.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

La tabella non solleva codici propri. La coppia ripetuta arriva come violazione della chiave primaria.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — i widget del preset riscritti
  uguali non spostano la data, un widget cambiato sposta la sola chiave `widget`.
* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — i widget del preset di sistema e di ruolo nella
  risoluzione.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella.
* 2026-11-08 — una riga cambiata sposta `contenuto_aggiornato_il` del preset, non più `data_update`; le due
  FK entrano in eccezione alla regola ATTIVO.
* 2026-11-20 — la composizione si giudica a fine transazione, sull'impronta: si sposta la chiave `widget`.

---

{% include-markdown "signature-core.md" %}
