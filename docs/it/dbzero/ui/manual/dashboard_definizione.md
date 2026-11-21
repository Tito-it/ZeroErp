## 📘 Documentazione Concettuale – Tabella `ui.dashboard_definizione`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — i widget che la dashboard può mostrare
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — i default della dashboard per ambito
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la scelta di ciascun utente
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — il gemello delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — risolve la dashboard per un utente
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — non si spegne con preset accesi

---

### 🎯 Scopo Principale

`ui.dashboard_definizione` è il catalogo delle **dashboard configurabili**: una riga per ogni griglia di
card che l'utente può personalizzare, riconosciuta dal suo `codice` (la home è `home`).

A differenza di una lista, una dashboard non legge da una vista sola: ogni widget porta il suo
collegamento e il suo contatore. Per questo la tabella non ha una vista sorgente.

---

### Il codice è l'identificatore stabile

Il frontend, il backend e la funzione di risoluzione cercano la dashboard per `codice`, unico; l'`id`
numerico non è lo stesso da un ambiente all'altro e non si usa fuori dal database. Il codice resta
minuscolo: la tabella è fra le eccezioni decise alla regola del codice maiuscolo.

Entra qui solo una griglia di card personalizzabile per utente. Un cruscotto analitico a forma fissa
non usa questa struttura.

---

### Una dashboard spenta non si risolve

Con `attivo` falso la dashboard non esiste per chi la chiede:
[fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) risponde
`E_UI_DASHBOARD_NON_TROVATA`, e il backend rifiuta col codice stesso il salvataggio, la cancellazione e
l'«ignora» della preferenza.

Una dashboard si spegne solo quando i suoi preset sono spenti
([trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)).
Non la trattengono le righe del pool né le preferenze degli utenti: sono in eccezione alla regola
ATTIVO, perché sono parti e stati dell'utente, non entità che vivono da sole.

---

### Chi la scrive

La tabella si popola col seed delle migrazioni. Né una funzione del database né il backend la
scrivono; l'audit lo tiene il trigger generico del framework.

---

### ⚠️ Che cosa oggi non copre

* **L'applicazione ha i privilegi di scrittura.** Il ruolo applicativo ha INSERT, UPDATE e DELETE
  sulla tabella, anche se nessun servizio la scrive: un errore del backend potrebbe aggiungere o
  togliere una dashboard. Lo schema `ui` non è sul modello «una scrittura = un verbo».
* **La lettura per codice ha due copie.** La funzione di risoluzione cerca la dashboard accesa per
  codice, e il backend ripete la stessa ricerca prima di scrivere una preferenza. Le liste hanno un
  building block per questa lettura, [fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice); le
  dashboard no.

---

### Codici errore

* `E_UI_DASHBOARD_NON_TROVATA` — codice inesistente o dashboard spenta, alla risoluzione.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — spegnimento con preset accesi.
* Il codice duplicato arriva come violazione di `uq_ui_dashboard_definizione_codice`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — la dashboard inesistente rifiutata.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — le regole ATTIVO e le eccezioni delle tabelle di `ui`.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella, con la home.
* 2026-11-08 — lo schema `ui` entra nell'ambito delle automazioni: audit del framework e regola ATTIVO,
  con le eccezioni per pool e preferenze.
* 2026-11-21 — codice, descrizione e note non sono mai la stringa vuota (un CHECK per colonna).

---

{% include-markdown "signature-core.md" %}
