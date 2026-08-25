## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_data_minima_numerabile_lotto`

> 👀 **Vedi anche**
>
> [vendite.fn_get_data_minima_numerabile](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile)
> [vendite.fn_imposta_data_documento_lotto](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
> [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)

---

### 🎯 Scopo Principale

**Da quale data in poi TUTTE le fatture non ancora numerate di questo lotto
possono prendere un numero.**

È la sorella «per lotto» di
[`fn_get_data_minima_numerabile`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile),
e serve la stessa schermata: l'operatore dichiara **una** data per l'intero atto,
quindi ha bisogno di **una** soglia.

```sql
SELECT vendite.fn_get_data_minima_numerabile_lotto(4212);
```

---

### ⭐ Perché il massimo, e non il minimo

Un lotto può contenere documenti di **registri diversi**: la natura instrada la
nota di credito su un sezionale suo. Ogni sezionale ha il proprio pavimento, e
una data sola deve andare bene per tutti — quindi si prende il **massimo**, cioè
il **più restrittivo**.

ℹ️ Solo le fatture **senza numero**: quelle già numerate non hanno più niente da
chiedere. `NULL` = nessun pavimento.

---

### ⚠️ È fail-open sotto RLS, e va saputo

`vendite.fatture` ha le policy e questa funzione è `SECURITY INVOKER`. Una
fattura del lotto **non visibile** a chi opera non entra nell'aggregazione, e il
minimo esce quindi **più basso del vero**.

È accettabile per una ragione sola: **questa è una targa, non un lucchetto.** Il
cancello vero, dentro `fn_get_next_progressivo`, legge il **contatore**, che la
RLS non ha — e rifiuta comunque.

⛔ Chi volesse usare questa funzione *al posto* del cancello sappia che sta
sostituendo un presidio con un suggerimento.

---

### ⚠️ Lotto inesistente e lotto invisibile danno la stessa risposta

Il guard iniziale solleva `E_LOTTO_NON_TROVATO` in entrambi i casi, e non prova a
distinguerli — sotto RLS non è distinguibile, ed è giusto che le due risposte
coincidano.

Il guard c'è per un'altra ragione: separare quei due casi da **«lotto senza
pavimento»**, che tornerebbe `NULL` come loro. Senza, `NULL` avrebbe voluto dire
tre cose diverse.

---

### Note operative

* ⭐ **Set-based**: un `JOIN` sul contatore, non una chiamata alla sorella per
  ogni fattura. Un lotto massivo ne ha molte, e la risposta è identica.
* ⭐ La serie si risolve **come la risolve chi numera**:
  `COALESCE(f.serie, r.serie_default, '')`.
* Guard di parametro: `p_lotto_id` obbligatorio e maggiore di zero
  (`E_VENDITE_CHIAMATA_NON_VALIDA`).
* `STABLE`.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-10.

---

{% include-markdown "signature-core.md" %}
