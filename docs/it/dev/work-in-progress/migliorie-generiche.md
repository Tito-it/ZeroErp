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

## 3. Quattro residui del cantiere «il lavoro che non torna indietro»

> Aggiunti il **2026-08-28**, archiviando
> [brief-be-fe-lavoro-che-non-torna-indietro.md](../work-done/brief-be-fe-lavoro-che-non-torna-indietro.md).
> ⛔ Nessuno dei quattro è un difetto di quel cantiere: sono cose **di altri
> perimetri** o **decisioni di prodotto**, tenute scritte perché un brief
> archiviato non è il posto dove lasciare roba viva.

### 3.1 ⏸️ Il codice errore «rientrato» nella baseline — *di chi possiede quel codice*

`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` risulta **rientrato** in
`scripts/codici-errore-baseline.sh` (verificato sul file committato
`db/baseline-codici-errore-famiglie.tsv`, riga 81).

⚠️ **Non è cosmetico**: finché la baseline non si stringe, quella famiglia resta
*dichiarata ammessa* e il presidio **non la vedrebbe tornare**. È un cancello
mezzo spento. Si chiude con `--update`, che è una **decisione** — ogni riga che
cambia dice che un codice ha cambiato significato.

### 3.2 ⏸️ Due convenzioni per `ordinamento_default` — *di chi possiede lo schema `ui`*

`clienti_default` ed `emittenti_fiscali_default` ordinano per **`campo_sorgente`**,
tutti gli altri preset per **`codice`**. Il team DB l'ha trovata e **non l'ha
chiusa di proposito**: deciderlo dentro un test significherebbe stabilire una
convenzione fuori dal cantiere che possiede le liste.

➡️ O si sceglie una convenzione e si bonifica, o si dichiara che valgono entrambe.

### 3.3 🟡 `pagina_dimensione` dichiarata e non applicata — *decisione di prodotto*

I preset delle liste della Lente 1 dichiarano `pagina_dimensione = 25`
(`dash_competenza_commesse`, `_gruppi`, `_residui`), ma il cruscotto pagina a
**10** (`PAGINATION.COMPACT_ROWS`) — liste compatte sotto le card.

Dalla correzione della paginazione del 2026-08-28 il caller vince sulla config
(vedi `frontend-standards.md`, *«una sola sorgente per `rows` e `first`»*), quindi
per quelle tre liste **il preset è dichiarato e non applicato**.

➡️ Va deciso quale dei due ha ragione: allineare il cruscotto al catalogo, o
correggere il preset a 10. ⚠️ Non è un difetto — è una divergenza fra ciò che il
catalogo dichiara e ciò che la schermata fa, ed è meglio saperlo che scoprirlo.

### 3.4 🔵 Il frontend non ha un runner di test — *debito trasversale*

Due correzioni del 2026-08-28 — il seleziona-tutto di pagina e la cascata della
paginazione — sono state provate con **script `node` usa-e-getta** sulla
reattività Vue vera: rossi prima, verdi dopo. ⛔ Ma **non girano in CI**, quindi
niente impedisce che tornino.

➡️ Se il frontend prende un runner (vitest), quelle due sono i primi casi da
portarci dentro: sono piccole, pure, e presidiano difetti che si vedevano solo a
video.

---

*ZeroERP Migliorie Generiche — avviato 25 marzo 2026*
