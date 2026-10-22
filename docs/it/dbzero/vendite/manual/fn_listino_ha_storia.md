## 📘 Documentazione Concettuale – Funzione `vendite.fn_listino_ha_storia`

> 👀 **Vedi anche**
>
> • [vendite.trgfn_listini_guard_spegnimento_storia](/dbzero/vendite/manual/trgfn_listini_guard_spegnimento_storia) — il guard che la legge
>
> • [vendite.listini_versioni](/dbzero/vendite/manual/listini_versioni) — gli stati di una versione
>
Guide: [Gestione listini](/guide/gestione-listini)

### 🎯 Scopo Principale

(rev 2026-10-22, decisione di Tid del 2026-10-21 e D-1 del 2026-10-22)

Dice se un listino **ha storia**: se ha almeno una versione che è stata **attivata**, cioè oggi
ATTIVA o CHIUSA, anche spenta.

| Il listino ha… | Ha storia? |
| --- | --- |
| nessuna versione, o solo bozze | no |
| almeno una versione ATTIVA o CHIUSA | sì |

Una **bozza** non conta: nessuno ci ha mai potuto prendere un prezzo. Una versione **attivata**
conta sempre: da lì può essere uscito un prezzo che sta su un documento.

Il predicato è «la versione **non è più in bozza**» (`stato <> 'BOZZA'`): oggi vuol dire
ATTIVA o CHIUSA, e uno stato nuovo dopo l'attivazione conterebbe da solo.

⚠️ Non è la regola «quale versione vale a una data», che ha la sua sede in
[vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore):
qui non c'è una data e conta anche una versione spenta.

Gli stati di una versione non tornano indietro (da ATTIVA non si torna in bozza, CHIUSA è
finale), quindi «ha oggi una versione ATTIVA o CHIUSA» e «ha avuto una versione attiva» sono la
stessa cosa.

---

### Chi la legge

* **Il database**, per lo spegnimento: un listino con storia non si spegne con l'interruttore, si
  chiude con la fine validità della versione
  ([vendite.trgfn_listini_guard_spegnimento_storia](/dbzero/vendite/manual/trgfn_listini_guard_spegnimento_storia)).
* **Il backend**, per il drawer: il toggle «Attivo» si mostra solo a un listino senza storia. La
  regola si legge da qui e non si ricopia.

---

### La forma

`SECURITY INVOKER`, `STABLE`. Chi la chiede vede il listino, e le versioni di un listino hanno lo
stesso perimetro del listino.

---

### 🧪 Il presidio

`db/pgtap/vendite/test-listino-spegnimento-storia-v1.sql`.

---
{% include-markdown "signature-core.md" %}
