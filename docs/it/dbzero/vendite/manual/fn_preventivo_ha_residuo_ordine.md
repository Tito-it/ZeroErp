## 📘 Documentazione Funzione – `vendite.fn_preventivo_ha_residuo_ordine`

> 👀 **Vedi anche**
>
[fn_preventivo_ha_residuo_commessa](fn_preventivo_ha_residuo_commessa.md) (gemella, ramo servizi)
> [vw_preventivi_righe_smistabili_ordine](vw_preventivi_righe_smistabili_ordine.md) (predicato unico)
> [fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)

---
### 🎯 Scopo Principale
`TRUE` se il preventivo ha righe natura **ORDINE** (merce) non ancora allocate
a un ordine: il push ordine avrebbe effetto. E' la meta' "merce" della coppia
simmetrica di capability del modello split-per-natura
(brief-preventivi-ordini.md D6/D8).

---

### Logica di funzionamento

`EXISTS` sulla vista predicato unico `vw_preventivi_righe_smistabili_ordine`
(righe attive, natura `destinazione_tipo = 'ORDINE'`, non gia' allocate via
`ordini_righe.preventivo_riga_id`). Nessun requisito di testata: l'ordine non
richiede billing account (diversamente dalla gemella commessa).

---

### Consumatori

* `script.fn_available_actions_preventivo` — capability `can_genera_ordine`
  (`ACCETTATO AND fn_preventivo_ha_residuo_ordine`).
* Gate **EVASO** lato BE (`preventivi_service.py`): il push commessa evade il
  preventivo solo se non resta residuo merce.

---

### Note operative

* Non considera COMMESSA (gestita dalla gemella) ne' CONTRATTO (non ammesso
  sul preventivo, MODALITA' A).
* Test: `db/pgtap/script/test-fn-available-actions-preventivo-genera-ordine-v1.sql`.
