## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_guard_spegnimento_storia`

> 👀 **Vedi anche**
>
> • [vendite.fn_listino_ha_storia](/dbzero/vendite/manual/fn_listino_ha_storia) — che cosa vuol dire «storia»
>
> • [vendite.listini](/dbzero/vendite/manual/listini) — la tabella che lo monta
>
Guide: [Gestione listini](/guide/gestione-listini)

### 🎯 Scopo Principale

(rev 2026-10-22, decisione di Tid del 2026-10-21)

Un listino **con storia** non si spegne con l'interruttore «Attivo»: ha dato prezzi ai documenti,
e quei prezzi devono restare riproducibili. Si chiude mettendo la **fine validità** alla versione
in vigore: alla scadenza la versione passa CHIUSA.

| Codice | Quando |
| --- | --- |
| `E_LISTINO_CON_STORIA_NON_SPEGNIBILE` | si prova a spegnere (`attivo` da vero a falso) un listino che ha storia |

Il codice è di classe **CONFLITTO_STATO**: è lo stato del listino a impedire la richiesta. Il
messaggio nomina il listino e dà il rimedio vero.

---

### Perché un guard suo

Prima lo spegnimento passava dalla catena generica «figli prima, padre poi», che rispondeva
`E_ATTIVO_BLOCK_CHILDREN_ACTIVE` con il rimedio «disattivare le righe». Su un listino con storia
quel rimedio **non si può eseguire**: versioni attivate e righe usate non si toccano. Un rifiuto
con un rimedio impossibile non aiuta nessuno.

---

### Quando scatta

* **Trigger**: `BEFORE UPDATE OF attivo`, per riga, su `vendite.listini`, solo quando `attivo`
  passa da vero a falso (`trg_listini_a05_guard_spegnimento_storia_upd`).
* **a05**: i trigger della stessa fase scattano in ordine di nome, e questo viene prima dei
  `a10_*_block_deact` della catena generica. Sul listino con storia parla lui.
* Un listino **senza storia** passa, e trova la catena generica.

---

### 🧪 Il presidio

`db/pgtap/vendite/test-listino-spegnimento-storia-v1.sql` (7 casi): la storia nei tre casi
(versione attiva, sola bozza, nessuna versione), il rifiuto col codice suo, lo spegnimento del
listino senza storia, la versione CHIUSA senza fine validità rifiutata, il codice registrato.

---
{% include-markdown "signature-core.md" %}
