## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_utilities`

> **Ultimo aggiornamento**: 27 novembre 2026
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

`anagrafiche.emittenti_fiscali_utilities` dice **quali utility gestisce ciascuna azienda** (emittente fiscale):
una riga per coppia azienda-utility (`uq_emittenti_fiscali_utilities_emittente_utility`), e la riga presente
vuol dire che l'azienda gestisce l'utility. Sulla stessa riga stanno i parametri d'importo dell'azienda per
quell'utility, tutti facoltativi.

---

### ⭐ La riga dice «gestita», i parametri sono facoltativi

Una riga senza parametri dice solo che l'azienda gestisce l'utility. I parametri non si leggono da qui: li dice
`anagrafiche.fn_parametri_importo_utility`, che mette insieme tre livelli (la riga, la policy generale
dell'azienda `emittenti_fiscali.rounding_policy` per il solo metodo, i valori di sistema di `config.utilities`).
La leggono il ricalcolo dei totali della fattura, i parametri delle righe senza regole dell'articolo e il lookup
delle utility di un billing account. «Personalizzata» vuol dire che la riga porta almeno un parametro.

---

### Chi usa la riga: billing account e documenti

Un'azienda tratta solo le utility che gestisce. Puntano alla riga, con una FK composta su azienda e utility,
differita al commit:

* il collegamento del billing account con la sua azienda (`fk_emittenti_fiscali_ba_utility_gestita`): un billing
  account nasce, o cambia azienda, solo su un'utility che l'azienda gestisce;
* il listino per categoria di cliente (`fk_categorie_clienti_listini_utility_gestita`);
* listini, commesse, fatture, registri e lotti di fatturazione (`fk_<tabella>_utility_gestita`). Una riga senza
  utility non si giudica.

Gli altri documenti di vendita prendono l'utility dal loro billing account. Per la stessa FK la riga si
**cancella** solo finché nessuno di loro la usa: è la correzione di un'attivazione sbagliata.

---

### `attivo`: sempre acceso

La riga non ha uno stato suo: `attivo` è sempre `true` (`chk_emittenti_fiscali_utilities_attivo`). Resta perché
porta l'automazione ATTIVO verso l'azienda, nei due versi:

* una riga nuova su un'azienda spenta si rifiuta (`E_ATTIVO_PADRE_NON_ATTIVO`, al COMMIT);
* un'azienda con righe non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`). Un'azienda che gestisce un'utility si
  spegne dopo aver cancellato le sue righe; riaccesa, le utility si riattivano a mano.

---

### Che cosa dicono le colonne

* **I decimali** (`arrotondamento_importi_dec`): da 0 a 2. Vuoti: quelli di sistema dell'utility.
* **Il metodo** (`metodo_arrotondamento_importi`): `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`, gli stessi valori di
  `rounding_policy`. Vuoto: la policy dell'azienda, poi quello di sistema.
* **Le soglie della fattura minima** (`minimo_soglia_min`, `minimo_soglia_max`): tutte e due o nessuna
  (`chk_emittenti_fiscali_utilities_soglie_coppia`), e quando ci sono la minima non supera la massima. Senza
  soglie l'azienda non ha fattura minima per quell'utility: le soglie non hanno un valore di sistema.
* **Azienda e utility** non si spostano (lucchetto di colonna): una riga sbagliata si cancella.

---

### L'utility deve poter essere servita da un emittente

Alla scrittura dell'utility o dell'azienda, `script.trgfn_guard_utility_tipo_ruolo_by_cols` controlla che il
ruolo di emittente fiscale sia ammesso per l'utility nella matrice `config.utilities_tipi_ruolo`
(`E_UTILITY_RUOLO_NON_AMMESSO`). Un'utility senza righe nella matrice non è ammessa per nessuno. Finché un'azienda
gestisce l'utility, la sua riga `EF` della matrice non esce (`E_UTILITY_EF_GESTITA`).

---

### Codici errore

* `E_UTILITY_RUOLO_NON_AMMESSO` — il ruolo di emittente fiscale non è ammesso per l'utility.
* `E_ATTIVO_PADRE_NON_ATTIVO` — una riga nuova su un'azienda spenta.
* `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` — un'azienda con righe non si spegne.
* `E_CODICE_NON_MODIFICABILE` — azienda o utility della riga cambiate.
* `23503` su `fk_…_utility_gestita` — un billing account o un documento su un'utility che l'azienda non gestisce, o la cancellazione di una riga ancora usata.

---

### Test

* `db/pgtap/vendite/test-parametri-importo-utility-v1.sql` — i tre livelli dei parametri, la riga senza
  parametri, la riga che non si spegne e non si sposta.
* `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql` — i parametri effettivi nel lookup di un billing
  account.
* `db/pgtap/config/test-utilities-tipi-ruolo-guard-uscita-ef-v1.sql` — l'utility gestita non esce dalla matrice.
* `db/pgtap/anagrafiche/test-utility-gestita-fk-v1.sql` — billing account, listino e cambio d'azienda su un'utility gestita, e la cancellazione della riga.
* `db/pgtap/dbops/test-automazione-guard-utility-tipo-ruolo.sql` — il guard della matrice utility-ruolo.

---

{% include-markdown "signature-core.md" %}
