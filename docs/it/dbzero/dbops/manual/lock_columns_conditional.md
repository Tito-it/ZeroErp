## 📘 Documentazione Concettuale – Tabella `dbops.lock_columns_conditional`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — i lock che valgono sempre, per ogni riga
>
> Approfondimento viste:
>
> * [dbops.vw_non_editable_fields](/dbzero/dbops/views/vw_non_editable_fields) — i lock statici, che il form riceve insieme a quelli di qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — valuta le regole su una riga e dice al form quali campi spegnere
> * [catalogo.fn_articolo_colonne_struttura](/dbzero/catalogo/funzioni/fn_articolo_colonne_struttura) — legge da qui le colonne strutturali di un articolo
> * [catalogo.fn_articolo_usato](/dbzero/catalogo/funzioni/fn_articolo_usato) — il predicato condiviso dalla regola del form e dal guard
> * [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva) — il guard che rifiuta, gemello delle regole sulla distinta
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard che rifiuta, gemello delle regole sull'uso

---

### 🎯 Scopo Principale

Il registro dei **lock condizionali**: colonne che non si possono modificare solo quando una
condizione sulla riga è vera — per esempio un flag di struttura di un articolo che è padre di una
distinta in vigore, o una colonna strutturale di un articolo già usato. Serve al **form**: dice
quali campi spegnere per quella riga.

È il complemento dei lock statici di `dbops.automation_lock_columns`, che valgono sempre. Le due
fonti arrivano insieme al form attraverso `dbops.fn_non_editable_fields`.

---

### ⭐ Segnala, non rifiuta

Una regola di qui non ferma nessuna scrittura: a rifiutare il salvataggio è un guard trigger
sulla tabella, che ha la regola scritta per conto suo. La riga di qui è il suo **gemello per il
form**: spegne il campo prima che l'operatore provi a cambiarlo.

Per questo togliere o disattivare una regola non apre la colonna: il guard continua a rifiutare,
e la colonna smette solo di apparire spenta. È la direzione sicura.

⚠️ Due copie della stessa regola possono divergere. La forma che non diverge è una condizione che
chiama **lo stesso predicato** del guard (le regole sull'uso dell'articolo chiamano
`catalogo.fn_articolo_usato`, come il guard). Le regole sulla distinta ripetono invece nel
testo la condizione del guard, e vanno cambiate insieme a lui: è successo col giorno di
riferimento, passato da quello del server a quello aziendale.

---

### La condizione

`condition_expr` è un'espressione booleana che si valuta sulla riga: `$1` è l'id della riga,
passato come testo, e il cast al tipo giusto lo fa l'espressione. Vero spegne il campo; falso o
vuoto no. L'id entra come parametro, quindi non può iniettare codice; l'espressione invece si
esegue così com'è scritta, e non deve avere effetti.

La valutazione gira con i diritti e la row level security di chi chiede: le tabelle che
l'espressione legge devono essere leggibili da chi usa il form. Un predicato che deve vedere oltre
la RLS — l'uso di un articolo nei documenti di altre aziende — è una funzione `SECURITY DEFINER`
che la condizione chiama.

---

### Chi scrive e chi legge

* Si scrive **solo da migrazione**: nessuna API espone il registro, e la revisione del codice è
  la protezione dell'espressione. Non c'è una validazione della sintassi.
* `enabled` falso spegne la regola senza cancellarla.
* La chiave unica è (`schema_name`, `table_name`, `column_name`, `condition_expr`): più regole
  sulla stessa colonna sono ammesse, e il campo si spegne se una qualsiasi vale.
* ⚠️ C'è un secondo lettore: `catalogo.fn_articolo_colonne_struttura` ricava le colonne
  strutturali di un articolo dalle regole accese di `catalogo.articoli` la cui condizione è,
  testualmente, la chiamata a `catalogo.fn_articolo_usato`. Una regola riscritta con un testo
  diverso esce da quell'elenco.

---

### Test

* `db/pgtap/dbops/test-fn-non-editable-fields-conditional.sql` — le regole sulla distinta: i flag
  spenti per il padre di una distinta in vigore, per il figlio in vigore e per il figlio di una
  distinta futura.
* `db/pgtap/catalogo/test-articolo-usato-struttura-v1.sql` — un articolo usato ha le colonne
  strutturali spente nel form.
* `db/pgtap/catalogo/test-articolo-colonne-struttura-v1.sql` — l'elenco delle colonne strutturali
  letto da qui coincide con quello scritto nel guard.
* `db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql`,
  `db/pgtap/vendite/test-righe-articolo-ammesso-v1.sql` — le regole gemelle dei guard sulla
  distinta a un livello e sul solo componente.

---

### Note di migrazione

* 2026-05-22 — nasce, con le regole sui flag di struttura di un articolo padre o figlio di una
  distinta attiva.
* 2026-10-10 — le regole sulla distinta confrontano col giorno aziendale invece della data del
  server, come il guard.
* 2026-10-13 — entrano la regola del componente che non diventa composito e quelle
  sull'articolo usato (`brief-db-articoli-ammessi-per-documento`); esce la regola del solo
  componente in bozza, assorbita dall'uso.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).

---

{% include-markdown "signature-core.md" %}
