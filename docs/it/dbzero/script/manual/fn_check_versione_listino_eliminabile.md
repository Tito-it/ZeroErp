## 📘 Documentazione Concettuale – Funzione `script.fn_check_versione_listino_eliminabile(p_versione_id)`

> 👀 **Vedi anche**
>
> [vendite.fn_elimina_versione_listino](/dbzero/vendite/funzioni/fn_elimina_versione_listino) ·
> [vendite.trgfn_listini_versioni_guard_per_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_per_stato) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) ·
> [script.fn_tabelle_che_trattengono](/dbzero/script/funzioni/fn_tabelle_che_trattengono) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16.11, E-1, E-2, E-3)

**Perché una versione di listino non si elimina.** Restituisce l'elenco dei motivi
(`codice`, `reason`, `reason_key`, `dettaglio`, `valori`); il primo è quello che si solleva.
Elenco vuoto = si elimina. Non solleva.

| # | Codice | Quando |
| --- | --- | --- |
| 1 | `E_LISTINO_VERSIONE_NON_ELIMINABILE` | la versione non è in bozza: attiva o chiusa, è stata usata per i prezzi |
| 2 | `E_LISTINO_VERSIONE_CITATA` | la versione è in bozza, ma un documento la usa: un contratto, un'offerta, un'attività di commessa (la versione o una sua riga) |

### Regole

* Con il motivo 1 si esce: una versione uscita dalla bozza non si elimina comunque.
* **Chi usa la versione non è scritto a mano**: lo dicono i legami del database
  (`script.fn_tabelle_che_trattengono`). Un documento nuovo che fissa una versione entra da solo.
  Le righe e i componenti della versione non contano: si eliminano con lei. `dettaglio.dove`
  elenca le tabelle.
* Versione inesistente o fuori perimetro: nessun motivo.
* La chiamano il verbo (prima di cancellare), il guard per stato (ramo DELETE) e la superficie
  della lista: una regola, tre letture.

---

{% include-markdown "signature-core.md" %}
