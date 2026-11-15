## 📘 Documentazione Concettuale – Funzione `script.fn_check_listino_riga_rettificabile(p_listino_riga_id)`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.fn_rettifica_riga_listino](/dbzero/vendite/manual/fn_rettifica_riga_listino) — il verbo ·
> [script.fn_check_listino_riga_scrivibile](/dbzero/script/manual/fn_check_listino_riga_scrivibile) — le scritture ordinarie ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) — il pulsante ·
> [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/manual/fn_listino_versione_in_vigore) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo

**Perché il prezzo di una riga di listino non si rettifica.** La rettifica corregge, col motivo,
il prezzo di una riga del **listino in uso**: è l'unica scrittura di una riga fuori dalla bozza.
Restituisce l'elenco dei motivi; il primo è quello che si solleva. Elenco vuoto = si rettifica. Non
solleva.

| # | Codice | `reason` | Quando |
| --- | --- | --- | --- |
| 1 | `E_RIGA_LISTINO_RETTIFICA_IN_BOZZA` | `VERSIONE_IN_BOZZA` | la versione è in bozza: la riga si modifica, non si rettifica |
| 2 | `E_RIGA_LISTINO_VERSIONE_CHIUSA` | `VERSIONE_CHIUSA` | la versione è CHIUSA |
| 3 | `E_RIGA_LISTINO_RETTIFICA_NON_IN_VIGORE` | `NON_IN_VIGORE` | la versione non è quella in vigore alla data operativa: non è ancora iniziata, o è già finita |
| 4 | `E_RIGA_LISTINO_PROPAGATA` | `RIGA_PROPAGATA` | il prezzo della riga è già stato usato da un documento |

Le `reason_key`: `vendite.listini.azione_reason.versione_in_bozza`, `.versione_chiusa`,
`.non_in_vigore`, `.riga_propagata`.

### Regole

* **In vigore** vuol dire la versione che
  [`vendite.fn_listino_versione_in_vigore`](/dbzero/vendite/manual/fn_listino_versione_in_vigore)
  restituisce alla data operativa (`script.fn_data_operativa`): la regola sta lì. Una versione
  attivata con l'inizio nel futuro non si rettifica e non si modifica: si clona.
* **Propagata**: la riga è citata (`listino_riga_id`) da una riga di commessa, un'attività
  fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od
  offerta, anche in bozza. Una tabella nuova che cita una riga di listino entra qui, con un
  `UNION ALL`. Per cambiare il prezzo di una riga propagata si fa una versione nuova del listino.
* Una riga che non si legge non si giudica: il verbo la cerca nel perimetro e risponde lui.
* La chiamano il verbo della rettifica, il guard delle righe dentro la porta del verbo e la
  superficie delle righe.

---

{% include-markdown "signature-core.md" %}
