## 📘 Documentazione Concettuale – Tabella `config.tipi_reso`

> 👀 **Vedi anche**
>
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) ·
> [vendite.fn_ordine_riga_qta_riconsegna](/dbzero/vendite/funzioni/fn_ordine_riga_qta_riconsegna)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Vocabolario del **tipo reso**, per riga. Discrimina i due esiti dell'ibrido reso tramite il flag
`riapre_residuo`:

| `codice_interno` | `riapre_residuo` | effetto |
| --- | --- | --- |
| `RESO_A_CREDITO` | `false` | alimenta la coda accrediti (nota di credito) |
| `RESO_PER_RICONSEGNA` | `true` | riapre il residuo ordine + coda ri-consegna |

### Regola d'oro

**Nessun `IF` hardcoded** nel motore: la logica legge il flag `riapre_residuo`. `codice_interno`
immutabile (lock auto-provisionato). Estendibile con nuovi tipi senza toccare il codice.
