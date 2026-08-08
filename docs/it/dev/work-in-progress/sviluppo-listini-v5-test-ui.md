# Test UI listini v5 — Piano operativo

> WIP creato il 2026-04-23 a chiusura Sprint v5.
> Scopo: piano test UI strutturato per validare end-to-end il modello v5
> (categorie + contratti + promo + BoM + L1+L2+L3) prima di considerare
> l'implementazione "blessed" per l'uso quotidiano.

## Stato del modello

Tutti gli sprint v5 sono **chiusi end-to-end** (DB+BE+FE+DOC). Vedi
[sviluppo-listini-v5.md §14.9](../work-done/sviluppo-listini-v5) per il tracking
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
- Almeno 3 utenti di test (vedi sezione "Setup utenti di test" sotto per la procedura
  operativa di creazione):
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

## Setup utenti di test (Junior/Senior)

"Junior" e "Senior" non sono ruoli nativi del modello permessi: sono **operatori
standard** distinti dall'attivazione/disattivazione di **due azioni di processo**
sull'area `vendite`. La definizione e la procedura sotto chiariscono come
istanziarli per i test, evitando ambiguita' su come assegnare i permessi.

### Azioni di processo coinvolte

Gia' presenti nel seed [azioni_processo.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv):

| id  | codename                  | area    | Concede di…                                                                                       |
| --- | ------------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| 9   | `prezzo_override_manuale` | vendite | Modificare manualmente il `prezzo_unitario` di una riga preventivo (override su pricing risolto)  |
| 10  | `approva_prezzo_override` | vendite | Approvare/rifiutare le pratiche `APPROVAZIONE_PREZZO` create da operatori senza override autonomo |

### Profilo dei 3 ruoli

| Aspetto                              | Admin (Tid)                 | Junior                                                    | Senior / Approver          |
| ------------------------------------ | --------------------------- | --------------------------------------------------------- | -------------------------- |
| `ruolo_applicativo`                  | `OPERATORE`                 | `OPERATORE`                                               | `OPERATORE`                |
| Binding `SUPER_ADMIN` (profilo 9100) | SI (bypass totale)          | NO                                                        | NO                         |
| Area `vendite`                       | bypass                      | `MODIFICA` (TUTTO)                                        | `MODIFICA` (TUTTO)         |
| Area `amministrazione`               | `MODIFICA` (per Scenario 1) | `BLOCCATO` o non assegnata                                | `BLOCCATO` o non assegnata |
| Azione `prezzo_override_manuale`     | bypass                      | **OFF**                                                   | **ON**                     |
| Azione `approva_prezzo_override`     | bypass                      | **OFF**                                                   | **ON**                     |
| Emittente fiscale assegnato          | nessuno (multi-EF)          | uno specifico (lo stesso del Senior per coerenza scenari) | uno specifico (idem)       |

> **Nota su lookup cross-dominio.** Gli autocomplete usati nel drawer preventivo
> (articoli, billing account, istanze utility) sono stati allineati al pattern
> dei lookup core (`skip_area_check = True`): non richiedono LETTURA sulle aree
> `catalogo`/`anagrafiche`. Resta protezione JWT + throttling search + scope
> emittente lato repository (un operatore vede solo BA/istanze del suo EF).
> L'operatore Senior/Junior puo' quindi avere solo `vendite = MODIFICA` senza
> aggiungere LETTURA su altre aree, e il drawer preventivo continua a funzionare.

### Procedura operativa di creazione

Eseguire come Admin (Scenario 1 prerequisito).

1. **Crea profilo "OPERATORE_PRICING_JUNIOR"** (`tipo = AD_HOC`):
   - Permessi area: `vendite = TUTTO`, tutte le altre aree = `BLOCCATO`
   - Azioni: nessuna
2. **Crea profilo "OPERATORE_PRICING_SENIOR"** (`tipo = AD_HOC`):
   - Permessi area: `vendite = TUTTO`, tutte le altre aree = `BLOCCATO`
   - Azioni: `prezzo_override_manuale` + `approva_prezzo_override` (entrambe ON)
3. **Crea i due utenti operatore** (es. `pricing.junior@test.it` e
   `pricing.senior@test.it`). Per ognuno: associa la risorsa umana, l'EF
   "test" (lo stesso per entrambi), invia invito attivazione.
4. **Bind del profilo all'identita'**:
   - Junior → bind a `OPERATORE_PRICING_JUNIOR`
   - Senior → bind a `OPERATORE_PRICING_SENIOR`
5. **Verifica**: login come Junior → la sidebar non mostra "Approvazioni prezzo"
   (azione 10 OFF); modifica prezzo riga preventivo → 403 `E_PRICING_OVERRIDE_NON_AUTORIZZATO`.
   Login come Senior → "Approvazioni prezzo" visibile e modifica prezzo riga OK.

### Scorciatoie ammesse

- Per i test di sola "approvazione" (§4.4-§4.6) si puo' anche usare l'Admin
  come Approver (bypass SUPER_ADMIN), saltando il Senior. La coda
  `approvazioni-prezzo` sara' visibile, ma il match emittente del filtro coda
  va valutato: l'Admin globale (no EF assegnato) solleva
  `E_APPROVAZIONE_PREZZO_NON_AMMESSA` (vedi §4.7). Per testare la coda
  filtrata serve un utente con EF (= Senior).
- L'azione `prezzo_override_manuale` di Senior puo' essere disattivata al
  volo per riprodurre il caso Junior senza creare un secondo utente, ma
  perdi il test simultaneo di "Junior crea richiesta + Senior approva".

## Indice scenari

1. **Setup admin pricing v5** (categorie, matrice, listini, contratti modalità A e C, promo)
2. **Pricing operativo** (preventivo + auto-fill + L1+L2+L3)
3. **BoM versionata** (chiudi riga + duplica nuova versione)
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

- [X] `/vendite/preventivi/` → nuovo preventivo per BA GOLD
- [X] Apri righe → aggiungi riga con articolo della promo (1.5)
- [X] Verifica `prezzo_unitario` pre-compilato dal resolver (3 stadi)
- [X] Badge origine prezzo: PROMO (stadio 0 batte tutto)
- [X] Cambia articolo a uno senza promo → origine CONTRATTO_LISTINO o CATEGORIA

### 2.2 L1 override

- [X] Login Senior (ha `prezzo_override_manuale`) → modifica prezzo riga
- [X] Verifica `meta.origine_prezzo='MANUALE'` + audit completo (FE non visibile, da DB)
- [X] Login operatore SENZA   aggiorna `prezzo_override_manuale` → tentativo override → errore 403 `E_PRICING_OVERRIDE_NON_AUTORIZZATO`

### 2.3 L2 limiti hint

- [X] Riapri drawer riga: hint "Variazione prezzo ammessa: sconto fino al 10%, maggiorazione fino al 5%" sotto il campo prezzo
- [X] Hint visibile in IT e in EN (switch lingua)
- [X] Imposta sconto 8% (entro limite) → save OK
- [X] Imposta sconto 25% (oltre limite) → banner inline `E_PRICING_SCONTO_ECCESSIVO`
  - [X] Detail mostra "Sconto richiesto: 25.00% — massimo ammesso: 10%."
  - [X] Pulsante "Richiedi approvazione" attivo

### 2.4 Suggerisci prezzo da diagnostico

- [X] Apri Dialog test resolver da `/vendite/listini/` → compila contesto
- [X] Esegui → output con `prezzo_finale`, `origine`, `listino_id`/`contratto_id`/`promo_id`

---

## Scenario 3 — BoM versionata (Sprint C immutabilità)

### 3.1 Trigger guard immutabilità

- [X] Articolo composito creato in 1.6 → riapri sub-drawer BoM
- [X] Verifica banner info "BoM immutabile" presente
- [X] Verifica menu kebab di riga: presenti "Gestisci Note", "Duplica come nuova versione", "Chiudi riga". **NESSUN "Elimina"** (rimosso intenzionalmente)
- [X] Click "Chiudi riga" sul componente C1 → dialog conferma `valido_al = oggi`
- [X] Conferma → toast "Riga BoM chiusa", riga ora ha `valido_al` valorizzato

### 3.2 Duplica come nuova versione

Workflow a 2 step (riallineato 2026-05-10):

- [X] Click kebab sulla riga **aperta** → "Duplica come nuova versione"
- [X] Si apre il **dialog "Duplica versione componente"** con DatePicker `chiudi_al` (default oggi) + messaggi info/warn
- [X] Conferma "Duplica versione" → toast **"Riga BoM chiusa"**, dialog si chiude, sorgente nella lista ora ha `valido_al` valorizzato
- [X] Subito dopo si **apre il form "Nuova versione componente"** con banner warn `nuova_versione_hint` ("Sorgente '{codice}' chiusa al {data}…")
- [D] Campi pre-compilati dai valori della riga sorgente, `valido_dal = chiudi_al + 1`
- [S] Cambia `coeff_qta` (es. da 2 a 3) — tutti i campi sono editabili
- [S] Salva → toast **"Componente aggiunto"**
- [S] Lista BoM ora mostra 2 righe (vecchia chiusa + nuova attiva con `coeff_qta=3`)
- [X] Variante: clicca "Annulla" sul form pre-compilato → la sorgente resta chiusa, nessuna nuova riga creata. Riapri il flow con "+" o ripeti "Duplica" per inserire la nuova versione manualmente

### 3.3 Defense-in-depth trigger DB

Lo scenario verifica che i trigger DB siano l'ultima linea di difesa: anche
se la UI viene bypassata (FE buggato, attaccante con curl), il backend
rifiuta le modifiche di struttura BoM con codice errore parlante. Si
esegue dalla Console DevTools del browser (utente gia' loggato).

#### Step 0 — trova `articolo_id` e `componente_id` di una riga aperta

L'`articolo_id` lo prendi dal Network tab guardando l'URL della GET
`/api/v1/catalogo/articoli/<UUID>/` quando apri il drawer dell'articolo
"Pacchetto-test" (§1.6).

```js
const TOKEN = localStorage.getItem('access_token')
const ARTICOLO_ID = 'PASTE_UUID_ARTICOLO_QUI'
const r = await fetch(`/api/v1/catalogo/articoli/${ARTICOLO_ID}/componenti/`, {
  headers: { Authorization: `Bearer ${TOKEN}` }
})
const body = await r.json()
const aperta = body.data.results.find(x => !x.valido_al)
console.log({ ARTICOLO_ID, COMPONENTE_ID: aperta?.id, valido_dal: aperta?.valido_dal })
window.__test = { ARTICOLO_ID, COMPONENTE_ID: aperta?.id, TOKEN }
```

#### Test 3.3 #1 — modifica campo struttura via PATCH diretto

- [X] Esegui in Console lo snippet sotto. **Verde 2026-05-10.**

```js
const { ARTICOLO_ID, COMPONENTE_ID, TOKEN } = window.__test
const r = await fetch(`/api/v1/catalogo/articoli/${ARTICOLO_ID}/componenti/${COMPONENTE_ID}/`, {
  method: 'PATCH',
  headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ coeff_qta: 99 })
})
console.log(r.status, await r.json())
```

Atteso: HTTP **409**, body `error.code = "E_BOM_MODIFICA_VIETATA"`,
`error.message` con hint "chiudi+inserisci" (dal seed `messaggi_errore`).

> **Bug fix 2026-05-10**: la prima esecuzione di questo test ha rilevato
> che la policy `E_BOM_MODIFICA_VIETATA` mancava in
> [error_policies.py](../../../../backend/apps/core/services/error_policies.py),
> per cui il middleware cadeva sul fallback HTTP 400 invece di 409. Policy
> aggiunta esplicitamente con `http_status=409` + `user_message`. Vedi
> tabella "Bug trovati" in fondo al documento.

#### Test 3.3 #2 — chiusura con data invalida (`valido_al < valido_dal`)

- [X] Esegui in Console lo snippet sotto. **Verde 2026-05-10.**

```js
const { ARTICOLO_ID, COMPONENTE_ID, TOKEN } = window.__test
const r = await fetch(`/api/v1/catalogo/articoli/${ARTICOLO_ID}/componenti/${COMPONENTE_ID}/`, {
  method: 'PATCH',
  headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ valido_al: '1999-01-01' })
})
console.log(r.status, await r.json())
```

Atteso: HTTP **400**, body `error.code = "E_BOM_VALIDO_AL_INVALIDO"`,
`error.message` parlante "valido_al non puo' essere precedente a valido_dal".

#### Note di pipeline

Perche' i codici `E_*` arrivano dal DB ma escono come 4xx puliti: i trigger
BoM sollevano P0001 via `script.fn_log_and_raise_error`. Lato Django,
anche se `fn_update_componente` non cattura esplicitamente la
`DatabaseError` (cattura solo `IntegrityError`), il middleware globale
[`ErrorTranslator._from_database_error`](../../../../backend/apps/core/services/error_translator.py)
estrae il codice `E_*` dal `message_primary` della DatabaseError e applica
la policy registrata in `error_policies.py` (HTTP status + user_message).
Funziona quindi senza translator dedicato lato service.

### 3.4 Espansione compositi — modello unificato (riscritto 2026-05-13)

> **Riferimenti**: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md),
> [refactor-componenti.md](../work-done/refactor-componenti.md) §2 Fase F
> (⛔ documento storico superato: resta valido solo l'elenco dei 4 scenari).
>
> **Pre-requisito**: migration `20260513-01..32` applicate su `dev/db-tid`
> (modello unificato + fix JSONB + default `attivo=TRUE` sempre); BE Fase
> B + FE Fase C/D + Fase E atterrate.
>
> **Decisione 2026-05-13 — BoM contratto immutabile**: tutti i figli BoM
> validi alla data finiscono SEMPRE nella riga con `attivo=TRUE`.
> L'operatore non sceglie la composizione (nessuna checkbox Attivo nel
> Dialog/Panel). Modifica solo i prezzi con gating L1
> `prezzo_override_manuale`.

#### Setup comune ai 4 scenari

- [ ] Articolo composito **`ART-COMP-001`** con BoM (tutti coeff_qta verificati):
  - `ART-CTR-OBB1` (`obbligatorio=TRUE`, `esposto_in_fattura=TRUE`, `coeff_qta=1`, UoM `pz`, IVA `22%`)
  - `ART-LAV-OBB2` (`obbligatorio=TRUE`, `esposto_in_fattura=FALSE`, `coeff_qta=4`, UoM `h`, IVA `22%`)
  - `ART-EXTRA-OPZ` (`obbligatorio=FALSE`, `esposto_in_fattura=TRUE`, `coeff_qta=1`, UoM `pz`, IVA `22%`)
- [ ] Verifica vincolo IVA coerente padre-figli: tentare INSERT BoM con
  figlio IVA `10%` → trigger catalogo solleva `E_BOM_IVA_DISCORDANTE`
- [ ] Listini configurati:
  - `listini_righe`: `ART-CTR-OBB1` €200/pz, `ART-LAV-OBB2` €75/h
  - `listini_righe`: `ART-EXTRA-OPZ` €40/pz
  - `listini_righe_componenti` (bundle, opzionale): vuoto per ora (vedi 3.4.D)
- [ ] Verifica vincolo listino su composito: tentare INSERT
  `listini_righe(ART-COMP-001, ...)` → trigger catalogo solleva
  `E_LISTINO_RIGA_COMPOSITO_VIETATO`
- [ ] Preventivo `PRV0000XXX` in DRAFT, cliente in categoria STANDARD,
  utility configurata, emittente OK

#### Scenario 3.4.A — Tutto da listino (path felice, no override)

- [ ] Operatore apre drawer riga preventivo, seleziona articolo
  `ART-COMP-001`, UoM, qty=1
- [ ] Dialog "Componenti di ART-COMP-001" si apre automaticamente
- [ ] Tabella popolata con **tutti e 3** i componenti (anche l'opzionale):
  - `ART-CTR-OBB1`: tag "Obbligatorio", suggerito €200 (LISTINO), In fattura "Sì"
  - `ART-LAV-OBB2`: tag "Obbligatorio", suggerito €75 (LISTINO), In fattura "No"
  - `ART-EXTRA-OPZ`: tag "Opzionale", suggerito €40 (LISTINO), In fattura "Sì"
- [ ] **Nessuna checkbox Attivo** (BoM contratto immutabile 2026-05-13)
- [ ] Riepilogo dialog: "3 componenti — totale stimato €540"
  (200·1 + 75·4 + 40·1 = €540)
- [ ] Bottone "Conferma componenti" abilitato (nessun prezzo NULL)
- [ ] Click Conferma → Dialog chiude, drawer riga padre mostra
  "3 componenti — totale stimato €540" + bottone "Modifica componenti"
- [ ] Campo prezzo padre disabilitato (tag "Calcolato dai componenti")
- [ ] Click "Salva riga" → riga creata
- [ ] Verifica DB:
  - `preventivi_righe.prezzo_unitario = 540` (SUM trigger `_z90_ricalcola_padre`)
  - `preventivi_righe_componenti`: **3 righe**, tutte `attivo=TRUE`
  - `origine_prezzo`: tutti `CATEGORIA` o `LISTINO` (resolver standalone)
- [ ] Verifica payload BE: `componenti_overrides` **NON** inviato (nessun
  override), `componenti_attivazioni` **NON** inviato
- [ ] EMETTI → ACCETTA → push commessa: toast verde "Push completato"
- [ ] Verifica `commesse_attivita`: **3 righe** (tutti i componenti
  attivi passano in commessa, incluso opzionale)
- [ ] Stato preventivo → EVASO automatico

#### Scenario 3.4.B — Override manuale prezzo su componente (gating L1)

- [ ] Operatore con azione `prezzo_override_manuale`
- [ ] Apre drawer riga, seleziona `ART-COMP-001` qty=2
- [ ] Dialog aperta, righe come 3.4.A ma con qty raddoppiate
  (`ART-CTR` qty=2, `ART-LAV` qty=8, `ART-EXTRA` qty=2)
- [ ] Operatore modifica prezzo `ART-LAV-OBB2` da €75 a €60 (sconto entro L2)
- [ ] Riepilogo aggiornato: "3 componenti — totale stimato €1080"
  (200·2 + 60·8 + 40·2 = €1080)
- [ ] Conferma → drawer mostra summary aggiornato
- [ ] Salva riga → backend riceve payload:
  - `componenti_overrides`: `{ART-LAV-OBB2: "60.000000"}` (solo il prezzo modificato)
  - `componenti_attivazioni`: **NON inviato** (no toggle)
- [ ] DB:
  - 3 righe in `preventivi_righe_componenti`, tutte `attivo=TRUE`
  - `ART-LAV-OBB2.origine_prezzo = MANUALE`, audit meta override
  - Altri due `LISTINO/CATEGORIA`
- [ ] EMETTI → ACCETTA → push commessa: **3 righe** in `commesse_attivita`
- [ ] Test gating L1 (operatore Junior senza `prezzo_override_manuale`):
  - Tenta override prezzo componente nel Dialog → 403
    `E_PRICING_OVERRIDE_NON_AUTORIZZATO`
- [ ] Test guard prezzo 0 obbligatorio: in EDIT panel, modifica
  `ART-CTR-OBB1` a €0 + bottone Save → bottone disabled FE +
  defense-in-depth BE/DB solleva `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`
- [ ] Test guard prezzo 0 opzionale: modifica `ART-EXTRA-OPZ` a €0 → OK
  (opzionali ammettono 0)

#### Scenario 3.4.C — BoM scaduta (errore parlante)

- [ ] Setup: chiudere la riga BoM di `ART-CTR-OBB1` con
  `valido_al = ieri` (pattern chiudi+nuova versione)
- [ ] Operatore apre drawer riga, seleziona `ART-COMP-001` qty=1
- [ ] Dialog tenta di aprire → la chiamata preview rileva BoM con
  meno componenti del previsto:
  - **Variante 1** lookup articolo `has_componenti_alla_data=FALSE`:
    Dialog NON si apre, drawer mostra Message error parlante
  - **Variante 2** BoM con 2 figli residui: Dialog si apre con 2
    componenti, padre = €340 (75·4 + 40·1)
- [ ] Tentativo Salva → se BoM **completamente** vuota alla data:
  - Fn `_init` solleva `E_DOC_COMPOSITO_BOM_VUOTA` con messaggio
    "Articolo composito ART-COMP-001 senza componenti validi alla
    data {data}: BoM scaduta o non configurata."
  - Riga padre **non viene creata** (transazione atomica `@transaction.atomic`)
- [ ] Operatore: aggiornare BoM in catalogo (nuova versione attiva) o
  cambiare data preventivo

#### Scenario 3.4.D — Listino bundle vs standalone (resolver bundle-aware)

- [ ] Setup: inserire in `vendite.listini_righe_componenti` per la
  versione listino corrente del cliente:
  - `(ART-COMP-001, ART-LAV-OBB2, 50€/h)` — prezzo bundle 50 invece
    di 75 standalone
- [ ] Operatore apre drawer riga, seleziona `ART-COMP-001` qty=1
- [ ] Dialog popolata:
  - `ART-LAV-OBB2`: suggerito **€50**, badge **"Listino bundle"**
    (severity `help`, codice origine `LISTINO_BUNDLE`)
  - `ART-CTR-OBB1`: resta €200 (LISTINO standalone)
  - `ART-EXTRA-OPZ`: resta €40 (LISTINO standalone)
- [ ] Riepilogo: "3 componenti — totale stimato €440"
  (200·1 + 50·4 + 40·1 = €440)
- [ ] Conferma + Salva → DB:
  - `preventivi_righe_componenti.origine_prezzo` di `ART-LAV-OBB2` =
    `LISTINO_BUNDLE`
  - Audit `prezzo_resolver_context.origine = LISTINO_BUNDLE`
- [ ] Test variante storica: cambiare data preventivo a un periodo in
  cui `listini_righe_componenti` NON copre `ART-LAV-OBB2` (validita'
  fuori range) → resolver fallback a STADIO 1 standalone €75/h

#### Verifiche finali post-smoke

- [ ] Riepilogo IVA del preventivo: pannello sempre visibile (decisione
  2026-05-13), mostra aggregato per aliquota IVA (footer con totale
  imponibile + imposta + totale documento). I 3 totali compatti
  fallback sono stati rimossi (ridondanti).
- [ ] In `preventivi_righe`, prezzo padre = SUM(figli × coeff_qta) post
  trigger `_z90_ricalcola_padre`
- [ ] Nessun `prezzo_unitario` NULL su `preventivi_righe` (default `0`
  placeholder se composito senza override + resolver fallisce, sovrascritto
  dal trigger SUM)
- [ ] Test promozione articolo standalone su `ART-LAV` (es. €60/h
  promo): nel contesto bundle resta €50 (il bundle vince, decisione
  dominio); per testare il flag `vale_in_contesto_padre = TRUE` sulla
  promo (se implementato in fase 2) si vedrebbe €60 invece di €50

#### Verifiche cross-scenario

- [ ] Riepilogo IVA del documento (`preventivi_riepiloghi_iva`) coerente:
  con figli tutti IVA 22%, padre IVA 22%, una sola riga di aggregato
- [ ] Vista fattura (post emissione lotto): padre con totale + figli
  `esposto_in_fattura = TRUE` come righe descrittive senza importo
  separato (totale documento = solo padre, no duplicazione)
- [ ] Cleanup fixture: articoli `ART-COMP-001`, `ART-CTR-OBB1`,
  `ART-LAV-OBB2`, `ART-EXTRA-OPZ` lasciati attivi per smoke replicato
  su ordini/contratti/ddt (Fase G)

#### Verifica defense-in-depth (cross-scenario)

- [ ] Tenta INSERT diretto su `preventivi_righe_componenti` con
  `componente_id` NON appartenente al BoM dell'articolo padre → trigger
  guard `E_DOC_COMPONENTE_NON_BOM`
- [ ] Tenta INSERT con componente `esposto_in_fattura = FALSE` →
  `E_DOC_COMPONENTE_NON_ESPOSTO`
- [ ] Tenta INSERT con BoM scaduta alla data preventivo →
  `E_DOC_COMPONENTE_BOM_NON_VALIDA`
- [ ] Tenta INSERT con riga padre non composita →
  `E_DOC_RIGA_NON_COMPOSITO`
- [ ] DELETE riga padre → componenti eliminati (FK CASCADE)
- [ ] UPDATE quantita riga padre da 1 a 3 → componenti ricalcolati
  via trigger `script.trgfn_componenti_propaga_qta` (quantita
  componente = `coeff_qta_snapshot × 3`)

#### Edge case all-or-nothing (post-fix 2026-05-11)

- [ ] Setup: preventivo con riga composito CASO A + altra riga normale
- [ ] Simula errore push su un componente (es. integrità DB violata
  in `commesse_attivita` con dato sporco)
- [ ] Push → HTTP 422 `E_COMMESSA_PUSH_PARZIALE_VIETATO`
- [ ] Verifica `commesse_attivita`: **zero righe create** (rollback
  totale atomic)
- [ ] Stato preventivo: **resta ACCETTATO** (no transizione EVASO)
- [ ] `commesse_push_log`: nessun record (rolled back)

---

## Scenario 4 — Workflow L3 (Sprint E end-to-end)

### 4.1 Richiesta approvazione (Operatore Junior)

- [ ] Login Junior (NO `approva_prezzo_override`)
- [ ] Apri preventivo in BOZZA, aggiungi riga con prezzo a sconto 25% (oltre limite L2 10%)
- [ ] Save normale → banner inline `E_PRICING_SCONTO_ECCESSIVO`, pulsante "Richiedi approvazione" attivo
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
- [ ] `/vendite/approvazioni-prezzo/` lista visibile (LETTURA), ma click Approva → 403 `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (manca `approva_prezzo_override`)

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

### #1 — §3.3 Test #1: HTTP status 400 invece di 409

- **Sintomo**: PATCH `coeff_qta` su una riga BoM ritornava `HTTP 400`, mentre il test plan attendeva `HTTP 409`. Il body era già parlante (codice `E_BOM_MODIFICA_VIETATA`, message + hint dal seed `messaggi_errore`), solo lo status era off.
- **Codice errore**: `E_BOM_MODIFICA_VIETATA`
- **Causa**: la policy non era registrata in
  [apps/core/services/error_policies.py](../../../../backend/apps/core/services/error_policies.py)
  per cui il middleware cadeva sul fallback generico `http_status=400` per
  qualunque codice `E_*` non noto.
- **Workaround**: nessuno — il codice e il message arrivavano comunque corretti, ma il toast UI veniva classificato come "validazione" invece che come "conflitto".
- **Status**: **Fixato 2026-05-10**. Aggiunta policy esplicita con `http_status=409` + `user_message`. Test BE 501/501 verdi. Richiesto restart gunicorn (no `--reload`).

### #2 — §3.4 push commessa: `E_IDEMPOTENCY_KEY_REQUIRED`

- **Sintomo**: click su "Push commessa" da `PreventiviIntegrazione.vue` → toast errore con `error.code = "E_IDEMPOTENCY_KEY_REQUIRED"`, body `detail = "Header Idempotency-Key mancante."`
- **Codice errore**: `E_IDEMPOTENCY_KEY_REQUIRED`
- **Causa**: in [preventiviApi.js](../../../../frontend/src/vendite/preventivi/api/preventiviApi.js)
  le funzioni `pushCommessa` e `generaPratica` chiamano endpoint BE con
  `require_idempotency_key=True` ma non inviavano l'header.
- **Workaround**: nessuno.
- **Status**: **Fixato 2026-05-10**. Entrambe le funzioni usano ora il
  helper centralizzato `generateIdempotencyKey()` da
  [core/utils/idempotency.js](../../../../frontend/src/core/utils/idempotency.js)
  (con fallback per non-secure context). Build vite verde.

### Pattern emerso

I bug #1 della duplica versione BoM (sessione precedente) e #2 di push
commessa sono entrambi del **tipo "FE non invia Idempotency-Key dove il BE
la richiede"**. Lo helper `generateIdempotencyKey()` esiste, ma scoprire i
chiamanti orfani avviene a runtime un endpoint alla volta. Opportunita'
di refactor: introdurre un wrapper API tipo `apiPostIdempotent(url,
payload)` che imposta l'header automaticamente, oppure esporre una
property `idempotent: true` lato BE/OpenAPI da usare per il check.
Per ora la regola sta nei commenti dei wrapper FE singoli.

---

*Documento di test UI v5 — 2026-04-23. Aggiornare in coda lista bug e
spostare in `work-done/` quando tutti gli scenari sono ✅ verdi.*
