# Design — Esito configurabile sugli step di flusso (MANUALE / AUTOMATICO / CONTESTUALE)

> **Tipo**: documento di design autorevole (lato nostro: modello + piano BE/FE).
> Il cambio schema è delegato al team DB → [brief-db-esito-configurabile-flussi.md](brief-db-esito-configurabile-flussi.md).
>
> **Data**: 2026-06-17 · **Stato**: 🟡 design concordato con Tid — DB da applicare,
> poi BE, poi FE (regola prerequisiti DB).
>
> **Origine**: review del ciclo di vita flusso durante il cantiere "pratica
> preventivi". Oggi ogni step richiede **due momenti** distinti — *generazione/avvio*
> e *registrazione esito* — anche quando l'esito è una pura formalità (pratica
> gestita internamente). Serve una **configurazione** che colassi i due momenti.

---

## 1. Problema

Uno step di flusso (`pratiche.flussi`) ha due assi indipendenti:

- **stato** (`flussi.stato_id` → `config.stati_flussi_pratiche`): DA_ESEGUIRE → IN_CORSO
  → COMPLETATO (+ SOSPESO/ANNULLATO/ERRORE);
- **esito** (`flussi.esito` ∈ POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE): colonna
  separata, **obbligatoria** al passaggio a COMPLETATO (guard DB
  `trgfn_flussi_guard_esito_completato`, errore `FLUSSI_ESITO_OBBLIGATORIO`).

Esistono già **tre automatismi**, ma nessuno configurabile:

1. step con **handler** (`template_flussi.handler_id`): `avvia_flusso` esegue l'handler
   e, se ritorna un risultato, auto-completa con esito **POSITIVO hardcoded**
   ([pratiche_service.py:401-406](../../../../backend/apps/pratiche/services/pratiche_service.py#L401-L406));
2. step di **preventivazione**: all'emissione `_completa_flusso_preventivazione`
   completa POSITIVO ([preventivi_service.py:664](../../../../backend/apps/vendite/services/preventivi_service.py#L664));
3. tutto il resto è **manuale**: `Avvia` (1 click) → form esito inline nel
   `FlussoDrawer` (select esito + note + Salva) → 2-3 click, esito scelto a mano ogni volta.

Il peso dei due momenti grava sugli step manuali (es. `RICHIESTA_CLIENTE`,
`APPROVAZIONE_CLIENTE`), che per una pratica gestita internamente sono formalità.

## 2. Modello — una sola configurazione su `template_flussi`

Due nuove colonne sul template-step:

| Colonna | Dominio | Default | Note |
|---|---|---|---|
| `modalita_esito` | `MANUALE` · `AUTOMATICO` · `CONTESTUALE` | `MANUALE` | come si ottiene l'esito |
| `esito_default` | stesso CHECK di `flussi.esito` (POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE), nullable | NULL | esito applicato/pre-selezionato |

### Comportamenti

- **MANUALE** (= oggi): `Avvia` → form esito (select + note) → `Salva`. Nessun cambio.
- **AUTOMATICO**: un'unica azione "**Avvia e completa**" porta DA_ESEGUIRE →
  COMPLETATO con `esito_default`, **senza che l'operatore scelga l'esito**.
- **CONTESTUALE**: un'unica azione avvia+completa in cui l'operatore **conferma/registra
  l'esito** (`esito_default` pre-selezionato, modificabile tra i valori ammessi) +
  note opzionali, con un solo Salva.

### Invarianti (guard DB)

1. `modalita_esito ≠ MANUALE` ⇒ `esito_default NOT NULL` (un automatismo deve sapere
   cosa scrivere).
2. `modalita_esito = AUTOMATICO` ⇒ `direzione = 'INTERNA'`. **Solo gli step a direzione
   interna possono auto-risolversi senza intervento umano**: un esito AUTOMATICO su uno
   step ENTRATA/USCITA equivarrebbe a *fabbricare* la risposta di una controparte
   esterna. `CONTESTUALE` **non** ha vincolo di direzione: un umano conferma comunque
   l'esito reale, solo in un'unica azione (nessuna perdita di fedeltà).

### Perché queste invarianti (razionale di modello)

`CONTESTUALE` è un **collasso UI** di due momenti che restano semanticamente entrambi
presenti (avvio + esito umano). `AUTOMATICO` è una **rinuncia all'esito umano**: lecita
solo dove non c'è una controparte esterna la cui risposta andrebbe attesa → `INTERNA`.
La direzione (`template_flussi.direzione`, già esistente: ENTRATA/USCITA/INTERNA) è il
segnale naturale e già modellato; non serve reintrodurre il flag `pratiche.solo_interna`
(droppato in `20260307-01`).

## 3. Applicazione al template preventivi (caso di test Tid)

Catena seedata ([20260608-08:11-16](../../../../db/changelog/migrations_v2/80_data/changelog/20260608-08-seed-template-flussi-preventivi-mctit.yaml#L11-L16)):

| Step | Direzione | Oggi | Config proposta (test) | Ammessa? |
|---|---|---|---|---|
| `RICHIESTA_CLIENTE` | ENTRATA | manuale (2-3 click) | **CONTESTUALE** (esito_default POSITIVO) | ✓ (CONTESTUALE libera) |
| `PREVENTIVAZIONE` | INTERNA | auto su emissione | MANUALE (invariato, completato dall'emissione) | n/a |
| `APPROVAZIONE_CLIENTE` | ENTRATA | manuale | CONTESTUALE (secondo banco di prova opzionale) | ✓ |
| `CONFERMA` | INTERNA | auto via handler `push_preventivo` | **AUTOMATICO** (esito_default POSITIVO) | ✓ (INTERNA) |

### Interazione con gli handler (unificazione)

`CONFERMA` ha già `handler_id=9001` (`vendita.push_preventivo`): all'avvio l'handler fa
il push e l'auto-chiusura usa **POSITIVO hardcoded**. Con il nuovo modello la
auto-chiusura legge `esito_default` (fallback POSITIVO per retro-compatibilità degli step
con handler ma senza `modalita_esito`). L'handler continua a girare; cambia solo che
**l'esito è configurato, non cablato**. Così handler-completion e `modalita_esito`
diventano lo **stesso** meccanismo dichiarativo, non due percorsi scollegati.

## 4. Piano Backend (dopo le colonne DB — non prima)

File: `apps/pratiche/services/pratiche_service.py`, `apps/pratiche/db/pratiche_repository.py`,
`apps/pratiche/api/views.py`.

1. **Proiezioni**: aggiungere `tf.modalita_esito`, `tf.esito_default` (e `tf.direzione`,
   oggi assente dal `_FLUSSO_SELECT`) a:
   - `_FLUSSO_SELECT` ([pratiche_repository.py:306-325](../../../../backend/apps/pratiche/db/pratiche_repository.py#L306-L325)) → usato da `list_flussi`/`get_flusso`;
   - `get_percorso_pratica` ([pratiche_repository.py:366-385](../../../../backend/apps/pratiche/db/pratiche_repository.py#L366-L385)) (qui `direzione` c'è già).
   Così FE e service ricevono la modalità senza round-trip extra.
2. **`avvia_flusso`** ([pratiche_service.py:380-412](../../../../backend/apps/pratiche/services/pratiche_service.py#L380-L412)):
   calcolare `auto_esito = esito_default or "POSITIVO"`. Completare (IN_CORSO→COMPLETATO,
   stessa tx) quando: (a) l'handler ha ritornato un risultato **oppure**
   (b) `modalita_esito = AUTOMATICO` (anche senza handler). Usare `auto_esito` al posto
   del POSITIVO hardcoded; `dispatch_handler_eventi(..., esito=auto_esito)`.
3. **CONTESTUALE — nuovo service** `avvia_e_completa_flusso(flusso_id, *, esito, note_esito, user)`:
   in una sola tx atomica `update_stato_flusso(IN_CORSO)` → `dispatch_handler` (per coerenza
   col percorso handler) → `update_stato_flusso(COMPLETATO, esito, note_esito)` →
   `dispatch_handler_eventi(evento="COMPLETATO", esito, user)`. Riusa il pattern
   1→2→3 già adottato da `avvia_flusso` (nessuna transizione 1→3 diretta in matrice).
4. **Endpoint** `ApiPraticaFlussoStato` ([views.py:411](../../../../backend/apps/pratiche/api/views.py#L411)):
   quando `nuovo_stato == COMPLETATO` e lo stato corrente è DA_ESEGUIRE → instradare a
   `avvia_e_completa_flusso` (oggi `completa_flusso` assume IN_CORSO). Per AUTOMATICO il
   FE chiama `nuovo_stato=IN_CORSO` (avvio) e il service auto-completa; vedi §5.
5. **Guard applicativa** in `completa_flusso`/`avvia_e_completa_flusso`: l'esito resta
   validato contro il dominio (già presente, [pratiche_service.py:432-436](../../../../backend/apps/pratiche/services/pratiche_service.py#L432-L436)).
6. **Test** service: AUTOMATICO senza handler completa con esito_default; AUTOMATICO con
   handler usa esito_default; CONTESTUALE avvia+completa atomico; MANUALE invariato;
   guard invariante 2 (AUTOMATICO su ENTRATA → errore parlante dal DB).

## 5. Piano Frontend (dopo BE)

File: `frontend/src/pratiche/components/FlussoDrawer.vue`, `PraticaPercorso.vue`,
`frontend/src/pratiche/api/pratiche-api.js`.

Il `FlussoDrawer` oggi calcola le azioni lato FE da `stato_codice_interno`
([FlussoDrawer.vue:80-94](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L80-L94)).
Estendere leggendo `flusso.modalita_esito` + `flusso.esito_default` (ora esposti):

- **MANUALE**: invariato (bottone `Avvia`; poi form esito inline su IN_CORSO).
- **AUTOMATICO**: su DA_ESEGUIRE mostrare un'unica azione "**Avvia e completa**"
  (label dedicata) → `cambiaStatoFlusso(nuovo_stato:'IN_CORSO')` (il BE auto-completa).
  Nessun form esito.
- **CONTESTUALE**: su DA_ESEGUIRE mostrare subito il form esito (select pre-impostato a
  `esito_default`, modificabile) + note + un solo `Salva` →
  `cambiaStatoFlusso(nuovo_stato:'COMPLETATO', esito, note_esito)` (il BE fa avvia+completa).
- `PraticaPercorso`: l'affordance dello step rispecchia la modalità (es. niente "due
  passi" per AUTOMATICO/CONTESTUALE).

i18n: nuove chiavi `pratiche.flusso_avvia_e_completa`, eventuale hint modalità. Nessun
testo hardcoded (frontend-standards §i18n).

## 6. Rollout / ordine

DB (2 colonne + CHECK + adattamento guard `trgfn_flussi_guard_esito_completato` per
invariante 2 a livello template; eventuale guard coerenza `esito_default`/`modalita_esito`)
→ BE (proiezioni + `avvia_flusso` + `avvia_e_completa_flusso` + endpoint + test) →
FE (FlussoDrawer/percorso + i18n). BE/FE **non** iniziano prima delle colonne.

Backfill: gli step esistenti restano `modalita_esito='MANUALE'`, `esito_default=NULL`
→ comportamento identico a oggi (nessuna regressione). La configurazione del template
preventivi (§3) è un **seed/upsert separato**, attivabile a piacere per il test.

## 7. Criteri di accettazione (end-to-end)

- Step MANUALE: comportamento odierno inalterato.
- Step AUTOMATICO (INTERNA): un click → COMPLETATO+esito_default; handler (se presente)
  eseguito; eventi a valle scattati con l'esito configurato.
- Step CONTESTUALE (qualsiasi direzione): un Salva → COMPLETATO con esito
  scelto/confermato (default pre-impostato) in un'unica transazione.
- `modalita_esito=AUTOMATICO` su step non-INTERNA → rifiutato a DB (invariante 2).
- `modalita_esito≠MANUALE` con `esito_default` NULL → rifiutato a DB (invariante 1).
- Template preventivi configurato come §3: `RICHIESTA_CLIENTE` contestuale, `CONFERMA`
  automatico, percorso completo senza i doppi passi.
