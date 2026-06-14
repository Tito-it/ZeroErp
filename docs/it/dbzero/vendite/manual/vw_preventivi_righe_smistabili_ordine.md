## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_righe_smistabili_ordine`

> 👀 **Vedi anche**
>
[vw_preventivi_righe_smistabili_commessa](vw_preventivi_righe_smistabili_commessa.md) (gemella, ramo servizi)
> [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine)
> [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)

---
### 🎯 Scopo Principale
Vista **predicato unico** del ramo ordine: le righe preventivo **eleggibili**
allo smistamento merce→ordine. Capability (`fn_preventivo_ha_residuo_ordine`),
push (`fn_push_preventivo_a_ordine`) e Pannello Smistamento leggono da qui la
stessa verita' (brief-preventivi-ordini.md D8).

---

### Predicato di riga

Una riga e' eleggibile se:

* attiva (`COALESCE(attivo, true) IS TRUE`);
* natura di riga con `destinazione_tipo = 'ORDINE'` (merce — il JOIN interno
  su `nature_vendita` esclude per costruzione le righe a natura NULL, che il
  modello tratta come COMMESSA/pregresso);
* non gia' allocata a un ordine (`NOT EXISTS` su
  `ordini_righe.preventivo_riga_id`) — idempotenza di riga, garantita anche
  dal vincolo UNIQUE.

---

### Note operative

* `security_invoker = on` (policy RLS).
* I servizi (`COMMESSA`) sono esclusi: il loro predicato e'
  `vw_preventivi_righe_smistabili_commessa`.
