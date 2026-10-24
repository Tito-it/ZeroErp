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
* non gia' **mandata** in commessa: `script.fn_get_stato_push_segment('PREV:<uid>:R:<riga_id>')
  = 'LIBERA'` — il classificatore unico del «gia' inviato» (componenti `#CMP:` e
  rettifiche `#RET:` compresi; una riga `ANNULLATA` non occupa) — idempotenza di
  riga. ⭐ rev 2026-10-12 (`20261012-09`, brief-db-annullo-a-valle-riapre-a-monte
  D-5): prima era un `NOT EXISTS` proprio, «qualsiasi `stato_emissione`»; annullata
  la commessa, la riga non tornava mai smistabile.

Le condizioni di **testata** (billing account, utility, stato ACCETTATO,
competenza) restano fuori dalla vista: le applica chi la consuma, come per la
gemella del ramo ordine.

> ⚙️ **Simmetria con il ramo ordine (fix gate EVASO, 2026-06-28).** La condizione
> di esclusione ancora il "residuo" all'**instradamento** (esistenza dell'attivita),
> esattamente come la gemella ordine lo ancora all'**allocazione**
> (`ordini_righe.preventivo_riga_id`). Prima ancorava alla **fatturazione**
> (`stato_emissione = 'EMESSA'`): il preventivo non raggiungeva mai `EVASO` al push,
> perche' il push crea le attivita in `NON_EMESSA`. `EVASO` = "tutte le righe
> instradate alla destinazione documentale", **non** "tutto fatturato".
> Brief: `brief-db-gate-evaso-ramo-commessa-asimmetria.md`.

---

### Note operative

* `security_invoker = on` (policy RLS).
* La merce (`destinazione_tipo = 'ORDINE'`) e' esclusa: il suo predicato e'
  `vw_preventivi_righe_smistabili_ordine`.
* **Attivita `ANNULLATA`**: una riga la cui unica attivita e' annullata risulta
  comunque **instradata** (esclusa) → non blocca `EVASO` e **non e' ri-pushabile**
  (`fn_upsert_commessa_attivita` vieta l'update se lo stato esistente
  `<> NON_EMESSA`). Decisione di dominio: una riga annullata a valle non riapre il
  preventivo. Coerente col ramo ordine ed evita preventivi permanentemente bloccati.
* **Match `segment_key`**: l'esclusione confronta il `segment_key` su **tutte** le
  commesse (non per singola commessa); l'idempotenza dell'upsert e' invece su
  `(commessa_id, segment_key)`. Rilevante solo se la stessa riga-preventivo dovesse
  instradarsi verso commesse diverse (oggi non accade).
* Test: `test-fn-preventivo-ha-residuo-commessa-v1.sql` (casi 8 `EMESSA`,
  10 `NON_EMESSA`, 11 componente BoM `#CMP`, 12 `ANNULLATA`) e
  `test-fn-list-preventivi-da-pushare-righe-ids-v1.sql`.
