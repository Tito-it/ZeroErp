# Brief FE — Pratica `PREVENTIVI` (dashboard + flusso + accettazione)

> **Tipo documento**: brief frontend (Vue 3 / PrimeVue / Pinia). Prerequisiti:
> deliverable DB applicati e BE dell'handler funzionante
> ([brief-be-pratica-preventivi.md](brief-be-pratica-preventivi.md)).
>
> **Data**: 2026-06-06 · **Stato**: pronto, riscontri FE risolti
>
> **Tesi centrale**: il FE è **quasi tutto già pronto**. La dashboard pratiche,
> il `FlussoDrawer`, il giornale, l'API client e il tab "Pratiche collegate" sul
> preventivo **esistono**. Il lavoro FE è **piccolo e mirato**: riconciliare il
> dialog di accettazione con la decisione "politica in configurazione", chiudere
> due gap di UX sul flusso e i18n.

---

## 1. Riscontri FE (verificati)

| Componente / feature | Stato reale | File |
|---|---|---|
| `PraticheDashboard` (master-detail + coda lavoro 3 livelli) | **Esiste, generica per tipo_prestazione** | `frontend/src/pratiche/views/PraticheDashboard.vue` |
| `PraticheCodaLavoro` (ASSEGNATO/COMPETENZA/REPARTO) | **Esiste** | `pratiche/components/PraticheCodaLavoro.vue` |
| `PraticaFlussiPanel` ("Da fare" / "Completati") | **Esiste** | `pratiche/components/PraticaFlussiPanel.vue` |
| `FlussoDrawer` (avvia + completa con esito) | **Esiste, parziale** | `pratiche/components/FlussoDrawer.vue` |
| `PraticaGiornaleTab` (timeline audit) | **Esiste** | `pratiche/components/PraticaGiornaleTab.vue` |
| Store Pinia pratiche (`userScoped`) | **Esiste** | `pratiche/stores/pratiche.js` |
| API client pratiche (CRUD, stato, flussi, coda, note/allegati, genera) | **Esiste, completo** | `pratiche/api/pratiche-api.js` |
| Tab "Pratiche collegate" sul preventivo | **Esiste** | `vendite/preventivi/components/PreventiviIntegrazione.vue` |
| `PreventiviDrawer` (create/edit, auto-save bozza, revisioni) | **Esiste** | `vendite/preventivi/components/PreventiviDrawer.vue` |
| Dialog accettazione preventivo (cattura `fatturazione_immediata` + `competenza_mese`) | **Esiste** | inline in `PreventiviDrawer.vue` |
| i18n `pratiche.*` + `preventivi.*` | **Esiste** | `frontend/src/locales/it.json` |

**Gap FE reali**:
- `FlussoDrawer`: nessuna UI per **sospensione** flusso, né visualizzazione
  esito-errore handler, né note/allegati a livello flusso (endpoint già esistono
  in `pratiche-api.js`).
- Nessuna UI per `pratiche_sorgenti` **lato pratica** (la pratica non mostra le
  sue sorgenti collegate; il preventivo invece vede le pratiche).
- `PreventiviDrawer` in CREATE **non** accetta `pratica_id` per pre-impostare il
  legame (oggi il legame si fa post-creazione via `genera-pratica`).

---

## 2. Deliverable FE

### F1 — Riconciliazione dialog accettazione preventivo (conseguenza decisione Tid)

**Il punto FE più importante.** Oggi il dialog di accettazione chiede SEMPRE
`fatturazione_immediata` + `competenza_mese` all'operatore. Con la politica **in
configurazione** sul percorso pratica, questi campi diventano **doppia verità**.

Comportamento corretto, coerente col doppio punto di ingresso §5.8:

| Percorso | Dialog accettazione |
|---|---|
| Preventivo **autonomo** (nessuna pratica `PREVENTIVI` collegata) | **Resta com'è**: l'operatore sceglie `fatturazione_immediata` + `competenza` (è l'unica fonte) |
| Preventivo **dentro pratica `PREVENTIVI`** | **Nasconde/disabilita** i due campi: la politica arriva dalla pratica (handler al `CONFERMA`). Mostra un hint: "Politica fatturazione gestita dalla pratica PRA-…" |

Implementazione: il `PreventiviDrawer` sa già se ci sono pratiche collegate
(`PreventiviIntegrazione` / `loadPratiche`). Aggiungere il branch nel dialog:
se esiste una pratica collegata di tipo `PREVENTIVI_*`, sopprimere i campi.
**Non** rimuovere il dialog (servirebbe al percorso autonomo).

> Questa è la traduzione UX della decisione di prodotto. Non rinegozia nulla: è
> la conseguenza diretta di "la politica vive in configurazione".

### F2 — `FlussoDrawer`: esito handler + stato `IN_CORSO`/`ERRORE`/`SOSPESO`

Il `CONFERMA_VENDITA` è il primo flusso con handler. Il drawer deve gestire:
- **avvio** del flusso → in caso (a) del brief BE, l'handler parte da solo sul
  passaggio a `IN_CORSO`: mostrare spinner/stato "esecuzione handler";
- **esito handler positivo**: il flusso transita a `COMPLETATO`, mostrare il
  risultato (`commessa_id` creata, link navigabile);
- **esito handler errore** (`E_VENDITA_*`): flusso in `ERRORE` (o `SOSPESO` se
  risolvibile). Mostrare il messaggio semantico parlante (envelope BE) e, dove
  pertinente, l'azione "Riprendi" (retry → `IN_CORSO`).

Stati flusso reali da gestire (da `config.stati_flussi_pratiche`):
`DA_ESEGUIRE, IN_CORSO, COMPLETATO, SOSPESO, ERRORE, ANNULLATO`.

> Riuso pattern: [feedback_dialog_cambio_stato_dati_processo],
> [feedback_drawer_result_check] (`if (result !== null)`),
> [feedback_useapihandler_solo_axios].

### F3 — Tab "Sorgenti collegate" lato pratica (gap, opzionale per la demo)

Nel `PraticaDrawer` aggiungere un tab che elenca `pratiche_sorgenti` della
pratica (preventivo ROOT + commessa COLLEGATO), con navigazione al documento.
Speculare a `PreventiviIntegrazione`. **Endpoint da verificare**: esiste già un
`GET /pratiche/{id}/sorgenti/`? In `pratiche-api.js` non risulta — se assente è
un piccolo deliverable BE+FE. Marcare come **nice-to-have**: non blocca il flusso
E2E, lo rende navigabile.

### F4 — i18n

Aggiungere chiavi mancanti per: stato/esito handler, messaggi `E_VENDITA_*`
(se mostrati come testo), hint riconciliazione F1, tab sorgenti F3. Le chiavi
`pratiche.*` e `preventivi.*` esistono già come base. Rispettare
[feedback_vue_i18n_linked_escape].

### F5 — (nice-to-have) aggancio in CREATE dal flusso `PREVENTIVAZIONE`

Far sì che, aprendo `PreventiviDrawer` dal flusso `PREVENTIVAZIONE` di una
pratica, il `pratica_id` sia pre-impostato e l'aggancio `ROOT` avvenga al primo
salvataggio bozza (oggi il legame è post-creazione via `genera-pratica`).
**Non** richiesto per il flusso minimo: l'aggancio ROOT lo garantisce comunque
l'handler al `CONFERMA` (§C6 brief BE). Da valutare per la fluidità operativa.

---

## 3. Cosa NON serve fare (FE già pronto)

- Dashboard pratiche, coda lavoro, ricerca, paginazione → **riuso diretto**, la
  dashboard è generica per `tipo_prestazione` (i due nuovi tipi compaiono da
  soli una volta seedati).
- Store, API client, giornale tab → **riuso diretto**.
- `PreventiviDrawer` testata/righe/revisioni/auto-save bozza → **invariato**.

---

## 4. Criteri di accettazione FE (smoke UI)

| ID | Test | Atteso |
|---|---|---|
| FE-S1 | Crea pratica `PREVENTIVI_IMMEDIATA` dalla dashboard | i due nuovi tipi compaiono nel Select; pratica creata |
| FE-S2 | Avanza i flussi 10→30 dalla dashboard; accetta il preventivo collegato | dialog accettazione **senza** campi fatturazione (F1, percorso pratica) |
| FE-S3 | Esegui `CONFERMA_VENDITA` | `FlussoDrawer` mostra esito handler, link a commessa creata; flusso `COMPLETATO`; pratica `CHIUSA` |
| FE-S4 | Caso errore: `PREVENTIVI_DIFFERITA` senza competenza in `meta` | flusso in `ERRORE`/`SOSPESO`, messaggio `E_VENDITA_COMPETENZA_RICHIESTA` leggibile |
| FE-S5 | Preventivo **autonomo** (no pratica), accettazione | dialog **con** campi fatturazione (percorso autonomo invariato) |
| FE-S6 | Giornale pratica | timeline mostra `DOMINIO_COMMESSA_CREATA`, `DOMINIO_PREVENTIVO_EVASO` |

---

## 5. Domande aperte FE (prima del piano)

1. **F1**: dove vive oggi il dialog di accettazione (inline `PreventiviDrawer`)
   e come rileva la presenza di una pratica `PREVENTIVI_*` collegata in fase di
   accettazione (è già caricata `loadPratiche`?).
2. **F3**: esiste `GET /pratiche/{id}/sorgenti/`? Se no, è un mini-deliverable
   BE+FE o si rimanda?
3. **Dipendenza dal wiring BE C3**: se il dispatch è automatico su `IN_CORSO`
   (raccomandato), il `FlussoDrawer` deve solo mostrare l'esito; se è azione
   esplicita, serve un bottone "Esegui".

---

## 6. Percorso flussi come roadmap (modello, non gap)

> Chiarimento Tid (2026-06-07): i flussi **non** vanno materializzati tutti alla
> creazione della pratica — sarebbe scorretto e confondente, perché un flusso può
> dipendere da scelte fatte nei flussi precedenti (percorsi condizionali). Il
> comportamento attuale del motore (pratica creata senza flussi, esecuzione
> progressiva) è quindi **corretto**, non un buco da tappare.

Conseguenza FE — la dashboard deve mostrare il **percorso suggerito** leggendolo
dal `template_flussi` del `tipo_prestazione`, non solo dai flussi già istanziati:

- **Roadmap/stepper** ordinato per `sequenza`: tutti gli step del tipo
  (`RICHIESTA_CLIENTE → PREVENTIVAZIONE → APPROVAZIONE_CLIENTE → CONFERMA`),
  inclusi quelli **futuri non ancora avviati**, così l'operatore vede dove deve
  arrivare.
- Stato visivo per step: completato / eseguibile-ora / non-ancora-abilitato.
- L'operatore clicca lo step **eseguibile** e lo completa; il successivo si
  abilita di conseguenza.
- Le **regole di prerequisito esistono già a DB** (`trgfn_flussi_guard_prerequisiti`
  / `fn_check_prerequisiti_flusso`, da `template_flussi_prerequisiti`): cliccare
  uno step non ancora abilitato → **errore parlante** (da mostrare in UI, non da
  reimplementare lato FE).

Oggi `PraticaFlussiPanel` mostra colonne "Da fare/Completati" sulle **istanze**.
Verifica/deliverable FE: arricchirlo (o affiancarlo) con la **vista percorso da
template** per gli step futuri. Endpoint dati: `template_flussi` +
`template_flussi_prerequisiti` (verificare se già esposti; `pratiche-api.js` ha
`fetchPrerequisiti`/`fetchRegoleGenerazione` ma sulle istanze, non sul template
completo a partita aperta — possibile mini-deliverable BE: endpoint "percorso del
tipo_prestazione").

> Nota di altitudine: *come* si istanzia il flusso al click (creazione on-demand
> dell'istanza vs auto-creazione del prossimo eseguibile al completamento del
> precedente) è una decisione BE/engine da chiudere nel piano. Non cambia il
> requisito FE: mostrare il percorso completo + far agire l'operatore sullo step
> eseguibile.

---

*Brief FE — Pratica PREVENTIVI / dashboard + flusso + accettazione — ZeroERP
(2026-06-06).*
