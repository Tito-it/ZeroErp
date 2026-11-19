## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — la dashboard del preset
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i widget del preset
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la preferenza che ne fotografa il contenuto
> * [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) — il profilo di un preset di ruolo
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda di un preset d'azienda
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il gemello delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — sceglie il preset di base
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili dell'utente, con la loro priorità
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la data del contenuto, al cambio della dimensione
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la data del contenuto, al cambio dei widget

---

### 🎯 Scopo Principale

`ui.dashboard_preset` contiene i **default di una dashboard** per ambito: di sistema, per un'azienda,
per un profilo di accesso. Un preset dice quali widget mostrare e quante card al massimo; i widget stanno
in [dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget).

---

### Tre ambiti, dal più specifico

* `ruolo` — per un profilo di accesso; vale per chi ha quel profilo fra i suoi;
* `emittente_fiscale` — per un'azienda;
* `sistema` — per tutti.

Il CHECK `chk_ui_dashboard_preset_ambito_refs` tiene ambito e riferimenti coerenti: il preset di sistema
non ha né profilo né azienda, quello di ruolo solo il profilo, quello d'azienda solo l'azienda.

La risoluzione cerca un preset di ruolo, poi d'azienda, poi di sistema, e prende il primo con almeno un
widget acceso. Fra più preset di ruolo vince il profilo con la priorità più alta (il binding sull'identità
prima di quello sul reparto, e questo prima di quello sulla veste).

---

### Un solo preset di default per combinazione

La risoluzione legge solo i preset con `is_default` vero, e l'indice unico parziale
`uq_ui_dashboard_preset_default` ne ammette uno per (dashboard, ambito, profilo, azienda). Un preset con
`is_default` falso non lo legge nessuno, né il database né il backend.

---

### `dimensione_max`: quante card al massimo

È il numero massimo di card che la dashboard mostra; il taglio lo fa il frontend. Un preset senza
dimensione lascia lo standard al ripiego del catalogo, 8. La preferenza dell'utente, se la porta, vince.

---

### ⭐ La data del contenuto, non quella dell'audit

`contenuto_aggiornato_il` è la data dell'ultimo cambio del **contenuto** del preset, quella che il banner
«preset aggiornato» confronta con la fotografia della preferenza. La spostano due trigger, sulle funzioni
condivise con i preset di lista: il cambio di `dimensione_max`
([trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato)) e una riga
di widget aggiunta, tolta o cambiata
([trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset)). Una riscrittura
uguale, come quella del seed, non la sposta. `data_update` resta l'audit del framework, che si sposta a
ogni UPDATE.

---

### Attivo: la dashboard deve essere accesa

Un preset acceso chiede una dashboard accesa, a fine transazione; la dashboard non si spegne finché ha
preset accesi. Le FK verso profilo e azienda sono in eccezione alla regola ATTIVO: spegnere un profilo o
un'azienda è un gesto del loro dominio, e non si ferma su un preset. Un preset spento la risoluzione non
lo legge.

---

### ⚠️ Che cosa oggi non copre

* **`dimensione_max` accetta zero e i negativi.** Nessun CHECK, nessun catalogo delle misure come per le
  liste: la risoluzione restituisce il valore così com'è, e il frontend tratta un valore non positivo come
  «nessun limite». La preferenza, invece, accetta solo un intero positivo.
* **Il preset d'azienda vale anche per un'azienda spenta.** La risoluzione confronta l'azienda passata dal
  chiamante senza guardare se è accesa; il preset di un profilo spento, invece, non entra, perché i profili
  applicabili sono solo quelli accesi.
* **Fra due profili con la stessa priorità vince uno a caso.** Senza veste nella sessione un utente può
  avere due profili della stessa priorità (due vesti di portale), e la scelta del preset di ruolo non ha
  uno spareggio.
* **Un preset può proporre widget fuori dal pool della dashboard.** Nessun vincolo lo impedisce; la
  risoluzione li toglie, ma sceglie lo stesso quel preset come base.
* **Il preset di base conta i widget accesi, non quelli che l'utente può vedere.** Un preset i cui widget
  l'utente non ha il permesso di vedere vince lo stesso, e la dashboard resta con le sole card aggiunte
  invisibili.
* **`emittente_fiscale_id` è un intero**, mentre l'id dell'azienda è un `bigint`; nel gemello delle liste
  la colonna è `bigint`.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

* `E_ATTIVO_PADRE_NON_ATTIVO` — un preset acceso su una dashboard spenta, a fine transazione.
* Il CHECK dell'ambito, il secondo default per la stessa combinazione e il codice ripetuto nella stessa
  dashboard arrivano come violazioni di vincolo.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — il preset di sistema, quello di ruolo che vince,
  la priorità fra due profili.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — il preset senza dimensione,
  la data del contenuto che non si sposta per una riscrittura uguale e si sposta per un cambio vero.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — i trigger e le eccezioni della regola ATTIVO.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella, sull'ENUM `ui.ambito_preset` delle liste.
* 2026-11-01 — il preset di base si cerca sempre, anche con una preferenza: dà le chiavi che la
  preferenza non ha.
* 2026-11-08 — la data del contenuto passa da `data_update` a `contenuto_aggiornato_il`, e `data_update`
  diventa l'audit; le FK verso profilo e azienda entrano in eccezione alla regola ATTIVO.

---

{% include-markdown "signature-core.md" %}
