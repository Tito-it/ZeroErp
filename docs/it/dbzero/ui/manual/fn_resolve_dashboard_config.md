## 📘 Documentazione Concettuale – Funzione `ui.fn_resolve_dashboard_config`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — la dashboard, cercata per codice
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la scelta dell'utente
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — i default per ambito
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i widget di un preset
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool della dashboard
> * [ui.widget](/dbzero/ui/tabelle/widget) — il catalogo globale, con area e azione
>
> Approfondimento funzioni:
>
> * [ui.fn_dashboard_da_codice](/dbzero/ui/funzioni/fn_dashboard_da_codice) — la dashboard accesa per codice
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il gemello delle liste
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — le chiavi del banner
> * [ui.fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb) — l'ordine e la dimensione letti senza cast che cadono
> * [ui.fn_dimensione_max_ammessa](/dbzero/ui/funzioni/fn_dimensione_max_ammessa) — il tetto da 1 a 100 delle card
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — la forma della preferenza, alla scrittura
> * [script.fn_get_user_permissions_map](/dbzero/script/funzioni/fn_get_user_permissions_map) — il livello dell'utente per area
> * [script.fn_get_user_actions_map](/dbzero/script/funzioni/fn_get_user_actions_map) — le azioni abilitate dell'utente

---

### 🎯 Scopo Principale

`ui.fn_resolve_dashboard_config` dice **che cosa una dashboard mostra a un utente**: quali widget, in che
ordine, quali visibili, quante card al massimo, e se il preset di partenza è cambiato. Combina la
preferenza dell'utente, il preset che gli spetta e il pool della dashboard, toglie i widget che l'utente
non può vedere, e restituisce i dati di ogni card letti freschi dal catalogo.

È il gemello di [fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config), più semplice: un
widget non ha livelli di accesso né colonne obbligatorie.

---

### La cascata va per chiave

Le due chiavi, i widget e la dimensione massima, si risolvono ognuna per conto suo, dal primo livello che
la contiene:

1. la **preferenza** dell'utente, se porta la chiave (la dimensione vale solo se è un intero da 1 a
   100, [fn_dimensione_max_ammessa](/dbzero/ui/funzioni/fn_dimensione_max_ammessa));
2. il **preset di base**;
3. il **catalogo**: per i widget, tutti quelli accesi del pool, visibili, nell'ordine del pool; per la
   dimensione, 8.

Lo **standard** di una chiave è ciò che darebbero il preset e il catalogo senza la preferenza. L'uscita
porta, per ogni chiave, il livello da cui viene (`origine`: `preferenza`, `ruolo`, `emittente_fiscale`,
`sistema` o `catalogo`) e la dimensione standard: il frontend al salvataggio rimanda solo le chiavi che
vengono dalla preferenza, più quella toccata.

---

### Il preset di base

Il preset di base si cerca sempre, anche quando c'è una preferenza: dà le chiavi che la preferenza non ha.
Lo sceglie [fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base), la stessa sede delle liste: il
primo preset acceso con almeno un widget acceso **nel pool** della dashboard, in quest'ordine:

* **di ruolo**, fra i profili applicabili all'utente nella veste corrente, quello di priorità più alta;
  solo con la veste valorizzata;
* **d'azienda**, per l'azienda passata dal chiamante, se c'è ed è accesa;
* **di sistema**.

Un preset i cui widget sono tutti spenti non conta: la ricerca scende al livello
successivo.

---

### I widget nuovi del pool

Un widget acceso del pool che la configurazione scelta non nomina si aggiunge in coda, invisibile: un
widget aggiunto al pool dopo il salvataggio compare nella personalizzazione senza riscrivere la
preferenza. Una voce della preferenza senza codice non spegne l'aggiunta.

`widget_nuovi` conta questi widget **dopo** il filtro dei permessi, come il gemello delle liste: annuncia
solo le card che l'utente può davvero trovare. Il frontend ne fa il badge «ci sono card nuove».

---

### Che cosa resta, e con quali dati

Dalla configurazione restano i widget accesi, nel pool della dashboard, e che l'utente può vedere: l'area,
se c'è, non BLOCCATA nella mappa dei permessi; l'azione, se c'è, abilitata. Le due mappe si leggono una
volta per chiamata, e fuori dalla veste di operatore negano tutto. Ogni widget porta etichetta, chiave
i18n, tipo, collegamento, chiave del contatore e soglia letti da `ui.widget`: la preferenza e il preset
portano solo codice, ordine e visibilità.

Dopo il filtro dei permessi l'elenco dei widget può essere vuoto, ed è un esito: a un utente che non vede
nessun widget del pool la funzione risponde un elenco vuoto, non una card di riempimento. La home non resta
muta perché lo stato vuoto lo dice il frontend («nessuna card attiva», «nessuna card disponibile per il tuo
profilo»).

---

### ⭐ Una preferenza scritta male non ferma la home

La forma della preferenza la giudica alla scrittura il guard
[trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma). La lettura non conta
su di lui: una riga scritta prima del guard, o senza passare dal trigger, non fa cadere la funzione.

* `widget` che non è un elenco vale «nessuna scelta»: i widget vengono dal preset o dal pool.
* L'ordine e la dimensione passano da [fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb): un
  valore che intero non è vale come assente; una dimensione fuori dal tetto vale come assente.
* Un campo che manca, o di tipo sbagliato, prende il default del pool: l'ordine del widget nel pool,
  visibile. Non esce mai vuoto.
* Una voce senza codice, o fuori dal pool, si salta; un codice ripetuto vale una volta, con la prima
  voce.

---

### Il preset di base nel risultato, e il banner

L'uscita porta `preset_base`: l'id, l'ambito e la data del contenuto per chiave del preset di base di
oggi, oppure null. È ciò che il backend salva con la preferenza; la fotografia la scrive poi il database.

Il banner ha due esiti, gemelli di quelli delle liste, che non si accendono insieme:

* `preset_base_cambiato` — la preferenza ha salvato una base che non è quella di oggi (spenta, cancellata
  o scavalcata da un altro preset): il banner propone il riallineamento;
* `preset_aggiornato_chiavi` — la base salvata è quella di oggi: le chiavi che la preferenza imposta
  (`widget`, `dimensione_max`, di origine `preferenza`) il cui contenuto nel preset è cambiato dopo la
  fotografia, vuoto se nessuna ([fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato)). Una
  chiave che la preferenza segue dal preset non entra. `preset_aggiornato` vale «almeno una».

«Ignora» è una scrittura che nomina `preset_base_id`: la fotografia si riallinea. In ogni altro caso tutti
e due sono spenti.

---

### La veste

La veste la legge [fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente): una veste che non esiste vale
come nessuna veste. Senza veste il passo del ruolo della scelta del preset si salta, e la cascata parte
dall'azienda: il ripiego non allarga. Le mappe dei permessi restano chiuse fuori dalla veste di operatore.

---

### ⚠️ Che cosa oggi non copre

* **Il preset di base può essere fatto di widget che l'utente non vede.** La scelta del preset guarda che
  abbia un widget acceso nel pool, non i permessi: un preset tutto protetto da permessi che l'utente non ha
  vince lo stesso, e la dashboard resta con le sole card aggiunte invisibili.

---

### Codici errore

* `E_UI_DASHBOARD_NON_TROVATA` — codice inesistente o dashboard spenta, dalla lettura per codice
  ([fn_dashboard_da_codice](/dbzero/ui/funzioni/fn_dashboard_da_codice)).

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — dashboard inesistente, catalogo del pool, widget con
  area nascosto, preset di sistema e di ruolo, preferenza che vince, widget nuovo contato, widget spento,
  priorità fra profili, campi opachi freschi.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — la cascata per chiave, la
  dimensione standard, l'origine, il banner acceso da un cambio dei widget sulla chiave `widget`, la
  dimensione che la preferenza segue dal preset che non entra nel banner.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — il preset fatto dei soli widget spenti del pool, che non è base, e quello
  con un widget del pool che lo è.
* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — una riga malformata scritta senza il guard che non
  ferma la funzione (codice ripetuto preso una volta, ordine e visibilità dal pool); una card nuova del
  pool di un'area non concessa che non conta in `widget_nuovi`, e una senza area che conta.
* `db/pgtap/ui/test-ui-catalogo-dashboard-v1.sql` — la dashboard spenta rifiutata, anche coi preset
  accesi.
* Nessun test costruisce il filtro per azione, il widget visibile con il permesso, il preset d'azienda della
  dashboard, il preset senza widget accesi che fa scendere la cascata, né «Ignora» (lo prova il gemello
  delle liste, sulla stessa funzione dello snapshot).

---

### Note di migrazione

* 2026-07-21 — nasce la funzione, gemella del risolutore delle liste.
* 2026-09-23 — la veste la legge `ui.fn_veste_corrente`, condivisa con le liste e con la ricerca libera.
* 2026-11-01 — la cascata va per chiave, con `origine` e `dimensione_max_standard`: fino ad allora una
  preferenza di soli widget rispondeva 8 invece della dimensione del preset.
* 2026-11-08 — il banner confronta `contenuto_aggiornato_il` del preset con la fotografia rinominata; l'uscita
  non cambia.
* 2026-11-20 — la scelta del preset di base passa a `ui.fn_preset_di_base`, comune con le liste: prima si
  leggevano i preset `is_default`, il ruolo senza spareggio con la veste nulla, l'azienda anche spenta, il
  preset fatto di widget fuori dal pool. Nell'uscita `preset_base` e `preset_base_cambiato`; il banner si
  calcola solo sulla base di oggi.
* 2026-11-20 — il banner diventa per chiave: guarda solo le chiavi di origine `preferenza`, e nell'uscita
  `preset_aggiornato_chiavi`; `preset_base.contenuto_aggiornato_il` è la mappa per chiave. L'«ignora» non
  c'è più: è la riscrittura di `preset_base_id`.
* 2026-11-21 — `widget_nuovi` si conta dopo il filtro dei permessi: prima contava anche le card che
  l'utente non può vedere. La lettura smette di cadere su una preferenza malformata, una voce senza codice
  non spegne più l'aggiunta dei widget nuovi, e la dimensione della preferenza vale solo da 1 a 100.
* 2026-11-21 — la dashboard per codice la legge `ui.fn_dashboard_da_codice`, condivisa col backend; il
  rifiuto non cambia.

---

{% include-markdown "signature-core.md" %}
