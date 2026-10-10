## 📘 Documentazione Funzione – `vendite.fn_preventivo_ha_residuo_commessa`

> 👀 **Vedi anche**
>
[fn_preventivo_ha_residuo_ordine](fn_preventivo_ha_residuo_ordine.md) (gemella, ramo merce)
> [vw_preventivi_righe_smistabili_commessa](vw_preventivi_righe_smistabili_commessa.md) (predicato unico)
> [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo)

---
### 🎯 Scopo Principale
`TRUE` se il **push commessa avrebbe effetto** sul preventivo: esistono righe
eleggibili (vista predicato unico). E' la meta' "servizi" della coppia
simmetrica di capability del modello split-per-natura.

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
   attive, natura COMMESSA o NULL, non ancora instradate in commessa).

**Nessun requisito di testata.** `billing_account_id` e `utility_id` del
preventivo sono `NOT NULL`: una testata «incompleta» non esiste, e capability e
push (`fn_list_preventivi_da_pushare`) leggono lo stesso predicato di riga
senza altro filtro. Fino al 2026-10-10 la funzione li ricontrollava, residuo di
quando il preventivo poteva nascere senza cliente; da allora e' simmetrica alla
gemella ordine (brief `brief-db-istanza-nasce-col-ba-residui`, R-2).

---

### Consumatori

* `script.fn_available_actions_preventivo` — capability `can_push_commessa`
  (`ACCETTATO AND fn_preventivo_ha_residuo_commessa`); se e' `FALSE` la reason
  e' `PREVENTIVO_NESSUNA_RIGA_COMMESSA`.
* Gate **EVASO** lato BE (`preventivi_service.py`): "tutte le righe smistate"
  = nessun residuo su entrambi i rami (questa fn + la gemella ordine).

---

### Note operative

* Non considera la merce (`ORDINE`): quella e' di `fn_preventivo_ha_residuo_ordine`.
* Lo stato documento (ACCETTATO) non e' verificato qui: lo applica il chiamante
  (stessa divisione di responsabilita' della gemella).
* Test: `db/pgtap/vendite/test-fn-preventivo-ha-residuo-commessa-v1.sql`.
