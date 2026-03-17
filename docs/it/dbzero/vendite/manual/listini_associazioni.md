## 📘 Documentazione Concettuale – Tabella `vendite.listini_associazioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini](/dbzero/vendite/tabelle/listini)  
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
>
🎯 Scopo Principale

La tabella `vendite.listini_associazioni` definisce quali listini sono candidati per
un dato contesto operativo (BA, utility, emittente fiscale), con priorita` di tie-break
tra listini concorrenti.

---

### Regole principali

* FK obbligatoria su `listino_id`;
* dimensioni contesto opzionali:
  * `billing_account_id`
  * `utility_id`
  * `emittente_soggetto_ruolo_id`
* `priorita > 0`;
* intervallo di validita` coerente (`valido_al > valido_dal` se presente);
* unicita` attiva per stessa combinazione listino+contesto+`valido_dal`
  (`uq_listini_associazioni_key_attiva`).

---

### Utilizzo previsto

* fase 1 del resolver: selezione listini candidati applicabili al contesto;
* tie-break tra listini tramite `priorita` (valore minore = priorita` piu` alta);
* controllo attivazione/disattivazione progressiva per go-live.

---

{% include-markdown "signature-core.md" %}
