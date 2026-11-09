## 📘 Documentazione Concettuale – Vista `dbops.vw_funzioni_check_codici`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo) — il presidio del canale del campo, che la legge
> * [dbops.vw_punti_primo_motivo](/dbzero/dbops/views/vw_punti_primo_motivo) — il rubinetto del primo motivo, che la legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_regexp_occorrenze](/dbzero/dbops/funzioni/fn_regexp_occorrenze) — l'estrazione che dichiara la propria cardinalità
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — il corpo senza commenti da cui la vista legge le tre funzioni
> * [dbops.fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile) — quali funzioni hanno un corpo da leggere: il perimetro
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — il meccanismo condiviso che solleva il primo motivo

---

### 🎯 Scopo Principale

La risalita «funzione → funzioni di controllo (`fn_check_*`) che nomina → codici d'errore che quei
controlli producono come motivo», con l'indicazione se il motivo porta anche il nome del campo da
correggere. È una tabella di collegamenti letta da due presidi, non un allarme.

Il perimetro sono le funzioni dal **corpo leggibile**, PL/pgSQL e SQL (comprese le SQL `BEGIN
ATOMIC`), come le decide [fn_corpo_leggibile](/dbzero/dbops/funzioni/fn_corpo_leggibile): una
funzione SQL che nomina una `fn_check_*` ne può sollevare i motivi, e una `fn_check_*` scritta in SQL
nomina motivi come le altre.

---

### ⭐ Perché esiste da sola

Due controlli hanno bisogno della stessa lettura:

* il **rubinetto** ([vw_punti_primo_motivo](/dbzero/dbops/views/vw_punti_primo_motivo)), che
  sorveglia le poche funzioni che sollevano il primo motivo «a mano» invece di passare dal
  meccanismo condiviso;
* il presidio del **canale del campo**
  ([vw_punti_canale_campo](/dbzero/dbops/views/vw_punti_canale_campo)), che deve vedere tutte le
  funzioni che sollevano il codice di un motivo, quelle a mano e quelle che passano dal meccanismo.

Se ciascuno si tenesse la propria copia, il giorno in cui una cambia le due misure direbbero cose
diverse sullo stesso fatto senza che nessuno se ne accorga: la lettura sta qui, una volta.

---

### Come si legge

Una riga per funzione, controllo e codice:

| Colonna | Che cosa porta |
| --- | --- |
| `funzione` | chi nomina il controllo |
| `check_funzione` | il controllo nominato: tutti quelli nominati nel testo, non solo quello percorso in un ramo |
| `check_emette_valori` | il controllo prepara anche i valori per comporre la frase del messaggio (anche per delega) |
| `codice` | un codice che il controllo può produrre; vuoto se non ne produce nessuno, e il collegamento resta visibile |
| `n_motivi` | quante volte il controllo lo nomina |
| `motivo_chiave` | `campo` o `parametro` se **ogni** motivo con quel codice porta anche quella chiave nel dettaglio; altrimenti vuoto. È pessimista di proposito |

---

### ⭐ Un controllo che passa la parola a un altro

Certi controlli non scrivono i propri motivi: restituiscono quelli di un altro controllo, tutti o una
parte. La vista segue il passaggio, a qualunque profondità:

| Il controllo… | … e la vista |
| --- | --- |
| **accoda** i motivi dell'altro o li prende per rilanciarli | eredita tutti i suoi codici |
| li **filtra** sugli elementi, confrontando il codice con dei letterali (uguale a uno, o in un elenco) | eredita **solo** quei codici |
| li **conta** o ci fa un `IF`, e poi scrive un motivo suo | non eredita niente: il codice è il suo |

⚠️ La terza riga non è un dettaglio: trattare ogni chiamata come un passaggio di parola metteva nel
perimetro del rubinetto punti che i motivi dell'altro li contano e basta. Il filtro si legge solo
nell'istruzione della chiamata; un filtro per esclusione (diverso da, non in) non è riconosciuto, e
allora si eredita tutto — un collegamento in più, mai uno in meno.

---

### ⚠️ Che cosa non dice

Legge il **testo** delle funzioni dal corpo senza commenti di
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione), di riga e a blocco e con i letterali
intatti: riconosce la forma scritta, non il significato. Lo stesso corpo vale per tutte le colonne,
compresa `check_emette_valori`: una parola citata in un commento della check non la fa emittente. Un controllo nominato in due rami di cui uno solo viene percorso compare
comunque: un collegamento in più costa una riga da guardare, uno in meno un caso non visto. Le
finestre dei motivi si tagliano sulle occorrenze della chiave `codice` e non sul punto e virgola,
perché un controllo scritto con una sola istruzione può costruire più motivi.

---

### ⚠️ Due proprietà che non si vedono nei risultati

Entrambe tengono la stima del costo sotto la soglia in cui PostgreSQL compila la query col JIT:
più di un secondo di preparazione per un decimo di secondo di lavoro, pagato da ogni lettura e dai
due presidi che la interrogano.

* **Legge solo i testi che contengono `fn_check_`**: un testo senza quel nome non può collegare
  niente, quindi le righe sono le stesse. Il prefiltro gira sul sorgente testuale, prima di togliere
  i commenti: è un sovrainsieme, perché togliere un commento accorcia il testo e non lo allunga.
  Una funzione SQL `BEGIN ATOMIC` non ha un sorgente testuale (il suo è vuoto): il prefiltro la
  lascia passare sempre, e la decide il filtro vero, sul corpo ricostruito.
* **Dichiara la cardinalità delle estrazioni**: le occorrenze si estraggono con
  [dbops.fn_regexp_occorrenze](/dbzero/dbops/funzioni/fn_regexp_occorrenze), che dichiara una riga
  invece delle dieci della funzione di sistema; i motivi si tagliano con una forma che non dichiara
  mille righe; l'estrazione delle deleghe si fa una volta sola. Senza, la stima saliva da sola appena
  le statistiche del catalogo contavano più corpi.

Chi riscrive la vista senza una delle due ottiene le stesse righe, solo molto più lente: per questo
c'è un pgTAP che guarda la stima del costo e non le righe.

La vista è `security_invoker` e legge i cataloghi di sistema.

---

### Test

* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il motivo che porta il campo nel dettaglio
  (`motivo_chiave`), la delega che eredita i codici e il consumo che non li eredita (casi costruiti).
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — la canarina: la risalita riconosce la forma
  con la variabile d'appoggio e la lega alla sua funzione di controllo.
* `db/pgtap/dbops/test-vw-funzioni-check-codici-sotto-jit-v1.sql` — la stima di questa vista e dei
  due presidi sotto la soglia del JIT; la cardinalità dichiarata e non inlineata; nessuna estrazione
  di sistema chiamata direttamente.
* `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` — i codici di una funzione di
  controllo di pagamenti restano visibili qui.
* `db/pgtap/dbops/test-presidi-codici-corpo-leggibile-v1.sql` — risale da una funzione SQL `BEGIN
  ATOMIC` alla check scritta in SQL e al suo codice (caso costruito).

---

### Note di migrazione

* 2026-09-21 — nasce staccando la risalita dal rubinetto
  (`brief-be-presidio-ui-action-e-canale-campi` §4): il presidio del canale del campo l'avrebbe
  ricopiata.
* 2026-09-24 — segue la delega su più livelli: due madri di revisione uscivano come ramo cieco nel
  presidio del canale del campo.
* 2026-10-10 — legge solo i testi che contengono `fn_check_`.
* 2026-10-12 — cardinalità dichiarata: il prefiltro da solo reggeva solo finché le statistiche
  sottostimavano i corpi con `fn_check_`.
* 2026-11-04 — i tre corpi si leggono da `fn_corpo_funzione` (D14 di `brief-db-revisione-dbops`):
  la copia di prima toglieva un commento anche dentro un letterale; e `check_emette_valori` leggeva il
  sorgente commenti compresi, così un 'valori' in un commento della check la dava per emittente.
* 2026-11-09 — il perimetro passa dal solo PL/pgSQL ai corpi leggibili, PL/pgSQL e SQL, letti da
  `fn_corpo_leggibile`; il prefiltro su `fn_check_` lascia passare le SQL `BEGIN ATOMIC`, che non
  hanno un sorgente testuale (`20261110-80`, `brief-db-revisione-dbops`, giro 12).

---

{% include-markdown "signature-core.md" %}
