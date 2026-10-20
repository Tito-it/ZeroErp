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

### Che cosa stampare: `p_tipo_documento_output_id`

(rev 2026-10-20 — `brief-db-modelli-documento-standard` §9)

Il secondo parametro, facoltativo, è il **tipo di documento** da produrre, e finisce sulla riga
della coda. Senza (`NULL`) la scelta resta al database alla stampa, se fra i modelli che possono
stampare ce n'è uno solo: è il comportamento di prima.

Il tipo arriva da chi accoda e non dal lotto. Il lotto dice **quali** fatture (emittente, tipo di
documento fiscale, competenza), non **che cosa** stampare. Se una fattura deve produrre due
documenti, sono due chiamate, ognuna idempotente sul suo tipo.

La funzione non controlla che il tipo possa stampare per le fatture: che esista lo garantisce la
FK, se può stampare lo decide la scelta del modello al momento della stampa
(`E_DOCUMENTI_TEMPLATE_NON_RISOLTO` sulla riga).

⭐ **Il punto è ciò che questa funzione NON fa**: non numera e non stampa. Numerazione
(come backstop idempotente) e render vivono nel **worker drainer**, fuori dalla transazione.

La ragione è il lock del registro fiscale: rendere i PDF dentro la transazione che numera
significa tenere quel lock per tutta la durata del rendering, bloccando ogni altra
numerazione. Accodare chiude subito la transazione; il worker drena con i suoi tempi.

Chiamata dal task di pipeline `stampa_documenti_lotto`, allo step DEFINITIVA.

---

### Idempotenza: la garantisce il vincolo, non il codice

```sql
ON CONFLICT DO NOTHING
```

Il vincolo di esclusione **parziale** `ex_fatture_stampa_coda_vivo` copre solo i work-item *vivi*,
uno per fattura e tipo, e una riga col tipo `NULL` esclude le altre della stessa fattura. Un
vincolo di esclusione ammette solo `ON CONFLICT DO NOTHING` senza bersaglio; l'unico altro vincolo
che l'inserimento può incontrare è la chiave primaria, che è generata. Il vincolo copre solo i vivi:
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
| `E_PARAMETRO_INVALIDO` | `p_lotto_id` nullo o `<= 0`, `p_tipo_documento_output_id` `<= 0` |
| `E_VALORE_MANCANTE` | `config.sorgenti` senza la riga `FATTURA` |

---

{% include-markdown "signature-core.md" %}
