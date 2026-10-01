## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_righe_dettaglio`

> 👀 **Vedi anche**
>
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) — la sorgente
> • [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga) — l'importo di riga
> • Gemelle: [vw_preventivi_righe_dettaglio](/dbzero/vendite/views/vw_preventivi_righe_dettaglio) · [vw_ordini_righe_dettaglio](/dbzero/vendite/views/vw_ordini_righe_dettaglio) · [vw_resi_righe_dettaglio](/dbzero/vendite/views/vw_resi_righe_dettaglio)
>
> **Verifica:** `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql`

---

### 🎯 Scopo Principale

(vista nata il 2026-09-28, `20260928-19`)

**Le righe di un DDT**, con articolo, unità di misura, IVA e importo: la
sorgente della lista configurabile `vendite.ddt_righe` e del repository del
backend.

---

### ⭐ Perché esiste

Come per l'ordine: le righe del DDT esistevano solo come due query Python
(`ddt_repository.list_righe` e `get_riga`, già con proiezioni diverse), e
l'importo di riga era scritto lì. Decisione di Tid (D-8.6 del
brief-db-liste-righe-documento): la sede è una vista.

---

### ⭐ La riga senza prezzo

Il DDT è il documento dove è nata la regola **«prezzo assente → nessun
valore, non zero»** (V-2/DEC-6): una riga di solo trasporto non vale zero.
`importo_riga` e `imponibile_riga_full` sono **NULL** su quella riga, e la
regola vive in [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga),
per tutti i documenti.

---

### Regole

- **Tutte le righe**, anche le non attive: il filtro lo mette chi legge.
- **Nessun `ORDER BY`**: l'ordine del documento è `riga_nr`, lo chiede chi legge.
- Niente date di consegna: il DDT **è** la consegna.
- `security_invoker`: `ddt_righe` è in RLS.

---

{% include-markdown "signature-core.md" %}
