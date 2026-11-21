## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preferenza_utente`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — la dashboard personalizzata
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il preset da cui l'utente è partito
> * [ui.widget](/dbzero/ui/tabelle/widget) — i widget che la preferenza cita per codice
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — il gemello delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — legge la preferenza e la combina con lo standard
> * [ui.trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot) — scrive la fotografia dal preset di base, a ogni salvataggio e a ogni «Ignora»
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — le chiavi del banner

---

### 🎯 Scopo Principale

`ui.dashboard_preferenza_utente` è la **scelta personale di un utente** per una dashboard: quali widget
vede, in che ordine, e quante card al massimo. Al più una riga per coppia (utente, dashboard).

---

### La preferenza porta solo le chiavi scelte

`configurazione` ha due chiavi, tutte e due facoltative: `widget` (l'elenco dei widget, ciascuno col suo
codice, l'ordine e se è visibile) e `dimensione_max`. Una chiave assente, o nulla, vuol dire «come lo
standard»: la funzione di risoluzione la prende dal preset di base o dal catalogo. Chi salva rimanda
solo le chiavi che la risoluzione dice venire dalla preferenza, più quella toccata. Il backend non
salva una preferenza senza chiavi: si toglie con la cancellazione.

Un widget si cita per `codice`, mai per `id`: l'id cambia da un ambiente all'altro. Un codice che non
corrisponde più a un widget acceso del pool della dashboard la risoluzione lo salta, senza errore.

`dimensione_max` vale solo se è un intero positivo; un valore diverso la risoluzione lo tratta come
chiave assente.

---

### La fotografia del preset di base, per il banner «preset aggiornato»

Al salvataggio il backend scrive in `preset_base_id` il preset di base che la risoluzione gli ha dato
(`preset_base`). La fotografia `preset_base_contenuto_aggiornato_il` la scrive il database: il trigger
[trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot), lo
stesso delle liste, copia la data del contenuto del preset, una per chiave (`{chiave: data}`), a ogni
scrittura che nomina la base o la fotografia, e il valore mandato dal backend non conta. Se poi il preset
cambia una chiave che la preferenza imposta, la risoluzione la mette in `preset_aggiornato_chiavi` e accende
`preset_aggiornato`; una chiave che la preferenza segue dal preset non accende niente.

L'utente spegne il banner con «Ignora», che è una scrittura di `preset_base_id`, anche con lo stesso valore:
la fotografia si riallinea, finché il preset non cambia di nuovo. Un preset cancellato porta
`preset_base_id` a NULL, e la fotografia torna vuota. Se la base salvata non è più quella di oggi, la
risoluzione risponde `preset_base_cambiato` invece di `preset_aggiornato`.

---

### La preferenza non trattiene nessuno

La preferenza è uno stato dell'utente, non un'entità con un suo ciclo di vita: non ha `attivo`, e le sue
FK verso la dashboard e verso il preset sono in eccezione alla regola ATTIVO. Una dashboard o un preset
scelti da un utente si spengono lo stesso; la risoluzione ripiega sul livello successivo. Cancellare
l'utente cancella le sue preferenze.

---

### Chi la scrive

La scrive solo il backend, con INSERT, UPDATE e DELETE diretti: il salvataggio (un UPSERT sulla coppia
utente e dashboard), la cancellazione e l'«ignora». La lettura passa dalla funzione di risoluzione; il
backend legge la riga direttamente solo per il proprio servizio di preferenza.

`data_update` la scrive il backend: la tabella non ha il trigger d'audit né le colonne `user_insert` e
`user_update`.

---

### ⚠️ Che cosa oggi non copre

* **Il database non controlla la forma della configurazione.** La controlla solo il backend (chiavi
  ammesse, codice obbligatorio, ordine intero positivo, nessun codice ripetuto, al più 100 widget). Il
  gemello delle liste ha un guard sulla misura di pagina; qui non c'è niente. Una riga scritta da altri
  che il backend:
  * con `widget` che non è un elenco, o con un ordine o un `visibile` che non si convertono, ferma la
    funzione di risoluzione: la home di quell'utente non si apre più;
  * con una voce senza codice, spegne in silenzio l'aggiunta dei widget nuovi del pool;
  * con un codice ripetuto, mostra la stessa card due volte.
* **Il preset di base può essere di un'altra dashboard.** Nessun vincolo lega `preset_base_id` alla
  dashboard della riga: la risoluzione lo tratta come una base che non è quella di oggi.
* **L'applicazione può scrivere qualunque cosa.** Nessuna RLS e nessun verbo: la riga di un utente la
  può scrivere chiunque abbia i privilegi del ruolo applicativo.

---

### Codici errore

La tabella non solleva codici propri. Una seconda riga per la stessa coppia arriva come violazione di
`uq_ui_dashboard_preferenza_utente_user_dashboard`; il backend usa l'UPSERT e non la incontra.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — la preferenza per chiave
  (soli widget, sola dimensione); il banner che si accende sulla chiave `widget` quando cambiano i widget
  del preset, e resta su quella sola quando cambia la dimensione, che la preferenza segue dal preset.
* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — la preferenza che vince sul preset, il widget
  spento che sparisce anche dalla preferenza.
* Nessun test costruisce, per le dashboard, «Ignora», la fotografia scritta dal trigger né una
  configurazione malformata: li prova il gemello delle liste, sulla stessa funzione.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella. La FK verso `django.auth_user` si aggiunge in coda all'installazione,
  dopo le migrazioni di Django che creano la tabella degli utenti.
* 2026-11-01 — la preferenza porta solo le chiavi scelte: fino ad allora salvarne una congelava anche
  l'altra.
* 2026-11-08 — la fotografia si chiama `preset_base_contenuto_aggiornato_il` e confronta la data del
  contenuto del preset, non più quella dell'audit; le due FK verso dashboard e preset entrano in
  eccezione alla regola ATTIVO.
* 2026-11-20 — la fotografia la scrive il database, e il trigger `z90` che la azzerava al cambio di base è
  tolto: azzerava anche la fotografia nuova portata dallo stesso UPSERT. La risoluzione espone il preset di
  base da salvare (`preset_base`), e la copia della cascata nel backend si ritira.
* 2026-11-20 — la fotografia diventa per chiave (`{chiave: data}`, le righe esistenti portate a
  `max(fotografia, ignorato)` per ogni chiave, banner identico), e `preset_aggiornato_ignored_at` si ritira:
  «Ignora» è riscrivere `preset_base_id`.

---

{% include-markdown "signature-core.md" %}
