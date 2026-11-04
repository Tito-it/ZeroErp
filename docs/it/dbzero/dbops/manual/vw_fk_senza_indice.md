## 📘 Documentazione Concettuale – Vista `dbops.vw_fk_senza_indice`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la policy, i cui flag spenti tolgono una chiave esterna da qui
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi in cui la vista cerca
>
> Approfondimento viste:
>
> * [dbops.vw_fk_con_indice_missing_policy](/dbzero/dbops/views/vw_fk_con_indice_missing_policy) — la sorella: le chiavi esterne che un indice dedicato ce l'hanno, ma non la riga di policy
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — gli indici nati quando la copertura si misurava male
>
> Approfondimento funzioni:
>
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — la legge per registrare le scoperte
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — la legge come guardia prima di creare
>
> Guide:
>
> * [Linee guida SQL — automazione indici FK](/linee-guida-sql#87-automazione-indici-fk) — quando una FK si considera coperta

---

### 🎯 Scopo Principale

Le chiavi esterne degli schemi di `dbops.automation_scope` che **nessun indice sa servire**, con
il comando che creerebbe l'indice dedicato. Rispetta la policy: una chiave esterna con
`consentito = false` in `dbops.fk_index_policy` non compare.

Ha due lettori, entrambi automatici: `dbops.fn_populate_fk_index_policy` la usa per registrare le
scoperte, e `dbops.apply_fk_index_policy` la usa come guardia, perché crea un indice solo se la
chiave esterna compare ancora qui.

---

### 🔑 Quando una chiave esterna è coperta

Non serve un indice **dedicato**. Il controllo referenziale cerca nella tabella figlia le righe con
la chiave uguale a un valore dato, e qualunque btree sappia servire quella ricerca va bene. La
chiave esterna è coperta quando esiste un btree **valido e pronto** tale che:

1. **le colonne della chiave esterna sono la testa dell'indice**, confrontate come insieme: un
   indice su contratto e numero di riga copre la chiave esterna sul solo contratto. Il confronto non
   guarda l'ordine, perché il controllo filtra per uguaglianza su tutte le colonne della chiave e
   qualunque loro permutazione in testa funziona;
2. **le colonne della testa sono colonne vere**, non espressioni: un'espressione in testa non serve
   un'uguaglianza sulla colonna;
3. **il predicato è assente, oppure è una congiunzione di soli «colonna della chiave esterna non
   nulla»**.

#### Perché un parziale «non nullo» copre

Il valore che il controllo cerca non è mai nullo: una riga figlia con la chiave esterna vuota non ha
padre da verificare, e il controllo nemmeno parte. Cercare un valore implica quindi «la colonna non
è nulla», e il planner sa dimostrarlo. Su una chiave esterna nullabile un indice parziale così non è
un ripiego: è **migliore** di uno totale, perché non indicizza righe che nessuno cercherà mai.

#### ⛔ Ogni altro predicato viene rifiutato

Un indice limitato, per dire, alle sole righe radice **non** copre la chiave esterna: il controllo
deve trovare qualsiasi riga figlia. La vista rifiuta ogni altro predicato **anche quando di fatto
coprirebbe**. È una scelta: l'errore possibile è segnalare come scoperta una chiave esterna coperta
— un indice di troppo — e mai il contrario.

---

### Il comando suggerito

`create_index_suggestion` è il comando che crea l'indice dedicato, col nome `ix_` seguito da tabella
e colonne, nella forma che il vincolo di `dbops.fk_index_policy` pretende. `fk_cols` elenca le
colonne della chiave esterna in ordine alfabetico, e nello stesso ordine entrano nell'indice.

⛔ Il comando non si esegue a mano: gli indici delle chiavi esterne nascono da
`dbops.apply_fk_index_policy`, dopo un seed che accende il flag. Un indice creato fuori dalla policy
non è governato da nessuno, e ricompare in `dbops.vw_fk_con_indice_missing_policy`.

---

### ⚠️ Che cosa non vede

* le chiavi esterne fuori dagli schemi di `dbops.automation_scope`;
* le chiavi esterne con `consentito = false`: per scelta, sono eccezioni dichiarate. Ne segue che
  una chiave esterna registrata dal popolamento a flag spento **esce da qui** e resta visibile solo
  come riga di policy.

Nel catalogo dei presidi la vista è iscritta come lavorazione che non entra in nessun digest: la
consuma già un programma, e leggerla in un riepilogo sarebbe una seconda lettura di ciò che
l'automazione sistema da sola.

---

### Test

* `db/pgtap/vendite/test-ddt-righe-componenti-v1.sql`, `test-ordini-righe-componenti-v1.sql`,
  `test-preventivi-righe-componenti-v1.sql`, `test-contratti-righe-componenti-v1.sql` — la chiave
  esterna verso la riga di documento è coperta dalla UNIQUE che ha la riga come prima colonna: il
  test verifica la proprietà (non compare qui), non il nome di un indice.

---

### Note di migrazione

* 2026-07-27 — la copertura passa al prefisso, con entrambi i lati ordinati allo stesso modo, e
  contano solo i btree validi con predicato assente o di soli «non nullo». Prima si pretendeva
  l'uguaglianza esatta dell'elenco di colonne: le chiavi esterne servite da una UNIQUE più larga
  risultavano scoperte, finivano in policy e ricevevano un indice gemello (27 dei 48 indici
  ridondanti censiti quel giorno). Il difetto speculare: un indice parziale qualsiasi contava come
  copertura, e due chiavi esterne risultavano a posto senza esserlo.

---

{% include-markdown "signature-core.md" %}
