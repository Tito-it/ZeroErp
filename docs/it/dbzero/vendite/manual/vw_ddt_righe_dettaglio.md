## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_righe_dettaglio`

> **Ultimo aggiornamento**: 3 novembre 2026

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

### ⭐ La riga-onere

(rev 3-11-2026, `20261103-34`, brief `brief-db-addebito-trasporto-ordine` §7.3)

Dal 2026-11-03 la bolla puo' portare **oneri** (trasporto, spese) come righe.
Due colonne in coda:

- `e_onere` — la riga e' un onere: `NOT` [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce)
  sulla natura **congelata** della riga. La stampa mette gli oneri dopo gli
  articoli con questo dato (lo fa il backend), senza ricostruire la regola.
- `causale_onere_id` — la causale dell'onere, dall'articolo; vuota sulla merce.

`evasa` non cambia: un onere copiato dall'ordine porta il legame ed e' fermo
come ogni riga evasa; la correzione della quantita' evasa si spegne col motivo
`RIGA_ONERE` (`correggi_qta_evasa_blocco`).

---

### Regole

- **Tutte le righe**, anche le non attive: il filtro lo mette chi legge.
- **Nessun `ORDER BY`**: l'ordine del documento è `riga_nr`, lo chiede chi legge.
- Niente date di consegna: il DDT **è** la consegna.
- `security_invoker`: `ddt_righe` è in RLS.

---

{% include-markdown "signature-core.md" %}

### Sezione del documento (rev 2026-11-03)

Dal `20261103-52`, in coda `sezione_documento` (1 articoli, 2 oneri, da `e_onere`). L'ordine del
documento è `sezione_documento, riga_nr`: gli oneri dopo gli articoli, a video e in stampa, come
sulla fattura (`vw_fattura_righe_lista`).
