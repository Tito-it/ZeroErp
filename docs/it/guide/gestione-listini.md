# Guida — Gestione Listini e Pricing (v5)

> **Ultima revisione**: 23 aprile 2026 — chiusura end-to-end Sprint E+F
> (workflow L3 approvazione + cleanup + doc API estesa). Il modello v5
> è feature-complete (resolver a 3 stadi: promo → contratto → categoria
> + L1+L2+L3 autorizzazioni prezzi + BoM versionata immutabile).
>
> La versione pre-v5 è archiviata in [gestione-listini-pre-v5](archive/gestione-listini-pre-v5.md)
> per riferimento storico.
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.listini](/dbzero/vendite/tabelle/listini) / [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) / [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) + [categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini)
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) + [contratti_righe](/dbzero/vendite/tabelle/contratti_righe) + [contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> * [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) (BoM versionata immutabile)
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> * [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito)
>
> **Vedi anche** — API e service backend:
>
> * [PricingService (backend)](/backend/vendite/manual/pricing_service)
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Approvazioni prezzo (workflow L3)](/backend/vendite/manual/api_approvazioni_prezzo)
> * [API Preventivi](/backend/vendite/manual/api_preventivi) (con flag `richiesta_approvazione` per L3)
> * [API Contratti](/backend/vendite/manual/api_contratti) / [API Promo articoli](/backend/vendite/manual/api_promo_articoli) / [API Matrice categorie/listini](/backend/anagrafiche/manual/api_categorie_clienti_listini)
>
> **Vedi anche** — piani sprint:
>
> * [Storico piano sprint v5 (work-done)](/dev/work-done/sviluppo-listini-v5) — tutti gli sprint chiusi end-to-end
> * [Piano test UI v5 (WIP attivo)](/dev/work-in-progress/sviluppo-listini-v5-test-ui) — 7 scenari per validazione UI

---

## 1. Cosa risponde il sistema pricing

> *"Quanto costa questo articolo, per questo cliente, in questa data, per questa utility?"*

Il sistema pricing v5 risponde deterministicamente attraverso **3 stadi** valutati in sequenza:

1. **STADIO 0 — PROMO**: esiste una promozione temporanea attiva su quella coppia (articolo, uom)? Se sì, vince.
2. **STADIO 1 — CONTRATTO**: il cliente ha un contratto individuale attivo? Se sì, il prezzo viene dal contratto (modalità A/B/C).
3. **STADIO 2 — CATEGORIA**: in assenza di contratto, il cliente ha una categoria commerciale? Se sì, la matrice categoria→listino determina il prezzo base.

Non ci sono tie-break: la struttura dati **garantisce** che ogni stadio produca al massimo una risposta.

---

## 2. Le entità in gioco

### 2.1 Listino

È un **contenitore di prezzi** identificato dalla combinazione:

- `utility_id` — il servizio (Gas, Energia, Idrico, "Base" per commercio)
- `tipologia_id` — la categoria di voce (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA, PRODOTTI, SERVIZI)
- `emittente_soggetto_ruolo_id` — chi emette la fattura (dimensione interna)

**Un solo listino** per ogni quadrupla (utility, tipologia, emittente, codice). Non esistono "listini derivati": le variazioni commerciali vivono altrove.

Un listino contiene:

- **Versioni** (`listini_versioni`) — finestre temporali con stato BOZZA → ATTIVA → CHIUSA. Solo una versione ATTIVA per listino nel periodo (vincolo `EXCLUDE`).
- **Righe** (`listini_righe`) — per ogni versione: (articolo, uom) → prezzo. Forma pura, senza dimensioni di scope.

### 2.2 Categoria cliente

Rappresenta la **politica commerciale trasversale** (STANDARD, BASE, SILVER, GOLD, PLATINUM).

Caratteristiche:

- ogni `billing_account` ha esattamente una `categoria_cliente_id` (default STANDARD)
- la categoria decide se il cliente **partecipa alle promo** (flag `partecipa_promo`)
- la categoria indirizza al listino corretto via la **matrice**

### 2.3 Matrice categoria → listino

Tabella `anagrafiche.categorie_clienti_listini`. Per ogni quadrupla:

```
(categoria_cliente, utility, emittente, classe_utenza opz.) → listino + variazione opz.
```

La variazione è opzionale (`tipo_variazione` + `valore_variazione`, coppia coerente):

- `PERCENTUALE` — firmata (negativo = sconto, positivo = maggiorazione)
- `VALORE_FISSO` — firmato
- Nessuna variazione → prezzo base del listino tal quale

`classe_utenza_id` è opzionale: la ricerca prova prima il match esatto poi il fallback a NULL (dimensione pricing per utility con gradazione, es. DOM-BTA su energia).

Vincolo `EXCLUDE`: non possono esistere due righe attive sovrapposte per la stessa quadrupla → il resolver STADIO 2 non ha ambiguità.

### 2.4 Contratto

È l'**accordo individuale** tra cliente ed emittente. Tre modalità possibili:

| Modalità | Listino | Variazione globale | Righe override | Quando usarla |
|---|---|---|---|---|
| **A** — listino + variazione | sì | sì | vuote o parziali | "Listino standard 2026 scontato 10%" |
| **B** — listino con override mirati | sì | sì o no | alcune righe con prezzo forzato | "Listino standard, ma art X a €50 fisso" |
| **C** — interamente negoziato | no | no | tutte le righe con prezzo | Grande cliente con condizioni 100% custom |

Un trigger DB blocca la transizione DRAFT → ATTIVO se la modalità C ha righe vuote (errore `E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE`).

### 2.5 Promo

Tabella `vendite.promo_articoli`. È un **overlay temporale** indipendente:

- (articolo, uom, validità) → tipo e valore variazione
- batte qualsiasi altro stadio se il cliente appartiene a una categoria con `partecipa_promo = true`
- ammette `PREZZO_FISSO` (prezzo assoluto sostitutivo) — vietato negli altri stadi

---

## 3. Resolver — i 3 stadi in dettaglio

La funzione `vendite.fn_resolve_prezzo_listino_v2` riceve:

- articolo, uom, data, billing_account
- utility, emittente (derivato dal JWT dell'operatore, 1-a-1)
- classe_utenza (opzionale, derivata da contratto o istanza)

### STADIO 0 — Promo overlay

```
Esiste riga in promo_articoli (articolo, uom, data) attiva?
  E la categoria del BA ha partecipa_promo = true?
    → SÌ: prezzo_base = STADIO 1/2, applica variazione promo → STOP
           origine = PROMO
    → NO: vai allo STADIO 1
```

### STADIO 1 — Contratto

```
Esiste contratto ATTIVO per (ba, utility, data)?
  → SÌ:
      Esiste riga override per (articolo, uom) con prezzo_unitario NOT NULL?
        → SÌ: prezzo = prezzo_unitario; origine = CONTRATTO_OVERRIDE
        → NO: se contratto ha listino_id (modalità A o B senza override):
               prezzo_base = riga listino
               applica variazione_globale se presente
               origine = CONTRATTO_LISTINO
             altrimenti (modalità C senza riga):
               ERRORE E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
  → NO: vai allo STADIO 2
```

### STADIO 2 — Categoria cliente

```
BA ha categoria_cliente_id (sempre sì: default STANDARD)?
  → SÌ:
      Cerca in matrice (categoria, utility, emittente, data):
        - prima: classe_utenza_id = <derivato>
        - fallback: classe_utenza_id IS NULL
      Se nessun match: ERRORE E_CATEGORIA_LISTINO_NON_MAPPATA
      Altrimenti:
        prezzo_base = riga listino
        applica variazione matrice se presente
        origine = CATEGORIA
```

### Output

Il resolver ritorna sempre:

- `prezzo_finale` e `prezzo_base_snapshot`
- `origine` ∈ `{PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA}`
- `tipo_variazione_applicata`, `valore_variazione_applicata`
- FK popolate del caso: `listino_id`, `contratto_id`, `promo_id`, `categoria_cliente_listino_id`

Lo snapshot viene salvato in `commesse_attivita` (8 colonne dedicate) per audit permanente.

---

## 4. Convenzione segno delle variazioni

Le variazioni di tipo `PERCENTUALE` e `VALORE_FISSO` sono **firmate**:

| Valore | Effetto |
|---|---|
| **Negativo** (es. -10) | Sconto (10%  di riduzione o -10€ di correzione) |
| **Positivo** (es. +5) | Maggiorazione |
| **Zero** | Vietato dal service (no-op inutile) |

`PREZZO_FISSO` (ammesso solo in promo) è un prezzo assoluto ≥ 0 che **sostituisce** il prezzo base.

Formule applicate dal resolver:

```
PERCENTUALE:  prezzo_finale = prezzo_base × (1 + valore / 100)
VALORE_FISSO: prezzo_finale = prezzo_base + valore
PREZZO_FISSO: prezzo_finale = valore
```

---

## 5. Articoli, tipologia e BoM

### 5.1 Tipologia articolo

Ogni articolo ha `listino_tipologia_id` (FK a `config.listini_tipologie`). Un articolo può essere inserito solo in listini con la **stessa tipologia** (guard DB trigger `trgfn_listini_righe_guard_tipologia`).

Esempi:

- articolo di tipologia `PRODOTTI` → inseribile solo in listini PRODOTTI
- articolo di tipologia `CONSUMO` (voce utility) → solo in listini CONSUMO per quella utility

### 5.2 Distinta base (BoM) — componenti esposti

Un articolo composito (`is_composito = true`) ha una distinta base in `articoli_componenti`. Il flag `esposto_in_fattura` decide il comportamento:

- **Nessun componente esposto**: il composito ha un prezzo unico (riga listino sul composito, o somma componenti a fallback)
- **Almeno un componente esposto**: il resolver ritorna N righe (una per componente), la pipeline di creazione attività espande l'articolo composito in N righe `commesse_attivita` separate

Logica completa in [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito).

### 5.3 Immutabilità della BoM — pattern "chiudi + nuova versione"

La distinta base è **immutabile nel tempo**: una volta inserita una riga in `articoli_componenti`, i campi di struttura (componente, `coeff_qta`, `esposto_in_fattura`, `obbligatorio`, `partecipa_qta`, `determina_qta_padre`, `valido_dal`) non possono essere modificati in place. Il trigger DB `trgfn_articoli_componenti_block_modifica_struttura` blocca gli UPDATE con errore `E_BOM_MODIFICA_VIETATA` e le DELETE (una riga BoM non si elimina mai: si chiude).

**Perché**: le commesse e le fatturazioni che hanno già consumato quella BoM restano ancorate alla struttura del momento, e lo snapshot `prezzo_bloccato` sulle righe commessa preserva il calcolo fatto all'epoca. Modificare la BoM "sotto" a una commessa emessa romperebbe la ricostruzione storica.

**Come si correggono errori o si evolve una distinta base**:

1. **Chiudi la riga corrente**: imposta `valido_al = oggi` (l'unico campo editabile in place). Dalla UI: menu kebab della riga → "Chiudi riga", oppure click sulla cella `valido_al` inline.
2. **Inserisci una nuova versione**: dalla UI → menu kebab → "Duplica come nuova versione". Il form si pre-compila con i valori della riga sorgente, `valido_dal = oggi`, `valido_al` vuoto. Modifica i campi desiderati e salva.

L'exclusion constraint daterange `ex_articoli_componenti_no_overlap` sull'indice GiST `(prodotto_id, componente_id, validita)` garantisce che non ci siano sovrapposizioni temporali tra versioni dello stesso componente.

**Campi ancora modificabili in place**: `note`, `meta`, `attivo`, `valido_al` (chiusura). Non sono campi di struttura.

---

## 6. Autorizzazioni override prezzo (L1)

Nel preventivo, il prezzo suggerito dal resolver può essere **sovrascritto manualmente** dall'operatore. L1 è attivo:

- Se il payload riga ha `prezzo_unitario` uguale al suggerito → passa sempre
- Se è diverso → il service verifica l'azione processo `prezzo_override_manuale`
  - Autorizzato: salva con origine `MANUALE`, traccia in `meta` il resolver originale
  - Non autorizzato: `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` (403)

Il badge UI mostra l'origine del prezzo (listino/contratto/promo/manuale) e il delta eventuale.

L2 (limite sconto/maggiorazione %) è in produzione (Sprint D 22-04-2026): vedi `VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT` in `config.parameters` e l'endpoint diagnostico `GET /vendite/pricing/limiti-utente/`.

### 6.1 L3 — Workflow approvazione out-of-policy (Sprint E)

Quando l'operatore richiede un prezzo che viola i limiti L2, può **richiedere approvazione al responsabile** invece di rinunciare. Il flusso:

1. **Riga oltre L2 + flag `richiesta_approvazione=true`**: il backend NON solleva errore. Crea una pratica `APPROVAZIONE_PREZZO` (stato APERTA, priorità NORMALE) e salva la riga con `stato_approvazione_prezzo='PENDING'` collegata alla pratica via `pratica_approvazione_prezzo_id`.
2. **Email best-effort al recipient configurato** in `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` (parameter scope user/group/emittente). Se il parameter non è configurato, la pratica resta visibile in coda senza notifica push.
3. **L'approver** (utente con azione `approva_prezzo_override` abilitata) vede la coda in `/vendite/approvazioni-prezzo/` filtrata per scope emittente. Per ogni pratica può:
   - **Approvare** → riga `stato_approvazione_prezzo='APPROVED'`, pratica CHIUSA con nota interna OK
   - **Rifiutare** → riga `stato_approvazione_prezzo='REJECTED'`, pratica CHIUSA con nota interna KO + motivazione

**Trigger DB di guardia**:
- `trgfn_preventivi_guard_transizione_approvazione`: blocca passaggio preventivo→ACCETTATO se esistono righe `stato_approvazione_prezzo='PENDING'` (`E_PREVENTIVO_RIGHE_PRICING_PENDENTI`)
- `trgfn_preventivi_righe_guard_pending`: blocca modifica struttura riga PENDING; permette solo transizione di stato approvazione (`E_RIGA_PREZZO_PENDENTE`)

**Endpoint API**:
- `POST /api/v1/vendite/righe/<riga_id>/approva-prezzo/` (body `{nota?}`)
- `POST /api/v1/vendite/righe/<riga_id>/rifiuta-prezzo/` (body `{motivazione?}`)
- `GET /api/v1/vendite/approvazioni-prezzo/?limit=&offset=`

**Riavvio richiesta**: se l'approver rifiuta, l'utente può modificare il prezzo (riga REJECTED non è bloccata) e ri-tentare. Una nuova violazione L2 con `richiesta_approvazione=true` crea una nuova pratica.

---

## 7. Ciclo di vita operativo

### 7.1 Nuovo listino

1. Admin: crea listino (codice, descrizione, utility, tipologia) — emittente derivato dall'operatore
2. Crea versione BOZZA con `valido_dal`
3. Popola righe prezzo (articoli coerenti con tipologia)
4. Attiva versione → BOZZA passa ad ATTIVA; eventuali versioni precedenti autoclose

### 7.2 Assegnare un listino a un cliente (scope categoria)

1. Definisci la categoria cliente (STANDARD, SILVER, GOLD…)
2. Imposta sul `billing_account` la `categoria_cliente_id`
3. Admin: crea riga matrice per (categoria, utility, emittente, classe_utenza opz.) → listino + variazione

Tutti i clienti della stessa categoria, utility, emittente condivideranno la regola senza duplicare listini.

### 7.3 Contratto individuale

1. Commerciale: stipula contratto con BA, scegliendo modalità A/B/C
2. Inserisce righe (se C: obbligatorie per ogni articolo preventivabile)
3. Transizione DRAFT → ATTIVO → il resolver STADIO 1 userà il contratto

### 7.4 Promo

1. Admin vendite: crea riga in `promo_articoli` (articolo, uom, periodo, tipo+valore variazione, codice)
2. La promo vale per tutti i BA con categoria che partecipa promo
3. A scadenza periodo (`valido_al`), la promo smette di applicarsi automaticamente

---

## 8. Garanzie DB

Il database rafforza la determinismo con vincoli espliciti (non è "responsabilità del client"):

| Vincolo | Tabella | Cosa garantisce |
|---|---|---|
| `ex_contratti_no_overlap` | `contratti` | Un solo contratto attivo per (BA, istanza, utility, ambito) nel periodo |
| `ex_categ_cli_listini_no_overlap` | `categorie_clienti_listini` | Una sola riga matrice per (categoria, utility, emittente, classe) nel periodo |
| `ex_promo_articoli_no_overlap` | `promo_articoli` | Una sola promo attiva per (articolo, uom) nel periodo |
| `ex_listini_versioni_no_overlap` | `listini_versioni` | Una sola versione ATTIVA per listino nel periodo |
| `uq_listini_righe_key_attiva` | `listini_righe` | Una sola riga attiva per (versione, articolo, uom) |
| `trgfn_listini_righe_guard_tipologia` | trigger | Articolo e listino devono avere la stessa tipologia |
| `trgfn_contratti_modalita_c_righe_complete` | trigger | Modalità C: attivazione blocca se righe incomplete |
| `trgfn_contratti_utilities_guard_tipo_classe` | trigger | Tipo/classe utenza coerenti con ambito (NULL per COMMERCIO) |

Il resolver poggia su queste invarianti — il codice Python non deve duplicarle.

---

## 9. Errori espliciti

Nessun fallback silenzioso. Ogni scenario non risolvibile produce un errore strutturato:

| Codice | Quando |
|---|---|
| `E_PREZZO_LISTINO_NON_TROVATO` | BA senza contratto e senza categoria mappata |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` | Categoria esistente ma nessuna riga in matrice per la quadrupla |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | Listino risolto ma nessuna riga prezzo per (articolo, uom) |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | Contratto modalità C senza riga per l'articolo richiesto |
| `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE` | Articolo in listino di tipologia diversa |
| `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` | L1: override prezzo non autorizzato |
| `E_VENDITE_PRICING_FAILED` | Errore generico pricing (envelope, dettaglio in `detail`) |
| `E_BOM_MODIFICA_VIETATA` | Tentata modifica/eliminazione campo struttura BoM. Risolvere con pattern chiudi+inserisci nuova versione (vedi §5.3) |
| `E_BOM_VALIDO_AL_INVALIDO` | Tentata chiusura riga BoM con `valido_al < valido_dal` |
| `E_PREVENTIVO_RIGHE_PRICING_PENDENTI` | Tentata accettazione preventivo con righe in attesa di approvazione (L3) |
| `E_RIGA_PREZZO_PENDENTE` | Tentata modifica struttura riga in stato `stato_approvazione_prezzo='PENDING'` |
| `E_APPROVAZIONE_PREZZO_NON_AMMESSA` | Tentata approva/rifiuta su riga non PENDING o senza pratica collegata; oppure coda approvazioni richiesta da admin globale senza emittente |

Tutti gestiti dal frontend con messaggi user-friendly (vedi `error_policies.py` backend).

---

## 10. Cosa NON c'è più (modello pre-v5)

Per chi arrivava dal vecchio modello:

- ❌ `vendite.listini_associazioni` — **droppata** (F1-DB-26). Il suo ruolo è coperto da categoria cliente + contratto + dimensione emittente interna al listino.
- ❌ "Listini derivati" con `listino_base_id` e variazione — mai implementati. La variazione vive nella matrice (per categoria) o nel contratto (individuale).
- ❌ `catalogo.articoli.voce_utility` — droppata. L'equivalente v5 è `listino_tipologia_id`.
- ❌ Resolver a 7 livelli con `match_rank` — sostituito dal resolver deterministico a 3 stadi senza tie-break.
- ❌ Campo `priorita` su versioni/associazioni — rimosso. Le invarianti `EXCLUDE` garantiscono univocità, niente tie-break.

---

*Gestione Listini e Pricing — ZeroERP v5 (23 aprile 2026, chiusura end-to-end)*
