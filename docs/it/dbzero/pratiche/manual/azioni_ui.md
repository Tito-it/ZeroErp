## 📘 Documentazione Concettuale – Tabella `pratiche.azioni_ui`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi)

---
### 🎯 Scopo Principale
La tabella `pratiche.azioni_ui` e' il **catalogo delle attivita' UI lanciabili dal flusso di pratica**. E' lo **specchio lato frontend** del registry handler (`pratiche.handler_flussi`):

* `handler_flussi` mappa una `handler_key` a un handler **Python** per l'automazione **server-side** (eseguita da Django sull'evento di flusso).
* `azioni_ui` mappa una `azione_ui_key` a un **componente/drawer di dominio** risolto dal **registry frontend** (`UI_ACTIVITY_REGISTRY`), per l'**attivita' interattiva** (es. aprire il drawer di un preventivo dentro la pratica).

Il DB conserva solo la chiave: non interpreta mai `azione_ui_key`, esattamente come per `handler_key`.

---

### Ruolo nel processo

* Un template di flusso con `azione_ui_id NOT NULL` (vedi [template_flussi](/dbzero/pratiche/tabelle/template_flussi)) **offre un'attivita' interattiva** nel flusso: il frontend risolve la `azione_ui_key` nel registry e apre il componente dichiarato.
* Un template con `azione_ui_id NULL` non offre attivita' interattiva (flusso avvia/completa standard).
* La chiave non presente nel registry FE → **nessun pulsante** (fail-safe): la registrazione effettiva delle azioni vive lato FE, il DB ne e' il catalogo referenziale.

---

### Relazione con il frontend

```js
// In frontend/src/pratiche/uiActivityRegistry.js
const UI_ACTIVITY_REGISTRY = {
  APRI_PREVENTIVO: { loadComponent: () => import('.../PreventiviDrawer.vue'), /* ... */ },
  // APRI_OFFERTA, APRI_CONTRATTO → quando nasceranno i relativi flussi
}
```

Il dispatch avviene per lookup: `azione_ui_key` → componente di dominio. Import lazy per non accoppiare `pratiche → vendite` (stessa cautela del registry handler lato Python).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `azione_ui_key` | VARCHAR(100), UNIQUE. Chiave risolta dal registry FE `UI_ACTIVITY_REGISTRY`. Non interpretata dal DB. |
| `codice` | VARCHAR(50), UNIQUE. Codice leggibile per interfaccia. |

---

### Seed corrente

| `azione_ui_key` | Consumatore |
|---|---|
| `APRI_PREVENTIVO` | template `PREVENTIVAZIONE` delle pratiche PREVENTIVI (apre il preventivo collegato dal flusso) |

Le voci `APRI_OFFERTA` / `APRI_CONTRATTO` (famiglia documenti confermata) entreranno nel catalogo **quando nasceranno i relativi flussi** — coerente col precedente `handler_flussi` (1 riga = 1 consumatore reale). Gli **ordini** restano fuori: nascono dal push a valle, non si aprono in bianco da un flusso.

---

### Convenzioni

* Registry puro: no `storicizza`, no `tx_id` (non serve tracciamento transazionale) — identico a `handler_flussi`.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
