# Guida — Configurazione e Personalizzazione delle Dashboard

> **Ultimo aggiornamento**: 21 novembre 2026
>
> **Destinatari**: chi prepara il catalogo delle dashboard (il seed delle migrazioni), chi lavora sulla home
> lato backend e frontend, l'operatore che personalizza la propria home.
>
> **Vedi anche** — schemi DB:
>
> * [ui.dashboard_definizione](/dbzero/ui/tabelle/dashboard_definizione) — le dashboard configurabili (la home è `home`)
> * [ui.widget](/dbzero/ui/tabelle/widget) — il catalogo globale delle card, con area e azione
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool: le card che una dashboard può mostrare
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — i default della dashboard per ruolo, azienda e sistema
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — le card di un preset, in ordine
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la scelta di ciascun utente
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la dashboard effettiva di un utente
> * [ui.fn_dashboard_da_codice](/dbzero/ui/funzioni/fn_dashboard_da_codice) — la dashboard accesa per codice
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base, per dashboard e liste
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — il banner «preset aggiornato»
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — che cosa una preferenza può contenere
>
> **Vedi anche** — API e service backend:
>
> * [API dashboard configurabile](/backend/ui/manual/api_ui_dashboard) — configurazione, contatori, preferenza
>
> **Vedi anche** — guide correlate:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — il meccanismo comune: preset, preferenze, banner

---

## 1. Che cos'è una dashboard

Una dashboard è una **griglia di card**: ognuna mostra un numero (un contatore), un'etichetta e un
collegamento alla schermata già filtrata da cui il numero viene. Oggi c'è una dashboard sola, la home
dell'operatore (`home`).

Le dashboard sono gemelle delle liste configurabili: catalogo, preset e preferenza dell'utente funzionano
allo stesso modo, e la scelta del preset di base è la stessa funzione. Questa guida dice ciò che è
proprio delle dashboard; il meccanismo comune è nella
[guida delle liste](/guide/configurazione-liste), §3 e §10.5.

---

## 2. Le entità in gioco

### 2.1 Dashboard (`dashboard_definizione`)

La dashboard si riconosce dal **codice**, stabile fra ambienti; l'`id` numerico non si usa fuori dal
database. Una dashboard spenta non risponde: chi la chiede riceve `E_UI_DASHBOARD_NON_TROVATA`, e i suoi
preset restano sospesi, com'erano, fino alla riaccensione.

### 2.2 Widget (`widget`)

Il widget è la card. Il catalogo è **globale**: lo stesso widget può stare in più dashboard. Porta:

* il **codice**, unico in tutto il catalogo, con cui preset e preferenze lo citano;
* l'**etichetta** e la sua chiave di traduzione;
* la **chiave del contatore**, che il backend sa calcolare; senza, la card non ha numero;
* il **collegamento** e la **soglia**, che legge il frontend; il database li conserva senza interpretarli;
* l'**area** e l'**azione** che la fanno vedere (§4).

### 2.3 Pool (`dashboard_widget`)

Il pool dice **quali card una dashboard può mostrare**, e il loro ordine di default. Un preset e una
preferenza scelgono solo fra le card del pool. Una card del pool che un preset propone non esce dal pool:
prima si toglie dal preset.

### 2.4 Preset (`dashboard_preset` e `dashboard_preset_widget`)

Il preset è il default della dashboard per un **posto**: il sistema, un ruolo (un profilo di accesso) o
un'azienda. Dice quali card, in che ordine, quali visibili, e quante card al massimo (`dimensione_max`, da
1 a 100). Un posto ha al più un preset acceso, e il posto di un preset non si cambia: si spegne e se ne fa
un altro.

### 2.5 Preferenza (`dashboard_preferenza_utente`)

La preferenza è la scelta di un utente su una dashboard: porta solo le chiavi che l'utente ha toccato
(`widget`, `dimensione_max`); le altre le dà il preset. È un dato personale: non ha audit, e la data
dell'ultima scrittura la scrive il database.

---

## 3. La cascata

Quando l'utente apre la home, ogni chiave viene dal primo livello che la contiene: la **preferenza**, poi
il **preset di base**, poi il **catalogo** (tutte le card accese del pool, nell'ordine di default).

Il preset di base è il primo preset acceso che ha almeno una card accesa del pool, nell'ordine: il preset
del ruolo (solo quando la sessione ha una veste), poi quello dell'azienda (se accesa), poi quello di
sistema. È la regola delle liste, scritta una volta per tutte e due.

Sopra la cascata valgono due regole:

* una card **aggiunta al pool** dopo la scelta dell'utente entra in coda, nascosta, e la home la conta fra
  le novità; l'utente la accende dalla modale delle card;
* una card **spenta** nel catalogo sparisce a tutti, anche a chi l'aveva nella preferenza.

Se l'amministratore cambia il preset da cui l'utente è partito, la home mostra il banner «preset
aggiornato», con le parti cambiate; «Ignora» lo chiude finché il preset non cambia di nuovo. È lo stesso
banner delle liste (guida delle liste, §10.5).

---

## 4. Chi vede quale card

Un widget dichiara un'area, un'azione, tutte e due o nessuna. L'utente vede la card se l'area non gli è
BLOCCATA e l'azione gli è abilitata; un riferimento vuoto non pone condizioni. Fuori dalla veste di
operatore le card con area o azione non si vedono.

Se il widget dichiara un'azione, l'area è vuota oppure quella dell'azione: un'azione appartiene a
un'area, e il widget non può dire due cose diverse sul permesso che lo mostra.

Una card che l'utente non può vedere **non arriva al frontend**: non arriva spenta, non arriva proprio. Per
lo stesso motivo il backend calcola i contatori delle sole card visibili, e non accetta chiavi dal client.

---

## 5. Una home senza card

Dopo il filtro dei permessi l'elenco delle card può essere vuoto, ed è un esito, non un errore. La regola
è che la home **non resti muta**: lo stato vuoto lo dice il frontend, e distingue due casi.

| Situazione | Che cosa vede l'utente |
| --- | --- |
| Ci sono card disponibili, ma nessuna accesa | «Nessuna card attiva»: le sceglie dall'ingranaggio |
| Nessuna card è disponibile per il suo profilo | «Nessuna card disponibile per il tuo profilo» |

Una card di riempimento, senza numero e senza collegamento, soddisferebbe la regola nella forma e la
nasconderebbe nella sostanza: per questo la card di benvenuto del seed è spenta.

---

## 6. Chi scrive che cosa

| Che cosa | Chi lo scrive |
| --- | --- |
| Dashboard, widget, pool, preset e loro composizione | Solo il seed delle migrazioni (i CSV di `ui`): l'applicazione li legge e non li scrive |
| La preferenza dell'utente | Il backend, quando l'utente salva, ripristina o ignora il banner |

Non c'è una pagina di amministrazione delle dashboard: una card nuova, un preset di ruolo o un cambio di
ordine si fanno nel CSV del seed. Quando una pagina admin servirà, riaprirà la scrittura sulle sole
tabelle che scrive.

---

## 7. Che cosa l'operatore può fare

Dall'ingranaggio della home l'operatore:

* accende e spegne le card fra quelle che il suo profilo vede;
* le riordina;
* torna allo standard (la preferenza si cancella, e la home riparte dal preset).

La preferenza può portare anche il numero massimo di card (`dimensione_max`, da 1 a 100): il backend lo
accetta e il database ne controlla il tetto. Non può vedere card che il suo profilo non vede, né cambiare
il preset degli altri.

---

## 8. Che cosa le dashboard oggi non fanno

* **Una dashboard sola**: la home. La struttura ne ammette altre, ma nessuna è nel seed.
* **Il preset di base non guarda i permessi**: un preset fatto solo di card che l'utente non vede vince lo
  stesso, e la home resta con le sole card aggiunte, nascoste.
* **La chiave del contatore non è controllata dal database**: l'elenco delle chiavi che il backend sa
  calcolare sta solo nel backend.
* **Nessuna pagina admin** (§6).

---
{% include-markdown "signature-core.md" %}
