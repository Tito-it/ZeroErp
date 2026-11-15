## 📘 Documentazione Concettuale – Vista `vendite.vw_listini_righe_azioni`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — la regola ·
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — il guard ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) — la riga nuova ·
> [config.azioni_riga](/dbzero/config/manual/azioni_riga)

### 🎯 Scopo

**Le azioni delle righe di listino**: una riga per riga (`listino_riga_id`,
`listino_versione_id`), col motivo per cui la riga **non si modifica e non si elimina**.

| Colonna | Che cosa |
| --- | --- |
| `modifica_blocco_reason` | il `reason` del primo motivo di `script.fn_check_listino_riga_scrivibile` per la riga: `VERSIONE_CHIUSA` o `RIGA_PROPAGATA`; `NULL` = si modifica e si elimina |
| `modifica_blocco_reason_key` | la sua chiave i18n |

È la superficie dell'azione `MODIFICA_RIGA_LISTINO` nel registro `config.azioni_riga`; il verbo è
il guard di stato delle righe, che solleva lo stesso motivo su UPDATE e DELETE. La riga **nuova**
della versione ha la sua colonna in `vendite.vw_listini_versioni_azioni`
(`aggiunta_riga_blocco_*`).

`security_invoker`: le sole righe dei listini del proprio perimetro, e i documenti che le citano
letti col perimetro di chi guarda, come il guard. Si filtra per `listino_versione_id` (le righe
del drawer della versione) o `listino_riga_id`.

---

{% include-markdown "signature-core.md" %}
