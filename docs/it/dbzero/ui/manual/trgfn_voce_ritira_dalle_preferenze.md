## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_voce_ritira_dalle_preferenze`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — il catalogo da cui la colonna esce
> * [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget) — il pool da cui la card esce
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — le preferenze che perdono la colonna
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — le preferenze che perdono la card
>
> Approfondimento funzioni:
>
> * [ui.fn_configurazione_senza_codici](/dbzero/ui/funzioni/fn_configurazione_senza_codici) — toglie la voce dalla configurazione
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — il guard che giudica ciò che resta
> * [ui.trgfn_misure_pagina_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_misure_pagina_ritira_dalle_preferenze) — la gemella, per la misura

---

### 🎯 Scopo Principale

`ui.trgfn_voce_ritira_dalle_preferenze` fa uscire una colonna tolta da una lista, o una card tolta dal
pool di una dashboard, anche dalle preferenze che la nominano. Della preferenza si toglie solo quella
voce: le altre restano nel loro ordine, e la misura o il numero di card non cambiano.

---

### Perché serve

La preferenza porta le colonne e le card per codice, dentro un campo JSONB dove una FK non arriva. Il
guard di forma vuole ogni codice nella lista o nel pool, e giudica la configurazione intera a ogni
salvataggio. Senza questa funzione una colonna che nessun preset nominava si toglieva, la preferenza
restava con il suo codice, e da lì ogni salvataggio che conservava le colonne veniva rifiutato, anche
il cambio delle sole righe per pagina. La schermata si apriva lo stesso, perché la lettura salta una
voce che il catalogo non ha più: il blocco si vedeva solo al salvataggio.

È montata `AFTER DELETE`, riga per riga, su [lista_colonna](/dbzero/ui/tabelle/lista_colonna) e su
[dashboard_widget](/dbzero/ui/tabelle/dashboard_widget). Il solo DELETE basta: le strade che con un
aggiornamento farebbero uscire un codice dal suo contenitore sono chiuse dal lucchetto di colonna (la
lista e il codice di una colonna, la dashboard e la card di una riga del pool, il codice di una card).

Se l'elenco della preferenza resta vuoto, la chiave esce: quella parte della preferenza torna a
seguire il preset.

La riscrittura delle preferenze passa dai loro trigger, come ogni scrittura di dominio: il guard di
forma giudica la configurazione che resta.

---

### Codici errore

* `E_TRIGGER_ARGOMENTI_INVALIDI` — la funzione montata su un'altra tabella, o non come trigger
  `AFTER DELETE` di riga.
* I codici del guard di forma, se la configurazione che resta non ha la forma ammessa.

---

### Test

* `db/pgtap/ui/test-ui-ritiro-voce-preferenze-v1.sql` — la voce della colonna ritirata esce dalla
  preferenza della lista e non da quella di un'altra lista con lo stesso codice; dopo il ritiro la
  persona cambia la sola misura e salva; la preferenza che aveva solo quella colonna segue il preset;
  lo stesso per la card tolta dal pool; il montaggio sulle due tabelle.

---

### Note di migrazione

* 2026-11-22 — nasce, con la bonifica delle voci che il ritiro di prima aveva lasciato (le tre
  colonne tolte dalla lista dei fornitori il 2026-11-21) e con i lucchetti dell'appartenenza.

---

{% include-markdown "signature-core.md" %}
