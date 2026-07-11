# Indice attività aperte — PRATICHE

> Generato il 2026-07-11 da una ricognizione dei documenti in `work-in-progress/`
> a tema gestione pratiche / workflow. Ordinato per importanza decrescente.
> Documento padre: `analisi-pratiche-valutazione-stato.md` · Tracker operativo autorevole: `gestione-pratiche-come-procedere.md`.

## Importanza ALTA

### 1. [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md)

**Descrizione**: documento operativo "come procedere" (2026-06-20), dichiarato autorevole per i prossimi passi del dominio pratiche. Consolida lo stato dopo la validazione E2E del primo consumatore (PREVENTIVI) e descrive il pattern DB→BE→FE da replicare sugli altri domini.

**Attività aperte**:

- 🔴 **Smoke UI E2E pratiche MAI eseguito** (giro reale crea pratica → avanza → accetta → conferma → commessa/fattura) — è l'urgenza principale e bloccante per procedere in sicurezza
- 🟡 Part B audit giornale (append-only) — aperta lato team DB
- Generalizzare handler accetta/push (oggi per-pratica PREVENTIVI) prima del 2° dominio
- Dialog FE smistamento riga-per-riga ("split natura") mancante (endpoint già pronto)
- Backfill dei 13 ROOT storici (aggancio documento↔flusso) non fatto
- Codici guard FE non mappati nel registry; esporre `template_flussi.chiude_pratica` nella UI config
- Predisporre la prima pratica nuova (raccomandata: OFFERTA)

### 2. [brief-design-guida-rollout-multidominio.md](brief-design-guida-rollout-multidominio.md)

**Descrizione**: brief di design (2026-07-07, il più recente) per estendere GUIDA (avanzamento milestone su stato proiettato) da PREVENTIVI a OFFERTA/ORDINE/CONTRATTO. Le 4 decisioni di design sono già prese: pronto per esecuzione — è la testa di lavoro corrente.

**Attività aperte**:

- Passo 0 (base condivisa): brief DB al team — G-est.1 (generalizzare `template_flussi_avanzamento_proiezione`/`fn_reconcile_sorgente` su fase/terminale) e G-est.2 (valorizzare `pratiche_sorgenti.flusso_id` sui link COLLEGATO)
- OFFERTA: primo dominio da attaccare (seed pratica + binding + trigger reconcile + registry FE + smoke E2E)
- CONTRATTO: decisione di dominio aperta a monte (quale transizione è il milestone — F3)
- ORDINE: cutover imperativo→dichiarativo (neutralizzare `_completa_flusso_ordine_pratica`, R2) + nodo àncora Forma C
- R1: coordinare G-est.2 con fix-transazioni (finding #4/#5/#10) sullo stesso branch
- F4: verificare per dominio che MOSTRA-display BE/FE non sia solo-preventivi

### 3. [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md)

**Descrizione**: documento strategico padre (2026-07-01) da cui derivano i brief della Gestione Pratiche. Diagnosi: motore forte, mancano i due strati sopra (esperienza operatore + strumenti di configurazione). Tabella voci V1–V11.

**Attività aperte**:

- V3 — Preset per settore + fork: design da generare (priorità media-alta)
- V4 — UI amministrazione workflow: BE pronto, resta l'editor FE (Fase 3) da generare
- V5 — Ispettore read-only discoverability opzioni: da generare (gemella di V4)
- V10 — Proiezione stato dominio: restano validazione E2E in-app MOSTRA e roll-out agli altri domini
- Cantiere `config.esiti_flussi_pratiche` (esiti data-driven bivio SMISTAMENTO): da finire
- V7 — AI copilota di configurazione: visione futura, non ora

## Importanza MEDIA

### 4. [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md)

**Descrizione**: brief di design (2026-07-01) sulla proiezione del descrittore normalizzato `fase`/`esito`/`terminale` del documento di dominio nella pratica. MOSTRA e GUIDA già implementate su PREVENTIVI; i residui sono in gran parte assorbiti dal brief roll-out multidominio (doc 2).

**Attività aperte**:

- Validazione E2E in-app di MOSTRA su PREVENTIVI
- §10.3 "azioni" nel descrittore (fase successiva, dopo MOSTRA)
- Indice a espressione `((uid::text))` per dominio al crescere dei volumi
- Promuovere la "regola dell'ancora" da frammento Python a vista DB condivisa (`vw_pratica_doc_sorgente`)

### 5. [analisi-gestione-operativa-attivita.md](analisi-gestione-operativa-attivita.md)

**Descrizione**: analisi (2026-06-29) dell'anello esterno "gestione operativa attività": agenda per operatore/responsabile/direzione, avvisi, posticipazione, sospensione del singolo flusso, ferie/assenze e riallocazione carico. Dichiarato "praticamente non realizzato".

**Attività aperte** (tutto da fare, in ordine di priorità interna):

- Agenda a fasce temporali (operatore/responsabile/direzione)
- Sistema avvisi (login + periodici + destinatari + fallback responsabile)
- Posticipazione flusso con nota/motivazione e limiti configurabili
- Sospensione temporanea del singolo flusso (oggi solo a livello pratica)
- Piano ferie/assenze + riallocazione carico (tabelle nuove da progettare)
- Punto di modello mancante: astrazione "voce d'agenda" (flusso + appuntamento + attività non-pratica)

### 6. [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)

**Descrizione**: grande analisi infrastrutturale (2026-05-18, agg. 2026-06-20) delle convenzioni di aggancio motore pratiche ↔ domini Anello 3. Fasi A→E chiuse (PREVENTIVI validato runtime); resta come riferimento di visione, non più tracker operativo.

**Attività aperte**:

- §8.6 Fase F — secondo consumatore (assistenza/acquisti/CRM): da avviare su OK; solo dopo il motore si promuove a "contratto stabile"
- §8.5 smoke UI E2E runtime (stesso item del doc 1)
- §7.2 decisioni formalmente APERTE su natura di riga (in gran parte consegnate con lo split natura, sezione da riallineare)
- §8.2/§8.3 visione ampia `VENDITA_STANDARD` (split natura → ordine+commessa+contratto): rinviata a secondo giro

### 7. [crm-ticketing-pratiche.md](crm-ticketing-pratiche.md)

**Descrizione**: bozza operativa (marzo 2026, il più datato) per un nuovo schema `assistenza` (ticketing) come Anello 3 sul motore pratiche, con gap analysis DB/BE/FE completa e posizionamento futuro del CRM. Candidato "Fase F — secondo consumatore", direzione opzionale da scegliere in base alle priorità di business.

**Attività aperte** (interamente da implementare):

- DB: schema `assistenza` completo D1–D15 (ticket, stati, categorie, worklog, materiali, trigger, seed)
- DB vendite: D16–D17 (campi `fonte_*` su `attivita_fatturabili` + trigger/job import)
- Backend app `assistenza` B1–B13 (repository, service, API, escalation ticket→pratica, test)
- Frontend modulo `assistenza` F1–F10 (store, lista, drawer, tab, escalation, i18n)

## Importanza BASSA / sostanzialmente chiusi (spostati in `work-done/` il 2026-07-11)

### 8. [gestione-pratiche-v2.md](../work-done/gestione-pratiche-v2.md)

**Descrizione**: piano v1→v2 del modulo pratiche, header "✅ COMPLETATO + in gran parte STORICO" (Fasi 1–7 atterrate). Non più riferimento corrente; alcune sezioni note come stale.

**Attività aperte residue**:

- G15 — pgAgent job riattivazione automatica sospensioni (priorità bassa)
- G16 — SLA alert WARNING/CRITICO da `calcoli_tempo` (priorità bassa)
- G17/G18 — tabelle `ext_*` e handler registry: futuro

### 9. [nota-be-backfill-data-apertura-pratiche.md](../work-done/nota-be-backfill-data-apertura-pratiche.md)

**Descrizione**: nota di decisione (2026-06-29): backfill `data_apertura` sulle pratiche storiche **non da eseguire ora** (solo DB di test; protezioni già attive). Sostanzialmente chiusa.

**Attività aperte residue**:

- Promemoria condizionale: rivalutare il backfill su dati reali/produzione (fonte: transizione →APERTA dal giornale)
