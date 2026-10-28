## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_transizione_stato()`

> 👀 **Vedi anche**
>
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) ·
> [config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni) ·
> [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) ·
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) ·
> [vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute) ·
> [Il modello del documento di vendita](/guide/modello-documento-di-vendita)

### 🎯 Scopo
(ultima revisione 28-10-2026 — brief `brief-modello-documento-vendita` §16)

Il guard dei **passaggi di stato** di una versione di listino. Montato da
`trg_listini_versioni_a10_guard_transizione_stato_upd` (`BEFORE UPDATE OF
stato_doc_listino_versione_id`, solo quando lo stato cambia).

### Regole

* Il passaggio dev'essere una riga attiva della matrice
  [config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni):
  oggi BOZZA → ATTIVA e ATTIVA → CHIUSA. Altrimenti `E_VERSIONE_STATO_TRANSIZIONE_INVALIDA`
  (versione, stato di partenza, stato d'arrivo, fine validità).
* **Verso CHIUSA**: la fine validità c'è ed è passata (`valido_al` < data operativa). Prima,
  la versione è ATTIVA con la chiusura programmata.
* **Verso ATTIVA**: solleva il primo motivo di
  [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile)
  (versione spenta, senza prezzi): la stessa regola che spegne «Attiva» nella lista.

Lo stato lo scrivono solo i verbi, dietro la porta: l'attivazione
([vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino)) e la
chiusura a scadenza ([vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute)).

---

{% include-markdown "signature-core.md" %}
