## 📘 Documentazione Concettuale – Funzione `vendite.fn_accoda_stampe_lotto()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda)
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Accoda in `vendite.fatture_stampa_coda` un work-item `PENDING` **per ogni fattura del lotto**,
e restituisce quante ne ha accodate davvero.

⭐ **Il punto è ciò che questa funzione NON fa**: non numera e non stampa. Numerazione
(come backstop idempotente) e render vivono nel **worker drainer**, fuori dalla transazione.

La ragione è il lock del registro fiscale: rendere i PDF dentro la transazione che numera
significa tenere quel lock per tutta la durata del rendering, bloccando ogni altra
numerazione. Accodare chiude subito la transazione; il worker drena con i suoi tempi.

Chiamata dal task di pipeline `stampa_documenti_lotto`, allo step DEFINITIVA.

---

### Idempotenza: la garantisce l'indice, non il codice

```sql
ON CONFLICT (sorgente_tipo_id, sorgente_id)
   WHERE stato IN ('PENDING', 'IN_CORSO')
   DO NOTHING
```

L'indice unico **parziale** `uq_fatture_stampa_coda_vivo` copre solo i work-item *vivi*:
riaccodare un lotto già accodato non duplica nulla, ma una fattura la cui stampa è già
conclusa (o fallita) **può essere riaccodata**. È esattamente il comportamento voluto — la
ristampa deve restare possibile.

⭐ `GET DIAGNOSTICS ROW_COUNT` dopo un `DO NOTHING` conta le righe **effettivamente
inserite**, non quelle esaminate: il valore di ritorno è quindi «quante nuove», e un secondo
giro sullo stesso lotto restituisce legittimamente **0**. Uno zero qui non è un errore.

---

### Nessun id cablato

Il tipo sorgente `FATTURA` è risolto da `config.sorgenti` per `codice_interno`, e
`sorgente_uid` è `f.id::text` perché per FATTURA il `key_selector` della sorgente polimorfa
dice `id`.

Se quella riga di configurazione manca, la funzione **solleva** `E_VALORE_MANCANTE` invece di
accodare con un tipo nullo: fail-closed.

---

### ⚠️ Una nota storica che spiega il codice

Fino al 2026-08-04 la `SELECT` filtrava su `lf.esclusa`. Quel flag era **dormiente**: nessuno
lo valorizzava, quindi «ogni fattura non esclusa» ha sempre voluto dire «ogni fattura». Il
predicato è stato tolto perché prometteva una selettività che non esisteva.

⭐ La stessa bonifica ha toccato `fn_guard_lotto_fatture_stato_coerente`, che portava lo stesso
filtro morto — e lì il flag occupava anche spazio nel messaggio diagnostico, dicendo sempre
`false`.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | `p_lotto_id` nullo o `<= 0` |
| `E_VALORE_MANCANTE` | `config.sorgenti` senza la riga `FATTURA` |

---

{% include-markdown "signature-core.md" %}
