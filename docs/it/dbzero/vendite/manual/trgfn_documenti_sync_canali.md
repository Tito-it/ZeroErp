## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_documenti_sync_canali()`

> 👀 **Vedi anche**
>
> • [vendite.documenti_fatturazione_canali](/dbzero/vendite/tabelle/documenti_fatturazione_canali)  
> • [vendite.fn_set_documento_canale_stato](/dbzero/vendite/funzioni/fn_set_documento_canale_stato)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  

---

### 🎯 Scopo Principale

(latest review 24-02-2026)  
La funzione trigger `vendite.trgfn_documenti_sync_canali()` mantiene
allineato il registro `documenti_fatturazione_canali` sugli eventi
principali dei documenti commerciali.

---

### ✅ Regole applicate

* su `vendite.ordini`:
  * apre canale `ORDINE_VENDITA` per l'ordine creato/aggiornato;
  * se l'ordine nasce da `PREVENTIVO`, marca il canale `PREVENTIVO` come `CONSUMATO`
    con target sull'ordine.
* su `vendite.ddt`:
  * apre canale `DDT_VENDITA`;
  * se il DDT nasce da `ORDINE_VENDITA`, marca il canale ordine come `CONSUMATO`
    con target sul DDT.
* su `vendite.ddt_ordini` (se presente):
  * applica un safety net ordine->DDT per mantenere consistenza canali.
* su `vendite.contratti`:
  * apre canale `DIRETTO` sulla sorgente contratto.

---

### 🧩 Obiettivo operativo

Rendere uniforme il tracciamento dei passaggi documento (`preventivo->ordine`,
`ordine->ddt`) e includere anche i contratti, evitando divergenze applicative
tra backend e logica DB.

---

{% include-markdown "signature-core.md" %}
