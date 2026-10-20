---
search:
  exclude: true
---

# Schema `acquisti`

## 📚 Tabelle (manuale)
- [ddt](manual/ddt.md) — (rev 2026-08-21)
- [ddt_indirizzi](manual/ddt_indirizzi.md) — (rev 2026-08-21)
- [ddt_righe](manual/ddt_righe.md) — (rev 2026-08-21)
- [note](manual/note.md) — `acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.
- [note_ddt](manual/note_ddt.md) — `acquisti.note_ddt` gestisce **note testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
- [note_ordini](manual/note_ordini.md) — `acquisti.note_ordini` gestisce **ordini testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
- [ordini](manual/ordini.md) — (rev 2026-08-21)
- [ordini_righe](manual/ordini_righe.md) — (rev 2026-08-21)
- [ordini_righe_fulfillment](manual/ordini_righe_fulfillment.md) — (rev 2026-08-21)

## ⚙️ Funzioni (manuale)
- [fn_get_acquisti_note](manual/fn_get_acquisti_note.md) — (rev 2026-08-21)
- [trgfn_acq_ordini_only_consegna_tipo_con](manual/trgfn_acq_ordini_only_consegna_tipo_con.md) — (rev 2026-08-21)
