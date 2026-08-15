## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_contabili_fondo_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
>
**Approfondimento funzioni:**
>
• [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura)  
> • [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile)  
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)  
>
### 🎯 Scopo Principale
Sincronizzare i fondi fattura assegnati a una fattura figlia nel layer
**contabile pre-posting** (`pagamenti.vendite_contabili` / `pagamenti.vendite_contabili_righe`),
senza scrivere movimenti pagamenti diretti.

---

### Regole principali

* `p_fattura_figlia_id` obbligatorio.
* Lavora su source `ASSEGNATO` con tipo `F_F_ADD_ACC`.
* Se il saldo effettivo della fattura sorgente risulta `0`, porta la source a
  `ANNULLATO` **scrivendone la ragione** in `motivo` (dal 2026-08-15) — e con un
  `COALESCE`, così una ragione già presente non viene sovrascritta.
* Altrimenti crea/aggiorna una riga in `pagamenti.vendite_contabili_righe`:
  * `meta.origine = 'FONDO_FATTURA'`
  * `meta.fondo_source_id = source_id`
  * `fattura_id` = fattura sorgente
  * `billing_account_id` = source billing account
* Usa `pagamenti.fn_get_or_create_vendite_contabile()` per risolvere la testata.
* Il saldo effettivo **non è più calcolato qui**: si legge da
  [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo)
  — residuo della fattura meno le righe contabili postabili, esclusa la riga del
  source corrente per idempotenza.

> ⭐ **Perché la formula è stata estratta.** La stessa domanda — *«questo fondo è
> ancora dovuto?»* — serve anche al guard di capienza di
> `fn_applica_fondi_fattura`. Due copie della regola darebbero prima o poi due
> risposte diverse alla stessa domanda, e il divario si vedrebbe solo come un
> fondo applicato che non doveva esserlo.

---

### 🔵 L'`ANNULLATO` automatico resta, ed è una scelta

È della stessa specie di quello **rimosso** da `fn_genera_fondi_fattura_source`,
ma con una differenza che conta: qui opera su fondi **già assegnati**, cioè dove
il denaro si è già mosso. Toglierlo prima che `pagamenti` abbia il **processo
rimborsi** lascerebbe scoperto il doppio conteggio — quindi resta, e nel
frattempo almeno **dichiara la propria ragione**.

⚠️ Le righe contabili che crea sono `ABBINATA`, cioè **postabili**: il giorno del
posting diventeranno movimenti veri. È corretto — la sorgente è saldata per
*trasferimento* — ma ogni misura di «incassato» deve **escludere i centri di
riscossione non-cassa**.

---

### Output

Ritorna:

* `inserted_righe`
* `updated_righe`
* `annullati_source`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_sync_contabili_fondo_fattura(
  p_fattura_figlia_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
