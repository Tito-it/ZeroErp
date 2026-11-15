## 📘 Documentazione Concettuale – Vista `vendite.vw_listini_righe_azioni`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) ·
> [script.fn_check_listino_riga_rettificabile](/dbzero/script/manual/fn_check_listino_riga_rettificabile) ·
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — il guard ·
> [vendite.fn_rettifica_riga_listino](/dbzero/vendite/manual/fn_rettifica_riga_listino) — il verbo della rettifica ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) — le azioni della versione ·
> [config.azioni_riga](/dbzero/config/manual/azioni_riga)

### 🎯 Scopo

**Le azioni delle righe di listino**: una riga per riga (`listino_riga_id`,
`listino_versione_id`), col motivo per cui ciascuna azione è spenta.

| Colonna | Che cosa |
| --- | --- |
| `modifica_blocco_reason` | il primo motivo di `script.fn_check_listino_riga_scrivibile` per la riga: `VERSIONE_CHIUSA` o `VERSIONE_NON_IN_BOZZA`; `NULL` = si modifica e si elimina, cioè la versione è in bozza |
| `modifica_blocco_reason_key` | la sua chiave i18n |
| `rettifica_blocco_reason` | il primo motivo di `script.fn_check_listino_riga_rettificabile`: `VERSIONE_IN_BOZZA`, `VERSIONE_CHIUSA`, `NON_IN_VIGORE`, `RIGA_PROPAGATA`; `NULL` = il prezzo si rettifica |
| `rettifica_blocco_reason_key` | la sua chiave i18n |

È la superficie delle azioni `MODIFICA_RIGA_LISTINO` (il verbo è il guard di stato delle righe) e
`RETTIFICA_RIGA_LISTINO` (il verbo è `vendite.fn_rettifica_riga_listino`) nel registro
`config.azioni_riga`. Su ogni riga al più una delle due è accesa: in bozza si modifica, nel
listino in vigore si rettifica. La riga **nuova** ha la sua colonna in
`vendite.vw_listini_versioni_azioni` (`aggiunta_riga_blocco_*`).

`security_invoker`: le sole righe dei listini del proprio perimetro, e i documenti che le citano
letti col perimetro di chi guarda. Si filtra per `listino_versione_id` (le righe del drawer della
versione) o `listino_riga_id`.

---

{% include-markdown "signature-core.md" %}
