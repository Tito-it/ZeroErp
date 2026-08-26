## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_pavimento_sequenza`

> 👀 **Vedi anche**
>
> [vendite.fn_get_pavimento_emissione](/dbzero/vendite/funzioni/fn_get_pavimento_emissione)
> [vendite.fn_get_pavimento_data_documento](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento)
> [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)
> [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)

---

### 🎯 Scopo Principale

**Da quale data in poi questo sezionale accetta un numero, guardando SOLO la
sequenza già emessa.**

Un registro numera in ordine di data: non si può emettere il documento n. 15 con
una data anteriore al n. 14. Questa funzione dice **dov'è quel pavimento**.

```sql
SELECT vendite.fn_get_pavimento_sequenza(3, NULL);    -- la serie del registro
SELECT vendite.fn_get_pavimento_sequenza(3, 'R2');    -- una serie esplicita
```

`NULL` = **nessun pavimento**: da quella sequenza non è ancora uscito niente, e
qualunque data va bene.

---

### ⛔ Non è «la data minima numerabile» — è UNA delle due primitive

I pavimenti sono **due**, e questa ne guarda uno solo:

| funzione | cosa guarda | domanda a cui risponde |
|---|---|---|
| **questa** | la sequenza già emessa | *«questo numero può venire dopo quelli che ci sono?»* |
| [`fn_get_pavimento_emissione`](/dbzero/vendite/funzioni/fn_get_pavimento_emissione) | il termine di emissione | *«questo documento si può ancora mandare?»* |
| [`fn_get_pavimento_data_documento`](/dbzero/vendite/funzioni/fn_get_pavimento_data_documento) | **entrambi** | *«qual è la prima data ammessa, e perché?»* |

⚠️ **Fino al 2026-08-26 questa funzione si chiamava `fn_get_data_minima_numerabile`.**
È stata rinominata quando il secondo pavimento è nato: «data minima numerabile»
descrive la **composizione**, non questa metà, e lasciare quel nome qui avrebbe
significato tenere un nome che mente accanto alla funzione che quel nome merita.
Il rename non ha rotto niente — la funzione non aveva chiamanti.

⛔ La sorella per lotto,
[`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto),
**non** è stata rinominata: quel nome è un contratto col backend e la `minDate`
del dialog di numerazione.

---

### ⛔ La serie si risolve come la risolve chi numera

`COALESCE(p_serie, r.serie_default, '')` — la stessa espressione che usano
`fn_assign_numero_fattura` e il backfill del contatore. **Se una delle tre
divergesse, cercherebbe una riga di contatore che non esiste e risponderebbe
«nessun vincolo».**

⚠️ **E la cosa è stata misurata, non supposta.** Il 2026-08-25 *tutte* le fatture
non ancora numerate avevano `serie` a `NULL` e la prendevano dal `serie_default`.
Un `COALESCE(serie, '')` avrebbe cercato il contatore della serie *vuota*, non
l'avrebbe trovato, e avrebbe risposto `NULL` — cioè **la risposta più permissiva
possibile proprio dove il cancello rifiuta**.

⛔ **`p_serie` non ha un valore di default**, al contrario della versione
precedente. Da primitiva interna, *dimenticare* la serie significa leggere il
contatore di un'**altra** sequenza: chi chiama deve decidere cosa passare.
ℹ️ `NULL` resta un valore legittimo e significa «la serie di default del
registro» — è la **risoluzione** a essere ammessa, non l'omissione.

---

### Note operative

* ℹ️ **Si legge il contatore, non `vendite.fatture`.**
  `registri_fatturazione_progressivi` non ha RLS, quindi la risposta è completa
  per chiunque; leggere le fatture darebbe un pavimento più basso del vero a chi
  non le vede tutte.
* ℹ️ Il massimo si prende **attraverso gli anni**, esattamente come fa il
  cancello — altrimenti un documento retrodatato al 31/12 dell'anno scorso
  passerebbe indisturbato, aprendo un numero in un anno già chiuso.
* Guard di parametro: `p_registro_id` obbligatorio e maggiore di zero
  (`E_VENDITE_CHIAMATA_NON_VALIDA`); registro inesistente → `E_CONFIG_MANCANTE`.
* `STABLE`, `SECURITY INVOKER`.
* Brief: `brief-db-limite-emissione-e-data-verificata` §11 DB-8.

---

{% include-markdown "signature-core.md" %}
