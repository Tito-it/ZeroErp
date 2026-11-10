## 📘 Documentazione Concettuale – Tabella `dbops.automazione_overlap`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — legge il registro e crea i vincoli che mancano
> * [dbops.fn_jsonb_array_di_testi](/dbzero/dbops/funzioni/fn_jsonb_array_di_testi) — la forma delle due liste di chiave, letta dal CHECK
> * [maintenance.proc_automations_overlap_job](/dbzero/maintenance/funzioni/proc_automations_overlap_job) — il giro che esegue l'apply, a orario e nella convergenza del rilascio
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione OVERLAP fra le altre del framework

---

### 🎯 Scopo Principale

Il registro dei vincoli di **non sovrapposizione** dei periodi di validità: una riga per tabella
dice quale chiave non può avere due periodi che si toccano, e da quali colonne si legge il
periodo. Da qui il framework crea, e ricrea se sparisce, il vincolo `EXCLUDE USING gist` della
tabella.

Il registro è la **fonte da cui il vincolo si ricostruisce**: un vincolo che un changeSet toglie
per sbaglio, o che una ricostruzione della tabella perde, torna al giro successivo dell'apply,
identico a quello registrato.

---

### Che cosa dice una riga

* **La tabella**: `target_schema` e `target_table`, la chiave del registro. Non c'è una FK verso
  il catalogo: una riga può restare indietro rispetto a una tabella rinominata o ritirata, e
  l'apply la salta dichiarandolo.
* **La chiave logica**, cioè le righe che non possono sovrapporsi fra loro: `key_columns` sono
  colonne semplici, che l'apply verifica e quota; `key_expressions` sono **espressioni** (per
  esempio un `COALESCE` che rende uguali fra loro i NULL di una colonna facoltativa), che l'apply
  usa così come sono scritte. Le due liste si sommano, colonne prima ed espressioni dopo, ciascuna
  nell'ordine in cui è scritta; serve almeno una chiave. Entrambe sono **array JSON di testi**
  (per esempio `["listino_id"]`), oppure vuote: il CHECK `chk_automazione_overlap_chiavi`
  rifiuta un valore che non è un array o un array con un elemento che non è un testo.
* **Il periodo**, in due forme: una colonna range nativa (`range_col`, per esempio una
  `validita` generata) oppure la coppia di date `valido_dal_col` / `valido_al_col`, da cui
  l'apply costruisce l'intervallo con gli estremi di `range_bounds` (di norma inclusi entrambi) e
  una fine vuota che vale «per sempre». Se `range_col` è valorizzata, vince lei.
* **Il perimetro**, facoltativo: `where_predicate` rende il vincolo **parziale**, valido solo fra
  le righe che soddisfano la condizione (per esempio solo fra le righe attive, o fra le versioni
  in un certo stato). Vuoto, il vincolo vale per tutte le righe.
* **Il nome** del vincolo, `constraint_name`; vuoto, vale il template `ex_<tabella>_no_overlap`.
  Lo risolve [fn_nome_oggetto_dichiarato](/dbzero/dbops/funzioni/fn_nome_oggetto_dichiarato),
  che lo accorcia con un hash oltre i 63 caratteri. ⭐ È dal nome che l'apply riconosce il vincolo
  della riga.
* **L'interruttore**: `active` vero rende la riga eleggibile; `exec_mode` (`AUTO`, `CI`,
  `SCHEDULED`) la limita a un contesto d'esecuzione, e `AUTO` vale per tutti. ⚠️ Spegnere una
  riga non toglie il vincolo già creato: togliere un vincolo d'integrità è una decisione, e la
  prende un changeSet esplicito, nello stesso cantiere che spegne la riga nel CSV. Un presidio pgTAP è rosso se una regola spenta ha
  ancora il suo vincolo.
* `note` racconta perché la riga è com'è.

---

### ⛔ `key_expressions` e `where_predicate` sono DDL di fiducia

I due campi entrano nel vincolo come testo, senza essere quotati né verificati: sono frammenti
di DDL. Li scrive solo chi migra, nel CSV del registro; mai un input applicativo.

---

### ⭐ È un mirror del CSV

Le righe vengono dal CSV `80_data/sql/dbops/automazione_overlap.csv`, ricaricato a ogni migrate,
come le altre tabelle `automazione_*` di `dbops`. Un vincolo di non sovrapposizione che nasce o
cambia forma si registra lì, a mano: è l'unica sorgente del registro, e non c'è una rilevazione
automatica che deduca le righe dallo schema. Nel CSV le due liste di chiave si scrivono come array
JSON.

Il caricamento aggiorna e aggiunge, non cancella: una riga che c'è solo sul database di una
macchina resta. Per ritirare una regola la si spegne nel CSV (`active` falso).

⚠️ Cambiare `where_predicate` o la chiave di una riga **non** cambia un vincolo già creato:
l'apply salta la tabella se ci trova già il vincolo col nome della riga (o un
`UNIQUE … WITHOUT OVERLAPS` sul periodo), senza confrontarne la forma. Il vincolo vecchio si toglie
con un changeSet, nello stesso cantiere che cambia la riga nel CSV, e il giro successivo lo ricrea
nella forma nuova.
Un altro `EXCLUDE` della tabella, con un altro nome, non conta: la regola riceve comunque il suo.

---

### Test

* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — ogni `constraint_name` di una riga
  attiva esiste come vincolo `EXCLUDE`, e nessun oggetto con quel nome è un semplice indice.
* `db/pgtap/dbops/test-overlap-regola-e-vincolo-v1.sql` — ogni regola attiva su una tabella che
  esiste ha il suo vincolo, per nome, o un `UNIQUE … WITHOUT OVERLAPS` sul periodo; nessuna regola
  spenta ha ancora il suo vincolo vivo.
* `db/pgtap/dbops/test-nomi-e-chiavi-registri-v1.sql` — le due liste di chiave sono `jsonb`, e il
  CHECK rifiuta una chiave che non è un array e un array con un elemento che non è un testo.
* `db/pgtap/vendite/test-listino-versione-in-vigore-v1.sql` — la riga del registro delle versioni
  di listino dice lo stesso predicato del vincolo vivo.
* I test del comportamento dell'apply sono nella scheda di
  [fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap).

---

### Note di migrazione

* 2026-01-19 — nasce il registro, insieme a seed e apply.
* 2026-04-12 — arriva `range_col`, per le tabelle con una colonna range nativa.
* 2026-06-02 — arrivano `where_predicate` (vincoli parziali) e `key_expressions`, e i vincoli
  parziali già esistenti vengono registrati (`refactor-overlap-v2`). Dallo stesso giorno l'apply
  ha un giro a orario: prima il registro non lo eseguiva nessuno.
* 2026-11-04 — ritirata `fn_seed_automazione_overlap`, la rilevazione automatica nata col
  registro. Non la chiamava nessuno, ed era una seconda sorgente: lanciata, riscriveva le righe
  curate dai changeSet (`brief-db-revisione-dbops`).
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — l'apply riconosce il vincolo della riga per nome, non da un qualsiasi `EXCLUDE`
  che nomini la colonna del periodo; il nome viene da `fn_nome_oggetto_dichiarato`, e sparisce la
  variante col suffisso `_c` (`brief-db-revisione-dbops`, giro 10c).
* 2026-11-09 — `key_columns` e `key_expressions` passano da array di testo nativi a `jsonb`
  (array JSON di testi), col CHECK `chk_automazione_overlap_chiavi`; il registro prende il suo CSV,
  come gli altri `automazione_*` (`20261110-38`, `-39`, `-40`, brief-db-revisione-dbops, giro 10c).
  Prima era l'unica tabella di configurazione senza CSV, perché Liquibase non carica un array
  nativo da un CSV, e le righe le scrivevano `INSERT` e `UPDATE` sparsi nei changelog. Il cambio
  di tipo sta in `80_data`, dopo quei changeSet vecchi, che su un database da zero scrivono ancora
  le chiavi nella forma di prima.

---

{% include-markdown "signature-core.md" %}
