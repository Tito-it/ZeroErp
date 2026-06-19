# Ristrutturazione documentale — piano operativo

> **Stato:** ✅ COMPLETO (2026-06-20) — spostato in `work-done/`. Punti (a), (b.2–4),
> (c) fatti e verificati. Unico deliverable deferito: la riscrittura di `installazione.md`
> (punto b.1), in attesa della decisione Docker vs venv →
> [promemoria-installazione-md.md](../work-in-progress/promemoria-installazione-md.md).
> **Scopo:** ricondurre la documentazione generica (top-level + `dev/` + `glossario/`) e le guide
> alla forma di una "mappa" navigabile, partendo da una segnalazione esterna che proponeva un
> *developer guide* in 8 sezioni. La diagnosi: non manca documentazione (ce n'è moltissima),
> manca lo **strato sottile in cima** e ci sono **frammentazione + disallineamenti di nav**.
> **Perimetro:** SOLO parte generica e guide. NON si entra nei domini (preventivi, offerte, contratti…).

---

## 1. Diagnosi: proposta esterna vs documentazione esistente

La segnalazione proponeva un developer guide in 8 sezioni. Mappatura sullo stato reale:

| # Sezione proposta | Stato | Dove vive oggi |
|---|---|---|
| 1. Filosofia e principi | ✅ Coperto (abbondante) | `manifesto.md`, `sviluppo-concentrico.md`, `sviluppo-concentrico-vocabolario.md`, `introduzione.md`, `perche-zeroerp.md`, `.codex/PROJECT_CONTEXT.md` |
| 2. Come farlo girare | ❌ Buco più grave | `installazione.md` è uno stub di 42 righe, markdown rotto, cita `mkdocs serve` (obsoleto → zensical). `dev/backend/backend-dev.md` e `play-book-operativo-backend.md` sono infra personale (Proxmox/LXC/Tailscale). Manca la pagina "tiralo su su una macchina qualsiasi". |
| 3. Architettura a colpo d'occhio | 🟡 Parziale | `architettura.md` è uno stub di 37 righe, nessun diagramma del ciclo di richiesta, cita Redis/RabbitMQ come "opzionali". Il meccanismo RLS/GUC è documentato benissimo ma in profondità (`guide/contratto-guc-app.md`, `guide/architettura-multi-face-auth.md`), non "a colpo d'occhio". |
| 4. Anatomia di un dominio | — | Escluso dal perimetro. Le guide dominio esistono già (`guide/gestione-*.md`). |
| 5. Ricette "dove intervenire" | ❌ Mancante | Il play-book è solo comandi infra. Nessuna ricetta cross-layer (es. "aggiungi un campo end-to-end"). |
| 6. Convenzioni | ✅ Coperto bene | `linee-guida-sql.md`, `linee-guida-trigger.md`, `dev/frontend/frontend-standards.md`, `dev/api.md`, i due cataloghi Building Block, `guide/architettura-permessi-e-autorizzazioni.md`. |
| 7. Trappole | ❌ Mancante come doc | Sparso (AGENTS.md "MAI modificare changelog", immutabilità daterange). Nessun "gotchas" consolidato. |
| 8. Glossario | 🟡 Frammentato | `glossario/devops&db.md`, `glossario/process-analysis.md`, `guide/glossario/glossario-utility.md`, + vocabolario concentrico. Due cartelle diverse, termini dominio sparsi. |

**Conclusione:** ~80% riorganizzazione, ~20% documenti nuovi piccoli e connettivi.
Lo strato ADR di cui parlava la segnalazione **esiste già** ed è corretto: `dev/work-done/` (90+ file)
e `dev/work-in-progress/`, giustamente fuori dal nav.

---

## 2. Problemi strutturali trovati (da sistemare a prescindere)

Indipendenti dalla segnalazione, rompono la doc pubblicata:

1. **Link di nav rotto** — `mkdocs.yml` punta a `it/dev/frontend-standards.md`, ma il file è in `it/dev/frontend/frontend-standards.md`. La pagina "UI" degli sviluppatori è morta.
2. **Cataloghi Building Block fuori dal nav** — `dev/backend/catalogo-building-block-backend.md` e `dev/frontend/catalogo-building-block-frontend.md` non sono nel nav, eppure CLAUDE.md li impone come "prima difesa contro le duplicazioni". Invisibili nella doc pubblicata.
3. **Sezione "Sviluppatori" del nav fuori sync** — mancano `play-book`, `piano-solidita-django.md`, `provisioning-db-roles.md`, `Policy-ricerca-e-paginazione(API-DB).md`, tutta `dev/frontend/`.
4. **Glossario in 2 cartelle** — `glossario/` e `guide/glossario/`, criterio non chiaro. `glossario-utility.md` non è nemmeno nel nav.
5. **`installazione.md` e `architettura.md` sono stub** — vanno riscritti (vedi §4).

---

## 3. Piano per fasi

### Punto (a) — Fix strutturale nav + raggruppamento glossario *(IN CORSO — basso rischio, alto valore)*

Tutte modifiche **additive o di solo path**, nessuno spostamento fisico di file:

- [x] Fix link rotto: `it/dev/frontend-standards.md` → `it/dev/frontend/frontend-standards.md`
- [x] Aggiungere al nav i due cataloghi Building Block (BE + FE)
- [x] Aggiungere al nav `frontend-standards.md` come riferimento FE, `Policy-ricerca-e-paginazione(API-DB).md` (con quoting per le parentesi nel path)
- [x] Riallineare la sottosezione "Backend" del nav ai file reali (`play-book`, `piano-solidita-django`, `provisioning-db-roles`, `gunicorn-dev-autoreload`)
- [x] Raggruppare nel nav i 3 glossari sotto un'unica sezione "Glossario", **includendo** `glossario-utility.md` (oggi assente dal nav). NB: solo raggruppamento nav, NESSUNO spostamento file.
- [x] Verifica build: `python scripts/build_docs_zensical.py` → exit 0, tutte le voci risolte (warning residui solo su `dbzero/` auto-gen, preesistenti)

**Punto (a) COMPLETATO il 2026-05-29.** Modifiche in `mkdocs.yml` (sezioni "Sviluppatori" e "Glossario").

### Punto (b) — Documenti nuovi connettivi (la "mappa") *(da fare dopo)*

1. **Riscrittura `installazione.md`** → "Come farlo girare su una macchina qualsiasi": servizi + ordine di avvio, env vars, login, applica/rollback migrazione, modello branch/PR. Separare il generico riproducibile dall'infra personale (Proxmox/Tailscale resta come riferimento marcato). *Pezzo a leva più alta.*
   **➡️ DEFERITO fuori da questo piano (2026-06-20)** → tracciato in
   [promemoria-installazione-md.md](../work-in-progress/promemoria-installazione-md.md).
   Sospeso il 2026-05-29 per decisione utente (aspettare): orientamento verso **Docker**
   ma non deciso, e stato del setup non chiaro. Stato reale rilevato: venv + `makefile`
   (target `db-migrate`/`db-setup` per Liquibase), `Dockerfile` per la CI (con librerie
   WeasyPrint), **nessun `docker-compose` dev**, modello a due server (DB + backend).
   Prossimo passo: auditare il setup attuale → decidere Docker vs venv → scrivere la pagina.
2. **[x] Riscrittura `architettura.md`** (2026-05-29) → "Architettura a colpo d'occhio": regola DB-first, tabella strati, diagramma mermaid del ciclo di richiesta, mezza pagina RLS/GUC in linguaggio semplice che **linka** (non duplica) multi-face/contratto-GUC/permessi. Già nel nav.
3. **[x] Nuovo "Ricette: dove intervenire per…"** (2026-05-29) → `dev/ricette-dove-intervenire.md`, nel nav. 3 ricette in sequenza DB→BE→FE: aggiungere un campo, aggiungere uno stato (data-driven), creare un nuovo dominio tracciato. Linka convenzioni/BB, non duplica.
4. **[x] Nuovo "Trappole"** → `dev/trappole.md` creato (2026-05-29), aggiunto al nav sotto "Sviluppatori", linguaggio non-tecnico. Consolidamento delle mine già pagate: delete head branches/`Tito-dev`, changelog Liquibase immutabili, periodi validità calcolati, indici FK, campi audit, codici errore, guard restrittivi, no logica business nel BE, no duplicazioni FE, dipendenze con conferma.

### Punto (c) — Unificazione fisica glossario *(COMPLETATO 2026-05-29)*

Decisioni §5 prese: **(1) unificare fisicamente; (2) termini dominio sulla stessa pagina; (3) Trappole = doc unico centrale; (4) `installazione.md` per ultimo, in attesa di decisione utente.**

- [x] `git mv guide/glossario/glossario-utility.md → glossario/glossario-utility.md`; rimossa cartella `guide/glossario/` vuota
- [x] Aggiornati i 6 link entranti attivi (`/guide/glossario/glossario-utility` → `/glossario/glossario-utility`). Lasciati intatti i riferimenti storici in `dev/work-done/` (record point-in-time)
- [x] Nav: i 3 glossari raggruppati; voce rinominata "Glossario di dominio"
- [x] Pagina estesa: titolo → "Glossario di dominio", sezione "Termini del settore utility" + nuova sezione "Termini di dominio ZeroERP" (commessa, preventivo, offerta, contratto, listino, emittente, emittente fiscale, fatturazione, lotto, pratica/flusso)
- [x] Linguaggio: riscritto in forma **comprensibile anche ai non tecnici** (no nomi funzioni/tabelle/vincoli nel testo dei termini di dominio)
- [x] Build zensical exit 0

> ⚠️ **Da validare con l'utente (esperto di dominio):** definizioni di **offerta commerciale**, **emittente** ed **emittente fiscale** — scritte in forma conservativa perché la doc pubblicata è ancora scarsa (solo analisi WIP).

---

## 4. Cosa NON tocchiamo

- I domini e le loro guide (`guide/gestione-*.md`).
- La doc auto-generata `dbzero/<schema>/` e `backend/<area>/`.
- `dev/work-done/` e `dev/work-in-progress/` (strato ADR, correttamente fuori nav).
- I changelog Liquibase già mergiati.

---

## 5. Decisioni da prendere insieme

1. **Unificazione fisica glossario (punto c):** `guide/glossario/glossario-utility.md` ha **link entranti da 7 file** (`guide/soggetti-e-ruoli-anagrafici.md`, `guide/gestione-delle-istanze-utility.md`, `guide/generazione-cliente.md`, `dbzero/anagrafiche/manual/catasto-architettura.md`, `dbzero/anagrafiche/manual/billing_account.md`, `dbzero/script/manual/fn_subentro_cliente.md`, `dev/work-done/...`). Spostarlo in `glossario/` impone di aggiornare tutti i link. **Da decidere:** lo spostiamo (con aggiornamento link) o lasciamo i file dove sono e unifichiamo solo logicamente nel nav? *(Nel punto (a) si fa solo nav.)*

2. **Glossario dominio:** i termini utility esistono (`glossario-utility.md`). Mancano i termini ZeroERP non-utility (commessa, preventivo, offerta, listino, pratica, emittente, billing account come concetto applicativo). **Da decidere:** pagina unica "Glossario di dominio" o estensione del glossario utility?

3. **Sezione "Trappole":** doc unico generico, oppure una sezione "trappole" in coda a ciascuna guida pertinente? **Da decidere:** mappa centrale vs distribuzione.

4. **`installazione.md` riproducibile:** confermare che il target è "macchina singola qualsiasi" (Docker? venv puro? entrambi?) prima di riscriverla.

---

## 6. Log avanzamento

- 2026-05-29 — Creato il documento. Diagnosi completata. Avvio punto (a).
- 2026-05-29 — Punto (a) completato: fix nav `mkdocs.yml` (link `frontend-standards` riparato, 2 cataloghi BB + Policy ricerca/paginazione + frontend-standards aggiunti, sottosezione Backend riallineata, 3 glossari raggruppati con `glossario-utility`). Build zensical exit 0.
- 2026-06-20 — Piano **CHIUSO** e spostato in `work-done/`. Punti (a), (b.2–4), (c) completati e verificati contro i file reali. Unico residuo — riscrittura `installazione.md` (b.1) — **deferito** a [promemoria-installazione-md.md](../work-in-progress/promemoria-installazione-md.md), in attesa della decisione Docker vs venv. Rimosse due righe spurie in fondo al file (`</content>`/`</invoke>`).
