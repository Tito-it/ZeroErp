## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_pavimento_lotto`

> 👀 **Vedi anche**
>
> [vendite.fn_get_data_minima_numerabile_lotto](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto)
> [vendite.fn_get_pavimento_data_documento](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento)
> [vendite.fn_imposta_data_documento_lotto](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)

---

### 🎯 Scopo Principale

**Da quale data in poi TUTTE le fatture non ancora numerate di un lotto possono
prendere un numero — e quale pavimento ha deciso.**

```sql
SELECT * FROM vendite.fn_get_pavimento_lotto(7307);
--  pavimento  | origine
-- ------------+-----------
--  2026-08-23 | SEQUENZA
```

Un lotto può contenere documenti di **registri diversi** — la natura instrada la
nota di credito su un registro suo — quindi una risposta sola deve valere per
tutti: si prende il **massimo**, cioè il più restrittivo.

ℹ️ Solo le fatture **senza numero**: quelle già numerate non hanno più niente da
chiedere.

---

### ⭐ Perché è nata accanto a `fn_get_data_minima_numerabile_lotto`

La **porta di dichiarazione**
([`fn_imposta_data_documento_lotto`](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto))
non ha bisogno solo della data: le serve anche sapere **quale** pavimento ha
morso, per scegliere fra i due codici errore.

Ma la firma di
[`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto)
è un **contratto**: il backend la chiama in tre punti aspettandosi uno scalare, e
per il frontend è la `minDate` del dialog di numerazione.

⇒ la funzione **vera** torna la coppia, e quella con il nome in servizio resta
come **lettura sottile**. Cambiare la firma di quest'ultima avrebbe fatto pagare
a tutti il bisogno di uno.

---

### ⛔ Non è più un `max(ultima_data)`

Il pavimento si compone **per fattura** — registro e serie sono del *documento*,
la competenza è sua (o, se manca, del lotto) — e i registri hanno **limiti di
emissione diversi**. Un `max` sul solo contatore ignorerebbe del tutto il limite
di emissione.

⭐ **E resta set-based**: la composizione gira una volta per **sezionale
distinto**, non una volta per fattura. Un lotto massivo ha molte fatture e pochi
sezionali.

⚠️ La competenza si legge dalla **fattura**, con ripiego su quella del lotto: dal
2026-08-26 è una proprietà del documento, e le fatture nate prima possono averla
a `NULL`.

⚠️ **A parità di data vince `SEQUENZA`**, come nella sede composta — qui la
regola si applica *fra sezionali diversi*.

---

### ⚠️ Fail-open sotto RLS, e va saputo

`vendite.fatture` ha le policy e questa funzione è `SECURITY INVOKER`: una
fattura del lotto **non visibile** a chi opera non entra nell'aggregazione, e il
pavimento esce **più basso del vero**.

È accettabile **solo perché questa è una targa e non un lucchetto**: il cancello
vero, in
[`fn_get_next_progressivo`](/dbzero/vendite/funzioni/fn_get_next_progressivo),
legge il contatore, che la RLS non ha.

⛔ **Chi volesse usare questa funzione al posto del cancello sappia che sta
sostituendo un presidio con un suggerimento.**

---

### Note operative

* ℹ️ **Torna sempre UNA riga, mai zero**: se nessun sezionale produce un
  pavimento la risposta è `(NULL, NULL)`, cioè «nessun vincolo». Chi chiama non
  deve distinguere «nessun vincolo» da «nessuna risposta».
* ⚠️ Il lotto **inesistente** e il lotto **non visibile** danno la stessa
  risposta (`E_LOTTO_NON_TROVATO`), e il guard c'è per distinguerli da «lotto
  senza pavimento», che tornerebbe `NULL` come loro.
* Guard di parametro: `p_lotto_id` obbligatorio e maggiore di zero
  (`E_VENDITE_CHIAMATA_NON_VALIDA`).
* `STABLE`, `SECURITY INVOKER`.
* Brief: `brief-db-limite-emissione-e-data-verificata` §11 DB-8.

---

{% include-markdown "signature-core.md" %}
