# Schema `acquisti`

## 📚 Tabelle
- [ddt](tabelle/ddt.md)
- [ddt_indirizzi](tabelle/ddt_indirizzi.md)
- [ddt_righe](tabelle/ddt_righe.md)
- [note](tabelle/note.md) — `acquisti.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.
- [note_ddt](tabelle/note_ddt.md)
- [note_ordini](tabelle/note_ordini.md)
- [ordini](tabelle/ordini.md)
- [ordini_righe](tabelle/ordini_righe.md)
- [ordini_righe_fulfillment](tabelle/ordini_righe_fulfillment.md)

## ⚙️ Funzioni
- [fn_get_acquisti_note](funzioni/fn_get_acquisti_note.md)
- [trgfn_a10_a_ddt_protect_num](funzioni/trgfn_a10_a_ddt_protect_num.md)
- [trgfn_a10_ao_only_consegna_tipo_con](funzioni/trgfn_a10_ao_only_consegna_tipo_con.md)
- [trgfn_a10_ordini_protect_num](funzioni/trgfn_a10_ordini_protect_num.md)
- [trgfn_ddt_indirizzi_only_allowed_tipi](funzioni/trgfn_ddt_indirizzi_only_allowed_tipi.md)

## 🔍 Views
