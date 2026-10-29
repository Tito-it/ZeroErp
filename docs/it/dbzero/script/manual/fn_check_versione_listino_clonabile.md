## 📘 Documentazione Concettuale – Funzione `script.fn_check_versione_listino_clonabile(p_sorgente_id, p_valido_dal)`

> 👀 **Vedi anche**
>
> [vendite.fn_clona_versione_listino](/dbzero/vendite/funzioni/fn_clona_versione_listino) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo
(29-10-2026 — brief `brief-modello-documento-vendita` §16.14, C-1)

**Perché una versione di listino non si copia in una versione che comincia a una data.**
Restituisce l'elenco dei motivi (`codice`, `reason`, `reason_key`, `dettaglio`, `valori`); il primo
è quello che si solleva. Elenco vuoto = si copia. Non solleva.

| # | Codice | Quando |
| --- | --- | --- |
| 1 | `E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE` | la copia comincerebbe prima della versione da cui nasce (decisione D2 dei listini) |

### Regole

* Una decorrenza nel passato è ammessa: i documenti già emessi non si correggono da soli, e lo
  dice il dialogo.
* **Si copia da qualunque stato**, anche da una bozza (decisione O1, confermata il 29-10-2026). Per
  questo «Clona» non ha un pulsante spento né una riga nel registro delle azioni: senza data la
  check risponde sempre «si copia».
* Versione inesistente o fuori perimetro: nessun motivo.

---

{% include-markdown "signature-core.md" %}
