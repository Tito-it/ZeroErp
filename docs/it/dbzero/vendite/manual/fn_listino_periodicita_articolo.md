## 📘 Documentazione Concettuale – Funzione `vendite.fn_listino_periodicita_articolo(p_listino_versione_id, p_articolo_id)`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.listini_kit](/dbzero/vendite/manual/listini_kit) ·
> [vendite.listini_righe](/dbzero/vendite/manual/listini_righe) ·
> [vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati)

### 🎯 Scopo
(31-10-2026 — brief `brief-db-contratto-righe-periodiche-in-commessa` §7.7, L12, D-2-bis)

**La periodicità con cui un articolo si addebita su una versione di listino.** Per un kit quella
di [`vendite.listini_kit`](/dbzero/vendite/manual/listini_kit); per gli altri quella della riga di
listino attiva. Fra due righe sullo stesso articolo, la prima che ha la periodicità. `NULL` =
nessuna periodicità su quel listino.

### Perché una funzione

È la **sede unica** (regola del 2). Prima della tabella dei kit la periodicità si leggeva dalla
riga di listino in due posti, il default della riga a canone e il lister dei canoni; con i kit
le copie sarebbero diventate due regole. Ritirate nello stesso giro.

| Chi la legge | Per che cosa |
| --- | --- |
| [`script.trgfn_righe_default_periodicita_da_listino`](/dbzero/script/funzioni/trgfn_righe_default_periodicita_da_listino) | la periodicità proposta a una riga a canone senza indicazione (l'adesione) |
| [`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati) | il ritmo di una quota fissa del listino, riga o kit |
| [`vendite.fn_documento_righe_preview`](/dbzero/vendite/manual/fn_documento_righe_preview) | la proposta di «Aderisci» sulla riga del listino |
| [`script.fn_check_versione_listino_attivabile`](/dbzero/script/manual/fn_check_versione_listino_attivabile) | il motivo 3: una quota fissa a canone senza periodicità |

### Regole

* `STABLE`, `SECURITY INVOKER`: legge sotto la sicurezza per riga di chi chiede.
* Non dice se l'articolo deve avere la periodicità: lo dice
  [`vendite.fn_articolo_quota_fissa_a_canone`](/dbzero/vendite/manual/fn_articolo_quota_fissa_a_canone).

---

{% include-markdown "signature-core.md" %}
