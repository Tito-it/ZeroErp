## 📘 Documentazione Concettuale – Funzione `ui.fn_resolve_dashboard_config`

> **Ultimo aggiornamento**: 20 novembre 2026
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
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — il gemello delle liste
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — il flag del banner
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

1. la **preferenza** dell'utente, se porta la chiave (la dimensione vale solo se è un intero positivo);
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

Un preset i cui widget sono tutti spenti, o tutti fuori dal pool, non conta: la ricerca scende al livello
successivo.

---

### I widget nuovi del pool

Un widget acceso del pool che la configurazione scelta non nomina si aggiunge in coda, invisibile, e si
conta in `widget_nuovi`: un widget aggiunto al pool dopo il salvataggio compare nella personalizzazione
senza riscrivere la preferenza. Il frontend ne fa il badge «ci sono card nuove».

---

### Che cosa resta, e con quali dati

Dalla configurazione restano i widget accesi, nel pool della dashboard, e che l'utente può vedere: l'area,
se c'è, non BLOCCATA nella mappa dei permessi; l'azione, se c'è, abilitata. Le due mappe si leggono una
volta per chiamata, e fuori dalla veste di operatore negano tutto. Ogni widget porta etichetta, chiave
i18n, tipo, collegamento, chiave del contatore e soglia letti da `ui.widget`: la preferenza e il preset
portano solo codice, ordine e visibilità.

Il catalogo garantisce una dashboard non vuota prima del filtro dei permessi, non dopo: a un utente che
non vede nessun widget resta una dashboard vuota, se il pool non ha un widget senza area né azione.

---

### Il preset di base nel risultato, e il banner

L'uscita porta `preset_base`: l'id, l'ambito e la data del contenuto del preset di base di oggi, oppure
null. È ciò che il backend salva con la preferenza; la fotografia la scrive poi il database.

Il banner ha due esiti, gemelli di quelli delle liste, che non si accendono insieme:

* `preset_base_cambiato` — la preferenza ha salvato una base che non è quella di oggi (spenta, cancellata
  o scavalcata da un altro preset): il banner propone il riallineamento;
* `preset_aggiornato` — la base salvata è quella di oggi, e il suo contenuto è cambiato dopo la
  fotografia senza che l'utente l'abbia ignorato dopo quel cambio
  ([fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato)).

In ogni altro caso tutti e due sono falsi.

---

### La veste

La veste la legge [fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente): una veste che non esiste vale
come nessuna veste. Senza veste il passo del ruolo della scelta del preset si salta, e la cascata parte
dall'azienda: il ripiego non allarga. Le mappe dei permessi restano chiuse fuori dalla veste di operatore.

---

### ⚠️ Che cosa oggi non copre

* **`widget_nuovi` conta anche i widget che il filtro toglie.** Il conteggio si fa all'aggiunta, prima dei
  permessi: un widget del pool che l'utente non può vedere resta contato come novità, e il badge annuncia
  una card che la personalizzazione non mostra. Il gemello delle liste ricalcola il contatore dopo il
  filtro; questa funzione no.
* **Una voce della preferenza senza codice spegne l'aggiunta dei widget nuovi.** Il confronto «non già
  nominato» su un elenco che contiene un codice nullo non è mai vero: `widget_nuovi` vale zero e nessun
  widget nuovo compare.
* **Una preferenza malformata ferma la funzione.** Se `widget` non è un elenco, o un ordine o una
  visibilità non si convertono, la chiamata fallisce invece di trattare la chiave come assente, come fa per
  la dimensione.
* **Il preset di base può essere fatto di widget che l'utente non vede.** La scelta del preset guarda che
  abbia un widget acceso nel pool, non i permessi: un preset tutto protetto da permessi che l'utente non ha
  vince lo stesso, e la dashboard resta con le sole card aggiunte invisibili.
* **La dimensione del preset non è controllata.** Zero o un negativo escono così come sono; la dimensione
  della preferenza, invece, deve essere un intero positivo.
* **Il banner è per preset intero.** Guarda tutto il contenuto del preset di base: una preferenza di soli
  widget vede il banner anche quando il preset cambia solo la dimensione, che le arriva già.
* **La dashboard per codice ha una seconda copia nel backend**, che la cerca prima di scrivere una
  preferenza; le liste hanno un building block per questa lettura.

---

### Codici errore

* `E_UI_DASHBOARD_NON_TROVATA` — codice inesistente o dashboard spenta.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — dashboard inesistente, catalogo del pool, widget con
  area nascosto, preset di sistema e di ruolo, preferenza che vince, widget nuovo contato, widget spento,
  priorità fra profili, campi opachi freschi.
* `db/pgtap/ui/test-fn-resolve-dashboard-config-cascata-per-chiave-v1.sql` — la cascata per chiave, la
  dimensione standard, l'origine, il banner acceso da un cambio del preset.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — il preset di widget fuori dal pool che non è base, e quello
  con un widget del pool che lo è.
* Nessun test costruisce il filtro per azione, il widget visibile con il permesso, il preset d'azienda della
  dashboard, il preset senza widget accesi che fa scendere la cascata, l'«ignora» del banner, né il
  conteggio dei widget nuovi tolti dal filtro.

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

---

{% include-markdown "signature-core.md" %}
