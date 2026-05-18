# Smoke UI — Listini v5 end-to-end [SUPERATO da test-ui]

> **⚠️ Documento superato il 2026-04-24.**
> Gli scenari utili sono stati assorbiti in
> [`sviluppo-listini-v5-test-ui.md`](../work-in-progress/sviluppo-listini-v5-test-ui.md)
> (opzione A consolidamento). In particolare sono stati integrati:
> §1.4bis contratto modalità C, §3.3 defense `E_BOM_VALIDO_AL_INVALIDO`,
> §3.3bis edit inline `valido_al` BoM, §6.2 route guard Amm. Software,
> §6.3 BLOCCATO livello oggetto, criteri di uscita gate finale.
>
> Il file è qui solo per riferimento storico; **non usare per nuove esecuzioni**.
>
> ---
>
> Checklist manuale stampabile per la validazione UI del modello pricing v5
> (resolver 3 stadi: promo → contratto → categoria). Esegui in ordine —
> ogni scenario presuppone che il precedente sia passato.
>
> **Creata**: 2026-04-22 (sprint A nuovo, §14.3bis del WIP `sviluppo-listini-v5.md`)
> **Target**: ambiente di sviluppo con DB v5 applicato e BE/FE build aggiornati.

## Prerequisiti

- [X] DB v5 applicato (tutti i changeSet `20260414-01..23` + `20260415-01..07`)
- [X] BE running con F2-BE-01..14 deployati
- [X] FE build dopo sprint A nuovo (`./node_modules/.bin/vite build` verde)
- [ ] Almeno 3 utenti di test preparati:
  - **ADMIN** — `SUPER_ADMIN` bindato (bypass totale, tutti permessi TUTTO)
  - **OPERATORE** — operatore vendite con area `vendite = TUTTO`, area `catalogo = LETTURA`, area `amministrazione = BLOCCATO`
  - **READONLY** — operatore vendite con area `vendite = LETTURA` su tutto

---


- [X] Navigate `/amm-software/matrice-categorie-listini` → lista si carica
- [x] Filtri toolbar: `categoria`, `utility`, `emittente`, `listino`, `attivo`
- [ ] Search 1 carattere ("a") → lista non cambia (guard attivo)
- [ ] Search 3 caratteri → fetch lista
- [ ] Cancella search a 2 caratteri → **lista si sv
## Scenario 1 — Utente ADMIN (TUTTO)

### 1.1 Admin pricing (Amm. Software)

- [ ] Login come ADMIN → home visibile
- [ ] Sidebar sinistra: voce "Amm. Software" accessibile (icona menu non greyed)
- [ ] Navigate `/amm-software/categorie-clienti` → lista si carica
- [ ] Nuovo → drawer si apre
  - [ ] Campo `codice` editabile, `ordinamento` numerico, `partecipa_promo` toggle
  - [ ] Salva senza descrizione → save button disabled
  - [ ] Compila tutto → salva → lista ricaricata con la nuova categoria
- [ ] Click riga categoria appena creata → drawer apre in edit
  - [ ] `codice` readonly (grigio), descrizione editabile
  - [ ] Modifica descrizione → salva → riga aggiornata

### 1.2 Matrice categorie → listini

- [ ] Navigate `/amm-software/matrice-categorie-listini` → lista si carica
- [ ] Filtri toolbar: `categoria`, `utility`, `emittente`, `listino`, `attivo`
- [ ] Search 1 carattere ("a") → lista non cambia (guard attivo)
- [ ] Search 3 caratteri → fetch lista
- [ ] Cancella search a 2 caratteri → **lista si svuota** (test fix S14.nA-FE-5)
- [ ] Nuovo → drawer
  - [ ] `categoria`, `utility`, `emittente`, `classe_utenza` (opzionale) selezionabili
  - [ ] `listino` LookupSelect funziona
  - [ ] `tipo_variazione` + `valore_variazione` opzionali in coppia coerente
  - [ ] Cambia `tipo_variazione` dopo aver inserito un valore → **valore si azzera** + toast warn (test fix S14.nA-FE-6)
  - [ ] `valido_dal` obbligatorio, `valido_al` opzionale
  - [ ] Save OK → riga in lista
- [ ] Edit matrice: dimensioni (categoria/utility/emittente/classe_utenza) bloccate, variazione editabile

### 1.3 Promo articoli (dominio vendite)

- [ ] Navigate `/vendite/promo-articoli` → lista
- [ ] Nuovo → drawer
  - [ ] `codice`, `descrizione`, `articolo` (ArticoloLookup server-side min 3 char), `uom`
  - [ ] `tipo_variazione` ammette i 3 valori (PERCENTUALE, VALORE_FISSO, PREZZO_FISSO)
  - [ ] Cambia `tipo_variazione` dopo aver messo valore → reset + toast
  - [ ] Hint segno: per `PREZZO_FISSO` mostra testo diverso (> 0)
  - [ ] `valido_dal` e `valido_al` entrambi obbligatori
  - [ ] Save → lista
- [ ] Crea una promo con `tipo=PERCENTUALE valore=-10` (sconto 10%) per un articolo specifico

### 1.4 Billing account + categoria cliente

- [ ] Navigate `/anagrafiche/clienti` → lista
- [ ] Nuovo cliente → drawer
  - [ ] Field `ba_categoria_cliente_id` LookupSelect visibile
  - [ ] Seleziona "STANDARD" (seed DB)
  - [ ] Save → cliente creato
- [ ] Edit cliente esistente → cambio categoria a "GOLD" → save

### 1.5 Contratto modalità A (listino + variazione globale)

- [ ] Navigate `/vendite/contratti` → lista
- [ ] Nuovo contratto → drawer
  - [ ] `billing_account_id` lookup
  - [ ] `utility_id` select filtrato per ruolo
  - [ ] Modalità A/B/C via SelectButton → scegli A
  - [ ] `listino_id` obbligatorio in A, `tipo+valore_variazione_globale` opzionali
  - [ ] `valido_dal` obbligatorio
  - [ ] Save DRAFT → contratto creato
- [ ] Click contratto in lista → drawer edit
  - [ ] Tab "Righe": lista vuota (modalità A)
  - [ ] Tab "Utility": utility_id + classe_utenza_id
  - [ ] Cambio stato DRAFT → ATTIVO via pulsante in header
  - [ ] Confirm dialog → conferma → stato cambia a ATTIVO

### 1.6 Contratto modalità C (interamente negoziato)

- [ ] Nuovo contratto → modalità C, senza listino
- [ ] Save DRAFT
- [ ] Apre righe → aggiungi 1 riga (articolo + uom + `prezzo_unitario` obbligatorio)
- [ ] Prova cambio stato DRAFT → ATTIVO senza righe → **errore** (guard modalità C)
- [ ] Aggiungi riga → riprova → stato ATTIVO OK

### 1.7 Articolo + tipologia + BoM esposto

- [ ] Navigate `/catalogo/articoli` → lista
- [ ] Filtri toolbar: attivo, composito, tipologia_articoli, gruppo
- [ ] Verifica che il filtro "Voce Utility" **non esiste** (rimosso S14.nA-FE-2)
- [ ] Nuovo articolo composito → drawer
  - [ ] `listino_tipologia_id` LookupSelect `config.listini_tipologie`
  - [ ] Seleziona "PRODOTTI"
  - [ ] Save
- [ ] Sub-drawer BoM → aggiungi 2 componenti
  - [ ] Toggle `esposto_in_fattura` su 1 componente → on
  - [ ] Sull'altro lascia false
  - [ ] Salva

### 1.7.bis BoM immutabile — pattern chiudi+duplica (Sprint C FE)

Scenario che verifica l'adeguamento `ArticoloBomDrawer` post trigger DB `E_BOM_MODIFICA_VIETATA` (§14.4 sviluppo-listini-v5).

- [ ] Riapri il sub-drawer BoM dell'articolo composito creato in 1.7
- [ ] Verifica che compare il **banner info "bom_immutabile_hint"** sopra la tabella
- [ ] Verifica che la voce di menu kebab "**Elimina**" **non esiste più**
- [ ] Verifica presenza del

- [ ] Navigate `/amm-software/matrice-categorie-listini` → lista si carica
- [ ] Filtri toolbar: `categoria`, `utility`, `emittente`, `listino`, `attivo`
- [ ] Search 1 carattere ("a") → lista non cambia (guard attivo)
- [ ] Search 3 caratteri → fetch lista
- [ ] Cancella search a 2 caratteri → **lista si svle 3 voci kebab: Gestisci Note, **Duplica come nuova versione**, **Chiudi riga**
- [ ] Click kebab → "Chiudi riga"
  - [ ] Dialog conferma mostra "La riga sarà chiusa con valido al = {oggi}..."
  - [ ] Conferma → toast "Riga BoM chiusa"
  - [ ] La riga ora ha `valido_al = oggi` visibile in tabella
- [ ] Click kebab sulla stessa riga chiusa → "Duplica come nuova versione"
  - [ ] Form inserimento si apre con titolo **"Nuova versione componente"**
  - [ ] Banner warn "nuova_versione_hint" visibile sopra il form
  - [ ] Campi pre-compilati: componente (AutoComplete), coeff_qta, esposto_in_fattura, obbligatorio, partecipa_qta
  - [ ] `valido_dal` = oggi, `valido_al` = vuoto
  - [ ] Cambia `coeff_qta` a un valore diverso (es. da 2 a 3)
  - [ ] Salva → toast "Componente aggiunto" + lista BoM mostra 2 righe (vecchia chiusa + nuova attiva)
- [ ] Defense-in-depth: prova a chiudere una riga con `valido_al < valido_dal` via console DevTools (`updateArticoloComponente(..., { valido_al: '1999-01-01' })`)
  - [ ] Backend risponde errore `E_BOM_VALIDO_AL_INVALIDO`
  - [ ] Toast errore con messaggio parlante "valido_al deve essere >= valido_dal"
- [ ] Verifica edit inline valido_al (click sulla cella): funziona come chiusura rapida (coerente con l'azione kebab)

### 1.8 Resolver pricing (diagnostico)

- [ ] Apri Dialog test resolver (bottone nella lista listini)
- [ ] Compila: articolo (della promo creata in 1.3), uom, BA (cliente GOLD di 1.4), utility, data oggi
- [ ] Esegui → dovrebbe risolvere con **origine = PROMO** (stadio 0 batte)
- [ ] Cambia articolo a uno senza promo → origine = CATEGORIA o CONTRATTO_LISTINO

### 1.9 Preventivo con pricing

- [ ] Navigate `/vendite/preventivi` → lista
- [ ] Nuovo preventivo per il BA GOLD → salva DRAFT
- [ ] Apre righe → aggiungi riga con l'articolo della promo
- [ ] Verifica che `prezzo_unitario` viene suggerito dal resolver
- [ ] Modifica manualmente il prezzo → nessun blocco (ADMIN = L1 autorizzato)

### 1.9.bis Workflow L3 approvazione prezzo (Sprint E)

Setup: utente operatore con `prezzo_override_manuale` ON, `VENDITE_MAX_SCONTO_PCT=10` (parameter), assenza di `approva_prezzo_override`. Secondo utente "Manager" con `approva_prezzo_override`.

- [ ] Apri PreventiviRigaForm su riga BA GOLD, prezzo resolver = X
- [ ] Imposta prezzo manuale con sconto 25% (oltre limite 10%) → submit normale
  - [ ] Banner inline `E_PRICING_SCONTO_ECCESSIVO` visibile con detail "Sconto richiesto: 25.00% — massimo ammesso: 10%."
  - [ ] Pulsante "Richiedi approvazione" ora **attivo** (non disabled come pre-Sprint E)
- [ ] Click "Richiedi approvazione"
  - [ ] Toast success "Richiesta approvazione inviata"
  - [ ] Drawer si chiude
  - [ ] In `PreventiviRigheTable`: la riga ha **Tag warn "In approvazione"** sotto il prezzo, tooltip mostra `pratica #N`
- [ ] Tenta accettazione preventivo (cambio stato → ACCETTATO)
  - [ ] Errore `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` (banner toast)
- [ ] Tenta modifica della riga PENDING (es. cambia quantità) via UI
  - [ ] Errore `E_RIGA_PREZZO_PENDENTE` (defense-in-depth backend trigger)
- [ ] Login come Manager (utente con `approva_prezzo_override`)
- [ ] Navigate `/vendite/approvazioni-prezzo/`
  - [ ] Coda mostra la pratica pending creata
  - [ ] Colonne visibili: ID, Data, Descrizione, Priorità, Azioni
- [ ] Click "Approva" su quella pratica
  - [ ] Dialog conferma con campo "Nota interna (opzionale)"
  - [ ] Compila nota "Cliente strategico, prezzo concordato call"
  - [ ] Conferma → toast "Esito approvazione registrato"
  - [ ] Pratica scompare dalla coda (stato CHIUSA)
- [ ] Torna come operatore → riga ora ha Tag success "Approvato"
- [ ] Tenta accettazione preventivo → ora OK (no righe PENDING)
- [ ] Verifica caso rifiuto (ripeti scenario 25% + Richiedi approvazione, manager apre Dialog "Rifiuta", motivazione "Sconto eccessivo per categoria", conferma → riga Tag danger "Rifiutato"; preventivo accettabile)
- [ ] Defense-in-depth: scenario admin globale (senza emittente assegnato) → GET `/vendite/approvazioni-prezzo/` ritorna 409 `E_APPROVAZIONE_PREZZO_NON_AMMESSA`

**Gate Scenario 1**: tutti i check ✅. Nessun errore server/500 nel log backend.

---

## Scenario 2 — Utente READONLY (LETTURA sull'area vendite)

### 2.1 Setup

- [ ] Logout ADMIN
- [ ] Login come READONLY (profilo/reparto con `vendite = LETTURA`)

### 2.2 Visualizzazione lista vendite

- [ ] Navigate `/vendite/contratti` → lista si carica
- [ ] Toolbar: badge "Sola lettura" presente (ReadonlyBadge)
- [ ] Pulsante "Nuovo": **nascosto** (NewButton disabilitato)
- [ ] Pulsante "Ricarica": visibile e funzionante
- [ ] Click su una riga → drawer si apre in edit mode

### 2.3 Drawer readonly cumulativo

- [ ] DrawerTitle mostra badge "Sola lettura"
- [ ] Tutti i campi form sono greyed / non interagibili (pointer-events: none)
- [ ] `DrawerFooter`: pulsante "Salva" nascosto/disabilitato, solo "Chiudi"/"X"
- [ ] Testo dei campi è selezionabile per copia (not click)

### 2.4 Sub-drawer readonly propagato

- [ ] Apri sub-drawer "Righe" contratto → anche quello è in readonly
- [ ] Apri sub-drawer "Utility" → idem

### 2.5 Admin areas bloccate

- [ ] Prova navigate `/amm-software/categorie-clienti` → **route guard blocca** / redirect a 403
- [ ] Sidebar: voce "Amm. Software" nascosta o greyed

**Gate Scenario 2**: tutti i check ✅. L'utente non riesce a modificare nulla.

---

## Scenario 3 — Utente BLOCCATO livello oggetto

### 3.1 Setup

- [ ] Logout READONLY
- [ ] Login come OPERATORE con override: `vendite = TUTTO` MA `vendite.contratto = BLOCCATO` (override oggetto admin-applicato)

### 3.2 Lista contratti bloccata

- [ ] Navigate `/vendite/contratti` → raggiunge la pagina (area aperta)
- [ ] Invece della SearchTable appare `AccessoBloccatoPanel` con icona lock + messaggio `common.accesso_negato_elenco`
- [ ] Nessuna toolbar, nessun filtro, nessuna DataTable visibili
- [ ] **Nessuna fetch al backend** (verifica in Network tab del browser)

### 3.3 Altre aree vendite normali

- [ ] Navigate `/vendite/preventivi` → lista normale (area vendite aperta, oggetto preventivo non bloccato)
- [ ] Navigate `/vendite/promo-articoli` → lista normale

### 3.4 Side-effect: drawer contratto da altre vie

- [ ] Nel drawer cliente, tab "Contratti" del BA (se esiste) → se tenta di mostrare contratti bloccati, deve mostrare AccessoBloccatoPanel o campo vuoto

**Gate Scenario 3**: tutti i check ✅. L'oggetto bloccato è inaccessibile ma l'area funziona per gli altri oggetti.

---

## Note di uscita

- [ ] Zero errori JavaScript console browser durante tutti i test
- [ ] Zero HTTP 500 nel log backend
- [ ] Zero warning Vue da parent→child props mismatch
- [ ] I toast (save success, tipo_variazione_reset, errori) appaiono in alto a destra con durata corretta

In caso di fallimento: annotare scenario + step + screenshot + errore console/network e aprire follow-up nel WIP `sviluppo-listini-v5.md`.

---

*Smoke UI Listini v5 — ZeroERP (22 aprile 2026, sprint A nuovo)*
