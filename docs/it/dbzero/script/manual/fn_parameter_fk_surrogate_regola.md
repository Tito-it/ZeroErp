## 📘 Documentazione Concettuale – Funzione `script.fn_parameter_fk_surrogate_regola`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.parameter_fk_surrogate](/dbzero/config/tabelle/parameter_fk_surrogate) — il registro delle regole fra cui la funzione sceglie
>
> Approfondimento viste:
>
> * [dbops.vw_parameter_fk_surrogate_dangling](/dbzero/dbops/views/vw_parameter_fk_surrogate_dangling) — il presidio dei valori appesi, che nomina la regola scelta qui
>
> Approfondimento funzioni:
>
> * [script.fn_check_parameter_fk_surrogate](/dbzero/script/funzioni/fn_check_parameter_fk_surrogate) — la verifica del valore, che chiede qui quale regola applicare
>
> Guide:
>
> * [Configurazione e gestione dei parametri](/guide/configurazione-e-gestione-parametri) — i parametri e i loro valori

---

### 🎯 Scopo Principale

Dice quale regola di `config.parameter_fk_surrogate` governa un codice di parametro, e ne
restituisce l'id: al massimo una. Vuoto (`NULL`) vuol dire che nessuna regola lo governa, e il
parametro non è soggetto alla verifica.

---

### Come sceglie

Fra le regole **abilitate** che prendono il codice:

1. una corrispondenza esatta (`EXACT`) vince su un pattern (`LIKE`);
2. fra due dello stesso tipo, vince il pattern più lungo, cioè il più specifico.

⚠️ Due pattern `LIKE` della stessa lunghezza che prendono lo stesso codice sono un'ambiguità del
registro: la scelta fra loro non è definita, e il rimedio è correggere il registro.

---

### ⭐ Una scelta, una sede

È il solo posto in cui la scelta è scritta. La leggono:

* la verifica `script.fn_check_parameter_fk_surrogate`, che i guard sui parametri chiamano quando
  si scrive un valore;
* il presidio `dbops.vw_parameter_fk_surrogate_dangling`, che cerca i valori rimasti appesi.

Così il presidio e la verifica nominano sempre la stessa regola: un codice preso da più pattern
compare nel presidio una volta sola, col bersaglio che la verifica usa davvero.

Restituisce l'id e non le colonne della regola: chi la chiama unisce il registro e ne legge le
colonne coi loro tipi.

---

### Test

* `db/pgtap/dbops/test-vw-parameter-fk-surrogate-dangling-v1.sql` — un codice preso da una regola
  esatta e da un `LIKE` compare nel presidio una volta sola, col bersaglio della regola esatta.

---

{% include-markdown "signature-core.md" %}
