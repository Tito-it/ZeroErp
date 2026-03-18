## 📘 Documentazione Concettuale – Tabella `vendite.commesse_sorgenti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
>
### 🎯 Scopo Principale
La tabella `vendite.commesse_sorgenti` traccia la sorgente ROOT della commessa e
garantisce idempotenza sorgente a livello commessa.

---

### Regole principali

* una sola root per commessa (`UNIQUE commessa_id + ruolo_link`);
* in v1 `ruolo_link` ammesso solo `ROOT`;
* una sorgente (`sorgente_tipo_id + sorgente_uid + ruolo_link`) non puo` essere
  collegata due volte.

---

### Utilizzo previsto

* tracciabilita` della root source commessa;
* protezione anti-doppio aggancio documento->commessa;
* base per recovery/audit lato orchestratore push.

---

{% include-markdown "signature-core.md" %}
