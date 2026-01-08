# Schema `acquisti`

## 📚 Tabelle (manuale)
- [note](manual/note.md) — `acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.
- [note_ddt](manual/note_ddt.md) — `acquisti.note_ddt` gestisce **note testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
- [note_ordini](manual/note_ordini.md) — `acquisti.note_ordini` gestisce **ordini testuali**.  Vedi documento principale [acquisti.note](/dbzero/acquisti/tabelle/note)
