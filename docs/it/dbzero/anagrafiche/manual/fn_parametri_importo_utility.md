## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_parametri_importo_utility()`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities)
> [config.utilities](/dbzero/config/tabelle/utilities)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-7, D-7 di Tid)

Dice i **parametri d'importo effettivi** di un'azienda per una utility: con quanti decimali e con
quale metodo si arrotondano gli importi delle sue fatture, e le soglie della fattura minima. È il
punto unico: chi ha bisogno di questi parametri lo chiede qui.

### Da dove viene ogni parametro

| Parametro | 1° livello | 2° livello | 3° livello |
|---|---|---|---|
| decimali | la riga dell'azienda per l'utility | il valore di sistema dell'utility | — |
| metodo | la riga dell'azienda per l'utility | la policy generale dell'azienda (`rounding_policy`) | il valore di sistema dell'utility |
| soglie del minimo | la riga dell'azienda per l'utility | — (nessun minimo) | — |

`personalizzata` dice se la riga dell'azienda per l'utility c'è.

### Righe

Una riga se l'utility esiste, zero se non esiste o è `NULL`: chi la legge distingue «utility
mancante» da «parametri di sistema».

### Chi la legge

* `vendite.fn_ricalcola_totali_fattura`: una fattura si chiude anche senza la riga dell'azienda;
* `anagrafiche.fn_lookup_utilities_per_ba`: le utility di un BA mostrano i parametri effettivi;
* `vendite.fn_parametri_importo_riga`: per le righe di fattura senza regole dell'articolo.

### Note di migrazione

Prima la riga dell'azienda era l'unica sede: il ricalcolo la pretendeva (senza, la fattura si
fermava con `E_CONFIG_MANCANTE`) e il lookup la mostrava in `LEFT JOIN`, con `NULL` senza riga.
Nessuno la crea: un'azienda nuova non chiudeva una fattura.
