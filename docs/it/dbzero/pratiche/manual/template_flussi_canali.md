## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_canali`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) (campo `solo_interna`)

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi_canali` e' la **relazione M:N** tra template flussi e canali di visibilita'. Definisce su quali interfacce esterne un flusso e' esposto (es. portale clienti, app tecnica).

---

### Ruolo nel processo

* Ogni template flusso puo' essere visibile su zero, uno o piu' canali.
* Pratiche con `solo_interna = true` non espongono flussi su alcun canale — la relazione esiste ma viene ignorata dalla logica applicativa.
* Il sistema canali e' **estensibile**: nuovi canali si aggiungono in `config.canali_pratiche` e si collegano qui senza modifiche al codice.

---

### Caratteristiche

| Aspetto | Dettaglio |
|---------|-----------|
| **Relazione** | Immutabile: si cancella e ricrea (no UPDATE). |
| **Audit** | Solo `data_insert/user_insert` — coerente con l'immutabilita'. |
| **UQ** | `(template_flusso_id, canale_id)` — no duplicati. |
| **FK template** | ON DELETE CASCADE — se il template viene rimosso, i canali collegati spariscono. |
| **FK canale** | ON DELETE NO ACTION — il canale non puo' essere rimosso se ha collegamenti. |

---

### Esempio

| template_flusso | canale | Significato |
|-----------------|--------|-------------|
| "Richiesta Allacciamento" | WEB_CLIENTI | Il cliente puo' avviare la richiesta dal portale web |
| "Sopralluogo" | APP_TECNICA | Il tecnico vede e gestisce il sopralluogo dall'app mobile |

---

{% include-markdown "signature-core.md" %}
