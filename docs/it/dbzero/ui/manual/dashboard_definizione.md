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
> * [ui.fn_dashboard_da_codice](/dbzero/ui/funzioni/fn_dashboard_da_codice) — la dashboard accesa per codice
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — risolve la dashboard per un utente

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

### Una dashboard spenta non si risolve, e sospende i suoi preset

Con `attivo` falso la dashboard non esiste per chi la chiede: la lettura per codice,
[fn_dashboard_da_codice](/dbzero/ui/funzioni/fn_dashboard_da_codice), risponde
`E_UI_DASHBOARD_NON_TROVATA`, e con lei la risoluzione e il backend, che rifiuta col codice stesso il
salvataggio, la cancellazione e l'«ignora» della preferenza.

Una dashboard si spegne anche con i preset accesi, e li **sospende** senza toccarli: alla riaccensione
tornano com'erano. È la forma delle liste. Non la trattengono i preset, le righe del pool né le
preferenze degli utenti: le loro FK sono in eccezione alla regola ATTIVO.

---

### Chi la scrive

La tabella la possiede il CSV del seed. L'applicazione la legge e non la scrive: ha il solo `SELECT`,
come sulle altre tabelle del catalogo delle dashboard (widget, pool, preset e loro composizione). Le
preferenze degli utenti restano scrivibili. L'audit lo tiene il trigger generico del framework.

---

### Una home senza card è un esito

La dashboard non promette una card a ogni utente: dopo il filtro dei permessi l'elenco dei widget può
essere vuoto. La regola è che la home non resti muta, e lo stato vuoto lo dice il frontend («nessuna
card attiva», «nessuna card disponibile per il tuo profilo»), non una card di riempimento.

---

### Codici errore

* `E_UI_DASHBOARD_NON_TROVATA` — codice inesistente o dashboard spenta, dalla lettura per codice.
* Il codice duplicato arriva come violazione di `uq_ui_dashboard_definizione_codice`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-dashboard-config.sql` — la dashboard inesistente rifiutata.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — le regole ATTIVO e le eccezioni delle tabelle di `ui`.
* `db/pgtap/ui/test-ui-catalogo-dashboard-v1.sql` — la dashboard spenta coi preset accesi, la lettura per
  codice, la porta in sola lettura, i testi non vuoti.

---

### Note di migrazione

* 2026-07-21 — nasce la tabella, con la home.
* 2026-11-08 — lo schema `ui` entra nell'ambito delle automazioni: audit del framework e regola ATTIVO,
  con le eccezioni per pool e preferenze.
* 2026-11-21 — codice, descrizione e note non sono mai la stringa vuota (un CHECK per colonna).
* 2026-11-21 — la dashboard spenta sospende i preset invece di non spegnersi; la lettura per codice ha
  il suo building block; l'applicazione perde la scrittura.

---

{% include-markdown "signature-core.md" %}
