## 📘 Documentazione Concettuale – Tabella `dbops.automation_scope`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole che girano dentro l'ambito deciso qui
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la politica degli indici delle FK, che dell'ambito legge solo lo schema
>
> Approfondimento viste:
>
> * [dbops.vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore) — le tabelle con una colonna che promette un'automazione che nessuno esegue
>
> Approfondimento funzioni:
>
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — ricava dalla tabella l'elenco degli schemi
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — ricava dalla tabella il filtro per tabella dentro uno schema
> * [dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito) — lo schema è governato dalla politica degli indici delle FK
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

### ⭐ La politica degli indici delle FK legge solo lo schema

Gli indici delle chiavi esterne (`dbops.fk_index_policy`) non seguono il filtro per tabella: uno
schema con almeno una riga qui è governato per intero, qualunque sia il suo filtro. È una scelta
dichiarata. L'indice di una chiave esterna serve a ogni tabella dello schema, mentre l'elenco delle
tabelle serve ai trigger delle altre automazioni: aggiungere una tabella all'elenco solo per il suo
indice vorrebbe dire armare su di lei anche quei trigger.

La lettura sta in un posto solo,
[dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito): la usano
le viste degli indici e la procedura che applica la politica. In `dbops`, per esempio, la politica
governa le chiavi esterne di tutte le tabelle, non solo dei registri che l'elenco espone ai trigger.

---

### ⛔ Uno schema fuori dall'elenco non ha automazioni

Fuori dall'elenco una tabella non riceve nessuno dei trigger generati: storico, `tx_id`,
audit, lock, blocco del `DELETE`, regola del periodo. Lo schema `ui` è fuori, e dove una
sua tabella ha bisogno di un comportamento che altrove dà l'automazione, il
trigger si scrive a mano. Uno schema nuovo che deve avere le automazioni entra con una
riga nel seed.

⛔ Una tabella fuori dall'elenco non deve promettere ciò che nessuno esegue: una colonna `tx_id`,
`storicizza` o `cleanup_at` senza il trigger montato a mano (o, per `cleanup_at`, senza il purge,
che è solo del runner) la segnala il presidio
[dbops.vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore),
che usa lo stesso filtro dei due livelli qui sotto. Il debito noto sta in
[dbops.marcatori_automazione_debito](/dbzero/dbops/tabelle/marcatori_automazione_debito).

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
