## 📘 Documentazione Concettuale – Tabella `config.canali_pratiche`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) (campo `canale_origine_id`)

---
### 🎯 Scopo Principale
La tabella `config.canali_pratiche` definisce i **canali di visibilita'** attraverso cui i flussi di una pratica possono essere esposti verso l'esterno. Non e' un flag booleano sulla pratica ma un **registry di interfacce** configurabile.

---

### Ruolo nel processo

* La tabella M:N `pratiche.template_flussi_canali` collega ogni template flusso ai canali su cui e' visibile.
* Il campo `canale_origine_id` su `pratiche.pratiche` indica da quale canale esterno e' arrivata la richiesta che ha originato la pratica (`NULL` = creata internamente).
* Pratiche con `solo_interna = true` non espongono flussi su alcun canale.

---

### Valori previsti (seed DB-6)

| codice_interno | Descrizione |
|----------------|-------------|
| `WEB_CLIENTI` | Portale web per i clienti |
| `APP_TECNICA` | Applicazione mobile per tecnici |
| `PORTALE_FORNITORI` | Portale per i fornitori |

---

### Estensibilita'

Nuovi canali possono essere aggiunti senza modifiche al codice. Basta inserire un record in questa tabella e collegarlo ai template flussi desiderati tramite `template_flussi_canali`.

---

### Convenzioni

* Pattern config standard: `codice`, `codice_interno` locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
