# WIP — Migliorie generiche

> Data apertura: 2026-03-25
>
> Stato: **BACKLOG** — raccolta migliorie funzionali da implementare

---

## 1. Indirizzi: suggerimento "Applica anche al soggetto"

> Priorita: bassa | Complessita: bassa | Stato: **DA FARE**

### Situazione attuale

La cascata indirizzi (istanza → ruolo → soggetto) funziona correttamente in **lettura**:
se un livello specifico non ha un indirizzo di un certo tipo, il fallback lo eredita dal
livello superiore. La **scrittura** avviene al livello dove serve (servizio, ruolo, soggetto).

### Idea valutata e scartata

Invertire la logica di scrittura: se scrivo un indirizzo a livello servizio e non esiste a
livello soggetto, crearlo automaticamente sul soggetto cosi' tutti i livelli lo vedono.

**Scartata perche'**:

- Effetti collaterali invisibili: altri servizi/ruoli vedono un indirizzo che non hanno chiesto
- Modifica = cascata incontrollata: toccare l'indirizzo soggetto impatta tutti i livelli
- Conflitto di ownership: chi possiede l'indirizzo? Il soggetto o il servizio che l'ha creato?

### Miglioria proposta

Quando l'operatore crea un indirizzo a livello servizio/ruolo e il soggetto **non ha ancora**
un indirizzo di quel tipo, mostrare un **suggerimento UI** (non automatico):

> "Il soggetto non ha un indirizzo di tipo [FATTURAZIONE]. Vuoi applicarlo anche al soggetto?"

L'operatore sceglie esplicitamente. Se accetta, il sistema crea l'indirizzo anche a livello
soggetto. Azione consapevole, nessun automatismo.

### Impatto tecnico

| Area | Modifica | Complessita |
|------|----------|-------------|
| **Frontend — Drawer indirizzo** | Dopo save, check se il soggetto ha gia' quel tipo | Bassa |
| **Frontend — UI** | Toast/dialog con suggerimento e bottone "Applica al soggetto" | Bassa |
| **Backend** | Nessuna modifica — usa le API esistenti per creare l'indirizzo soggetto | Nessuna |

---

## 2. Ricerca universale: modalita "Tutti i ruoli"

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
