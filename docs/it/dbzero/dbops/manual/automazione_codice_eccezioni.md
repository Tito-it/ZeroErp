## 📘 Documentazione Concettuale – Tabella `dbops.automazione_codice_eccezioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `CODICE_MAIUSCOLO`, interruttore e nome del trigger
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito delle automazioni, che il perimetro restringe
>
> Approfondimento funzioni:
>
> * [dbops.fn_codice_maiuscolo_perimetro](/dbzero/dbops/funzioni/fn_codice_maiuscolo_perimetro) — dove le righe di questo registro diventano «non dovuto»
> * [dbops.fn_run_automations_codice_maiuscolo](/dbzero/dbops/funzioni/fn_run_automations_codice_maiuscolo) — il motore che toglie il trigger dalle tabelle in eccezione
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il trigger che qui non si monta
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.8, l'automazione CODICE_MAIUSCOLO

---

### 🎯 Scopo Principale

Il registro delle colonne `codice` che l'automazione CODICE_MAIUSCOLO **non normalizza**. La regola
vale per esclusione: ogni colonna `codice` di una tabella dell'ambito si salva in maiuscolo e senza
spazi ai bordi, e una tabella nuova nasce presidiata senza che nessuno debba registrarla. Qui
stanno le colonne per cui la regola sarebbe sbagliata.

---

### Chi va in eccezione

Una colonna `codice` che **non è un codice dell'operatore**:

* una **chiave tecnica letta per nome** dal codice: il nome di una colonna, di uno schema, di un
  job, la chiave di una lista o di un widget. Portarla in maiuscolo farebbe sparire la cosa che
  nomina;
* un codice che arriva da un **sistema esterno** dove il maiuscolo conta.

`codice_interno` non è nel perimetro e non si registra qui: lo scrive la migrazione, non
l'operatore.

---

### ⛔ Il motivo è obbligatorio

Il CHECK `chk_automazione_codice_eccezioni_motivo` pretende un motivo: un'eccezione senza perché è
un buco nel framework, non una decisione. `column_name` oggi vale solo `codice` (CHECK), ma sta
nella chiave: la regola è della colonna, e un secondo codice entrerebbe come riga.

---

### Le righe di oggi

Le ha decise Tid il 2026-11-04, sulle colonne con valori non in maiuscolo nei seed.

| Tabella | Perché |
| --- | --- |
| `ui.lista_colonna` | il codice è il nome della colonna sorgente della lista |
| `ui.lista_definizione`, `ui.lista_preset` | chiavi di lista e preset lette per nome da viste, BE e FE |
| `ui.widget`, `ui.dashboard_definizione`, `ui.dashboard_preset` | chiavi lette per nome dal FE |
| `dbops.processi` | il codice è il nome del job e del giornale delle corse |
| `config.aree_funzionali` | il codice è il nome di uno schema |
| `config.assets_ownership` | codici tecnici; eccezione di prudenza, da togliere quando si verifica che nessuno li confronta per nome |
| `config.note_stili` | lo stile esce dalle note per nome (`script.fn_get_note`) |

⚠️ `ui` e `dbops.processi` oggi sono fuori dall'ambito delle automazioni: le righe restano perché
la regola è sulla colonna, e reggono anche se l'ambito si allarga.

---

### Il seed e il ritiro di una riga

Le righe arrivano da `80_data`, dal CSV `dbops/automazione_codice_eccezioni.csv`, con un mirror
sulla chiave naturale (schema, tabella, colonna). Una riga nuova toglie il trigger al giro
successivo del motore (azione TOGLIE). Il mirror non cancella: per ritirare un'eccezione serve una
cancellazione esplicita in un changeSet nuovo, e il giro dopo il trigger torna.

---

### Test

`db/pgtap/dbops/test-codice-maiuscolo-v1.sql`: le dieci righe ci sono e nessuna ha il trigger
(test 8); un'eccezione nuova porta a TOGLIE e la tabella salva il codice com'è (test 20-21).

---

### Note di migrazione

* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).

---

{% include-markdown "signature-core.md" %}
