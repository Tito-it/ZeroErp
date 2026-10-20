---
search:
  exclude: true
---

# Schema `acquisti`

## 📚 Tabelle
- [ddt](tabelle/ddt.md) — (rev 2026-08-21)
- [ddt_indirizzi](tabelle/ddt_indirizzi.md) — (rev 2026-08-21)
- [ddt_righe](tabelle/ddt_righe.md) — (rev 2026-08-21)
- [note](tabelle/note.md) — `acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.
- [note_ddt](tabelle/note_ddt.md) — `acquisti.note_ddt` gestisce **note testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
- [note_ordini](tabelle/note_ordini.md) — `acquisti.note_ordini` gestisce **ordini testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
- [ordini](tabelle/ordini.md) — (rev 2026-08-21)
- [ordini_righe](tabelle/ordini_righe.md) — (rev 2026-08-21)
- [ordini_righe_fulfillment](tabelle/ordini_righe_fulfillment.md) — (rev 2026-08-21)

## ⚙️ Funzioni
- [fn_get_acquisti_note](funzioni/fn_get_acquisti_note.md) — (rev 2026-08-21)
- [trgfn_acq_ordini_only_consegna_tipo_con](funzioni/trgfn_acq_ordini_only_consegna_tipo_con.md) — (rev 2026-08-21)

## 🔍 Views
