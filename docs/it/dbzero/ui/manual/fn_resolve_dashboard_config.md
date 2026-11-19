## 📘 Documentazione Concettuale – Funzione `ui.fn_resolve_dashboard_config`

> **Ultimo aggiornamento**: 18 novembre 2026
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
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili dell'utente, per i preset di ruolo
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
È il primo, in quest'ordine, che sia di default, acceso e con almeno un widget acceso:

* **di ruolo**, fra i profili applicabili all'utente nella veste corrente, quello di priorità più alta;
* **d'azienda**, per l'azienda passata dal chiamante, se c'è;
* **di sistema**.

Un preset i cui widget sono tutti spenti non conta: la ricerca scende al livello successivo.

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

### Il banner «preset aggiornato»

Se la preferenza ha una fotografia del suo preset di base, `preset_aggiornato` è vero quando il contenuto
di quel preset è cambiato dopo la fotografia e l'utente non l'ha ignorato, o il preset è cambiato di nuovo
dopo l'«ignora». In ogni altro caso è falso.

---

### La veste

La veste la legge [fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente): senza veste nella sessione,
o con una veste che non esiste, valgono i profili di tutte le vesti dell'utente. Per la presentazione è un
ripiego sicuro; le mappe dei permessi restano chiuse fuori dalla veste di operatore.

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
* **Il preset di base può essere fatto di widget che l'utente non vede, o fuori dal pool.** La scelta del
  preset guarda solo che i suoi widget siano accesi: un preset tutto fuori dal pool, o tutto protetto da
  permessi, vince lo stesso, e la dashboard resta con le sole card aggiunte invisibili.
* **Fra due profili con la stessa priorità vince uno a caso.** Senza veste nella sessione due profili di
  portale hanno la stessa priorità, e l'ordinamento non ha uno spareggio.
* **Il preset d'azienda vale anche per un'azienda spenta.** La funzione non guarda se l'azienda passata è
  accesa.
* **La dimensione del preset non è controllata.** Zero o un negativo escono così come sono; la dimensione
  della preferenza, invece, deve essere un intero positivo.
* **Il banner legge il preset della fotografia così com'è.** Se quel preset è stato spento, o non è più la
  base dell'utente, un suo cambio accende lo stesso il banner.
* **Il preset di base ha una seconda copia nel backend.** Il backend, per scrivere la fotografia, ripete la
  cascata per conto suo e prende il primo preset di default acceso, senza guardare i widget; con una veste
  che non esiste fallisce, invece di valere come «tutte le vesti». La funzione non restituisce il preset di
  base che ha scelto.
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
* Nessun test costruisce il filtro per azione, il widget visibile con il permesso, il preset d'azienda, il
  preset senza widget accesi che fa scendere la cascata, l'«ignora» del banner, né il conteggio dei widget
  nuovi tolti dal filtro.

---

### Note di migrazione

* 2026-07-21 — nasce la funzione, gemella del risolutore delle liste.
* 2026-09-23 — la veste la legge `ui.fn_veste_corrente`, condivisa con le liste e con la ricerca libera.
* 2026-11-01 — la cascata va per chiave, con `origine` e `dimensione_max_standard`: fino ad allora una
  preferenza di soli widget rispondeva 8 invece della dimensione del preset.
* 2026-11-08 — il banner confronta `contenuto_aggiornato_il` del preset con la fotografia rinominata; l'uscita
  non cambia.

---

{% include-markdown "signature-core.md" %}
