# Test UI listini v5 — Piano operativo

> WIP creato il 2026-04-23 a chiusura Sprint v5.
> Scopo: piano test UI strutturato per validare end-to-end il modello v5
> (categorie + contratti + promo + BoM + L1+L2+L3) prima di considerare
> l'implementazione "blessed" per l'uso quotidiano.

## Stato del modello

Tutti gli sprint v5 sono **chiusi end-to-end** (DB+BE+FE+DOC). Vedi
[sviluppo-listini-v5.md §14.9](sviluppo-listini-v5) per il tracking
completo. La presente checklist è il complemento operativo che esercita
le funzionalità in UI.

Test Django: 1662 verdi. Vite build: ~916ms. La smoke UI precedente
(`smoke-listini-v5.md`, 2026-04-22) è stata assorbita in questo
documento il 2026-04-24 ed è archiviata in `work-done/`.

## Obiettivi

1. **Validazione funzionale**: ogni feature v5 esercitata almeno una volta
   in scenario realistico end-to-end (NON solo unit test).
2. **Validazione UX**: messaggi i18n IT/EN coerenti, banner/dialog
   apparirebbero al momento giusto, badge stato leggibili.
3. **Validazione defense-in-depth**: trigger DB sollevano errori parlanti
   anche quando la UI bypassa accidentalmente la guard FE.
4. **Regressione cross-sprint**: ogni scenario chiude verificando che
   altri scenari precedenti restino integri.

## Prerequisiti ambiente

- DB landato fino a `20260422-07` incluso (Sprint E DB completo)
- Backend `dev/backend-tid` HEAD `e1408643` o successivi (Sprint E BE+FE allineato)
- Almeno 3 utenti di test:
  - **Admin**: SUPER_ADMIN o area `amministrazione = MODIFICA` (serve per tutto Scenario 1 Setup admin pricing)
  - **Operatore Junior**: area `vendite = MODIFICA`, `prezzo_override_manuale` ON, **NO** `approva_prezzo_override` (usato in §2.2 errore 403, §4.1/§4.3 richiesta approvazione)
  - **Operatore Senior / Approver**: area `vendite = MODIFICA`, `prezzo_override_manuale` ON, `approva_prezzo_override` ON (usato in §2.1/§2.2 L1 autorizzato, §4.4/§4.5/§4.6 coda approvazioni)
- Configurazione minima:
  - 1 emittente fiscale assegnato a entrambi gli utenti
  - 1 BA "GOLD" con categoria_cliente associata
  - Almeno 1 listino UTILITY + 1 listino COMMERCIO con righe
  - Almeno 1 contratto modalità A su BA GOLD
  - Almeno 1 promo articolo attiva oggi
  - Almeno 1 articolo composito con BoM (1 componente esposto + 1 non esposto)
  - Parametri L2: `VENDITE_MAX_SCONTO_PCT=10`, `VENDITE_MAX_MAGGIORAZIONE_PCT=5`
  - Parametro L3 email opzionale: `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`

## Indice scenari

1. **Setup admin pricing v5** (categorie, matrice, listini, contratti modalità A e C, promo)
2. **Pricing operativo** (preventivo + auto-fill + L1+L2+L3)
3. **BoM versionata** (chiudi+duplica nuova versione, edit inline valido_al)
4. **Workflow L3** (richiedi → coda → approva/rifiuta)
5. **Defense-in-depth trigger DB**
6. **Readonly cumulativo + accesso bloccato** (LETTURA area, route guard Amm. Software, BLOCCATO livello oggetto)
7. **Cross-locale i18n** (switch IT ↔ EN)

---

## Scenario 1 — Setup admin pricing v5

> **Utente**: Admin (SUPER_ADMIN o area `amministrazione = MODIFICA`).
> Gli operatori Junior/Senior di pricing non hanno accesso a `/amm-software/` e non possono eseguire questo scenario.

### 1.1 Categorie clienti

- [X] Login Admin → `/amm-software/categorie-clienti/` lista visibile
- [X] Crea nuova categoria "GOLD" con `partecipa_promo=true` → toast success
- [X] Tenta crea duplicato stesso codice → errore parlante `E_ANAG_DUPLICATO`

### 1.2 Matrice categorie ↔ listini

- [X] Apri `/amm-software/matrice-categorie-listini/`
- [X] Mappa GOLD → listino-COM-001 per utility GAS con `tipo_variazione=PERCENTUALE`, `valore_variazione=-5`
- [X] Verifica overlap blocked: tentando seconda riga GOLD/GAS overlap → errore

### 1.3 Listini

- [X] `/vendite/listini/` lista filtrabile per tipologia
- [X] Crea listino COM-002 (commercio) → drawer + pulsante "Nuova versione" → BOZZA
- [X] Aggiungi 3 righe articolo nella versione BOZZA
- [X] Attiva versione → BOZZA → ATTIVA

### 1.4 Contratti

- [X] `/vendite/contratti/` → nuovo contratto modalità A su BA GOLD legato al listino COM-001
- [X] Aggiungi variazione globale `+2%`
- [X] Stato BOZZA → ATTIVO

### 1.4bis Contratto modalità C (interamente negoziato)

- [X] Nuovo contratto modalità C (SelectButton A/B/C → C), senza listino
- [X] Save DRAFT → contratto creato
- [X] Prova cambio stato DRAFT → ATTIVO **senza righe** → errore guard modalità C
- [X] Apre righe → aggiungi 1 riga (articolo + uom + `prezzo_unitario` obbligatorio)
- [X] Riprova cambio stato → ATTIVO OK

### 1.5 Promo articoli

- [x] `/vendite/promo-articoli/` → nuova promo `PROMO-TEST-Q1` su articolo X
- [x] `tipo_variazione=PREZZO_FISSO`, `valore_variazione=9.99`, valida 7 giorni
- [x] Stato attiva, quindi appare nei filtri

### 1.6 Articolo + BoM

- [X] `/catalogo/articoli/` → nuovo articolo composito "Pacchetto-test"
- [X] `is_composito=true`, `listino_tipologia_id` selezionato
- [X] Sub-drawer BoM → aggiungi 2 componenti, 1 con `esposto_in_fattura=true`
- [X] Verifica banner info "BoM immutabile" appare sopra la tabella

**Gate**: tutti i check ✅, nessun 500 nel log backend.

---

## Scenario 2 — Pricing operativo

### 2.1 Preventivo + auto-fill resolver

- [ ] `/vendite/preventivi/` → nuovo preventivo per BA GOLD
- [ ] Apri righe → aggiungi riga con articolo della promo (1.5)
- [ ] Verifica `prezzo_unitario` pre-compilato dal resolver (3 stadi)
- [ ] Badge origine prezzo: PROMO (stadio 0 batte tutto)
- [ ] Cambia articolo a uno senza promo → origine CONTRATTO_LISTINO o CATEGORIA

### 2.2 L1 override

- [ ] Login Senior (ha `prezzo_override_manuale`) → modifica prezzo riga
- [ ] Verifica `meta.origine_prezzo='MANUALE'` + audit completo (FE non visibile, da DB)
- [ ] Login operatore SENZA `prezzo_override_manuale` → tentativo override → errore 403 `E_PREV_OVERRIDE_NON_AUTORIZZATO`

### 2.3 L2 limiti hint

- [ ] Riapri drawer riga: hint "Variazione prezzo ammessa: sconto fino al 10%, maggiorazione fino al 5%" sotto il campo prezzo
- [ ] Hint visibile in IT e in EN (switch lingua)
- [ ] Imposta sconto 8% (entro limite) → save OK
- [ ] Imposta sconto 25% (oltre limite) → banner inline `E_PREV_SCONTO_ECCESSIVO`
  - [ ] Detail mostra "Sconto richiesto: 25.00% — massimo ammesso: 10%."
  - [ ] Pulsante "Richiedi approvazione" attivo

### 2.4 Suggerisci prezzo da diagnostico

- [ ] Apri Dialog test resolver da `/vendite/listini/` → compila contesto
- [ ] Esegui → output con `prezzo_finale`, `origine`, `listino_id`/`contratto_id`/`promo_id`

---

## Scenario 3 — BoM versionata (Sprint C immutabilità)

### 3.1 Trigger guard immutabilità

- [ ] Articolo composito creato in 1.6 → riapri sub-drawer BoM
- [ ] Verifica banner info "BoM immutabile" presente
- [ ] Verifica menu kebab di riga: presenti "Gestisci Note", "Duplica come nuova versione", "Chiudi riga". **NESSUN "Elimina"** (rimosso intenzionalmente)
- [ ] Click "Chiudi riga" sul componente C1 → dialog conferma `valido_al = oggi`
- [ ] Conferma → toast "Riga BoM chiusa", riga ora ha `valido_al` valorizzato

### 3.2 Duplica come nuova versione

- [ ] Click kebab sulla riga chiusa → "Duplica come nuova versione"
- [ ] Form si apre con titolo "Nuova versione componente" + banner warn hint versionamento
- [ ] Campi pre-compilati con valori della riga sorgente, `valido_dal=oggi`
- [ ] Cambia `coeff_qta` (es. da 2 a 3)
- [ ] Salva → toast "Componente aggiunto"
- [ ] Lista BoM ora mostra 2 righe (vecchia chiusa + nuova attiva)

### 3.3 Defense-in-depth trigger DB

- [ ] Apri DevTools console e tenta UPDATE diretto via API: `PATCH /catalogo/articoli/{id}/componenti/{componente_id}/` con `coeff_qta` modificato → errore 409 `E_BOM_MODIFICA_VIETATA` con hint "chiudi+inserisci"
- [ ] Prova a chiudere una riga con `valido_al < valido_dal` via console DevTools (`updateArticoloComponente(..., { valido_al: '1999-01-01' })`) → backend risponde `E_BOM_VALIDO_AL_INVALIDO`, toast con messaggio parlante "valido_al deve essere >= valido_dal"

### 3.3bis Edit inline valido_al (chiusura rapida)

- [ ] Click sulla cella `valido_al` di una riga aperta → input inline
- [ ] Imposta data oggi → save → riga chiusa (comportamento coerente con azione kebab "Chiudi riga")
- [ ] Riapri: edit inline con `valido_al < valido_dal` → stesso errore `E_BOM_VALIDO_AL_INVALIDO`

### 3.4 Espansione compositi nella pipeline (S14.C-BE-1/BE-2)

- [ ] Push preventivo con riga articolo composito → run commesse_push
- [ ] Verifica creazione N attività in `vendite.commesse_attivita` (1 per componente)
- [ ] `segment_key` differenziato con suffix `#CMP:{componente_id}`
- [ ] `quantita = quantita_padre × coeff_qta` (no rounding)

---

## Scenario 4 — Workflow L3 (Sprint E end-to-end)

### 4.1 Richiesta approvazione (Operatore Junior)

- [ ] Login Junior (NO `approva_prezzo_override`)
- [ ] Apri preventivo in BOZZA, aggiungi riga con prezzo a sconto 25% (oltre limite L2 10%)
- [ ] Save normale → banner inline `E_PREV_SCONTO_ECCESSIVO`, pulsante "Richiedi approvazione" attivo
- [ ] Click "Richiedi approvazione" → toast success "Richiesta approvazione inviata"
- [ ] Drawer si chiude, lista righe mostra **Tag warn "In approvazione"** sotto il prezzo
- [ ] Tooltip badge: "Riga in attesa di approvazione (pratica #N)"

### 4.2 Guard transizione preventivo

- [ ] Tenta accettazione preventivo (cambio stato → ACCETTATO)
- [ ] Errore 409 `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` (toast)

### 4.3 Guard modifica riga PENDING

- [ ] Tenta modifica della riga PENDING (es. cambia quantità) via UI
- [ ] Errore 409 `E_RIGA_PREZZO_PENDENTE` (defense-in-depth backend)

### 4.4 Coda approver (Senior/Approver)

- [ ] Logout, login Senior con `approva_prezzo_override`
- [ ] Sidebar Vendite → "Approvazioni prezzo" voce visibile (post-Sprint E navigation)
- [ ] Click → `/vendite/approvazioni-prezzo/` carica coda
- [ ] La pratica creata in 4.1 è visibile, colonne: ID, Data, Descrizione, Priorità, Azioni

### 4.5 Approva

- [ ] Click "Approva" su quella pratica
- [ ] Dialog: header "Approva override prezzo", textarea "Nota interna (opzionale)"
- [ ] Compila nota "Cliente strategico, prezzo concordato call"
- [ ] Conferma → toast "Esito approvazione registrato"
- [ ] Pratica scompare dalla coda (stato CHIUSA)
- [ ] Login Junior → riga preventivo ora ha **Tag success "Approvato"**
- [ ] Tenta accettazione preventivo → ora OK (no righe PENDING)

### 4.6 Rifiuta

- [ ] Ripeti scenario 4.1 con altra riga oltre L2
- [ ] Login Senior → coda → click "Rifiuta"
- [ ] Dialog: textarea "Motivazione (consigliata)"
- [ ] Compila "Sconto eccessivo per categoria"
- [ ] Conferma → toast "Esito rifiuto registrato"
- [ ] Login Junior → riga ora ha **Tag danger "Rifiutato"**
- [ ] Modifica prezzo riga (riga REJECTED non bloccata) → save OK con prezzo entro L2

### 4.7 Defense-in-depth admin globale

- [ ] Login utente admin globale (no emittente assegnato)
- [ ] GET `/vendite/approvazioni-prezzo/` → 409 `E_APPROVAZIONE_PREZZO_NON_AMMESSA`
- [ ] La coda è multi-tenant per emittente; admin globale deve usare `cerca_pratiche` generico

---

## Scenario 5 — Defense-in-depth trigger DB (cross-sprint)

Test che simulano bypass UI tramite DevTools / curl. Importanti perché
la UI è disegnata per evitare gli errori, ma i trigger sono la guardia
finale contro bug FE.

- [ ] Modifica BoM via PATCH diretto → `E_BOM_MODIFICA_VIETATA`
- [ ] DELETE BoM via DELETE diretto → `E_BOM_MODIFICA_VIETATA`
- [ ] UPDATE riga PENDING su `prezzo_unitario` via PATCH diretto → `E_RIGA_PREZZO_PENDENTE`
- [ ] UPDATE riga PENDING su `meta` via PATCH → ammesso (allowlist trigger 07)
- [ ] Transizione preventivo → ACCETTATO con riga PENDING via POST diretto → `E_PREVENTIVO_RIGHE_PRICING_PENDENTI`

---

## Scenario 6 — Readonly cumulativo + accesso bloccato

### 6.1 Area vendite LETTURA (readonly cumulativo)

Setup: utente con livello area `vendite` LETTURA, `amministrazione` = BLOCCATO.

- [ ] `/vendite/preventivi/` lista visibile, toolbar con badge "Sola lettura" (ReadonlyBadge)
- [ ] Pulsante "Nuovo" nascosto, "Ricarica" visibile
- [ ] Drawer riga: tutti i campi grigi (prop `readonly` + `useInjectReadonly`), DrawerFooter con solo "Chiudi"/"X"
- [ ] Sub-drawer BoM: nessun pulsante "Aggiungi", "Chiudi riga", "Duplica" visibile
- [ ] Banner info BoM immutabile NON visibile (è UX per editor)
- [ ] `/vendite/approvazioni-prezzo/` lista visibile (LETTURA), ma click Approva → 403 `E_PREV_OVERRIDE_NON_AUTORIZZATO` (manca `approva_prezzo_override`)

### 6.2 Area Amm. Software bloccata (route guard)

- [ ] Prova navigate `/amm-software/categorie-clienti` → route guard blocca / redirect a 403
- [ ] Sidebar: voce "Amm. Software" nascosta o greyed

### 6.3 BLOCCATO livello oggetto (vendite TUTTO, oggetto bloccato)

Setup: utente con `vendite = TUTTO` MA override oggetto `vendite.contratto = BLOCCATO`.

- [ ] Navigate `/vendite/contratti` → raggiunge la pagina (area aperta)
- [ ] Invece della SearchTable appare `AccessoBloccatoPanel` con icona lock + messaggio `common.accesso_negato_elenco`
- [ ] Nessuna toolbar, nessun filtro, nessuna DataTable visibili
- [ ] **Nessuna fetch al backend** (verifica in Network tab del browser)
- [ ] Navigate `/vendite/preventivi` → lista normale (oggetto preventivo non bloccato)
- [ ] Navigate `/vendite/promo-articoli` → lista normale
- [ ] Eventuale tab "Contratti" dentro drawer cliente (se esiste) → AccessoBloccatoPanel o campo vuoto

---

## Scenario 7 — Cross-locale i18n

- [ ] Switch lingua IT → EN sul profilo utente
- [ ] Tutti i testi v5 (banner L2, dialog L3, badge stato_approvazione, hint BoM) tradotti
- [ ] Switch EN → IT, verifica retrofit

Chiavi i18n nuove introdotte da Sprint C+D+E sono ~38; lista completa in
`frontend/src/locales/it.json` (sezioni `preventivi.*`, `approvazioni_prezzo.*`,
`catalogo.*`, `sidebar.vendite.approvazioni-prezzo`).

---

## Note di esecuzione

- Eseguire scenari 1-4 in **ordine** (preparano i dati per gli scenari successivi)
- Scenari 5-7 indipendenti, ordine libero
- Tempo stimato esecuzione completa: **2-3 ore** con 2 utenti
- In caso di errore: registrare codice + screenshot + steps in issue tracker
- Annotare in fondo al WIP eventuali bug trovati per follow-up

## Criteri di uscita (gate finale)

- [ ] Zero errori JavaScript nella console browser durante tutti gli scenari
- [ ] Zero HTTP 500 nei log backend
- [ ] Zero warning Vue da parent→child props mismatch
- [ ] Toast (save success, reset tipo_variazione, errori) appaiono in alto a destra con durata corretta

## Bug trovati durante esecuzione

(da popolare durante i test)

| #   | Scenario | Sintomo | Codice errore | Workaround | Status |
| --- | -------- | ------- | ------------- | ---------- | ------ |
| -   | -        | -       | -             | -          | -      |

---

*Documento di test UI v5 — 2026-04-23. Aggiornare in coda lista bug e
spostare in `work-done/` quando tutti gli scenari sono ✅ verdi.*
