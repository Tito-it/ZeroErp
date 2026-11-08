## 📘 Documentazione Concettuale – Funzione `vendite.fn_accoda_stampe_lotto`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda in cui accoda
> * [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) — le fatture del lotto
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `FATTURA`

---

### 🎯 Scopo Principale

Accoda in `vendite.fatture_stampa_coda` un work-item `PENDING` **per ogni fattura del lotto**,
e restituisce quante ne ha accodate davvero.

---

### Che cosa stampare: `p_tipo_documento_output_id`

Il secondo parametro, facoltativo, è il **tipo di documento** da produrre, e finisce sulla riga
della coda. Senza (`NULL`) la scelta resta al database alla stampa, se fra i modelli che possono
stampare ce n'è uno solo.

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

L'inserimento ignora i conflitti (`ON CONFLICT DO NOTHING`). Il vincolo di esclusione **parziale** `ex_fatture_stampa_coda_vivo` copre solo i work-item *vivi*,
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

Il tipo sorgente `FATTURA` è risolto da `config.sorgenti` per `codice_interno`, e la fattura
sta in `sorgente_id` (`vendite.fatture.id`), perché per FATTURA il `key_selector` dice `id`: è
la sola chiave della riga di coda, con una FK vera verso la fattura.

Se quella riga di configurazione manca, la funzione **solleva** `E_VALORE_MANCANTE` invece di
accodare con un tipo nullo: fail-closed.

---

### Ogni fattura del lotto, senza filtri

La funzione accoda **tutte** le fatture del lotto: non filtra su `lf.esclusa`, un flag che
nessuno valorizza e che prometterebbe una selettività che non esiste.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | `p_lotto_id` nullo o `<= 0`, `p_tipo_documento_output_id` `<= 0` |
| `E_VALORE_MANCANTE` | `config.sorgenti` senza la riga `FATTURA` |

---

### Note di migrazione

* 2026-08-04 — via il predicato su `lf.esclusa`, dormiente; la stessa bonifica tocca
  `fn_guard_lotto_fatture_stato_coerente`.
* 2026-10-20 — arriva `p_tipo_documento_output_id` (brief-db-modelli-documento-standard §9).
* 2026-11-07 — la fattura sta solo in `sorgente_id`: la coda non ha più il doppione testuale
  `sorgente_uid` (`f.id::text`) (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
