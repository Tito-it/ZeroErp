## 📘 Documentazione Concettuale – Vista `vendite.vw_ordini_righe_dettaglio`

> 👀 **Vedi anche**
>
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) · [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) — le sorgenti
> • [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga) — l'importo di riga
> • Gemelle: [vw_preventivi_righe_dettaglio](/dbzero/vendite/views/vw_preventivi_righe_dettaglio) · [vw_ddt_righe_dettaglio](/dbzero/vendite/views/vw_ddt_righe_dettaglio) · [vw_resi_righe_dettaglio](/dbzero/vendite/views/vw_resi_righe_dettaglio)
>
> **Verifica:** `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql`

---

### 🎯 Scopo Principale

(vista nata il 2026-09-28, `20260928-18`)

**Le righe di un ordine**, con articolo, unità di misura, IVA, importo, evaso e
residuo: la sorgente della lista configurabile `vendite.ordine_righe` e del
repository del backend.

---

### ⭐ Perché esiste

Fino al 2026-09-28 le righe d'ordine esistevano solo come due query Python
(`ordini_repository.list_righe` e `get_riga`), con proiezioni già diverse fra
loro e due regole di dominio che al database non stavano da nessuna parte:
l'importo di riga e il calcolo di evaso e residuo. Decisione di Tid (D-8.6 del
brief-db-liste-righe-documento): per le righe di un documento la sede è una
vista, e il repository la legge.

---

### Colonne da sapere

| Colonna | Cosa |
| --- | --- |
| `importo_riga` | `round(script.fn_imponibile_riga(…), 2)`: per mostrare |
| `imponibile_riga_full` | lo stesso a precisione piena: per chi aggrega |
| `qta_evasa_operativa` | somma dei fulfillment (UoM base) ÷ `factor_to_base`, 6 decimali |
| `qta_residua_operativa` | ordinato − evaso, **mai negativo**, in UoM operativa |
| `data_consegna_richiesta_cliente` / `data_consegna_confermata` | la richiesta è del cliente, la confermata è la nostra promessa (si decide alla conferma: può essere vuota in bozza) |
| `is_composito_caso_a` | la riga ha componenti attivi: il FE mostra la freccia di espansione |
| `data_consegna_confermata_blocco` | perché la data confermata della riga **non** si cambia ora: `STATO_NON_AMMETTE` (lo stato dell'ordine) o `RIGA_SPEDITA` (la riga è già partita con un DDT, anche in parte). `NULL` = si cambia. Dalla stessa check del guard, `script.fn_check_ordine_riga_data_consegna_confermata` (dal 2026-10-11, `20261012-07`) |

⚠️ Un `factor_to_base` a zero dà evaso e residuo **NULL**, non una divisione per
zero.

---

### Regole

- **Tutte le righe**, anche le non attive: il filtro lo mette chi legge.
- **Nessun `ORDER BY`**: l'ordine lo chiede chi legge (per il documento,
  `riga_nr`).
- `security_invoker`: `ordini_righe` e i fulfillment sono in RLS.

---

{% include-markdown "signature-core.md" %}
