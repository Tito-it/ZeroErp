## 📘 Documentazione Concettuale – Funzione `vendite.fn_articolo_quota_fissa_a_canone(p_articolo_id)`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_versione_listino_attivabile](/dbzero/script/manual/fn_check_versione_listino_attivabile) ·
> [vendite.listini_righe](/dbzero/vendite/manual/listini_righe) ·
> [vendite.fn_articolo_erogazioni](/dbzero/vendite/funzioni/fn_articolo_erogazioni)

### 🎯 Scopo
(31-10-2026 — brief `brief-db-contratto-righe-periodiche-in-commessa` §7.10)

**L'articolo è una quota fissa a canone?** Sì quando ha una tipologia di listino di quota fissa
(`config.listini_tipologie.e_quota_fissa`) e la sua erogazione di default è `CANONE`
([`fn_articolo_erogazioni`](/dbzero/vendite/funzioni/fn_articolo_erogazioni)). Una quota così si
addebita da sé, ogni periodo, a ogni contratto del listino che non la ritocca: per questo, sul
listino, deve avere la periodicità.

### Chi la legge

È la sede unica (regola del 2) della condizione:

* il motivo 3 di [`script.fn_check_versione_listino_attivabile`](/dbzero/script/manual/fn_check_versione_listino_attivabile):
  la versione non si attiva con una quota fissa a canone senza periodicità;
* il guard [`vendite.trgfn_listini_righe_guard_periodicita_quota_fissa`](/dbzero/vendite/funzioni/trgfn_listini_righe_guard_periodicita_quota_fissa):
  fuori dalla bozza la sua periodicità non si toglie.

⚠️ La dice il **catalogo**, che può cambiare dopo l'attivazione del listino. Il lister dei canoni
lo vede e lo segnala (`SENZA_PERIODICITA`, `QUOTA_FISSA_SENZA_CANONE`, in
[`fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati)).

`STABLE`, `SECURITY INVOKER`.

---

{% include-markdown "signature-core.md" %}
