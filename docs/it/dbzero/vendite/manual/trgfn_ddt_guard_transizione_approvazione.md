## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_transizione_approvazione`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
>
> Funzioni:
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)

---

### 🎯 Scopo Principale

(rev 2026-07-09; rev 2026-09-24)

**Gate emissione** del DDT (BoM CASO A). Trigger function agganciata a `vendite.ddt` come
`trg_ddt_a10_guard_approvazione_upd` (`BEFORE UPDATE OF stato_doc_ddt_id`). Si auto-gatta a
**EMESSO** (`RETURN NEW` se lo stato non è EMESSO).

Alla transizione a EMESSO blocca se, sulle righe del DDT, esistono componenti CASO A:

* attivi, con il prezzo in attesa di approvazione (`PENDING`) → `E_DOC_PREZZO_PENDENTE`, o
  rifiutato (`REJECTED`) → `E_DOC_PREZZO_RIFIUTATO` (rev 2026-09-24, vedi sotto);
* attivi con `prezzo_unitario IS NULL` → `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`.

I motivi li legge da [`script.fn_check_ddt_emittibile`](/dbzero/script/funzioni/fn_check_ddt_emittibile)
(punto 5, chiesto solo se la causale vende) e solleva quelli di sua competenza.

Simmetrico ai guard di testata di preventivo, contratto, offerta e ordine: dal 2026-09-24 tutti
chiedono il prezzo non autorizzato allo stesso building block. Convive con il
guard grafo transizioni (`trg_ddt_a10_guard_transizione_upd`): concern diverso, nessuna
sovrapposizione di regola.

> **Nota storica**: la funzione era definita ma non agganciata (analisi §2.1); di fatto sul DB non
> esisteva. Il changeSet `20260709-05` la crea (dalla doc auto-gen) e la aggancia.

---

### Rev 2026-09-24 — i codici del prezzo non autorizzato

Il ramo che sollevava `E_COMPONENTE_PREZZO_PENDENTE` lascia il posto a due rami,
`E_DOC_PREZZO_PENDENTE` ed `E_DOC_PREZZO_RIFIUTATO`: sono i codici del building block
[`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
a cui [`fn_check_ddt_emittibile`](/dbzero/script/funzioni/fn_check_ddt_emittibile) ora chiede
il punto 5. Ne segue che il DDT non si emette neppure con un prezzo **rifiutato**, e che un
componente **spento** non conta più. Il ramo della valorizzazione non cambia.

`E_COMPONENTE_PREZZO_PENDENTE` resta vivo, ma solo come codice del guard **per riga**
([`trgfn_ddt_righe_componenti_guard_pending`](/dbzero/vendite/funzioni/trgfn_ddt_righe_componenti_guard_pending)):
un componente in attesa non si modifica.

I codici si confrontano col motivo **letterali**, come gli altri rami del ciclo: il guard sceglie
quali motivi sono suoi, gli altri li solleva un altro dei quattro guard di emissione.
(changeSet `20260924-32`, brief `brief-db-preventivi-congelamento-pricing`.)
