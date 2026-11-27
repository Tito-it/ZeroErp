## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_parametri_importo_utility`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — la riga dell'azienda per l'utility, il primo livello
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la policy generale di arrotondamento dell'azienda
> * [config.utilities](/dbzero/config/tabelle/utilities) — i parametri di sistema dell'utility
>
> Approfondimento funzioni:
>
> * [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura) — il ricalcolo dei totali della fattura
> * [vendite.fn_parametri_importo_riga](/dbzero/vendite/funzioni/fn_parametri_importo_riga) — i parametri di una riga di fattura
> * [anagrafiche.fn_lookup_utilities_per_ba](/dbzero/anagrafiche/funzioni/fn_lookup_utilities_per_ba) — le utility di un billing account

---

### 🎯 Scopo Principale

`anagrafiche.fn_parametri_importo_utility` dice i parametri d'importo effettivi di un'azienda per una utility:
con quanti decimali e con quale metodo si arrotondano gli importi delle sue fatture, e le soglie della fattura
minima. È il punto unico: chi ha bisogno di questi parametri li chiede qui.

---

### Da dove viene ogni parametro

| Parametro | 1° livello | 2° livello | 3° livello |
| --- | --- | --- | --- |
| decimali | la riga dell'azienda per l'utility | il valore di sistema dell'utility | — |
| metodo | la riga dell'azienda per l'utility | la policy generale dell'azienda (`rounding_policy`) | il valore di sistema dell'utility |
| soglie della fattura minima | la riga dell'azienda per l'utility | — (nessun minimo) | — |

Conta solo una riga accesa: una riga spenta è come assente. `personalizzata` dice se la riga accesa
dell'azienda per l'utility c'è. L'azienda si passa col suo ruolo (`emittente_soggetto_ruolo_id`), e deve
essere un'azienda: un ruolo che non è un emittente, o nessun ruolo, è rifiutato (`E_PARAMETRO_INVALIDO`). I
valori di sistema sono quelli di un'azienda senza personalizzazioni, non la risposta per chi azienda non è.

---

### Una riga, o nessuna

Una riga se l'utility esiste, zero se non esiste o è `NULL`: chi legge distingue «utility mancante» da
«parametri di sistema», e la traduce in `E_CONFIG_MANCANTE`. Per questo il ruolo sbagliato non dà zero righe:
direbbe che manca l'utility, cioè la causa sbagliata.

---

### Chi la legge

* `vendite.fn_ricalcola_totali_fattura`: una fattura si chiude anche senza la riga dell'azienda;
* `vendite.fn_parametri_importo_riga`: per le righe di fattura senza regole dell'articolo;
* `anagrafiche.fn_lookup_utilities_per_ba`: le utility di un billing account mostrano i parametri effettivi.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il ruolo non è un emittente, o manca.

⚠️ Con il rifiuto la funzione ha due istruzioni, e non si espande più dentro chi la chiama: una chiamata per riga
di fattura in `vendite.fn_parametri_importo_riga`.

---

### Test

* `db/pgtap/vendite/test-parametri-importo-utility-v1.sql` — i valori di sistema senza la riga, le soglie vuote,
  la policy dell'azienda per il metodo, la riga che vince, l'utility inesistente; il ricalcolo della fattura e i
  parametri di riga che li usano; il ruolo che non è un emittente, e nessun ruolo (test 13 e 14).

---

### Note di migrazione

* 2026-10-21 — nasce. Prima la riga dell'azienda era l'unica sede: il ricalcolo la pretendeva (senza, la fattura
  si fermava con `E_CONFIG_MANCANTE`) e il lookup la mostrava con `NULL` quando mancava. Nessuno la crea, quindi
  un'azienda nuova non chiudeva una fattura.
* 2026-11-27 — un ruolo che non è un emittente è rifiutato (`E_PARAMETRO_INVALIDO`): prima riceveva i valori di
  sistema.

---

{% include-markdown "signature-core.md" %}
