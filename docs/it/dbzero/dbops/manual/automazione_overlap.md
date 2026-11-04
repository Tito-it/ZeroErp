## 📘 Documentazione Concettuale – Tabella `dbops.automazione_overlap`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — legge il registro e crea i vincoli che mancano
> * [dbops.fn_seed_automazione_overlap](/dbzero/dbops/funzioni/fn_seed_automazione_overlap) — la rilevazione automatica dallo schema, oggi senza chiamanti
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
  usa così come sono scritte. Le due liste si sommano; serve almeno una chiave.
* **Il periodo**, in due forme: una colonna range nativa (`range_col`, per esempio una
  `validita` generata) oppure la coppia di date `valido_dal_col` / `valido_al_col`, da cui
  l'apply costruisce l'intervallo con gli estremi di `range_bounds` (di norma inclusi entrambi) e
  una fine vuota che vale «per sempre». Se `range_col` è valorizzata, vince lei.
* **Il perimetro**, facoltativo: `where_predicate` rende il vincolo **parziale**, valido solo fra
  le righe che soddisfano la condizione (per esempio solo fra le righe attive, o fra le versioni
  in un certo stato). Vuoto, il vincolo vale per tutte le righe.
* **Il nome** del vincolo, `constraint_name`; vuoto, lo sceglie l'apply dal suo template.
* **L'interruttore**: `active` vero rende la riga eleggibile; `exec_mode` (`AUTO`, `CI`,
  `SCHEDULED`) la limita a un contesto d'esecuzione, e `AUTO` vale per tutti.
* `note` racconta perché la riga è com'è.

---

### ⛔ `key_expressions` e `where_predicate` sono DDL di fiducia

I due campi entrano nel vincolo come testo, senza essere quotati né verificati: sono frammenti
di DDL. Li scrive solo chi migra, con un changeSet di `80_data`; mai un input applicativo.

---

### Chi scrive il registro

Le righe si registrano a mano, con changeSet di `80_data`, quando un vincolo di non
sovrapposizione nasce o cambia forma. La funzione di rilevazione automatica
[fn_seed_automazione_overlap](/dbzero/dbops/funzioni/fn_seed_automazione_overlap) esiste, ma oggi
non la chiama nessuno: la sua scheda dice perché non va lanciata su un registro curato a mano.

⚠️ Cambiare `where_predicate` o la chiave di una riga **non** cambia un vincolo già creato:
l'apply salta la tabella se ci trova già un vincolo sul periodo. Il vincolo vecchio si toglie
nello stesso changeSet che cambia la riga, e il giro successivo lo ricrea nella forma nuova.

---

### Test

* `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql` — ogni `constraint_name` di una riga
  attiva esiste come vincolo `EXCLUDE`, e nessun oggetto con quel nome è un semplice indice.
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

---

{% include-markdown "signature-core.md" %}
