## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_pavimento_data_documento`

> 👀 **Vedi anche**
>
> [vendite.fn_get_pavimento_sequenza](/dbzero/vendite/funzioni/fn_get_pavimento_sequenza)
> [vendite.fn_get_pavimento_emissione](/dbzero/vendite/funzioni/fn_get_pavimento_emissione)
> [vendite.fn_get_pavimento_lotto](/dbzero/vendite/funzioni/fn_get_pavimento_lotto)
> [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)
> [vendite.fn_calcola_data_documento](/dbzero/vendite/funzioni/fn_calcola_data_documento)

---

### 🎯 Scopo Principale

**Il pavimento EFFETTIVO della data di un documento — e quale dei due pavimenti
ha deciso.**

```sql
SELECT * FROM vendite.fn_get_pavimento_data_documento(3, NULL, date '2026-07-01');
--  pavimento  | origine
-- ------------+------------
--  2026-08-14 | EMISSIONE
```

| colonna | significato |
|---|---|
| `pavimento` | la **prima data ammessa**: il maggiore fra il pavimento della sequenza e quello del limite di emissione. `NULL` = nessun vincolo |
| `origine` | `SEQUENZA` o `EMISSIONE` — **serve a scegliere la frase**, non a scegliere la data |

---

### ⛔ Perché una sede sola, e non tre `GREATEST`

Il pavimento effettivo serve in **tre posti**:

* la **nascita** del documento — [`fn_calcola_data_documento`](/dbzero/vendite/funzioni/fn_calcola_data_documento);
* la **targa** del dialog — [`fn_get_pavimento_lotto`](/dbzero/vendite/funzioni/fn_get_pavimento_lotto);
* il **cancello** — [`fn_get_next_progressivo`](/dbzero/vendite/funzioni/fn_get_next_progressivo).

Tre `GREATEST` scritti a mano in tre punti sarebbero **tre implementazioni della
stessa regola**, e il giorno in cui una cambia le altre due mentono senza che
nulla lo dica. ⭐ Si condivide la **funzione**, non una copia della sua logica.

---

### ⭐ `pavimento` è SEMPRE quello effettivo, mai quello di `origine`

È il valore che finisce **nella frase dell'errore** e nella `minDate` del
dialog. Nominare il pavimento di *sequenza* mentre a mordere è il *limite*
direbbe all'operatore di scegliere una data **che verrebbe rifiutata di nuovo**:
un messaggio che manda a sbattere due volte è peggio di un messaggio generico.

---

### ⭐ `origine` esiste per scegliere il codice errore

I due rifiuti si rimediano in modi diversi:

| origine | la frase dice | come si rimedia |
|---|---|---|
| `SEQUENZA` | «la data è anteriore all'ultimo numero già emesso» | risalendo alla fattura che porta quel numero — e c'è un **bersaglio** che la apre |
| `EMISSIONE` | «la data è troppo vecchia perché sia ancora emettibile» | solo avvicinando la data a oggi — **nessun bersaglio**, non c'è niente da aprire |

Dire il primo quando vale il secondo manda a cercare la cosa sbagliata.

⚠️ **Il pareggio va a `SEQUENZA`.** Quando i due pavimenti coincidono la data
minima è la stessa ma le frasi no: quella della sequenza può portare un
**pulsante** che apre la fattura già numerata, quella del limite può solo dire
una data. A parità, si mostra quella che porta l'operatore da qualche parte.

---

### Note operative

* ℹ️ **`GREATEST` ignora i `NULL`, e qui serve**: la sequenza risponde `NULL`
  finché da quel sezionale non è uscito niente. Nessun `COALESCE` difensivo.
* ℹ️ Se fossero `NULL` entrambi la risposta è `(NULL, NULL)` — «nessun
  vincolo» — e chi legge deve trattarla come tale. Oggi non capita: il limite di
  emissione c'è sempre.
* ℹ️ **I guard di parametro stanno nelle due primitive**, che li hanno già
  entrambi: ripeterli qui sarebbe una seconda copia della stessa validazione,
  con il difetto in più di poter divergere. ⚠️ Conseguenza da sapere: l'errore
  **nomina la primitiva**, non questa funzione.
* ℹ️ `origine` è `text` e non un `%TYPE`: non riflette nessuna colonna, è un
  discriminante che vive solo fra questa funzione e chi la chiama.
* `STABLE`, `SECURITY INVOKER`.
* Brief: `brief-db-limite-emissione-e-data-verificata` §11 DB-4.

---

{% include-markdown "signature-core.md" %}
