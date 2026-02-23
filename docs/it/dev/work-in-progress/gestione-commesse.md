# Gestione commesse - analisi e piano operativo (23-02-2026)

## 1) Obiettivo

Definire una base architetturale solida e scalabile per la gestione commesse, in modo che:

1. preventivi, ordini e future sorgenti (ticket, consumi, integrazioni) generino sempre una commessa (reale o fittizia);
2. la fatturazione passi da `attivita_fatturabili` con regole coerenti e tracciabili;
3. il modello sia estendibile a nuove sorgenti future (ticket, CRM, integrazioni esterne);
4. si evitino refactor distruttivi quando verra` introdotto il ramo ticket.

Riferimenti correlati:

1. `docs/it/dev/work-in-progress/ripresa-lavori-attivita-fatturabili.md`
2. `docs/it/dev/work-in-progress/fatturazione-attivita-progetto.md`

## 2) Contesto attuale e gap

Stato attuale sintetico:

1. il dominio `attivita_fatturabili` e` gia` centrale nella pipeline di fatturazione;
2. esiste una matrice sorgenti -> branch/policy (PREVENTIVI, ORDINI, CONSUMI, ecc.);
3. il modello target e` definito: layer commessa obbligatorio tra commerciale e fatturabile.

Gap principali:

1. mancano ancora le entita` DB operative (`commesse`, `commesse_sorgenti`, `commesse_attivita`) e relative funzioni core;
2. il percorso unico via commessa e` deciso ma non ancora imposto tecnicamente su tutti i flussi legacy;
3. la tracciabilita` end-to-end (origine commerciale -> commessa -> esecuzione -> fattura) non e` ancora completa a runtime;
4. i futuri ticket non hanno ancora un aggancio operativo implementato (solo disegno architetturale).

## 3) Principi architetturali (decisioni guida)

1. **Commessa come aggregate centrale**, non come appendice di ordine/preventivo.
2. **Sorgente primaria unica per commessa**: una commessa ha una sola sorgente root.
3. **Attivita_fatturabili resta il layer fiscale**: la commessa governa l'operativo, non sostituisce la pipeline fiscale.
4. **Lineage esplicito a 2 livelli**:
   - origine operativa diretta (commessa/task/worklog)
   - origine commerciale primaria (preventivo/ordine/ticket)
5. **Policy configurabile**: per ogni commessa decidere se fatturare da documento, consuntivo o mista.
6. **Idempotenza e deduplica by design**: chiavi univoche su bridge e origine attivita.
7. **Branch pipeline invariato ma estendibile**: aggiunta ticket come nuovo branch, non nuovo motore.
8. **Percorso unico**: eliminare il flusso diretto documento -> attivita_fatturabili; emissione solo tramite commessa.

Regola bloccante (da applicare in DB e backend):

1. qualunque inserimento in `attivita_fatturabili` senza `commessa_id` deve essere considerato non conforme;
2. eventuali flussi legacy diretti devono essere disattivati o instradati su commessa `AUTO`;
3. i task pipeline dei branch commerciali non devono mai emettere direttamente record fiscali.

Chiusura gap bloccanti (pre-DB-1):

1. `segment_key` definita e obbligatoria;
2. `root source` risolta con regola sorgente primaria unica per commessa;
3. semantica errore `GENERAZIONE_COMMESSA` formalizzata;
4. backfill storico Fase A formalizzato;
5. breaking change `fatturazione_immediata` dichiarato;
6. policy `MISTA` formalizzata;
7. lifecycle commessa `AUTO` formalizzato.

## 4) Soluzione funzionale proposta

### 4.1 Quando creare una commessa

Decisione finale:

1. per ogni sorgente eleggibile si crea sempre una commessa;
2. tipologie commessa:
   - `REALE` (processo operativo con task/worklog/milestone)
   - `AUTO` (commessa fittizia tecnica per percorso standard rapido);
3. `attivita_fatturabili` viene emessa solo da `commessa_attivita` (o unità equivalente della commessa `AUTO`).

Chiarimento operativo:

1. anche per `fatturazione_immediata` si crea sempre commessa `AUTO`;
2. anche nel percorso immediato si crea sempre una `commessa_attivita` tecnica;
3. solo dopo si emette in `attivita_fatturabili`.

### 4.2 Regole di fatturazione per commessa

Policy commessa:

1. `DA_DOCUMENTO`: usa valori commerciali come base primaria.
2. `DA_CONSUNTIVO`: usa solo attivita operative approvate.
3. `MISTA`: base documento con conguaglio da consuntivo.

Specifica operativa `MISTA`:

1. fase 1: emissione baseline da documento (quota iniziale deterministica);
2. fase 2: conguaglio da consuntivo su `commessa_attivita` approvate;
3. saldo finale:
   - delta positivo: nuova attivita_fatturabile di conguaglio;
   - delta negativo: nota di credito/attivita negativa secondo policy fiscale;
4. idempotenza:
   - stessa finestra temporale + stessa `segment_key` non deve rigenerare doppio conguaglio.

Gate minimo:

1. per commessa `REALE`, nessuna attivita fatturabile e` emettibile senza gate operativo minimo conforme alla policy.

### 4.3 Fatturazione immediata

Decisione architetturale:

1. `fatturazione_immediata` non identifica piu` "con o senza commessa": la commessa esiste sempre;
2. `fatturazione_immediata` abilita il percorso rapido solo su commessa `AUTO`;
3. su commessa `REALE` prevale il gate operativo e la priorita` non bypassa i controlli;
4. `sorgente_*` in `attivita_fatturabili` resta sempre la provenienza originaria (es. PREVENTIVO/ORDINE), anche quando il passaggio avviene via commessa `AUTO`.

Breaking change dichiarato:

1. il vecchio comportamento "documento direttamente fatturabile" e` deprecato;
2. da questa revisione, `fatturazione_immediata` significa:
   - creazione commessa `AUTO`,
   - creazione `commessa_attivita` tecnica,
   - emissione immediata verso lotto giornaliero.

Matrice operativa:

1. commessa `AUTO` + `fatturazione_immediata=false`
   - emissione ordinaria in `attivita_fatturabili`, scheduling standard lotti.
2. commessa `AUTO` + `fatturazione_immediata=true`
   - emissione rapida con ingresso preferenziale in lotto giornaliero.
3. commessa `REALE` (+ qualsiasi valore immediata)
   - emissione subordinata ai gate operativi (approvazione/milestone/consuntivo).

Priorita` operativa (entita` distinta):

1. introdurre campo/config `priorita_operativa` (es. `ALTA`, `NORMALE`, `BASSA` o ranking numerico);
2. la priorita` ordina la lavorazione pipeline su tutte le commesse;
3. non sostituisce i gate funzionali della commessa `REALE`.

## 5) Modello tecnico proposto (DB)

### 5.1 Tabelle nuove (core)

1. `vendite.commesse`
   - identita`, stato, owner, perimetro BA/utility, policy fatturazione, metadati.
2. `vendite.commesse_sorgenti`
   - bridge sorgente: collega la commessa alla sola sorgente primaria.
3. `vendite.commesse_attivita`
   - attivita operative atomiche (task, ore, milestone, consumi) con esito e approvazione.
4. `vendite.commesse_attivita_log` (opzionale ma consigliato)
   - log tecnico/funzionale per audit e diagnosi.

Specifica `ruolo_link` (chiusura gap):

1. valori ammessi:
   - `ROOT` (unico valore ammesso in questa fase);
2. vincolo:
   - una sola riga `ROOT` per `commessa_id`;
3. estensione futura:
   - eventuali ruoli aggiuntivi (`DERIVATA`, `REFERENZA`) fuori scope attuale.

### 5.2 Integrazione con attivita_fatturabili

Estensioni consigliate:

1. aggiungere in `vendite.attivita_fatturabili`:
   - `commessa_id` (`NOT NULL`)
   - `commessa_attivita_id` (`NOT NULL`)
2. mantenere `sorgente_tipo_id/sorgente_uid/sorgente_riga` per idempotenza esistente;
3. tracciare chiaramente:
   - origine diretta operativa tramite `commessa_id/commessa_attivita_id`
   - origine primaria tramite `sorgente_tipo_id/sorgente_uid/sorgente_riga`.

Decisione:

1. non introdurre `lineage_root_source` (ne` in `meta` ne` come colonna dedicata), per evitare ridondanza.
2. la sorgente primaria resta nei campi `sorgente_*` di `attivita_fatturabili`.

Condizioni obbligatorie del modello:

1. `commesse` deve conservare sempre una sorgente primaria valida (`sorgente_*`).
2. la sorgente primaria della commessa deve essere stabile (no cambi arbitrari post-creazione).
3. in emissione da commessa verso `attivita_fatturabili`, i campi `sorgente_*` devono essere valorizzati con la root source della commessa.
4. `commessa_id` e `commessa_attivita_id` devono essere sempre valorizzati (incluso percorso `fatturazione_immediata` con commessa `AUTO`).
5. `commessa_id/commessa_attivita_id` identificano solo l’origine operativa diretta, non sostituiscono la root source.
6. la root source deve rimanere invariata rispetto al documento evento originale.
7. deduplica e idempotenza non devono basarsi su sola root source quando esistono parzializzazioni.
8. una commessa deve avere esattamente una root source (`ruolo_link='ROOT'`).

### 5.3 Vincoli e idempotenza

1. su `commesse_sorgenti`:
   - unique su (`sorgente_tipo_id`, `sorgente_uid`[, `sorgente_riga`], `ruolo_link`);
   - unique su (`commessa_id`, `ruolo_link`) con `ruolo_link='ROOT'` per garantire una sola root per commessa.
2. su `commesse_attivita`:
   - chiave tecnica idempotente per evitare doppio inserimento da stesso evento sorgente.
3. su `attivita_fatturabili`:
   - policy di deduplica su `sorgente_* + segment_key` (o equivalente `commessa_attivita_id`),
     per consentire N quote/fatture della stessa sorgente primaria senza duplicazioni illegittime.

### 5.4 Regole future di univocita` (da finalizzare)

Decisione gia` presa:

1. la presenza di `commessa_id` e `commessa_attivita_id` non sostituisce la root source;
2. la root source resta obbligatoria e sempre coerente all'origine documento.

Proposta tecnica da validare prima dei vincoli definitivi:

1. univocita` operativa primaria:
   - unique su (`commessa_attivita_id`, `segment_key`) dove `attivo=true`;
2. univocita` di sicurezza sulla sorgente:
   - unique su (`sorgente_tipo_id`, `coalesce(sorgente_uid::text, sorgente_riga::text)`, `segment_key`) dove `attivo=true`;
3. vincolo anti-doppio canale:
   - impossibile avere due record attivi con stesso `segment_key` e stessa root source ma commesse diverse, salvo split esplicito con chiave diversa;
4. regola parzializzazione:
   - stessa root source puo` produrre N record solo con `segment_key` diversa e motivazione tracciata in `meta`.

Definizione operativa `segment_key` (chiusura gap bloccante):

1. `segment_key` rappresenta il segmento economico-fiscale atomico emettibile;
2. `segment_key` deve essere deterministica rispetto a:
   - `commessa_attivita_id`
   - periodo/competenza (`competenza_dal`, `competenza_al` o mese)
   - tipo quota (`BASE`, `SAL`, `CONGUAGLIO`)
   - progressivo di split tecnico quando presente
3. `segment_key` non puo` cambiare su rerun dello stesso evento;
4. `segment_key` e` obbligatoria per tutte le righe emesse da commessa.

Nota:

1. `segment_key` deve essere deterministica e stabile su rerun per garantire idempotenza.

### 5.5 Root source resolution (chiusura gap)

Regola adottata:

1. una commessa ha una sola sorgente primaria (`ROOT`);
2. `fn_emit_attivita_fatturabili_da_commessa(...)` legge sempre la `ROOT` della commessa;
3. i campi `sorgente_*` emessi in `attivita_fatturabili` sono sempre quelli della `ROOT`;
4. se manca la `ROOT`, emissione in errore bloccante.

## 6) Pipeline e orchestrazione

### 6.1 Estensione branch attuali

Branch attuali/futuri:

1. `PREVENTIVI`
2. `ORDINI`
3. `CONSUMI`
4. `COMMESSE` (nuovo ramo operativo)
5. `TICKET` (futuro, stessa semantica)

### 6.2 Contratto pipeline raccomandato

1. step `RACCOLTA_INPUT`: acquisisce documenti/eventi sorgente;
2. step `GENERAZIONE_COMMESSA`: crea/aggiorna sempre una commessa (`REALE` o `AUTO`);
3. step `ACQUISIZIONE_OPERATIVA`: crea `commesse_attivita`;
4. step `NORMALIZZA/VALIDA/DEDUPLICA`: prepara `attivita_fatturabili`;
5. step `PRONTO_FATTURAZIONE`: rende eleggibili per lotto fiscale.

Semantica errore `GENERAZIONE_COMMESSA`:

1. errore tecnico o dati obbligatori mancanti:
   - stato task `ERRORE`
   - blocco `GLOBAL` per run corrente;
2. anomalia non bloccante di record singolo:
   - stato task `WARNING`
   - blocco `BRANCH` se configurato;
3. nessuna riga puo` proseguire verso `ACQUISIZIONE_OPERATIVA` senza `commessa_id`.

### 6.3 Policy blocco

1. `BRANCH`: errore commessa blocca solo ramo commessa.
2. `GLOBAL`: errori configurati come globali bloccano run completo.
3. ticket potra` usare stesso meccanismo senza variazioni architetturali.

## 7) API e contratti applicativi (backend)

Set minimo suggerito:

1. API commesse:
   - create/get/update stato
   - elenco sorgenti collegate
   - elenco attivita operative
2. API integrazione pipeline:
   - run con policy commessa (`REALE`/`AUTO`, `DA_DOCUMENTO`/`DA_CONSUNTIVO`/`MISTA`)
   - status con evidenza gate commessa
3. API tracciabilita`:
   - dato fatturabile -> commessa -> sorgente primaria.

## 8) Migrazione incrementale consigliata

### Fase A - Fondazione modello

1. creare tabelle commesse + bridge + attivita;
2. aggiungere relazioni obbligatorie in `attivita_fatturabili` (`commessa_id`, `commessa_attivita_id`);
3. backfill storico obbligatorio:
   - creare commessa `AUTO` per ogni record storico senza commessa;
   - creare `commessa_attivita` tecnica 1:1 per storico;
   - valorizzare `commessa_id`, `commessa_attivita_id`, `segment_key`;
4. solo dopo backfill completo attivare `NOT NULL` e unique nuove.

### Fase B - Attivazione percorso unico

1. introdurre commessa `AUTO` come default per tutte le sorgenti attive;
2. mappare a `REALE` i casi che richiedono operativita` (servizi/progetti/ticket).

Lifecycle commessa `AUTO`:

1. stati minimi:
   - `CREATA` -> `PRONTA_FATTURAZIONE` -> `CHIUSA`;
2. transizione standard:
   - `CHIUSA` immediatamente dopo emissione in `attivita_fatturabili` e sincronizzazione stato `COMPLETED`;
3. riapertura:
   - non prevista salvo correzione tecnica esplicita.

### Fase C - Gate fatturazione

1. attivare gate per tutte le commesse di tipo `REALE`;
2. impedire emissione fatturabile senza prerequisiti operativi.

### Fase D - Estensione ticket

1. aggiungere `TICKET` in `config.sorgenti`/policy branch;
2. riusare `commesse_sorgenti` senza cambiare modello core.

## 9) Rischi e mitigazioni

1. **Rischio complessita` eccessiva iniziale**
   - mitigazione: rollout per flag e perimetro limitato.
2. **Rischio duplicazioni tra documento e commessa**
   - mitigazione: percorso unico via commessa + guardrail anti-bypass + deduplica su `source + segment_key`.
3. **Rischio blocchi operativi non desiderati**
   - mitigazione: policy `BRANCH/GLOBAL` configurabile e testata.
4. **Rischio regressione fatturazione attuale**
   - mitigazione: commessa `AUTO` come sostituto compatibile del vecchio percorso diretto.

## 10) Roadmap operativa (focus DB completo, backend posticipato)

Principio operativo:

1. chiudere prima tutto il refactor DB;
2. aprire backend solo dopo gate DB verde.

### 10.1 DB-0 Inventario e baseline tecnica

Obiettivo: congelare lo stato attuale e identificare i punti legacy da rimuovere.

Attivita`:

1. inventario vincoli/indici/trigger su `vendite.attivita_fatturabili`;
2. inventario funzioni che leggono/scrivono `attivita_fatturabili`;
3. inventario dipendenze su unique legacy di sorgente.

Output atteso:

1. lista ufficiale oggetti da deprecare (in primis `uq_attivita_fatturabili_v_sorgente_fk`);
2. lista oggetti da mantenere (`uid`, FK sorgente, trigger guardia sorgente).

### 10.1-bis Bloccanti da chiudere prima di DB-1

1. definizione finale `segment_key` approvata;
2. definizione finale `ruolo_link=ROOT` approvata;
3. conferma regola: una commessa = una sorgente primaria;
4. semantica errore `GENERAZIONE_COMMESSA` approvata;
5. piano backfill storico approvato.

### 10.2 DB-1 Schema commessa core

Obiettivo: introdurre il layer commessa operativo obbligatorio.

Attivita`:

1. creare `vendite.commesse`;
2. creare `vendite.commesse_sorgenti`;
3. creare `vendite.commesse_attivita`;
4. aggiungere in `vendite.attivita_fatturabili`:
   - `commessa_id` FK
   - `commessa_attivita_id` FK
5. rollout `NOT NULL` su entrambe le colonne (con backfill prima del vincolo finale).

Output atteso:

1. ogni record fatturabile riferibile a commessa e attivita` commessa;
2. tracciabilita` root source invariata via `sorgente_*`.

### 10.3 DB-2 Unicita` e idempotenza (migrazione dal modello legacy)

Obiettivo: spostare la deduplica da “solo sorgente” a modello commessa-centrico.

Attivita`:

1. rimuovere unique legacy:
   - `uq_attivita_fatturabili_v_sorgente_fk` (`sorgente_tipo_id`, `sorgente_uid`);
2. introdurre unique primaria operativa:
   - `unique (commessa_attivita_id, segment_key)` su record attivi;
3. introdurre unique di sicurezza su root source:
   - `unique (sorgente_tipo_id, coalesce(sorgente_uid::text, sorgente_riga::text), segment_key)` su record attivi;
4. introdurre check/guard su `segment_key` (non nulla e deterministica nel percorso pipeline).

Output atteso:

1. consentita parzializzazione controllata della stessa sorgente primaria;
2. eliminata collisione artificiale del vecchio unique “solo source”.

### 10.4 DB-3 Funzioni core e guardrail

Obiettivo: rendere il percorso commessa l’unico percorso tecnico valido.

Attivita`:

1. implementare/aggiornare:
   - `fn_get_or_create_commessa(...)`
   - `fn_link_commessa_sorgente(...)`
   - `fn_upsert_commessa_attivita(...)`
   - `fn_emit_attivita_fatturabili_da_commessa(...)`
2. aggiornare funzioni pipeline attivita per chiamare solo path commessa;
3. introdurre guardrail anti-bypass:
   - blocco inserimenti diretti in `attivita_fatturabili` senza origine commessa;
4. mantenere `sorgente_*` come origine primaria immutata in emissione.

Output atteso:

1. nessun percorso `documento -> attivita_fatturabili` residuo;
2. flussi `fatturazione_immediata` instradati su commessa `AUTO` + `commessa_attivita`.

### 10.5 DB-4 Policy e seed operativi

Obiettivo: rendere le regole deterministiche e governate da configurazione DB.

Attivita`:

1. seed policy commessa (`AUTO`/`REALE`) per sorgente;
2. seed policy `fatturazione_immediata` e `priorita_operativa`;
3. seed mapping pipeline `COMMESSE` e step reali non `noop`;
4. seed profilo go-live con scope sorgenti esplicito.

Output atteso:

1. nessuna logica hardcoded richiesta nel backend per decidere il tipo commessa;
2. comportamento uniforme tra ambienti.

### 10.6 DB-5 Test pgtap e validazione dati

Obiettivo: chiusura tecnica DB prima del passaggio backend.

Attivita`:

1. pgTAP DDL/FK/NOT NULL/unique/check nuovi;
2. pgTAP regressione su funzioni core commessa;
3. pgTAP anti-bypass diretto documento -> fatturabile;
4. pgTAP su univocita`:
   - stessa root source + stesso `segment_key` non duplicabile;
   - stessa root source + `segment_key` diversa ammessa (parzializzazione);
5. verifica dati storici post-backfill:
   - nessun record `attivita_fatturabili` senza `commessa_id/commessa_attivita_id`.

Output atteso:

1. suite DB verde;
2. integrita` dati legacy riallineata.

### 10.7 Gate di uscita DB (obbligatorio)

Il backend parte solo se tutti i gate sono chiusi:

1. schema commessa completo e vincoli attivi;
2. unique legacy sorgente rimossi;
3. nuove unique commessa-centriche attive e validate;
4. funzioni commessa-core operative e testate;
5. pgTAP completo verde.

### 10.8 Backend (post-DB, fuori perimetro attuale)

Solo dopo il punto 10.7:

1. BE orchestrazione task commessa;
2. BE API commesse e status;
3. BE test e rollout.

## 11) Decisione raccomandata

Adottare **commessa multi-sorgente sempre presente** (reale o auto) come layer operativo unico, mantenendo:

1. sorgente primaria sempre in `sorgente_*` su `attivita_fatturabili`;
2. deduplica robusta per parzializzazioni (`source + segment_key`);
3. `commessa_id` e `commessa_attivita_id` sempre valorizzati;
4. gate operativo obbligatorio sulle commesse `REALE`;
5. compatibilita` futura con ticket senza refactor strutturale.
