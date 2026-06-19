# Brief design — Coda lavoro operatore: pannello "Le mie attività"

> **Tipo documento**: brief design (autorevole) — **FE** (il BE esiste già).
> **Priorità**: 🟡 media — chiude l'anello dell'assegnazione flusso (consumer lato operatore).
> **Data**: 2026-06-19 · **Stato**: ✅ **IMPLEMENTATO** (FE, commit `acec053c2`, 2026-06-20)
> — presentazione decisa (pannello in alto), deliverable F1–F5 completi e criteri di
> accettazione §8 soddisfatti (ESLint + build verdi). Vedi §9 per i residui.
>
> **Origine**: lo sviluppo dell'**assegnazione flusso a operatore/reparto**
> ([brief-design-assegnazione-flusso-user-reparto.md](../work-done/brief-design-assegnazione-flusso-user-reparto.md),
> commit `a97798d40`) ha reso evidente che manca il **consumatore lato operatore**: dove
> l'operatore vede e prende i flussi che gli sono stati assegnati. Quel consumatore è la
> **coda lavoro**, oggi presente ma mal presentata (sidebar nascosta finché non cerchi).
>
> **Riferimento di visione**:
> [analisi-gestione-operativa-attivita.md](../work-in-progress/analisi-gestione-operativa-attivita.md) (agenda
> operatore/responsabile/direzione). Questo brief realizza **solo il primo tassello**: la
> coda dell'**operatore**, ben presentata nella gestione pratiche.

---

## 1. Contesto e razionale (l'anello)

Assegnazione e coda sono le due metà dello stesso anello:

```
ASSEGNAZIONE (input)                       CODA LAVORO (output)
flussi.risorsa_umana_id / unita_org_id  →  l'operatore li vede nel pannello "Le mie attività"
(appena costruito, a97798d40)              e ci entra (→ percorso pratica) per lavorarli
```

I 4 livelli della coda mappano 1:1 la policy reparto-first:

| Livello | Significato | Sorgente |
|---|---|---|
| ASSEGNATO | assegnato direttamente a me | `flussi.risorsa_umana_id = me` |
| REPARTO | instradato al mio reparto, da prendere | `flussi.unita_organizzativa_id = mio reparto anagrafico` |
| LIBERO | da assegnare (pratica mia, nessun routing) | caso C policy |
| COMPETENZA | prendibile per skill | `competenze_flussi` (avanzato, opzionale) |

## 2. Stato attuale

**Backend — completo e testato** (nessun lavoro previsto): `fn_coda_lavoro_operatore` (4
livelli) → `GET /pratiche/coda-lavoro/`; `fn_prendi_in_carico_flusso` →
`POST /pratiche/flussi/<id>/prendi-in-carico/`. Store FE già pronto (`loadCodaLavoro`,
`codaLavoro`, `codaLoading`, `prendiInCarico`). Componente `PraticheCodaLavoro.vue` esistente.

**Frontend — da rivedere**: la coda vive solo come **sidebar** di `PraticheDashboard.vue`,
mostrata **`v-if="hasSearched"`** → invisibile finché non cerchi. Nessun empty-state per
non-operatori.

## 3. Decisioni prese (2026-06-19)

- **Presentazione: pannello in alto** (collassabile, con contatori), full-width — **scelto
  per adattabilità ai piccoli schermi** (impila, niente larghezza fissa) e riuso futuro
  (home/calendario). Scartata la sidebar (richiede collasso a overlay sotto soglia mobile).
- **La coda resta nella gestione pratiche** (`/pratiche`): **non** si elimina, **non** è una
  vista isolata. È il pannello d'ingresso del workspace pratiche.
- **Click su un'attività → seleziona la pratica e mostra il percorso** (comportamento
  attuale `onCodaSelectFlusso`): è lì che si vede lo stato dei flussi e si agisce. **Niente**
  FlussoDrawer isolato dalla coda.
- **Sempre visibile**: rimosso il gate `hasSearched` per il pannello (la coda è indipendente
  dalla ricerca).
- **Livello COMPETENZA**: tenuto (sezione nascosta se vuota; resta vuoto finché non c'è
  UI/seed competenze — atteso, non bug).

## 4. Obiettivo e non-obiettivi

**Obiettivo**: l'operatore, entrando in gestione pratiche, vede **in evidenza** un pannello
"Le mie attività" con i flussi assegnati/prendibili (contatori sempre visibili), lo espande,
e cliccando un'attività entra nella pratica (percorso) per lavorarla.

**Non-obiettivi** (roadmap futura, §7): widget in **home**, **vista dedicata** a piena
pagina, **calendario** delle attività, agenda **responsabile/direzione**, UI admin
`competenze_flussi`, bilanciamento carico, notifiche scadenza.

## 5. Piano deliverable (FE)

Prerequisito: nessuno (BE pronto). Tutto frontend, basso rischio (refactor di presentazione).

| # | Deliverable | File | Note |
|---|---|---|---|
| F1 | Componente pannello collassabile | `src/pratiche/components/MieAttivitaPanel.vue` (nuovo) | Banner full-width: titolo + **contatori per livello** (badge) + toggle espandi/comprimi; in espanso rende `PraticheCodaLavoro`. Riemette `select-flusso`/`prendi-in-carico`. Riusabile (home/calendario futuri) |
| F2 | Empty-state non-operatore | (in F1) | se `auth.emittenteCorrente`/risorsa_umana assenti → "nessuna attività"; niente fetch |
| F3 | Integrazione dashboard | `src/pratiche/views/PraticheDashboard.vue` | sostituire la `<aside>` sidebar con `<MieAttivitaPanel>` in cima a `dashboard-main`, **sempre** montato (rimuovere il gate `hasSearched`); mantenere handler `onCodaSelectFlusso` (→ pratica+percorso) e `onPrendiInCarico` |
| F4 | Layout CSS | (in F3) | da flex row (sidebar+main) a colonna: pannello in alto + lista + percorso; rimuovere CSS `.dashboard-sidebar*` |
| F5 | i18n IT/EN | `src/locales/it.json`, `en.json` | titolo pannello, contatori, espandi/comprimi, empty-state; riuso label `coda_*`/`prendi_in_carico` |

> Nota: `loadCodaLavoro()` resta su `onMounted` della dashboard (già presente). Il pannello
> collassato carica comunque i contatori (serve il fetch); valutare collasso di default con
> contatori visibili.

## 6. UX del pannello

- **Collassato (default)**: barra `Le mie attività · [3 assegnate] [2 reparto] [1 da assegnare]`
  con chevron per espandere. I badge usano la severity dei livelli (danger/warn/secondary/info).
- **Espanso**: elenco per livello (sezioni di `PraticheCodaLavoro`), item = pratica + step +
  stato + scadenza. Azione per livello: ASSEGNATO → entra; COMPETENZA/REPARTO/LIBERO →
  "Prendi in carico" (poi al refresh passa ad ASSEGNATO).
- **Click item** → seleziona la pratica nella lista + carica il percorso sotto (workflow
  attuale). L'operatore lavora i flussi dal percorso/`FlussoDrawer` come oggi.
- **Empty-state**: nessuna attività / non operatore.
- **Responsive**: full-width, badge e contenuto impilano; nessuna larghezza fissa.

## 7. Roadmap futura (fuori da questo brief)

- **Home**: stesso `MieAttivitaPanel` (o `PraticheCodaLavoro`) come widget nella home.
- **Vista dedicata** "Le mie attività" a piena pagina + voce di menu (quando l'agenda cresce).
- **Calendario**: attività calendarizzate (scadenze/date previste) — vista calendario che
  riusa la stessa sorgente dati (`fn_coda_lavoro_operatore` + date flusso/pratica).
- **Agenda responsabile/direzione**: viste aggregate (analisi-gestione-operativa-attivita).
- **UI competenze**: per popolare `competenze_flussi` (abilita il livello COMPETENZA).

## 8. Criteri di accettazione

- Entrando in `/pratiche` il pannello "Le mie attività" è visibile **senza** dover cercare,
  coi contatori per livello.
- Espandendolo si vedono i flussi; un flusso assegnato all'operatore è in ASSEGNATO; uno
  instradato al suo reparto è in REPARTO ed è prendibile in carico.
- Click su un'attività → la pratica si seleziona e sotto compare il percorso.
- Utente non-operatore → empty-state, nessun errore.
- La sidebar coda non esiste più (sostituita dal pannello); la lista admin resta intatta.
- ESLint + build verdi.

## 9. Aperto / chiuso

- ✅ **`PraticheView.vue` orfano** (vecchia lista pre-dashboard, non instradata): **eliminato**
  2026-06-20 (zero referenze in `src/`, soppiantata da `PraticheDashboard.vue`).
- ✅ **Collasso di default del pannello**: adottata la proposta **chiuso** con contatori
  (non ruba spazio; l'operatore espande).
