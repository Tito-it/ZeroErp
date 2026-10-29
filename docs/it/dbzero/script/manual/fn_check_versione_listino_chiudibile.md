## 📘 Documentazione Concettuale – Funzione `script.fn_check_versione_listino_chiudibile(p_versione_id, p_valido_al)`

> 👀 **Vedi anche**
>
> [vendite.fn_programma_chiusura_versione_listino](/dbzero/vendite/funzioni/fn_programma_chiusura_versione_listino) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/views/vw_listini_versioni_azioni) ·
> [vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo
(29-10-2026 — brief `brief-modello-documento-vendita` §16.14, C-2 e C-3)

**Perché una versione di listino non si chiude a una data.** «Chiudere» vuol dire fissare la fine
della validità di una versione attiva; lo stato «chiusa» lo scrive poi il job, a fine validità.
Restituisce l'elenco dei motivi (`codice`, `reason`, `reason_key`, `dettaglio`, `valori`); il primo
è quello che si solleva. Elenco vuoto = si chiude. Non solleva.

| # | Codice | Quando |
| --- | --- | --- |
| 1 | `E_LISTINO_VERSIONE_NON_CHIUDIBILE` | la versione non è attiva: in bozza la fine si decide con le altre date, una chiusa non cambia più |
| 2 | `E_LISTINO_VERSIONE_FINE_NEL_PASSATO` | la fine proposta è prima di oggi: toglierebbe il prezzo ai documenti già datati dopo quella fine |

### Regole

* «Oggi» è la data operativa dell'azienda (`script.fn_data_operativa`), la stessa del job che
  chiude le versioni scadute. Oggi è ammesso: la versione vale fino a stasera.
* Senza data (`p_valido_al` vuoto) c'è solo il motivo 1: dice se il pulsante «Chiudi» si accende,
  ed è anche il caso di chi toglie la chiusura.
* Una fine prima dell'inizio non è un motivo di qui: la rifiuta il controllo comune delle date.
* Non sta nel controllo della tabella: l'attivazione di una versione chiude la precedente anche
  nel passato (decisioni D3 e D2 dei listini), e la tabella non sa chi la sta scrivendo.
* Versione inesistente o fuori perimetro: nessun motivo.

---

{% include-markdown "signature-core.md" %}
