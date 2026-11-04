## 📘 Documentazione Concettuale – Tabella `pratiche.handler_flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi)

---
### 🎯 Scopo Principale
La tabella `pratiche.handler_flussi` e' il **registry degli handler flusso**. Ogni record mappa una `handler_key` univoca a un handler Python nel `handler_registry.py` di Django. Il DB contiene solo la chiave; il mapping effettivo e' nel codice applicativo.

---

### Ruolo nel processo

* I template flussi con `handler_id NOT NULL` delegano l'esecuzione a un handler automatico (su evento **IN_CORSO**).
* I template con `handler_id NULL` rappresentano **step manuali** (completati dall'operatore).
* Il campo `handler_key` e' la chiave usata da Django per risolvere la classe Python associata.
* Gli handler non scattano più solo all'avvio: il legame [`template_flussi_handler_eventi`](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) permette di eseguire un handler anche al **COMPLETATO** di uno step, **esito-aware** (es. `vendita.post_smistamento` su `SMISTAMENTO` COMPLETATO/MERCE_PRESENTE). Stesso registry, stesso `HANDLER_MAP`.
* ⛔ Il registro del DB e `HANDLER_MAP` devono dire la stessa cosa: un handler si ritira **prima** a DB (collegamenti spenti, poi handler spento) e solo dopo dal codice. L'ordine e il perché stanno in [`template_flussi_handler_eventi`](/dbzero/pratiche/tabelle/template_flussi_handler_eventi). In Fase 2 anche l'esecuzione IN_CORSO (oggi su `template_flussi.handler_id`) confluirà in quella tabella.

---

### Relazione con Django

```python
# In services/handler_registry.py
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    "APPUNTAMENTO": AppuntamentoHandler,
    "SOPRALLUOGO":  SopralluogoHandler,
    # ...
}
```

Il dispatch avviene tramite lookup: `handler_key` → classe Python → `execute(flusso_id, pratica_id, params)`.

I parametri operativi per l'handler sono configurati nel campo `handler_params` del template flusso associato.

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `handler_key` | VARCHAR(100), UNIQUE. Chiave per il mapping Python. |
| `codice` | VARCHAR(50), UNIQUE. Codice leggibile per interfaccia. |

---

### Convenzioni

* Registry puro: no `storicizza`, no `tx_id` (non serve tracciamento transazionale).
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
