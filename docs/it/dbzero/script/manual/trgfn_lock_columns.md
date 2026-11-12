## 📘 Documentazione Concettuale – Trigger function `script.trgfn_lock_columns`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro delle colonne bloccate, da cui l'automazione genera i trigger
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le colonne bloccate solo a certe condizioni, che il form legge
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — la frase di ogni codice passato come argomento
>
> Approfondimento viste:
>
> * [dbops.vw_non_editable_fields](/dbzero/dbops/views/vw_non_editable_fields) — le colonne bloccate, come le legge il form
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra il rifiuto e solleva il codice
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — l'override per la manutenzione, nella stessa forma, sulle cancellazioni
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — la regola `LOCK_COLUMNS`

---

### 🎯 Scopo Principale

La trigger function generica che **impedisce di cambiare le colonne protette** di una tabella: per
ogni colonna che un UPDATE modifica, rifiuta con il codice d'errore dichiarato per quella colonna.

Una sola funzione serve tutte le tabelle: le colonne e i codici arrivano come argomenti del
trigger, quindi una colonna nuova da bloccare è una riga di registro, non una funzione nuova.

---

### Gli argomenti sono coppie: colonna e codice

Il trigger passa gli argomenti a coppie, prima il nome della colonna e poi il codice d'errore da
sollevare quando quella colonna cambia. Ogni colonna ha il suo codice, quindi l'operatore legge
una frase che parla del campo che ha toccato.

Un numero dispari di argomenti è un trigger montato male: la funzione rifiuta ogni UPDATE con
`E_ARGOMENTI_A_COPPIE`, prima di guardare i valori.

---

### Che cosa conta come modifica

La funzione confronta il valore vecchio e quello nuovo **resi a testo**, con «distinto da»: un
passaggio da NULL a un valore, o viceversa, è una modifica. Un UPDATE che riscrive lo stesso
valore passa.

La funzione non giudica il resto della riga: le colonne che non sono fra gli argomenti si
modificano liberamente, e se nessuna colonna protetta cambia l'UPDATE passa.

---

### Il rifiuto dice quale campo correggere

Il codice si solleva con il nome della colonna come valore del messaggio, e con un contesto che
porta `campo` (la colonna da evidenziare nel form), `column`, il valore vecchio e quello nuovo. La
registrazione e il rilancio li fa `script.fn_log_and_raise_error`, nell'area `database`, con il
nome del trigger come origine.

---

### ⭐ I trigger li genera l'automazione, non una migrazione

Chi vuole bloccare una colonna la dichiara in `dbops.automation_lock_columns`, col suo codice: la
regola `LOCK_COLUMNS` monta il trigger su quella tabella. Il form legge lo stesso registro, da
`dbops.vw_non_editable_fields`, per mostrare il campo come non modificabile: il blocco e la sua
resa a video hanno una fonte sola.

Fa eccezione una tabella fuori dall'ambito dell'automazione: lì il trigger lo monta una
migrazione, e il registro lo dichiara comunque (la regola è nella guida e nella pagina di `dbops.automation_lock_columns`).

---

### ⚠️ L'override per la manutenzione

Una transazione di manutenzione può modificare le colonne protette accendendo
`zeroerp.allow_lock_columns_override` al valore `on`, con `SET LOCAL` per non portarlo oltre la
transazione. Con l'override acceso la funzione lascia passare la riga senza controlli; con il
GUC assente, o con qualunque altro valore, le colonne restano protette.

Serve a non dover spegnere e riaccendere il trigger: è la stessa forma dell'override delle
cancellazioni di `script.trgfn_delete_block_by_guc`.

---

### Codici errore

* `E_ARGOMENTI_A_COPPIE` — il trigger ha un numero dispari di argomenti.
* Il codice passato come argomento per ogni colonna, quando quella colonna cambia: è il registro
  a sceglierlo (per esempio `E_CODICE_NON_MODIFICABILE`).

---

### Test

* `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql`, `db/pgtap/vendite/test-ordini-lock-cliente.sql`,
  `db/pgtap/config/test-user-emittenti-fiscali-immutable.sql` — colonne bloccate di tabelle
  diverse: il cambio è rifiutato col codice dichiarato per la colonna.
* `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql` — ogni codice sollevato ha il suo
  messaggio.

---

### Note di migrazione

* 2025-05-07 — nasce.
* 2025-06-17 — la registrazione del rifiuto passa per `dblink`, in una sessione separata, così
  il log resta anche quando la transazione viene annullata.
* 2026-03-28 — l'override per la manutenzione `zeroerp.allow_lock_columns_override`.
* 2026-11-11 — il contesto porta `campo`, la colonna da evidenziare nel form
  (`brief-db-revisione-catalogo`, giro G1-G2).

---

{% include-markdown "signature-core.md" %}
