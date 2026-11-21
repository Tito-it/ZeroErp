## 📘 Documentazione Concettuale – Tabella `ui.dashboard_preset`

> **Ultimo aggiornamento**: 20 novembre 2026
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
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — sceglie il preset di base
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — legge le chiavi del preset di base
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

La scelta del preset di base ([fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base)) cerca un preset
di ruolo, poi d'azienda, poi di sistema, e prende il primo acceso con almeno un widget acceso nel pool della
dashboard. Fra più preset di ruolo vince il profilo con la priorità più alta (il binding sull'identità prima
di quello sul reparto, e questo prima di quello sulla veste); il passo del ruolo vale solo con la veste
valorizzata. Il preset d'azienda vale solo se l'azienda è accesa.

---

### Un preset acceso per posto: vale se è acceso

Un **posto** è la combinazione (dashboard, ambito, profilo, azienda). L'indice unico parziale
`uq_ui_dashboard_preset_posto` ammette un solo preset acceso per posto, con il profilo e l'azienda vuoti
contati come un valore della chiave. Il preset acceso è quello che vale; quelli spenti non li legge la
risoluzione e non occupano il posto.

Una bozza si prepara spenta. Per sostituire il preset di un posto si spegne il vecchio **prima** di
accendere il nuovo: l'indice non si differisce a fine transazione.

---

### `dimensione_max`: quante card al massimo

È il numero massimo di card che la dashboard mostra; il taglio lo fa il frontend. Un preset senza
dimensione lascia lo standard al ripiego del catalogo, 8. La preferenza dell'utente, se la porta, vince.

---

### ⭐ La data del contenuto, non quella dell'audit

`contenuto_aggiornato_il` è la data dell'ultimo cambio del **contenuto** del preset, per chiave: un
oggetto `{chiave: data}` con `widget` e `dimensione_max`, le chiavi della configurazione della
preferenza. Il banner «preset aggiornato» la confronta, chiave per chiave, con la fotografia della
preferenza, e guarda solo le chiavi che la preferenza imposta. La scrive solo il database, con la
funzione condivisa con i preset di lista
([trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato)): chi la
scrive riceve `E_UI_PRESET_CONTENUTO_DERIVATO`. La chiave `widget` si sposta quando cambia
`composizione_impronta`, l'impronta dei widget del preset, che il trigger differito della
composizione ([trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset))
scrive a fine transazione, solo se è cambiata. Una riscrittura uguale, come quella del seed o un
DELETE seguito dall'INSERT delle stesse righe, non sposta niente. `data_update` resta l'audit del framework, che si sposta a
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
* **Un preset può proporre widget fuori dal pool della dashboard.** Nessun vincolo lo impedisce; la
  risoluzione li toglie, e un preset fatto solo di widget fuori dal pool non è base.
* **Il preset di base conta i widget accesi, non quelli che l'utente può vedere.** Un preset i cui widget
  l'utente non ha il permesso di vedere vince lo stesso, e la dashboard resta con le sole card aggiunte
  invisibili.
* **`emittente_fiscale_id` è un intero**, mentre l'id dell'azienda è un `bigint`; nel gemello delle liste
  la colonna è `bigint`.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

* `E_ATTIVO_PADRE_NON_ATTIVO` — un preset acceso su una dashboard spenta, a fine transazione.
* Il CHECK dell'ambito, il secondo preset acceso nello stesso posto e il codice ripetuto nella stessa
  dashboard arrivano come violazioni di vincolo.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — il preset di sistema, quello di ruolo che vince,
  la priorità fra due profili.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — il preset senza dimensione,
  la data del contenuto che non si sposta per una riscrittura uguale e si sposta per un cambio vero.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — i trigger e le eccezioni della regola ATTIVO.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — il preset fatto di widget fuori dal pool che non è base, e
  quello con un widget del pool che lo è.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella, sull'ENUM `ui.ambito_preset` delle liste.
* 2026-11-01 — il preset di base si cerca sempre, anche con una preferenza: dà le chiavi che la
  preferenza non ha.
* 2026-11-08 — la data del contenuto passa da `data_update` a `contenuto_aggiornato_il`, e `data_update`
  diventa l'audit; le FK verso profilo e azienda entrano in eccezione alla regola ATTIVO.
* 2026-11-20 — `is_default` si ritira, e con lui l'indice `uq_ui_dashboard_preset_default`: un preset
  acceso non di default non lo leggeva nessuno, e i preset in quello stato sono stati spenti. Al suo posto
  `uq_ui_dashboard_preset_posto`, sui soli preset accesi.
* 2026-11-20 — `contenuto_aggiornato_il` diventa per chiave e la scrive solo il database; nasce
  `composizione_impronta`.

---

{% include-markdown "signature-core.md" %}
