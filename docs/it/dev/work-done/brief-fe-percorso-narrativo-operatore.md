# Brief FE — Il Percorso pratica da grafo-macchina a racconto operatore

> **Tipo**: brief FE (design → implementazione) · **Data**: 2026-07-01
> **Owner**: Tid · **Stato**: 🟢 implementazione completa (2026-07-01): **B1-B5 fatti** (Strato A lessico + vista-racconto + esiti globali data-driven + modalità tecnica ADMIN); BE percorso/flusso con display fields; brief DB coda consegnato. **Resta solo la verifica in-app** su PREVENTIVI prima di estendere ad altri tipi pratica.
>
> **Review critica 2026-07-02** — bug trovati e corretti sull'implementato:
> **(a)** B3b era **rotto**: `config.esiti_flussi_pratiche` mancava dalla whitelist
> lookup BE → Select esiti sempre vuoto, completamento manuale impossibile
> (errore inghiottito dal catch silente). Whitelist corretta; scoperto in cascata
> che il vocabolario espone anche gli **esiti di ramo** (`MERCE_PRESENTE`/
> `SOLO_SERVIZI`, mai input utente) → guard BE interim
> `require_esito_selezionabile_operatore` + discriminatore a DB richiesto con
> [brief-db-esiti-flussi-selezionabilita.md](brief-db-esiti-flussi-selezionabilita.md).
> **(b)** B1, fasce: un'istanza **aperta** (DA_ESEGUIRE/IN_CORSO/SOSPESO) ora va
> SEMPRE in ADESSO anche con `ramo` COMPLETATO (ripetizione in corso) o
> RAMO_CHIUSO (lavoro avviato prima del bivio): prima spariva dalla vista
> operatore. **(c)** B1, card ADESSO: aggiunti "Ripeti" (istanza ANNULLATO/ERRORE
> ripetibile) e l'azione generica "Apri" accanto all'affordance di dominio
> (prima mutuamente esclusive: il drawer del passo era irraggiungibile per gli
> step con documento). **(d)** pulizie: chiavi i18n orfane rimosse, commenti
> stantii "B5 arriverà" aggiornati, check verde via `--app-success-color`.
>
> **Origine**: voce **V1** di
> [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md)
> (Problema 1 — comprensibilità operatore), con **misura** delle superfici FE reali
> fatta il 2026-07-01. Principio guida ereditato da
> [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md):
> *la pratica non deve divergere dal programma standalone.*
>
> **Documenti collegati**: [Guida Gestione Pratiche §Flusso](../../guide/gestione-pratiche.md#flusso),
> [Gestione Pratiche — Configurazione](../../guide/gestione-pratiche-configurazione.md).

---

## 1. Problema (misurato)

Il vocabolario da motore **trapela verso l'operatore**, in modo concentrato e
prevedibile, e **peggiora con la profondità**: la superficie d'ingresso è quasi pulita,
la vista che dovrebbe essere il *racconto* (il Percorso) è la più leaky. Scorecard con
evidenze puntuali:

| Superficie | Voto | Perdite principali |
|---|---|---|
| **"Le mie attività"** ([MieAttivitaPanel.vue](../../../../frontend/src/pratiche/components/MieAttivitaPanel.vue)) | 🟢 buono | Livelli coda tradotti in intento (`COMPETENZA → "Da prendere"`, `LIBERO → "Da assegnare"`). Unico neo: la barra dice *"attività"*, il contenuto sotto dice *"flusso"* → **due parole per la stessa cosa**. |
| **Coda lavoro** ([PraticheCodaLavoro.vue](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue)) | 🟡 misto | Riga: **codice grezzo prima** della descrizione (`template_flusso_codice \|\| template_flusso_desc`, [L78](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L78)); stato = codice (`stato_flusso_codice`, [L80](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L80)); empty = *"Nessun **flusso** in coda"*. |
| **Percorso** ([PraticaPercorso.vue](../../../../frontend/src/pratiche/components/PraticaPercorso.vue)) | 🔴 il più leaky | **Titolo di ogni step = codice template grezzo** (`RICHIESTA_CLIENTE`…, [L124](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L124)); stato = `stato_codice_interno` ([L59-61](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L59-L61)); numero di **sequenza** (`#{{ step.sequenza }}`, [L120](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L120)); esito grezzo (*"Esito: POSITIVO"*, [L131-133](../../../../frontend/src/pratiche/components/PraticaPercorso.vue#L131-L133)); tooltip con la parola **"handler"** (`percorso_handler = "Step automatico (handler)"`). |
| **FlussoDrawer** ([FlussoDrawer.vue](../../../../frontend/src/pratiche/components/FlussoDrawer.vue)) | 🟠 testata leaky, corpo ok | Titolo *"**Esecuzione flusso** — APPROVAZIONE_CLIENTE"* ([L258-262](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L258-L262)), icona `pi-sitemap`; campo etichettato *"**Template**"* ([L289](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L289)); stato grezzo. **Corpo buono**: esiti umanizzati, "Reparto"/"Operatore" puliti, affordance *"Apri preventivo"*. |

**Il filo conduttore (rende il fix economico):** ogni tabella-vocabolario del motore ha
già una colonna **`descrizione`** pensata per l'occhio umano — verificato su
[`config.stati_flussi_pratiche`](../../dbzero/config/tabelle/stati_flussi_pratiche.md)
(`NOT NULL`), su `template_flussi.descrizione` (*"etichetta leggibile mostrata in UI"*) e
sulla nuova `config.esiti_flussi_pratiche.descrizione`. Il FE però renderizza
**`codice`/`codice_interno`** in posizione di titolo. **L'etichetta umana esiste nel dato
e non viene pescata.**

**La perdita più profonda (non lessicale):** anche traducendo ogni parola, resta il
problema vero — **il Percorso espone il modello di configurazione, non il compito.**
Mostra tutti gli step possibili, inclusi quelli *"Da creare"* (futuri) e i *"Rami chiusi"*
(bivio non preso), con i loro stati-macchina. È la mappa del template, non «cosa devo
fare adesso».

---

## 2. Principio

1. **L'operatore non deve mai vedere «il flusso».** *Flusso, template, prerequisito,
   sequenza, handler, direzione, modalità esito* sono plumbing: mai a video per un
   operatore. (Una modalità "tecnica/avanzata" per super-admin è ammessa — §6.)
2. **La vista è un racconto con l'azione del momento in evidenza.** «Sei qui → il
   prossimo passo è questo → [un pulsante]». Di norma il passo attivo è uno, ma il modello
   ammette rami paralleli e ripetizione (`ripetibile_adesso`): la vista regge **1..N passi
   attivi**, non ne assume esattamente uno. Il grafo, i rami morti e gli stati-macchina
   restano nel motore, non a video.
3. **Uniformità con lo standalone.** Il pulsante attivo apre *le stesse schermate* che
   l'operatore già conosce (già vero per l'affordance "Apri documento"): la pratica
   *orchestra*, non reinventa.
4. **Nessuna logica di business nel FE.** Le regole (prerequisiti esito-aware,
   ripetibilità, rami) restano a DB con **errore parlante**; il FE non le duplica.

---

## 3. Il fix in due strati

### 3.1 Strato A — Lessico + fonte-dato (il 70% economico)

Chiude gran parte della perdita **lessicale** senza toccare il motore. Due mosse:

**(a) Renderizzare `descrizione`, non `codice`.** Superficie per superficie:

| Superficie | Oggi renderizza | Deve renderizzare | Dipendenza |
|---|---|---|---|
| Percorso — titolo step | `template_flusso_codice` | `template_flusso_descrizione` | display field già presente sul flusso (usato nel drawer); da esporre anche nel payload percorso |
| Percorso / Coda / Drawer — stato | `stato_codice_interno` / `stato_flusso_codice` | `stato_*_descrizione` | **BE**: esporre display field `stato_descrizione` dove manca |
| Percorso — esito | `step.esito` (grezzo) | `esito_descrizione` | **BE**: display field da `config.esiti_flussi_pratiche.descrizione`. ⚠️ **Decisione §7.4**: data-driven anche in *scrittura* — il `Select` esiti di [FlussoDrawer.vue:43-48](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L43-L48) (oggi 4 valori hardcodati in i18n) sorge dagli esiti ammessi **per template**, non solo la `descrizione` in lettura |
| Coda — riga | codice-first | `descrizione`-first (invertire il fallback) | display field già disponibile |

**(b) i18n — togliere il gergo dalle superfici operatore:**

- `coda_vuota`: *"Nessun flusso in coda"* → *"Nessuna attività in coda"*;
- allineare a **una sola parola**: "attività" (non "flusso") ovunque l'operatore legga
  (`flusso_esecuzione`, `flusso_generico`, `flusso_avvia`, `flusso_col_template`,
  `percorso_handler`…);
- `flusso_col_template` *"Template"* → rimuovere dalla vista operatore (resta in modalità
  tecnica);
- `percorso_handler` *"Step automatico (handler)"* → *"Passo automatico"* (via l'"handler");
- valutare `pi-sitemap` → un'icona meno "organigramma" nel titolo del drawer.

> Nota: i **numeri di documento** (`PRA-0000216`, il numero preventivo) **restano**:
> gli operatori vivono coi numeri di documento; non sono gergo.

### 3.2 Strato B — La vista-racconto (il 30% strutturale) — **cuore del brief**

Il Percorso smette di essere la mappa del template e diventa il **viaggio della pratica**.

**Cosa nascondere** (resta nel motore, non a video per l'operatore):
- gli step **futuri "Da creare"** come card cliccabili in fila (il percorso condizionale
  non è ancora deciso: mostrarli tutti confonde);
- i **rami chiusi** (`RAMO_CHIUSO`): semplicemente non compaiono;
- gli **stati-macchina** grezzi e il **numero di sequenza**;
- la distinzione template/istanza (`flusso_id` null vs valorizzato): è un dettaglio
  implementativo.

**Cosa mostrare:**
- **il passo attivo** (di norma uno; **1..N** con rami paralleli o step ripetibile), in
  grande, con **una azione primaria** ("Fai il preventivo", "Conferma col cliente", "Avvia
  e completa") — riusando `modalita_esito` per collassare i click come già fa il motore;
- **dove si è nel viaggio**, in forma leggera e leggibile: passi *fatti* (✓, con la loro
  `descrizione`), passo *corrente*, e — se serve — «poi mancherà…» come **testo**, non come
  griglia di card cliccabili;
- il resto (esito registrato, chi è assegnato, tempi/SLA) come **contorno**, non come
  protagonista.

**Regole di comportamento invariate** (nessuna logica nel FE): cliccare qualcosa non
ancora percorribile continua a produrre l'**errore parlante del DB** (i prerequisiti
esito-aware restano l'unica fonte di verità); la ripetibilità di uno step continua a
venire dal flag `ripetibile_adesso` calcolato dal DB.

---

## 4. Sketch (prima → dopo)

**Oggi — Percorso = debugger:**

```text
Percorso
[#0 RICHIESTA_CLIENTE  (COMPLETATO)] → [#10 PREVENTIVAZIONE (IN_CORSO)] →
[#20 APPROVAZIONE_CLIENTE (Da creare)] → [#30 CONFERMA (Ramo chiuso)]
                                          Esito: POSITIVO   ⚡(handler)
```

**Dopo — Percorso = racconto:**

```text
Preventivo per Mario Rossi · PRA-0000216

  ✓ Richiesta registrata
  ▶ ADESSO: Fai il preventivo            [ Apri preventivo ]
    · poi: conferma col cliente, poi invio a valle

  (assegnato a te · reparto Commerciale · in tempo)
```

La stessa informazione, ma l'operatore legge **cosa ha fatto**, **cosa deve fare ora** e
**un pulsante** — non un grafo con stati-macchina e rami morti.

---

## 5. Deliverable FE (+ prerequisiti BE)

**BE (prerequisiti):**

- *Display field (piccolo, no logica)*: esporre nel payload di **percorso** e **coda** i
  `*_descrizione` per template step, stato ed esito (leggendo le colonne `descrizione` già
  esistenti).
- *Esiti data-driven (§7.4)*: esporre gli **esiti ammessi per template** (codice +
  `descrizione`) per alimentare il `Select` di FlussoDrawer, non più i 4 valori hardcodati.
  Se `config.esiti_flussi_pratiche` non ha già il binding template↔esiti → **brief al team
  DB** (view/funzione), non azione dall'agente.
- *Futuro certo-vs-condizionale (§7.2)*: per rendere "poi…" come testo troncato al primo
  bivio, il payload percorso deve marcare quali step futuri sono sul **percorso certo** vs
  **oltre un bivio non deciso**. Oggi c'è solo `RAMO_CHIUSO`; se il segnale non esiste →
  aggiungerlo (BE/DB) oppure il "poi…" degrada al solo prossimo step.

**FE:**

- **B1** — `PraticaPercorso.vue`: riprogettazione vista-racconto (§3.2 + §4): tre fasce
  **Fatti / Adesso (1..N) / Poi (testo)**; rimozione card "Da creare"/"Ramo chiuso" dalla
  vista operatore; "poi…" troncato al primo bivio (§7.2); render `descrizione`. Il
  rendering tecnico attuale **non si cancella**: diventa il ramo "modalità tecnica"
  gateato (B5).
- **B2** — `PraticheCodaLavoro.vue`: `descrizione`-first, stato via `descrizione`, empty
  "attività".
- **B3** — `FlussoDrawer.vue`: titolo senza "flusso"/codice grezzo (usare `descrizione` +
  contesto pratica), rimuovere il campo "Template" dalla vista operatore, stato via
  `descrizione`; `Select` esiti data-driven per-template (§7.4), non più i 4 valori
  hardcodati.
- **B4** — i18n `it.json`/`en.json`: unificare "attività", ripulire le chiavi gergo (§3.1b).
- **B5** — **(in-scope, §7.3)** toggle **modalità tecnica** per super-admin che ri-espone
  codici, sequenza, stati-macchina, rami (§6). Gate su **permesso reale** (super-admin,
  modello permessi v3), non flag libero; `modalitaTecnica` iniettato via `provide` e letto
  da `PraticaPercorso`/`FlussoDrawer`.

---

## 6. Vincoli e non-obiettivi

- **Non si tocca il motore** (DB/trigger/macchina a stati). Solo FE + display fields BE.
- **Nessuna regola nel FE**: prerequisiti/ripetibilità/rami restano a DB (errore parlante).
- **Modalità tecnica (in-scope, §7.3)**: per super-admin/diagnostica ri-mostra
  codici/sequenza/stati/rami — **opt-in gateato su permesso**, mai il default dell'operatore.
- **Non è l'ispettore di configurazione** (voce V4/V5 dell'analisi): questa è la vista
  *runtime* dell'operatore, non l'editor del workflow. Sono due lavori distinti.

---

## 7. Decisioni chiuse (2026-07-01)

Le tre domande aperte sono state chiuse dall'owner; si aggiunge una 4ª emersa in analisi
(esiti data-driven anche in scrittura).

1. **Quanto "viaggio" mostrare?** → ✅ **Fatti + adesso + "poi…"**. Tre fasce: passi
   *fatti* (✓ compatti, con `descrizione`), *adesso* (**1..N** card azione, non una sola),
   *poi* (testo). Vedi §3.2/§4.
2. **Rami condizionali** → ✅ **Ometti fino a percorribile**. Rami chiusi spariti; il
   "poi…" si tronca al primo bivio non deciso. Richiede segnale BE certo-vs-condizionale
   (§5) o, in mancanza, degrado al solo prossimo step.
3. **Modalità tecnica (B5)** → ✅ **Costruita ora**, non rimandata. In-scope con B1;
   gateata su permesso super-admin (§5, §6). *(Override della proposta iniziale di
   rimandare.)*
4. **Esiti data-driven** *(emersa in analisi)* → ✅ **Sì**. Non solo la `esito_descrizione`
   in lettura: anche il `Select` esiti di FlussoDrawer (oggi 4 valori hardcodati) diventa
   data-driven (§3.1, §5). ⚠️ **La ricognizione ha stabilito che gli esiti sono globali, non
   per-template** (nessun binding a DB): la variante "per template" va ridefinita → **§9**.

**Stato**: decisioni chiuse → **si attende completamento prerequisiti BE/DB (§5)** prima di
aprire l'implementazione B1→B5. Validazione su PREVENTIVI prima di estendere ad altri tipi
pratica.

---

## 8. Piano di sviluppo

Due vincoli guidano l'ordine: **(a)** i prerequisiti BE/DB gattano il FE — il FE non
parte finché i dati non ci sono (memoria `feedback_be_fe_attende_prerequisiti_db`); **(b)**
lo **Strato A** (lessico, §3.1) dipende solo dai display field ed è indipendente dallo
**Strato B** (racconto, §3.2): si spedisce prima, per valore immediato e a rischio basso.

> Convenzioni FE vincolanti per tutte le fasi (da `frontend-standards.md`): nessun testo
> hardcoded (tutto `$t()`), severity dai building block `statoFlussoSeverity`/
> `esitoFlussoSeverity`, azioni drawer via `DrawerActionsBar`, sola-lettura via
> `useReadonlyMode`. La modalità tecnica (§6) si modella come **mirror** di
> `useReadonlyMode` (provider/consumer con `provide`/`inject`), non come flag sparso.

### Fase 0 — Prerequisiti BE/DB (gate) — ✅ ricognizione fatta 2026-07-01

Esito della ricognizione BE/DB (payload percorso/coda/flusso + modello esiti). Riferimenti:
`backend/apps/pratiche/db/pratiche_repository.py` (percorso `get_percorso_pratica`, flusso
`get_flusso`), `fn_coda_lavoro_operatore` (funzione DB, coda),
`config.esiti_flussi_pratiche`, `pratiche.template_flussi`.

**P0.1 — Display field `*_descrizione`** — parzialmente pronto, **misto BE-puro / DB**:

- **Percorso** (query SQL in Python): `template_flusso_descrizione` ✅ già esposto;
  `stato_descrizione` ❌ e `esito_descrizione` ❌ mancanti → **BE puro** (aggiungere
  `sf.descrizione` sul join già presente + join a `config.esiti_flussi_pratiche` su
  `f.esito`). Agent-doable, niente team DB.
- **Flusso dettaglio** (`get_flusso`): `stato_descrizione` ✅, `template_flusso_descrizione`
  ✅, `esito_default` ✅. **Completo**.
- **Coda** (`fn_coda_lavoro_operatore`, **funzione DB**): `template_flusso_desc` ✅;
  `stato_flusso_descrizione` aggiunta dal team DB con migration **20260701-11** su richiesta
  del [brief-db-coda-lavoro-descrizione-stato.md](../work-done/brief-db-coda-lavoro-descrizione-stato.md)
  → ✅ **CONSEGNATO**. ⚠️ **Correzione alla ricognizione**: avevo introspezionato la fn dal
  file di migration **stantio** `20260614-02` invece che dalla versione **viva** `20260628-07`
  (violazione `feedback_db_doc_first`). Sulla versione viva **non esiste** alcun bug severity:
  il campo logico è `stato_flusso_codice_interno` (già usato, corretto), `stato_flusso_codice`
  è il codice **display**. Contratto reale della fn: `stato_flusso_codice_interno` +
  `stato_flusso_codice` + `stato_flusso_descrizione`.

**P0.2 — Esiti data-driven** — ⚠️ **il modello contraddice l'assunzione "per template"**:

- `config.esiti_flussi_pratiche` ha `descrizione` NOT NULL ✅, con 4 esiti strutturali +
  esiti di **dominio** seedati per ramo (vendite ecc.).
- **NON esiste** alcuna tabella di binding template↔esiti-ammessi: gli esiti sono
  **globali/universali** (ogni template può chiudersi con qualsiasi esito). `template_flussi`
  dichiara solo `esito_default`.
- Conseguenza: il "per template" della decisione §7.4 **non è supportato dal modello
  attuale** → ridefinizione su due opzioni A/B in **§9**.

**P0.3 — Segnale certo-vs-condizionale** — parzialmente pronto:

- Il percorso espone già `ramo` ∈ {COMPLETATO, PERCORRIBILE, RAMO_CHIUSO, FUTURO} ✅.
- `RAMO_CHIUSO` = bivio non preso → **ometti** (soddisfa §7.2); `FUTURO` = step a valle →
  materiale per il "poi…".
- **Manca** un flag esplicito "oltre-bivio": con più step `FUTURO` non si distingue il ramo
  lineare da una biforcazione aperta. → il "poi…" **oggi** si costruisce elencando gli step
  `FUTURO` come testo (o solo il prossimo); la troncatura precisa al bivio è un **refinement
  opzionale** = brief DB.

**P0.4 — Gate permesso modalità tecnica** — ❌ da decidere (owner + eventuale seed):
codename dedicato (es. `pratiche_vista_tecnica`) vs riuso `RUOLO_SISTEMA.ADMIN`. Decisione di
modello, vedi §9.

**Uscita Fase 0 (aggiornata)**: la **Fase 1** può partire SUBITO per **percorso** (BE puro)
e **flusso** (già completo); la parte **coda** richiede un breve **brief DB** (descrizione
stato + verifica severity). **P0.2** attende la decisione §9 (A/B). **P0.3** usa il fallback
oggi. **P0.4** attende decisione owner.

### Fase 1 — Strato A: lessico (dipende da P0.1)

- **B2 — `PraticheCodaLavoro.vue`**: riga `descrizione`-first (invertire il fallback a
  [L78](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L78)); `Tag`
  stato con *value* = `stato_flusso_descrizione || stato_flusso_codice`, severity via
  `statoFlussoSeverity(stato_flusso_codice_interno)` (**invariata**: il campo logico esiste
  ed era già corretto — vedi la correzione della ricognizione in Fase 0,
  [L80](../../../../frontend/src/pratiche/components/PraticheCodaLavoro.vue#L80)); empty via
  i18n. ✅ **fatto** — descrizione stato consegnata da 20260701-11.
- **B3a — `FlussoDrawer.vue` (parte lessicale)**: `DrawerTitle` con titolo da `descrizione`
  e contesto pratica invece del codice grezzo
  ([L258-262](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L258-L262));
  rimuovere il campo "Template"
  ([L288-291](../../../../frontend/src/pratiche/components/FlussoDrawer.vue#L288-L291))
  dalla vista operatore (torna in modalità tecnica, Fase 3); `Tag` stato via descrizione;
  valutare icona meno "organigramma" al posto di `pi-sitemap`.
- **B4 — i18n `it.json`/`en.json`**: `coda_vuota` → "Nessuna attività in coda"; una sola
  parola "attività" (mai "flusso"); `percorso_handler` → "Passo automatico" (via "handler");
  espungere "Template"/"flusso"/"handler" dalle superfici operatore.

**Acceptance F1**: su coda e testata drawer un operatore non legge codici grezzi né gergo;
comportamento invariato.

### Fase 2 — Strato B: la vista-racconto (dipende da P0.1; arricchita da P0.3)

- **B1 — `PraticaPercorso.vue`**: riscrittura in tre fasce (§3.2/§4):
  - **Fatti** — lista compatta ✓ con `template_flusso_descrizione`; niente sequenza né
    stato-macchina.
  - **Adesso (1..N)** — card grande per **ogni** step attivo (istanza `IN_CORSO`/
    `DA_ESEGUIRE`, o `COMPLETATO` con `ripetibile_adesso`) con **una** azione primaria.
    **Si riusa la logica esistente** (`uiActivityFor`, emit `open-attivita`/`open-flusso`/
    `create-flusso`) → uniformità con lo standalone; `modalita_esito` collassa i click come
    già fa il motore.
  - **Poi** — testo troncato al primo bivio (P0.3), oppure solo prossimo step lineare
    (fallback).
  - **Nascondere** le card "Da creare" future e gli step `RAMO_CHIUSO`.
  - Il rendering attuale (codici/sequenza/stati/rami) **non si cancella**: si isola dietro
    il flag `modalitaTecnica` (Fase 3).
  - Regole **invariate**: click non percorribile → errore parlante DB; `ripetibile_adesso`
    deciso dal DB. Nessuna regola di business nel FE (§2.4).
  - ✅ **Implementato 2026-07-01**: fasce derivate dal `ramo`
    (COMPLETATO→Fatti, PERCORRIBILE→Adesso 1..N, FUTURO→Poi testo), `RAMO_CHIUSO` nascosto;
    esito via `esito_descrizione`, stato via `stato_descrizione`. Emit verso il parent
    invariati (`open-flusso`/`create-flusso`/`open-attivita`). Il rendering tecnico è
    **preservato e isolato** dietro `useInjectTechnicalMode()` (`core/composables/useTechnicalMode.js`,
    default `false`) → resta **B5**: provider + toggle ADMIN nella detail pratica.

> Nota architetturale (memoria `feedback_regola_del_2_estrai_bb` + `feedback_concentrico_no_yagni`):
> tenere le tre fasce **dentro** `PraticaPercorso.vue`; estrarre sotto-componenti solo alla
> 2ª occorrenza reale — niente astrazione prematura.

**Acceptance F2**: l'operatore legge fatti / adesso / poi + un pulsante; nessun grafo,
nessuno stato-macchina, nessun ramo morto a video.

### Fase 3 — Modalità tecnica + esiti data-driven

- **B3b — Esiti data-driven** (§9.1 opzione **A**): sostituiti gli `esitiOptions` hardcodati
  con la lista **globale attiva** di `config.esiti_flussi_pratiche` (`codice_interno` +
  `descrizione`) via `lookupCodici` + `useGlobalLookup` (cache modulo-level); render esito
  registrato via `esito_descrizione` (esposto ora anche da `get_flusso`/`list_flussi`, BE).
  `esitoFlussoSeverity` invariata. Nessun filtro per-template (coerente col modello).
  ✅ **fatto 2026-07-01**.
- **B5 — Modalità tecnica** (§9.2): provider `provideTechnicalMode` (mirror di
  `useReadonlyMode`) montato in `PraticheDashboard`, con toggle visibile solo se
  **`auth.isSuperAdmin`** (realizzazione concreta di "super-admin/ADMIN" nel modello
  permessi di questo codebase). `PraticaPercorso` (ramo tecnico) e `FlussoDrawer` (campo
  "Template" + codice) iniettano il flag e **ri-mostrano** il plumbing quando attivo.
  **Default off**, nessun seed DB. ✅ **fatto 2026-07-01**.

**Acceptance F3**: il super-admin ri-vede tutto il plumbing con un toggle; l'operatore no.

### Validazione e chiusura

Validazione **E2E su un tipo pratica PREVENTIVI** (coda → percorso → drawer → completamento
con esito) prima di estendere ad altri tipi. A chiusura: aggiornare lo stato in testa e la
riga V1 di [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md).

**Sequenza consigliata**: P0.1 → Fase 1 (valore subito, rischio basso) → P0.3 → Fase 2 →
P0.2/P0.4 → Fase 3. Le fasi 1 e 2 sono indipendenti: parallelizzabili se P0.1 è pronto.

---

## 9. Decisioni aperte post-ricognizione (2026-07-01)

La ricognizione di Fase 0 ha fatto emergere due punti risolti dall'owner il 2026-07-01.

### 9.1 Esiti: lista globale vs binding per-template → ✅ **A (globale)**

Il modello rende gli esiti **globali** (nessun binding template↔esiti). La decisione §7.4
si ridefinisce su:

- **A — Lista globale data-driven** *(raccomandata, BE puro)*: il `Select` di FlussoDrawer e
  il render esito sorgono dall'elenco **globale attivo** di `config.esiti_flussi_pratiche`
  (`codice_interno` + `descrizione`). Colma la perdita reale — gli esiti di **dominio** non
  sono hardcodabili in i18n — e mostra tutti gli esiti validi. Nessuna DDL: lookup BE
  (whitelist + `lookupCodici`, `feedback_lookup_whitelist_first`). Non filtra per template
  (coerente col modello).
- **B — Binding per-template** *(estende il modello, DB)*: nuova tabella/relazione
  `template_flussi ↔ esiti_ammessi` per restringere gli esiti per template. Soddisfa la
  lettera del §7.4 ma richiede **modello + brief team DB**, e va motivata da un bisogno reale
  (oggi assente: nessun template vieta esiti).

Raccomandazione: **A** ora; **B** solo se emerge un template che deve vietare certi esiti.
**→ Deciso: A.** B3b usa la lista globale attiva di `config.esiti_flussi_pratiche` via
lookup BE; niente per-template.

### 9.2 Gate della modalità tecnica (B5) → ✅ **`RUOLO_SISTEMA.ADMIN`**

Il gate di P0.4 va deciso: **codename di processo dedicato** (es. `pratiche_vista_tecnica`,
seed permesso a DB, granulare) **oppure** riuso di **`RUOLO_SISTEMA.ADMIN`** (immediato, già
in `auth`, nessun DB). Trade-off: granularità/seed vs semplicità/subito. **→ Deciso:
`RUOLO_SISTEMA.ADMIN`** — nessun seed DB; il toggle modalità tecnica è visibile solo agli
ADMIN. Rivalutare un permesso dedicato solo se serve granularità futura.
> **Realizzazione**: in codice il gate è `auth.isSuperAdmin` (profilo SUPER_ADMIN id 9100),
> il concetto di "admin/super-admin" già esposto dall'auth store — non esiste un flag
> `ruolo_sistema` grezzo lato FE. Semanticamente equivalente all'intento §9.2.

---

*Brief vivo: aggiornare lo stato in testa e la riga V1 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) a chiusura.*
