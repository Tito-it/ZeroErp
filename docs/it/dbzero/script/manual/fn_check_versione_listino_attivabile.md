## 📘 Documentazione Concettuale – Funzione `script.fn_check_versione_listino_attivabile(p_versione_id)`

> 👀 **Vedi anche**
>
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) ·
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-4; rivisto il 1-11-2026)

**Perché una versione di listino non si attiva.** Restituisce l'elenco dei motivi
(`codice`, `reason`, `reason_key`, `dettaglio`, `valori`); il primo è quello che si solleva.
Elenco vuoto = si attiva. Non solleva.

| # | Codice | Quando |
| --- | --- | --- |
| 1 | `E_LISTINO_VERSIONE_SPENTA` | la versione è spenta (`attivo = false`) |
| 2 | `E_LISTINO_VERSIONE_SENZA_RIGHE` | la versione non ha prezzi: nessuna riga attiva e nessun composito col prezzo bundle |
| 3 | `E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA` | una quota fissa a canone ([`vendite.fn_articolo_quota_fissa_a_canone`](/dbzero/vendite/manual/fn_articolo_quota_fissa_a_canone)), riga o kit, senza periodicità ([`vendite.fn_listino_periodicita_articolo`](/dbzero/vendite/manual/fn_listino_periodicita_articolo)). Il primo articolo per codice; `dettaglio.campo` = `periodicita` |

### Regole

* Lo stato non è un motivo: chi può attivare da quale stato lo dice la matrice.
* Il motivo 3 (dal 31-10-2026, brief `brief-db-contratto-righe-periodiche-in-commessa` §7.3, D-3):
  una quota fissa a canone si addebita da sé a ogni contratto del listino, e fuori dalla bozza la
  riga non si corregge più. Senza periodicità ogni contratto del listino resterebbe con un canone
  che non può partire. La bozza resta libera di essere incompleta.
* Versione inesistente o fuori perimetro: nessun motivo.
* La chiamano il verbo (prima di chiudere le precedenti), il guard di transizione e la superficie
  della lista: una regola, tre letture.

---

{% include-markdown "signature-core.md" %}
