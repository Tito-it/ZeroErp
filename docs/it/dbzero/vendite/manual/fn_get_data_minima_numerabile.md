## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_data_minima_numerabile`

> 👀 **Vedi anche**
>
> [vendite.fn_get_data_minima_numerabile_lotto](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto)
> [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)
> [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)

---

### 🎯 Scopo Principale

**Da quale data in poi questo sezionale accetta un numero.**

Un registro numera in ordine di data: non si può emettere il documento n. 15 con
una data anteriore al n. 14. Questa funzione dice **dov'è il pavimento**.

```sql
SELECT vendite.fn_get_data_minima_numerabile(3);           -- serie del registro
SELECT vendite.fn_get_data_minima_numerabile(3, 'R2');     -- serie esplicita
```

`NULL` = **nessun pavimento**: da quella sequenza non è ancora uscito niente, e
qualunque data va bene.

---

### ⭐ È una TARGA, non un secondo cancello

Il controllo vero vive in `vendite.fn_get_next_progressivo`, che **rifiuta** un
numero con data anteriore. Questa funzione serve al **frontend**, per aprire il
DatePicker con la `minDate` già giusta: così il rifiuto diventa l'eccezione
invece della norma.

⛔ **Se targa e cancello divergessero, comanda il cancello.** Chi usasse questa
funzione *al posto* del controllo starebbe sostituendo un presidio con un
suggerimento.

---

### ⛔ La serie si risolve diversamente da chi numera, ed è voluto

| funzione | `p_serie` a `NULL` significa… |
|---|---|
| **questa** (API di lettura) | «quella del registro» → `COALESCE(p_serie, r.serie_default, '')` |
| `fn_get_next_progressivo` (interna) | niente: la serie arriva **già risolta** dal chiamante |

La ragione è che questa è un'**API di lettura**: chiedere *«qual è il minimo del
registro 3»* senza sapere che la sua serie è `R2` deve dare la risposta giusta.

⚠️ **E la differenza è stata misurata, non supposta.** Il 2026-08-25 *tutte* le
fatture non ancora numerate avevano `serie` a `NULL` e la prendevano dal
`serie_default`. Un `COALESCE(serie, '')` avrebbe cercato il contatore della
serie *vuota*, non l'avrebbe trovato, e avrebbe risposto `NULL` — cioè **la
risposta più permissiva possibile proprio dove il cancello rifiuta**.

---

### Note operative

* ℹ️ **Si legge il contatore, non `vendite.fatture`.**
  `registri_fatturazione_progressivi` non ha RLS, quindi la risposta è completa
  per chiunque; leggere le fatture darebbe un pavimento più basso del vero a chi
  non le vede tutte.
* ℹ️ Il massimo si prende **attraverso gli anni**, esattamente come fa il
  cancello.
* Guard di parametro: `p_registro_id` obbligatorio e maggiore di zero
  (`E_VENDITE_CHIAMATA_NON_VALIDA`); registro inesistente → `E_CONFIG_MANCANTE`.
* `STABLE`.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-10.

---

{% include-markdown "signature-core.md" %}
