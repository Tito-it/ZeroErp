## 📘 Documentazione Concettuale – Funzione `vendite.fn_applica_fondi_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
> • [vendite.tipi_fondi_fattura](/dbzero/vendite/tabelle/tipi_fondi_fattura)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_genera_fondi_fattura_source](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_source)  
>
### 🎯 Scopo Principale
(latest review 15-08-2026)

La funzione **`vendite.fn_applica_fondi_fattura()`** applica i fondi fattura
in stato `DISPONIBILE` ad una **fattura figlia**, creando le righe in
`vendite.fatture_fondi_fattura` e aggiornando la `source` a stato `ASSEGNATO`.

> ⭐ **È l'unica funzione del fondo che MUOVE DENARO**: assegnare una source a una
> fattura figlia ne cambia il totale. È il motivo per cui i due presidi del
> cantiere stanno entrambi qui.

---

### Regole principali

* `billing_account_id`, `utility_id`, `tipo_doc_fiscale_id`, `emittente_soggetto_ruolo_id`, `valuta_id` obbligatori.
* `fattura_figlia_id` obbligatorio.
* `tipo_fondo_fattura_id` opzionale (se valorizzato filtra i fondi).
* Usa solo righe `source` con `stato = 'DISPONIBILE'` e `fattura_figlia_id IS NULL`.
* Aggiorna la `source`:
  * `fattura_figlia_id`, `data_assegnazione`, `user_assegnazione`
  * `stato = 'ASSEGNATO'`
* `FOR UPDATE OF s SKIP LOCKED`: due giri paralleli non si contendono lo stesso
  fondo.

---

### ✅ I due presidi, applicati il 2026-08-15

Piano: [brief-db-fondo-fattura…](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2.

**1. La chiave sorgente ↔ figlia è passata da cinque elementi a nove** (D-4).

I cinque parametri di scope (`billing_account`, `utility`, `tipo_doc_fiscale`,
`emittente`, `valuta`) erano un **sottoinsieme** della chiave con cui si
accorpano le attività in fattura
([`fn_build_fattura_key`](/dbzero/vendite/funzioni/fn_build_fattura_key)):
mancavano **reseller, registro, termine e modalità di pagamento**.

⚠️ Conseguenza concreta: un fondo nato da una fattura a 30 giorni poteva finire
su una figlia a 60 — due documenti che il sistema tiene **deliberatamente
separati**, visto che il termine è nella chiave proprio per non accorparli.
Adesso il confronto è **riga contro riga** su `vendite.fatture`, con la forma
copiata da `fn_get_or_create_fattura_header` per non creare una seconda
definizione della chiave: `=` sui cinque non nullable, `IS NOT DISTINCT FROM` sui
quattro nullable.

ℹ️ I cinque parametri restano ma **cambiano mestiere**: da filtro sulla source a
*sanity check* sulla **figlia**. Applicati alla source erano ridondanti e
potevano far saltare in silenzio un fondo la cui colonna denormalizzata fosse
rimasta indietro.

**2. Si verifica che la sorgente sia ancora capiente** (D-3b).

Prima la funzione assegnava qualunque riga `DISPONIBILE` che combaciasse con lo
scope, **senza guardare se la fattura sorgente fosse stata pagata nel frattempo**.
Adesso rilegge il residuo — al netto del contributo già dato dal fondo stesso —
e verifica con
[fn_check_fondo_fattura_capiente](/dbzero/vendite/funzioni/fn_check_fondo_fattura_capiente)
che regga ancora l'importo. Se non regge, **il fondo non si applica e resta
dov'è**.

⭐ Non è un ricalcolo del fondo — quello è vietato: è una **lettura nell'istante
dell'atto**. Ed è la contropartita dell'`ANNULLATO` automatico rimosso dalla
generazione: non un altro automatismo che scrive, ma un controllo dove il denaro
si muove.

> ⚠️ **La regola di capienza non è scritta qui**, ed è una scelta: la usa anche
> [vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere)
> — negata — per mostrare il motivo `NON_PIU_CAPIENTE`. Due copie avrebbero detto,
> senza errori e senza log, che un fondo è inapplicabile mentre il giro lo applica.
>
> 🔴 E nell'estrarla è saltato fuori un difetto che nessuno cercava: la capienza
> veniva calcolata **due volte sulla stessa riga**, una per il segno e una per il
> valore assoluto. È una funzione `VOLATILE` che interroga `pagamenti`: non solo
> il doppio del lavoro, ma **due valutazioni indipendenti** che in teoria possono
> rispondere numeri diversi — accettando metà condizione e rifiutando l'altra.
> Adesso si legge una volta, in `LATERAL`.

---

### Output

Ritorna il numero di righe applicate.

---

### Esempio d’uso

```sql
SELECT vendite.fn_applica_fondi_fattura(
  p_billing_account_id => 10,
  p_utility_id => 2,
  p_tipo_doc_fiscale_id => 1,
  p_emittente_soggetto_ruolo_id => 5,
  p_valuta_id => 1,
  p_fattura_figlia_id => 123,
  p_tipo_fondo_fattura_id => NULL
);
```

---

{% include-markdown "signature-core.md" %}
