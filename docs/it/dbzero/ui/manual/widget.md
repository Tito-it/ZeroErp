## 📘 Documentazione Concettuale – Tabella `ui.widget`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — le dashboard in cui il widget è disponibile
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — i preset che lo propongono
> * [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali) — l'area che lo fa vedere
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — l'azione che lo fa vedere
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — l'analogo delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — filtra i widget per permesso e li restituisce
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — un widget acceso chiede area e azione accese

---

### 🎯 Scopo Principale

`ui.widget` è il **catalogo globale dei widget** delle dashboard. Ogni widget è una card: un'etichetta, un
contatore, una soglia di attenzione e un collegamento a una schermata già filtrata.

Il widget non appartiene a una dashboard: il legame sta nel pool
([dashboard_widget](/dbzero/ui/tabelle/dashboard_widget)), e lo stesso widget può stare in più dashboard.

---

### Il codice è unico in tutto il catalogo

Preferenze e preset citano il widget per `codice`, unico in tutto il catalogo e non solo in una
dashboard. Il codice resta minuscolo: la tabella è fra le eccezioni decise alla regola del codice
maiuscolo.

---

### Il database conserva, non interpreta

`deep_link`, `contatore_key` e `soglia` sono opachi per il database: li conserva e la risoluzione li
restituisce freschi, letti da qui a ogni chiamata. La forma del collegamento e della soglia la legge il
frontend; il valore del contatore lo calcola il backend, che conosce le sue chiavi in un elenco proprio.
Un widget senza contatore, come la card di benvenuto, è una card senza numero.

`tipo_widget` dice la forma della card al frontend; oggi c'è solo `kpi`.

---

### Chi lo vede: area e azione

Un widget dichiara un'area funzionale, un'azione, entrambe o nessuna. La risoluzione lo mostra solo se
l'utente non ha l'area BLOCCATA e ha l'azione abilitata; un riferimento vuoto non pone condizioni. Non c'è
una tabella di permessi del widget: un widget o si vede o no. Le mappe dei permessi sono quelle
dell'utente e della veste corrente, e fuori dalla veste di operatore negano tutto.

Un widget acceso chiede area e azione accese, a fine transazione; un'area o un'azione non si spengono
finché un widget acceso le cita.

---

### Spento, sparisce a tutti

Con `attivo` falso il widget sparisce da ogni dashboard, anche per chi lo aveva nella preferenza. Il pool e
i preset non lo trattengono: le loro FK sono in eccezione alla regola ATTIVO. Un widget citato da un pool o
da un preset non si cancella.

---

### ⚠️ Che cosa oggi non copre

* **«Mai vuota» non è garantita.** La risoluzione ripiega fino al catalogo del pool, ma il filtro dei
  permessi viene dopo: a un utente senza permessi resta qualcosa solo se il pool ha un widget acceso
  senza area né azione. Nessun vincolo lo chiede.
* **Area e azione possono non essere coerenti.** Un'azione appartiene a un'area, e il widget può dichiarare
  un'area diversa da quella della sua azione.
* **La chiave del contatore non è controllata.** Il database accetta qualunque testo; l'elenco delle chiavi
  che il backend sa calcolare sta solo nel backend.
* **L'applicazione ha i privilegi di scrittura** senza che nessun servizio scriva la tabella.

---

### Codici errore

* `E_ATTIVO_PADRE_NON_ATTIVO` — un widget acceso su un'area o un'azione spente, a fine transazione.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — lo spegnimento di un'area o di un'azione che un widget acceso cita.
* Il codice ripetuto arriva come violazione di `uq_ui_widget_codice`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — il widget con area che l'utente non vede, il widget
  spento che sparisce anche dalla preferenza, i campi opachi restituiti freschi.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — le regole ATTIVO verso area e azione.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella, col catalogo della home.
* 2026-11-08 — lo schema `ui` entra nell'ambito delle automazioni: audit del framework e regola ATTIVO.
* 2026-11-21 — codice, etichetta, chiave di traduzione e chiave del contatore non sono mai la
  stringa vuota (un CHECK per colonna).

---

{% include-markdown "signature-core.md" %}
