# Design — Aggancio documento↔flusso (ROOT per-flusso, non per-pratica)

> **Tipo**: documento di design autorevole (lato nostro). Il cambio schema è
> delegato al team DB → [brief-db-aggancio-documento-flusso.md](brief-db-aggancio-documento-flusso.md).
>
> **Data**: 2026-06-16 · **Stato**: 🟦 APERTO (design approvato da Tid, in attesa DB)
>
> **Origine**: review critica del flusso pratica→preventivo (sessione 2026-06-15/16).
> Tre fragilità distinte convergono su un'unica causa di modello.

---

## 1. Problema — tre fragilità, una causa

Oggi il preventivo aperto da un flusso di pratica viene agganciato alla **pratica**
(`pratiche.pratiche_sorgenti`, `ruolo_link='ROOT'`, chiave per-pratica). Da qui tre
fragilità emerse in review:

1. **Doppio ROOT** — la chiave unica è per-pratica su `sorgente_uid`: due preventivi
   (uid diversi) possono entrambi diventare ROOT della stessa pratica. Se la
   risoluzione FE "esiste già?" fallisce in transitorio e si ricade su CREATE, si
   ottiene un secondo ROOT.
2. **Auto-completamento per ricerca** — all'emissione, per sapere *quale* flusso
   chiudere, il BE deve **cercare** il flusso della pratica con `azione_ui_key =
   APRI_PREVENTIVO` IN_CORSO. Ricerca = ambiguità (più preventivazioni) + dipendenza
   dallo stato.
3. **Caso limite "DA_ESEGUIRE"** — se all'emissione il flusso non è IN_CORSO, la
   ricerca non trova nulla e il flusso resta indietro.

**Causa comune**: il documento appartiene concettualmente al **passo di
preventivazione** (un flusso), non a tutta la pratica. Agganciandolo alla pratica si
perde la precisione e nascono le tre fragilità.

## 2. Modello — aggancio al flusso

Spostare l'ancora del legame ROOT dal livello **pratica** al livello **flusso**:
il preventivo (e in futuro offerta/contratto) è ROOT **di un flusso**.

- `pratiche.pratiche_sorgenti` acquista **`flusso_id`** (FK → `pratiche.flussi`,
  NULLABLE).
- Per i link **ROOT** generati dall'attività UI di un flusso, `flusso_id` è
  valorizzato e vincolato **unico per flusso** (max 1 ROOT per flusso).
- I link **COLLEGATO** a valle (COMMESSA/ORDINE_VENDITA dai push handler) restano con
  `flusso_id` NULL: non nascono da un'attività di flusso, non sono toccati dal vincolo.

`pratica_id` resta (utile per le query di pratica e per i COLLEGATO senza flusso): si
**aggiunge** `flusso_id`, non si sostituisce.

## 3. Come chiude i tre punti

1. **Doppio ROOT → impossibile per costruzione.** Vincolo unico "max 1 ROOT per
   flusso": il secondo aggancio viola il vincolo a DB, qualunque cosa faccia il FE.
   Non serve più il guard applicativo né il partial-unique per-pratica (proposta
   superata).
2. **Auto-completamento esatto.** Il preventivo conosce il **suo** `flusso_id`: al-
   l'emissione si completa *quel* flusso, senza cercarlo per `azione_ui_key` e senza
   ambiguità su quale preventivazione.
3. **Caso "DA_ESEGUIRE" dissolto.** Per agganciare serve un `flusso_id` esistente:
   l'apertura del documento garantisce flusso esistente **e avviato** (vedi §4) →
   all'emissione è sempre IN_CORSO. Il caso limite non si presenta.

## 4. Ciclo di vita / prerequisito

Per legare al flusso, **il flusso deve esistere ed essere avviato (IN_CORSO) quando
si apre il documento**. Oggi l'affordance "apri preventivo" può comparire su uno step
non ancora istanziato (`flusso_id` null) e il payload non porta `flusso_id`.

Nuovo invariante dell'attività UI di flusso:

> Cliccare "apri documento" su uno step **garantisce prima un flusso avviato**
> (crea+avvia se "da creare", avvia se DA_ESEGUIRE), poi apre il drawer passando il
> `flusso_id`. Il documento si lega a quel flusso al primo salvataggio.

Effetto collaterale positivo: sparisce anche l'attuale possibilità di "lavorare il
documento senza far partire il passo".

## 5. Backend (dopo la colonna DB — non prima)

- `collega_pratica(preventivo_id, *, pratica_id, flusso_id)` — aggancia ROOT al
  flusso (oltre che alla pratica). Idempotente; il vincolo DB blocca il secondo ROOT.
- **Riapertura**: `get_preventivo_id_by_flusso_root(flusso_id)` rimpiazza
  `get_preventivo_id_by_pratica_root` come fonte per l'attività UI (che ora ha il
  `flusso_id`). Il metodo per-pratica resta solo se serve a query aggregate.
- **Auto-completamento (emissione)**: da `get_pratica_id_by_preventivo_root` +
  `get_flusso_in_corso_by_azione_ui` (ricerca) a **`get_flusso_root_by_preventivo`**
  (reverse diretto): l'emissione legge il `flusso_id` del preventivo e completa
  quello. Più semplice e senza la costante `_AZIONE_UI_APRI_PREVENTIVO`.
- **Handler** `accetta_preventivo` / `push_preventivo`: ricevono già `flusso_id` →
  possono risolvere il preventivo per-flusso (più preciso del per-pratica attuale).
  Allineamento opzionale, non bloccante.

## 6. Frontend (dopo BE)

- **Percorso** ([PraticaPercorso.vue]): `onApriAttivita` include `flusso_id` nel
  payload (lo step lo conosce già). Per step "da creare"/DA_ESEGUIRE, l'host prima
  crea/avvia il flusso, poi apre l'attività.
- **Registry** ([uiActivityRegistry.js]): `resolveExisting(ctx)` risolve per
  `ctx.flussoId`; `onSaved` passa `flusso_id` a `collegaPratica`.
- **Host** ([PraticheDashboard.vue] `onOpenAttivita`): garantisce flusso avviato →
  risolve esistente per-flusso → apre edit/create.

## 7. DB — sintesi (dettaglio nel brief dedicato)

Aggiungere `flusso_id` (FK nullable) a `pratiche_sorgenti`; vincolo unico "max 1 ROOT
per flusso"; **backfill** dei 13 ROOT PREVENTIVO esistenti (flusso preventivazione
della pratica); pgTAP. *Il come è scelta del team DB.* → vedi
[brief-db-aggancio-documento-flusso.md](brief-db-aggancio-documento-flusso.md).

## 8. Rollout, retrocompatibilità, debito superato

- **Ordine**: DB (colonna+vincolo+backfill) → BE (collega/resolver/auto-completamento)
  → FE (passaggio `flusso_id` + garanzia flusso avviato). BE/FE **non** iniziano prima
  della colonna (regola prerequisiti DB).
- **Retrocompatibilità**: `flusso_id` nullable + backfill → nessuna rottura sui
  COLLEGATO; le letture per-pratica continuano a funzionare durante la transizione.
- **Superato da questo design** (rimuovere quando si esegue):
  - la proposta "partial-unique ROOT per-pratica" (review punto 1) → sostituita dal
    vincolo per-flusso;
  - la ricerca `get_flusso_in_corso_by_azione_ui` + costante
    `_AZIONE_UI_APRI_PREVENTIVO` (review punto 3) → sostituite dal reverse diretto;
  - lascia invariata la decisione **atomica** "tutto-o-niente" all'emissione (review
    punto 2, confermata da Tid): con l'aggancio esatto i fallimenti spuri spariscono.

## 9. Criteri di accettazione (end-to-end)

- Una pratica non può avere due ROOT preventivo sullo **stesso** flusso (vincolo DB).
- "Apri preventivo" su un passo riapre **il** preventivo di quel flusso (mai un nuovo
  doppione), anche con più preventivazioni nella stessa pratica.
- Emettere completa **esattamente** il flusso del preventivo, senza ricerche.
- Aprire un documento su un passo lo porta IN_CORSO: nessun "emesso ma flusso fermo".
</content>
