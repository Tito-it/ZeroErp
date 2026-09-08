## 📘 Documentazione Concettuale – Vista `script.vw_lotto_documento_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
**Approfondimento funzioni:**
>
• [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> • [script.fn_gruppi_trascinati_da_uscita](/dbzero/script/funzioni/fn_gruppi_trascinati_da_uscita)
> • [vendite.fn_escludi_documento_da_giro](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Dice **quale bozza di un lotto contiene righe di quale documento**: la terna
*(lotto, fattura, documento)*, senza ripetizioni.

Serve a rispondere a una domanda che una fattura da sola non sa risolvere:
*se tolgo questo documento dal giro, che cosa viene via insieme a lui?*

---

### Perché è una vista e non due query

La stessa relazione si legge nei **due versi**, e da due punti diversi:

| Chi chiede | Che cosa vuole sapere |
| --- | --- |
| [`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro) | *questo documento quali bozze tocca?* — per cancellarle |
| [`script.fn_gruppi_trascinati_da_uscita`](/dbzero/script/funzioni/fn_gruppi_trascinati_da_uscita) | *questa bozza quali documenti contiene?* — per dire chi viene trascinato |

Scritti separatamente sarebbero **due catene da tenere allineate a mano**. E
questa catena è facile da sbagliare — vedi qui sotto.

---

### 🔴 La trappola: da dove si legge il documento

La chiave del documento **non** si calcola su `vendite.attivita_fatturabili`.

Lì la sorgente è la **commessa** (l'attività nasce *dalla* commessa) e
l'identificativo è un valore derivato: calcolando la chiave da quelle colonne si
ottengono chiavi del tipo `COMMESSA:<valore derivato>` che **non corrispondono a
nessun documento** del perimetro di un lotto.

⭐ Il legame giusto è **diretto e già scritto**: `attivita_fatturabili` porta il
riferimento alla riga di commessa da cui è nata, e *quella* riga porta la
sorgente del **documento** (l'ordine, il preventivo, il DDT…). È da lì che si
costruisce la chiave, con
[`vendite.fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key).

> ⚠️ Misurato il 2026-09-08: calcolando la chiave dal posto sbagliato le
> corrispondenze col perimetro di un lotto noto erano **zero su quattro**; dal
> posto giusto, **quattro su quattro**.

---

### Due cose sul perimetro

* **Si guarda solo dentro un lotto.** Le fatture arrivano dal legame
  lotto-fatture: una fattura di un **altro** lotto che contenesse lo stesso
  documento non viene toccata dall'uscita, e nominarla prometterebbe un effetto
  che non c'è.
* **La vista rispetta i permessi di chi legge** (`security_invoker`): le righe di
  commessa hanno il filtro di perimetro emittente, e il collegamento alla
  commessa **è** il perimetro.

---

### Esempio d'uso

```sql
-- Le bozze del lotto 11221 che contengono righe di questo documento
SELECT DISTINCT fattura_id
  FROM script.vw_lotto_documento_righe
 WHERE lotto_id   = 11221
   AND gruppo_key = 'ORDINE_VENDITA:01a06ce4-b46a-7a49-a72f-c07c29de47bb';

-- Quanti documenti diversi copre ciascuna bozza del lotto
SELECT fattura_id, count(*) AS documenti
  FROM script.vw_lotto_documento_righe
 WHERE lotto_id = 11221
 GROUP BY fattura_id;
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md`.

---

{% include-markdown "signature-core.md" %}
