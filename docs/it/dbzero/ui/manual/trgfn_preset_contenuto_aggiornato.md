## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preset_contenuto_aggiornato`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — preset di lista: contenuto è ordinamento, filtri e righe per pagina
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — preset di dashboard: contenuto è il numero massimo di widget
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — lo snapshot che la data confronta
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — lo snapshot delle dashboard
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la stessa data, mossa dalle righe del preset
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il flag «preset aggiornato» delle liste
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — il flag delle dashboard
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — l'audit, che è un'altra data

---

### 🎯 Scopo Principale

`ui.trgfn_preset_contenuto_aggiornato` porta `contenuto_aggiornato_il` di un preset all'ora della
transazione quando cambia il **contenuto** della testata del preset. È la data che i due resolver
confrontano con lo snapshot salvato nella preferenza per accendere il banner «preset aggiornato».
La usano i preset di lista e quelli di dashboard.

---

### ⭐ Che cosa è contenuto lo dice il trigger, non la funzione

La funzione scrive soltanto la data. Quali colonne sono contenuto lo dice la condizione `WHEN` di
ciascun trigger `BEFORE UPDATE` che la monta:

* su [lista_preset](/dbzero/ui/tabelle/lista_preset), l'ordinamento di default, i filtri di
  default e le righe per pagina;
* su [dashboard_preset](/dbzero/ui/tabelle/dashboard_preset), il numero massimo di widget.

Così la funzione è una sola per le due famiglie, e una colonna di contenuto nuova si aggiunge al
`WHEN` della sua tabella.

---

### Non è l'audit

`data_update` è l'audit del framework e si sposta a ogni UPDATE, anche se riscrive la riga uguale
(il seed lo fa a ogni giro) o tocca solo `attivo`. Se il banner guardasse l'audit si accenderebbe a
tutti a ogni rilascio. Il `WHEN` confronta valore vecchio e nuovo: una riscrittura uguale non
sposta la data del contenuto. Codice, descrizione, ambito, `is_default` e `attivo` non sono
contenuto.

All'INSERT il trigger non c'è: la data nasce col default della colonna.

Il contenuto che sta nelle righe del preset (colonne, widget) lo segue l'altra funzione,
[trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset).

---

### ⚠️ Che cosa oggi non copre

* **La data si scrive anche a mano.** Un UPDATE che cambia solo `contenuto_aggiornato_il`, o un
  INSERT che la indica, passa col valore scritto: l'applicazione può spostare la data avanti o
  indietro senza cambiare il contenuto, e accendere o spegnere il banner a tutti.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — testata del preset di lista
  riscritta uguale e cambiata; i due trigger sulle funzioni condivise.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — lo stesso sul preset di
  dashboard.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — col trigger d'audit montato, un UPDATE che non tocca il
  contenuto sposta `data_update` e non la data del contenuto; un UPDATE del contenuto le sposta
  tutte e due.

---

### Note di migrazione

* 2026-11-01 — la data del contenuto nasce per la preferenza per chiave, scritta in `data_update`
  da `trgfn_preset_data_update_contenuto`.
* 2026-11-08 — prende il posto di `trgfn_preset_data_update_contenuto` e scrive la colonna nuova
  `contenuto_aggiornato_il`; `data_update` torna a essere l'audit del framework.

---

{% include-markdown "signature-core.md" %}
