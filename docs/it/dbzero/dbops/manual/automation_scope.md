## 📘 Documentazione Concettuale – Tabella `dbops.automation_scope`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole che girano dentro l'ambito deciso qui
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — legge l'elenco direttamente, per decidere quali FK guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — ricava dalla tabella l'elenco degli schemi
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — ricava dalla tabella il filtro per tabella dentro uno schema
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework che questa tabella delimita

---

### 🎯 Scopo Principale

L'elenco degli schemi, e dentro uno schema delle tabelle, su cui girano le automazioni del
database: è una allow-list, e uno schema che non compare qui è fuori dal perimetro di ogni
automazione che non riceve un ambito esplicito.

Una riga è una coppia schema e filtro di tabella. Il filtro `*all` vuol dire «tutto lo
schema»; un altro valore è un pattern `LIKE` sul nome della tabella. La chiave è la coppia,
quindi uno schema può comparire più volte con filtri diversi.

---

### Da dove viene l'ambito di una corsa

L'ambito di una corsa si decide in tre gradini, e il primo che risponde vince:

1. l'elenco di schemi passato esplicitamente alla funzione;
2. gli schemi di questa tabella, se la tabella esiste e ha righe;
3. altrimenti tutti gli schemi utente, tolti quelli di sistema e `storico`.

Il gradino 3 è una rete per un database in cui la tabella è vuota: con il seed caricato non
si raggiunge. ⚠️ Il fallback esclude `storico`, l'elenco del seed invece lo contiene:
lo schema `storico` è nell'ambito, e sono i runner della storicizzazione a escluderlo per
conto proprio.

---

### ⚠️ Due livelli, e il secondo vale solo dentro il primo

* **Schema**: `fn_resolve_scope` restituisce gli schemi elencati, e i runner girano solo su
  quelli.
* **Tabella**: `fn_table_in_scope` decide quali tabelle di uno schema entrano. Uno schema
  con una riga `*all` entra per intero; uno schema con soli pattern entra solo per le
  tabelle che li soddisfano (è il caso di `dbops`, che espone alle automazioni pochi
  registri e non i suoi strumenti).

Il filtro per tabella risponde «sì» anche per uno schema che non ha nessuna riga: per lui la
decisione l'ha già presa il livello schema. Chi lo chiama da solo, senza passare per
l'elenco degli schemi, vede quindi tutto.

---

### ⛔ Uno schema fuori dall'elenco non ha automazioni

Fuori dall'elenco una tabella non riceve nessuno dei trigger generati: storico, `tx_id`,
audit, lock, blocco del `DELETE`, regola del periodo. Lo schema `ui` è fuori, e dove una
sua tabella ha bisogno di un comportamento che altrove dà l'automazione, il
trigger si scrive a mano. Uno schema nuovo che deve avere le automazioni entra con una
riga nel seed.

---

### Come si aggiorna

La sede è il CSV di seed `80_data/sql/dbops/automation_scope.csv`: si edita quello, non si
scrive a mano sul database. Un elenco esplicito passato a una singola chiamata non tocca la
tabella e vale solo per quella corsa.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — restringe l'ambito di `dbops` a tre tabelle
  di prova e verifica che la pulizia giri solo su quelle.
* `db/pgtap/documenti/test-documenti-schema-base.sql` — lo schema `documenti` è registrato
  per intero.
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — ogni regola di pulizia
  attiva punta a uno schema che l'ambito comprende.

---

{% include-markdown "signature-core.md" %}
