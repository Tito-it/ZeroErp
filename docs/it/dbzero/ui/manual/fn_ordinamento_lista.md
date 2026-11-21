## 📘 Documentazione Concettuale – Funzione `ui.fn_ordinamento_lista`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — l'ordinamento di partenza del preset
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — codice, campo sorgente e flag `ordinabile`
> * [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso) — i permessi di colonna
>
> Approfondimento funzioni:
>
> * [ui.fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) — la scelta del preset di base
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello di ogni colonna per l'utente
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la riga della lista dal codice
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — la configurazione della lista, che l'ordinamento non porta
> * [ui.trgfn_ui_lista_preset_guard_ordinamento](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_ordinamento) — la forma dell'ordinamento alla scrittura
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — l'ordinamento di partenza

---

### 🎯 Scopo Principale

`ui.fn_ordinamento_lista` risponde con quale ordinamento parte una lista per un utente: le colonne e le
direzioni del suo preset di base, tolte quelle per cui l'utente non può ordinare, con il campo con cui
il backend ordina davvero.

---

### Da dove viene

L'ordinamento di partenza è del **preset di base**, scelto da
[fn_preset_di_base](/dbzero/ui/funzioni/fn_preset_di_base) come per la configurazione della lista: il
preset di ruolo (solo con la veste), poi quello dell'azienda, poi quello di sistema. La preferenza
dell'utente non entra: il clic sull'intestazione di una colonna vale per la sessione e non si salva.

Senza preset di base, o con un preset che non dice l'ordinamento, la risposta è un elenco vuoto: il
database non propone nessuna colonna da cui partire.

---

### Che cosa esce

Ogni voce dice la colonna (il suo codice), la direzione e il **campo sorgente**, nell'ordine scritto nel
preset. Il codice è l'identità della colonna; il campo sorgente è ciò che il backend passa al proprio
elenco delle colonne su cui ammette l'ordinamento, e che il frontend usa per accendere l'intestazione.

Escono dall'elenco le voci di una colonna:

* spenta;
* non `ordinabile`, o senza campo sorgente;
* `BLOCCATO` per l'utente, secondo
  [fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello): la stessa regola con cui la
  lista toglie la colonna e la ricerca libera non ci cerca. Un ordinamento non rivela l'ordine dei valori
  di una colonna che l'utente non vede.

---

### ⭐ Una chiamata leggera, una sede sola

Il backend chiede l'ordinamento a ogni pagina di una lista quando la richiesta non porta un ordinamento
proprio. Questa funzione risponde la sola chiave, senza risolvere colonne e permessi dell'intera
configurazione. È anche l'unica sede dell'ordinamento risolto:
[fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) non lo porta.

---

### Codici errore

* `E_UI_LISTA_NON_TROVATA` — lista inesistente o spenta (dal building block della lista).

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — le voci di una colonna spenta, di una non
  ordinabile e di una sensibile senza permesso tolte, il campo sorgente in uscita; una lista senza preset
  che risponde un elenco vuoto.

---

### Note di migrazione

* 2026-11-21 — nasce. Prima l'ordinamento usciva dalla configurazione della lista, preso dalla
  preferenza o dal preset così com'era scritto, anche con colonne spente, non ordinabili o bloccate per
  l'utente.

---

{% include-markdown "signature-core.md" %}
