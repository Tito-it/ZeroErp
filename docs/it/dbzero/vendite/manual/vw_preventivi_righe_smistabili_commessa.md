## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_righe_smistabili_commessa`

> 👀 **Vedi anche**
>
[vw_preventivi_righe_smistabili_ordine](vw_preventivi_righe_smistabili_ordine.md) (gemella, ramo merce)
> [vendite.fn_preventivo_ha_residuo_commessa](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_commessa)
> [vendite.fn_list_preventivi_da_pushare](/dbzero/vendite/funzioni/fn_list_preventivi_da_pushare)

---
### 🎯 Scopo Principale
Vista **predicato unico** del ramo commessa: le righe preventivo **eleggibili**
al push verso `commesse_attivita` (servizi una tantum). Capability
(`fn_preventivo_ha_residuo_commessa`), list-fn (`fn_list_preventivi_da_pushare`)
e Pannello Smistamento leggono da qui la stessa verita' — nessuna
ricostruzione ad hoc del filtro (brief-db-smistamento-preventivi.md, A.1).

---

### Predicato di riga

Una riga e' eleggibile se:

* `attivo IS TRUE`, `quantita > 0`, `prezzo_unitario >= 0`;
* natura di riga NULL (pregresso pre-trigger, trattata COMMESSA) **oppure**
  `nature_vendita.destinazione_tipo = 'COMMESSA'`;
* non gia' **EMESSA** in commessa (`NOT EXISTS` su `commesse_attivita` per
  `segment_key 'PREV:<uid>:R:<riga_id>'` con `stato_emissione = 'EMESSA'`) —
  idempotenza di riga.

Le condizioni di **testata** (billing account, utility, stato ACCETTATO,
competenza) restano fuori dalla vista: le applica chi la consuma, come per la
gemella del ramo ordine.

---

### Note operative

* `security_invoker = on` (policy RLS).
* La merce (`destinazione_tipo = 'ORDINE'`) e' esclusa: il suo predicato e'
  `vw_preventivi_righe_smistabili_ordine`.
* Test: coperta indirettamente da
  `test-fn-preventivo-ha-residuo-commessa-v1.sql` e
  `test-fn-list-preventivi-da-pushare-righe-ids-v1.sql`.
