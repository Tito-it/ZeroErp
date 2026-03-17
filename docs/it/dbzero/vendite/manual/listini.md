## 📘 Documentazione Concettuale – Tabella `vendite.listini`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • [vendite.listini_associazioni](/dbzero/vendite/tabelle/listini_associazioni)  
> • [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)  
>
🎯 Scopo Principale

La tabella `vendite.listini` rappresenta la testata anagrafica dei listini prezzo
del dominio vendite.

Contiene i dati stabili del listino (codice, descrizione, dominio), mentre validita`
temporale e prezzi sono demandati rispettivamente a `listini_versioni` e
`listini_righe`.

---

### Regole principali

* `codice` univoco (`uq_listini_codice`).
* `dominio` ammesso solo tra:
  * `UTILITY`
  * `COMMERCIO`
* `attivo=true` abilita il listino per associazione e risoluzione prezzi.

---

### Utilizzo previsto

* contenitore principale per listini multi-dominio;
* separazione tra identita` listino e versionamento temporale;
* base per mapping contesto (`listini_associazioni`) e pricing resolver.

---

{% include-markdown "signature-core.md" %}
