## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_utilities`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'azienda, con la sua policy generale di arrotondamento
> * [config.utilities](/dbzero/config/tabelle/utilities) — l'utility, con i parametri di sistema
> * [config.utilities_tipi_ruolo](/dbzero/config/tabelle/utilities_tipi_ruolo) — quali ruoli possono servire un'utility
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility) — i parametri effettivi, sui tre livelli
> * [script.trgfn_guard_utility_tipo_ruolo_by_cols](/dbzero/script/funzioni/trgfn_guard_utility_tipo_ruolo_by_cols) — il ruolo emittente ammesso per l'utility

---

### 🎯 Scopo Principale

`anagrafiche.emittenti_fiscali_utilities` tiene i parametri d'importo che un'azienda vuole diversi da quelli di
sistema per una utility: i decimali e il metodo di arrotondamento degli importi, e le soglie della fattura
minima. La riga è facoltativa: senza, valgono i parametri di sistema.

---

### ⭐ Una riga è un'eccezione, non una configurazione obbligatoria

> ⚠️ **Cambio di modello deciso il 2026-11-27, non ancora costruito** ([brief-db-utility-gestite-dall-emittente](/dev/work-in-progress/brief-db-utility-gestite-dall-emittente)): la tabella diventa anche
> l'**elenco delle utility gestite** dall'azienda (riga accesa = utility attiva; un'azienda senza righe non ne gestisce
> nessuna), e i parametri d'importo restano facoltativi sulla riga. Questa sezione descrive il funzionamento di oggi,
> vero finché il giro DB non è applicato: si riscrive in quel giro.

Una riga per coppia azienda-utility (`uq_emittenti_fiscali_utilities_emittente_utility`). Nessuno la crea da sé:
un'azienda nuova fattura con i parametri di sistema dell'utility (`config.utilities`) e, per il solo metodo, con
la sua policy generale (`emittenti_fiscali.rounding_policy`).

I parametri non si leggono da qui: li dice `anagrafiche.fn_parametri_importo_utility`, che mette insieme i tre
livelli, e la leggono il ricalcolo dei totali della fattura, i parametri delle righe senza regole dell'articolo e
il lookup delle utility di un billing account.

---

### `attivo`: una riga spenta è come assente

`attivo` spegne l'eccezione senza cancellarla: `anagrafiche.fn_parametri_importo_utility` guarda solo le righe
accese, e con la riga spenta tornano i parametri di sistema e la policy dell'azienda. Una riga accesa chiede
un'azienda accesa (`E_ATTIVO_PADRE_NON_ATTIVO`, al COMMIT, anche quando la riga si riaccende), e un'azienda con
righe accese non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`): le righe si spengono prima.

---

### Che cosa dicono le colonne

* **I decimali** (`arrotondamento_importi_dec`): da 0 a 2.
* **Il metodo** (`metodo_arrotondamento_importi`): `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`, gli stessi valori di
  `rounding_policy`. È obbligatorio: una riga che c'è decide anche il metodo, e la policy dell'azienda vale
  solo senza riga.
* **Le soglie della fattura minima** (`minimo_soglia_min`, `minimo_soglia_max`): tutte e due o nessuna
  (`chk_emittenti_fiscali_utilities_soglie_coppia`), e quando ci sono la minima non supera la massima. Senza
  soglie l'azienda non ha fattura minima per quell'utility: le soglie non hanno un valore di sistema.

---

### L'utility deve poter essere servita da un emittente

Alla scrittura dell'utility o dell'azienda, `script.trgfn_guard_utility_tipo_ruolo_by_cols` controlla che il
ruolo di emittente fiscale sia ammesso per l'utility nella matrice `config.utilities_tipi_ruolo`
(`E_UTILITY_RUOLO_NON_AMMESSO`). Un'utility che nella matrice non ha righe è aperta a tutti i ruoli.

---

### ⚠️ Che cosa oggi non copre

* **`utility_id` è `bigint`**, mentre `config.utilities.id` è `integer`: la FK regge, ma i tipi delle due
  colonne divergono.

---

### Codici errore

* `E_UTILITY_RUOLO_NON_AMMESSO` — il ruolo di emittente fiscale non è ammesso per l'utility.
* `E_ATTIVO_PADRE_NON_ATTIVO` — una riga accesa su un'azienda spenta.

---

### Test

* `db/pgtap/vendite/test-parametri-importo-utility-v1.sql` — i tre livelli dei parametri, con e senza la riga.
* `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql` — i parametri effettivi nel lookup di un billing
  account.
* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — il guard della matrice utility-ruolo.

---

{% include-markdown "signature-core.md" %}
