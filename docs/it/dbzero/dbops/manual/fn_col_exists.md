## 📘 Documentazione Concettuale – Funzione `dbops.fn_col_exists`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — la usa per sapere se padre e figlio hanno la colonna `attivo`
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — la usa per tenere nel lock atteso solo le colonne che esistono
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — un altro dei runner che la interrogano
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — i runner che generano trigger dalle regole

---

### 🎯 Scopo Principale

Dice se una colonna esiste in una tabella: vero o falso, dato lo schema, la tabella e il nome
della colonna.

È una funzione di tre righe su cui poggiano molte **automazioni**: i runner che generano trigger
dalle regole la chiamano per lavorare solo con le colonne che la tabella ha davvero. Senza, una
regola che nomina una colonna assente farebbe fallire il DDL generato invece di essere saltata.

---

### ⚠️ «Non la vedo» e «non c'è» danno la stessa risposta

La funzione legge `information_schema`, che mostra solo le colonne su cui chi interroga ha qualche
privilegio. Un falso può quindi voler dire «la colonna non c'è» oppure «non la vedo». I runner
delle automazioni girano come proprietario dello schema, e per loro le due cose coincidono; un
chiamante con meno privilegi può ricevere un falso per una colonna che esiste.

Il confronto dei nomi è esatto: una colonna creata con un nome fra virgolette e lettere maiuscole
si trova solo scrivendo il nome esattamente così.

---

{% include-markdown "signature-core.md" %}
