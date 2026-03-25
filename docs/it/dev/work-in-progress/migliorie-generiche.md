# WIP — Migliorie generiche

> Data apertura: 2026-03-25
>
> Stato: **BACKLOG** — raccolta migliorie funzionali da implementare

---

## 1. Ricerca universale: modalita "Tutti i ruoli"

> Priorita: media | Complessita: media | Stato: **DA FARE**

### Situazione attuale

La ricerca universale (`SearchDrawer`) richiede sempre la selezione di un tipo ruolo
(CLIENTE, FORNITORE, ecc.) tramite dropdown. Non e possibile cercare soggetti
indipendentemente dal ruolo — es. trovare un soggetto che ha sia ruolo CLIENTE che
FORNITORE, o un soggetto senza ruoli.

### Obiettivo

Aggiungere un'opzione "Tutti i ruoli" (checkbox o voce nel dropdown) che cerca su tutti
i soggetti senza filtro ruolo. I risultati mostrano il soggetto con tutti i suoi ruoli.

### Impatto tecnico

| Area | Modifica | Complessita |
|------|----------|-------------|
| **Frontend — SearchDrawer** | Checkbox/toggle "Tutti i ruoli", non invia `tipo_ruolo_id` | Bassa |
| **Backend — search_view.py** | Rendere `tipo_ruolo_id` opzionale nella validazione | Bassa |
| **Backend — fn_search_soggetti_universale** | Query senza filtro ruolo, restituire soggetti con JSONB ruoli | Media |
| **Frontend — SearchDetailTable** | Espansione secondo livello con righe miste (CLIENTE + FORNITORE) | Media-alta |
| **Frontend — DetailActions** | Il pulsante "imposta contesto" deve sapere QUALE ruolo selezionare | Media |

### Punto critico

Il dettaglio secondo livello (espansione riga). Oggi mostra colonne specifiche per variante
(cliente → utility/stato, fornitore → attivo/passivo). Con "tutti i ruoli" un soggetto puo
avere righe CLIENTE e FORNITORE nella stessa espansione — servono colonne adattive o raggruppate.

### Approccio suggerito

1. Nel dropdown tipo ruolo aggiungere voce "Tutti" (id = null)
2. Backend: se `tipo_ruolo_id` assente, query su tutti i soggetti con JOIN su ruoli
3. SearchDetailTable: usare variante `mixed` che mostra colonna "Tipo ruolo" + colonne generiche
4. DetailActions: il payload include `tipo_ruolo_codice` della riga specifica selezionata

---

*ZeroERP Migliorie Generiche — avviato 25 marzo 2026*
