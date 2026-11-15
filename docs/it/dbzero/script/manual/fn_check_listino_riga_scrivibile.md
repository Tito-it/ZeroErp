## 📘 Documentazione Concettuale – Funzione `script.fn_check_listino_riga_scrivibile(p_listino_versione_id, p_listino_riga_id, p_operazione)`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [script.fn_check_listino_riga_rettificabile](/dbzero/script/manual/fn_check_listino_riga_rettificabile) — l'altra porta, la rettifica ·
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) ·
> [vendite.trgfn_listini_righe_comp_guard_immutabilita_v5](/dbzero/vendite/manual/trgfn_listini_righe_comp_guard_immutabilita_v5) ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) ·
> [config.stati_doc_listino_versioni](/dbzero/config/manual/stati_doc_listino_versioni) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo

**Perché non si scrive nelle righe di una versione di listino.** Le righe
(`vendite.listini_righe`), i prezzi dei componenti dei kit (`vendite.listini_righe_componenti`) e
la periodicità dei kit (`vendite.listini_kit`) hanno una regola sola: **si scrivono solo in
bozza**. Restituisce l'elenco dei motivi (`codice`, `reason`, `reason_key`, `dettaglio`,
`valori`); il primo è quello che si solleva. Elenco vuoto = si scrive. Non solleva.

| # | Codice | `reason` | Quando |
| --- | --- | --- | --- |
| 1 | `E_RIGA_LISTINO_VERSIONE_CHIUSA` | `VERSIONE_CHIUSA` | la versione è CHIUSA: è la storia dei prezzi |
| 2 | `E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA` | `VERSIONE_NON_IN_BOZZA` | la versione non è in bozza: è il listino in uso, o lo sarà |

Le `reason_key` sono `vendite.listini.azione_reason.versione_chiusa` e
`vendite.listini.azione_reason.versione_non_in_bozza`.

### Regole

* **In bozza si scrive tutto**, fuori dalla bozza **niente**: né una riga nuova, né una modifica, né
  un'eliminazione, per qualunque colonna. La bozza è lo stato che il vocabolario marca `iniziale`,
  mai il codice `BOZZA`. CHIUSA si nomina col codice: è la destinazione della chiusura.
* **Il prezzo sbagliato di una riga in uso si corregge con la rettifica**, una porta a parte, col
  motivo: [`vendite.fn_rettifica_riga_listino`](/dbzero/vendite/manual/fn_rettifica_riga_listino),
  con la sua regola in
  [`script.fn_check_listino_riga_rettificabile`](/dbzero/script/manual/fn_check_listino_riga_rettificabile).
  Per tutto il resto si clona la versione, si cambia la bozza e la si attiva.
* `p_listino_riga_id` è la riga che c'è (`NULL` = una riga nuova), della tabella del guard che
  chiama; `p_operazione` l'operazione (senza: INSERT o UPDATE secondo la riga). Entrano nel
  dettaglio e nei valori del messaggio, **non nella regola**.
* Una versione che non si legge non si giudica (elenco vuoto): parlano la chiave esterna e la
  policy della tabella che si scrive.
* La chiamano i tre guard (righe, componenti, kit), che ne sollevano il primo motivo, e le
  superfici della versione e delle righe: una regola, più letture.

### Perché

Il modello dei listini (sviluppo-listini-v3, 2026-04-12) dice che in una versione attiva sulle righe
non si fa **nessuna operazione**, e che la rettifica controllata è un'operazione a parte, «esplicita,
non mascherata dal PATCH ordinario». Il guard delle righe, che non sapeva riconoscere la rettifica,
lasciava passare ogni scrittura di una riga non ancora usata: con la rettifica dal verbo, la
scrittura ordinaria torna alla regola del modello.

---

{% include-markdown "signature-core.md" %}
