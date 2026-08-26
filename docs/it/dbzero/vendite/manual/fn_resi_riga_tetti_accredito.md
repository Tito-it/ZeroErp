## 📘 Documentazione Concettuale – Funzione `vendite.fn_resi_riga_tetti_accredito(...)`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti) ·
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md) ·
> [trgfn_resi_accrediti_guard](trgfn_resi_accrediti_guard.md) ·
> [fn_accredita_riga_reso](fn_accredita_riga_reso.md)
>
> Brief autorevole: `docs/it/dev/work-done/brief-design-note-credito-resi.md` (§12.6-ter)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

I **due tetti** di un accredito, letti **sopra la RLS**:

| Colonna | Cosa dice | Unità | Chi la consuma |
|---|---|---|---|
| `accredito_dovuto` | quanti pezzi il conto della merce dichiara accreditabili per quella riga di reso | **unità padre** (merce) | `fn_accredita_riga_reso`, come uguaglianza |
| `qta_riga_fattura` | quanti pezzi ha fatturato la riga di fattura che si sta rettificando | unità di **riga di fattura** | `trgfn_resi_accrediti_guard`, come tetto |

⭐ **Le due misure sono in unità diverse, e non è un dettaglio**: su un articolo
composito tre righe di documento valgono **una** unità di merce. È il motivo per
cui i due numeri escono insieme ma vengono consumati da due presidi diversi —
vedi [trgfn_resi_accrediti_guard](trgfn_resi_accrediti_guard.md).

---

### 🔴 Perché è `SECURITY DEFINER`

Perché i suoi consumatori sono **un guard e una funzione madre**, e sotto RLS
una riga fuori perimetro si legge come «non c'è».

`vendite.fatture_righe` e `vendite.resi` hanno policy attive. Se la riga di
fattura da accreditare stesse fuori dal perimetro di chi scrive, la lettura
tornerebbe zero righe — e un tetto letto come zero **smette di dire la verità**:
blocca a sproposito, o (con un confronto indeterminato, senza `COALESCE`) tace e
lascia passare.

È esattamente il difetto già visto in
`trgfn_resi_righe_guard_origine_coerente`, e la cura è la stessa: **la riga
correlata si legge da una `SECURITY DEFINER`**.

⚠️ **Con `search_path` fissato** (`pg_catalog, pg_temp`): una `SECURITY
DEFINER` senza è dirottabile — un chiamante può anteporre uno schema suo e far
risolvere i nomi altrove. È il pattern già usato da `script.fn_job_run_start`.

⭐ **Non è un buco di sicurezza.** La funzione restituisce **due numeri** e nulla
di riservato: quanto vale un accredito dovuto e quanti pezzi ha fatturato una
riga. Chi può chiamarla sta già scrivendo su quella riga di reso.

---

### ⚠️ Zero, non `NULL`, sull'assenza

È il valore **fail-closed**: una riga fuori dalla coda ha accredito dovuto `0`, e
qualunque quantità positiva lo supera. Con `NULL` il confronto del guard sarebbe
indeterminato e **non bloccherebbe**.

---

### Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `p_resi_riga_id` | `vendite.resi_righe.id%TYPE` | la riga di reso |
| `p_fattura_riga_id` | `vendite.fatture_righe.id%TYPE` | la riga di fattura da rettificare |

### 📦 Output

Una riga sola.

| Colonna | Tipo |
|---|---|
| `accredito_dovuto` | `vendite.resi_righe_accrediti.qta_partita%TYPE` |
| `qta_riga_fattura` | `vendite.fatture_righe.qta%TYPE` |

---

{% include-markdown "signature-core.md" %}
