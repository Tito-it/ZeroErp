## 📘 Documentazione Funzione – `vendite.fn_preventivo_ha_residuo_commessa`

> 👀 **Vedi anche**
>
[fn_preventivo_ha_residuo_ordine](fn_preventivo_ha_residuo_ordine.md) (gemella, ramo merce)
> [vw_preventivi_righe_smistabili_commessa](vw_preventivi_righe_smistabili_commessa.md) (predicato unico)
> [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo)

---
### 🎯 Scopo Principale
`TRUE` se il **push commessa avrebbe effetto** sul preventivo: esistono righe
eleggibili (vista predicato unico) **e** la testata e' completa. E' la meta'
"servizi" della coppia simmetrica di capability del modello split-per-natura.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION vendite.fn_preventivo_ha_residuo_commessa(
  p_preventivo_id vendite.preventivi.id%TYPE
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
```

---

### Logica di funzionamento

1. Guard standard su `p_preventivo_id` (NULL o <= 0 → `E_PARAMETRO_INVALIDO`).
2. `EXISTS` sulla vista `vw_preventivi_righe_smistabili_commessa` (righe
   attive, natura COMMESSA o NULL, non gia' EMESSE) **AND** requisiti di
   testata: `billing_account_id IS NOT NULL AND utility_id IS NOT NULL`.

**Perche' la testata** (asimmetria voluta rispetto alla gemella ordine): il
predicato del push commessa (`fn_list_preventivi_da_pushare`) richiede BA e
utility; senza questo check la capability direbbe TRUE su preventivi che il
push non listerebbe mai — capability e push divergenti.

---

### Consumatori

* `script.fn_available_actions_preventivo` — capability `can_push_commessa`
  (`ACCETTATO AND fn_preventivo_ha_residuo_commessa`); il caso "righe ok ma
  testata incompleta" produce la reason `PREVENTIVO_SENZA_BILLING_ACCOUNT`.
* Gate **EVASO** lato BE (`preventivi_service.py`): "tutte le righe smistate"
  = nessun residuo su entrambi i rami (questa fn + la gemella ordine).

---

### Note operative

* Non considera la merce (`ORDINE`): quella e' di `fn_preventivo_ha_residuo_ordine`.
* Lo stato documento (ACCETTATO) non e' verificato qui: lo applica il chiamante
  (stessa divisione di responsabilita' della gemella).
* Test: `db/pgtap/vendite/test-fn-preventivo-ha-residuo-commessa-v1.sql`.
