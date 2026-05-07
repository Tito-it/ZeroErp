# Sviluppo Listini — Pricing ZeroERP (WIP)

> Stato: **BACKEND E FRONTEND IMPLEMENTATI, DA TESTARE SU UI REALE.**
>
> Ultima revisione: aprile 2026
>
> Questo documento consolida:
> * l'analisi architetturale DB (ex `gestione-listini.md`, 24-02-2026)
> * lo stato di backend + frontend listini (ex `gestione-articoli-listini.md`, parti §4, §6, checklist Fasi 5-6)
> * i bloccanti e la roadmap aperta
>
> Documento sorgente canonico per lo sviluppo listini. I due WIP precedenti sono stati consolidati qui.
>
> **Rettifiche prezzi** (DB-L4) sono trattate nel documento dedicato [sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md).
>
> Prerequisiti gia' disponibili:
>
> * Schema `catalogo` completo (articoli, UoM, BoM, note) — vedi [work-done/gestione-articoli.md](../work-done/gestione-articoli.md)
> * Schema `vendite.listini*` operativo fino a DB-L3
> * Funzione DB: `vendite.fn_resolve_prezzo_listino`, `vendite.fn_resolve_commessa_prezzi`
> * Backend + frontend listini implementati (vedi §6 e §7)
>
> Riferimenti:
>
> * [docs/it/dbzero/vendite/tabelle/listini.md](../../dbzero/vendite/tabelle/listini.md) — schema listini
> * [docs/it/dev/work-done/gestione-articoli.md](../work-done/gestione-articoli.md) — dominio catalogo (completato)
> * [docs/it/dev/work-in-progress/gestione-commesse-v2.md](../work-in-progress/gestione-commesse-v2.md) — integrazione commessa
> * [docs/it/dev/api.md](../api.md) — linee guida API

---

## 1) Obiettivo

Definire un modello listini/prezzi scalabile che supporta:

1. pricing standard (prezzo fisso/versionato),
2. pricing utilities (gas/energia/idrico) con evoluzione futura a formule/scaglioni,
3. integrazione piena con modello commessa v2,
4. rettifiche prezzi sia manuali che automatiche.

Documento di riferimento per decisioni DB, backend e frontend listini. La logica e' la stessa sia per il dominio utility (gas, energia, idrico) sia per il dominio commercio (servizi, manifatturiero).

---

## 2) Stato attuale e gap

### Stato attuale

1. Esiste una base molto buona su articoli, componenti BoM e UoM operative (vedi [work-done/gestione-articoli.md](../work-done/gestione-articoli.md)).
2. Esistono snapshot di conversione quantita (`factor_to_base`) nelle righe documento.
3. Esiste in `config` una classificazione tariffaria (`tipi_tariffe_ee`) ma non un motore listini completo.
4. Backend e frontend listini **implementati e verdi sui test unitari**; manca la verifica su UI reale e il motore rettifiche.

### Gap chiusi (DB-L1, L2, L3)

1. Struttura listini/versioni/righe/associazioni operativa
2. Resolver prezzo deterministico con precedenze
3. Integrazione commessa v2 (snapshot pricing, `prezzo_bloccato`, `pricing_mode`)
4. Base dati pronta per formule/scaglioni utilities (schema estensibile)

### Gap aperti

1. Gestione rettifiche prezzi post-emissione (DB-L4)
2. Test UI reale end-to-end (verifica permessi, readonly mode, drawer pattern)
3. Documentazione API backend (`docs/it/backend/vendite/manual/`)

---

## 3) Principi architetturali

1. Modello commessa v2 invariato: nessun bypass.
2. Prezzo risolto in modo deterministico e auditabile.
3. Emittente fiscale dimensione attiva gia in v1.
4. UoM non forzata unica per articolo in listino.
5. Rettifiche possibili sia manuali che automatiche, con stesso motore delta.
6. Formule/scaglioni previste ma non obbligatorie in v1.

---

## 4) Decisioni chiave con motivazione

### 4.1 Emittente fiscale attiva in v1

**Decisione**: `emittente_soggetto_ruolo_id` entra subito tra le dimensioni prezzo.

**Motivazione**:

1. e' gia centrale nei flussi fatturazione,
2. evitarla ora crea ambiguita su prezzi/fiscalita perimetro,
3. evita rework su resolver e migrazioni successive.

### 4.2 UoM non unica per articolo

**Decisione**: la chiave prezzo include `articolo_id + uom_id` (non solo articolo).

**Motivazione**:

1. `catalogo.articoli_uom_operativa` prevede piu UoM operative per articolo,
2. forzare UoM unica romperebbe casi reali (ore, confezioni, conversioni operative),
3. mantiene coerenza con snapshot `factor_to_base` dei documenti.

### 4.3 Rettifiche manuali e automatiche

**Decisione**: doppio canale rettifica (`MANUALE`, `AUTOMATICA`) con pipeline unica delta.

**Motivazione**:

1. nella pratica servono entrambi i canali,
2. un solo motore evita divergenze di risultato tra processi umani e batch,
3. audit unico semplifica compliance e troubleshooting.

> Sviluppo e roadmap dettagliata del motore rettifiche in documento dedicato: [sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md).

### 4.4 Formule utilities in fase successiva

**Decisione**:

1. v1 listini con prezzi fissi/versionati,
2. predisposizione strutturale per `FORMULA` e `SCAGLIONI` in v2.

**Motivazione**:

1. accelera go-live con rischio controllato,
2. evita bloccare il progetto su formula engine complesso,
3. mantiene estendibilita senza cambiare schema base.

### 4.5 Contesto non-utility esplicito

**Decisione**: il dominio include anche casi non-utility con `utility_id = NULL` (servizi commerciali puri).

**Motivazione**:

1. ordini/preventivi non sono sempre legati a utility,
2. il resolver deve coprire esplicitamente questi casi, non solo il perimetro utility.

### 4.6 Separazione app Django

Listini, versioni, righe, associazioni → `apps/vendite/` (schema `vendite`, file dedicati `listini_*`).

Motivazione: rispetta l'allineamento app-schema. I listini vivono in `vendite` perche' il resolver prezzo e' integrato con il ciclo vendita.

---

## 5) Modello dati (v1)

### 5.1 Tabelle core

1. **`vendite.listini`**
   - anagrafica listino (codice, descrizione, dominio, attivo).
   - `dominio` valori v1 ammessi: `UTILITY`, `COMMERCIO`
   - domini futuri possibili: `INDUSTRIA` (e altri perimetri verticali)
2. **`vendite.listini_versioni`**
   - versionamento temporale (`valido_dal`, `valido_al`, priorita, stato).
   - stati: `BOZZA` → `ATTIVA` → `CHIUSA`
3. **`vendite.listini_righe`**
   - prezzo per contesto dimensionale.
   - precisione `numeric(22,10)` (vedi §5.4).
4. **`vendite.listini_associazioni`**
   - assegnazione listino a perimetri (BA/utility/emittente).
   - include `priorita` (tie-break tra listini candidati nello stesso contesto).

**Regola operativa**:

1. `listini_associazioni` non e solo configurazione UI;
2. il resolver deve prima ricavare i listini candidati da questa tabella,
3. poi applicare la precedenza dimensionale su `listini_righe`.
4. se i listini candidati sono multipli, la scelta non e "per listino vincente", ma per miglior match di riga su tutto il set candidati.

### 5.2 Dimensioni riga listino (v1 attive)

1. `articolo_id` obbligatorio,
2. `uom_id` obbligatorio,
3. `periodo` tramite versione listino (`valido_dal/valido_al`),
4. `billing_account_id` opzionale,
5. `utility_id` opzionale,
6. `emittente_soggetto_ruolo_id` opzionale ma attiva.

### 5.3 Regole di unicita

1. no overlap temporale per stessa combinazione dimensionale nella stessa versione logica,
2. unique su chiave completa dimensionale + versione,
3. coerenza date (`valido_al > valido_dal` o null open-ended),
4. constraint GIST `ex_listini_versioni_no_overlap` per no-overlap versioni attive.

### 5.4 Policy precisione prezzo (v1)

Decisione operativa confermata:

1. fino a `attivita_fatturabili` (inclusa) il prezzo usa precisione alta `numeric(22,10)`;
2. in `fatture_righe` il prezzo di aggregazione/esposizione resta a `6` decimali;
3. il resolver listino e le funzioni di push/pull non devono introdurre arrotondamenti anticipati.

**Motivazione**:

1. nel dominio utilities (gas/energia/idrico) sono frequenti importi unitari molto piccoli;
2. mantenere `22,10` a monte evita perdita di informazione prima della fase fiscale;
3. l'arrotondamento a `6` decimali rimane confinato al layer righe fattura.

---

## 6) Resolver prezzo (deterministico)

### 6.1 Ordine di precedenza

1. `BA + utility + emittente + articolo + uom` (match_level = 1, piu' specifico)
2. `BA + utility + articolo + uom` (match_level = 2)
3. `BA + emittente + articolo + uom` — non-utility (match_level = 3)
4. `BA + articolo + uom` — non-utility (match_level = 4)
5. `utility + emittente + articolo + uom` (match_level = 5)
6. `utility + articolo + uom` (match_level = 6)
7. `articolo + uom` — fallback (match_level = 7)

### 6.2 Firma funzione

1. `fn_resolve_prezzo_listino(...)` deve ricevere `p_data_riferimento` obbligatoria,
2. senza `p_data_riferimento` la funzione deve andare in errore esplicito.

### 6.3 Tie-break

1. priorita associazione listino (`listini_associazioni.priorita`),
2. priorita versione listino,
3. data validita piu specifica/recente,
4. id stabile.

### 6.4 Comportamento errori

1. **Nessun match**: errore esplicito `E_PREZZO_LISTINO_NON_TROVATO` (no fallback silenzioso).
2. **Ambiguo**: se due match restano equivalenti dopo tutti i tie-break, errore esplicito `E_PREZZO_LISTINO_AMBIGUO` (code interno `AMBIGUOUS_PRICE_MATCH`).
3. **Parametro invalido**: errore `E_PARAMETRO_INVALIDO`.

**Motivazione**:

1. prevedibilita operativa,
2. riduzione anomalie "prezzo inatteso",
3. facilita test automatici.

### 6.5 Decisione multi-listino

1. precedenza per specificita riga su tutti i listini candidati;
2. priorita listino usata **solo come tie-break**.

**Esempio**:

* Listino A: associazione priorita 10, riga con solo articolo+UoM (livello 7)
* Listino B: associazione priorita 50, riga con BA+utility+emittente (livello 1)

Vince il Listino B perche' il match di livello 1 e' piu' specifico del livello 7, indipendentemente dalla priorita dell'associazione.

---

## 7) Integrazione con commessa v2

### 7.1 Snapshot su `commesse_attivita`

Salvare:

1. `listino_versione_id`,
2. `prezzo_snapshot`,
3. `prezzo_bloccato`,
4. `pricing_mode` (`FIXED` in v1; `FORMULA/SCAGLIONI` pronti per v2).

**Motivazione**:

1. rerun idempotente,
2. audit "perche quel prezzo",
3. supporto revisioni listino senza mutare storico.

### 7.2 Gerarchia prezzo documento vs listino

**Decisione**:

1. se su documento e presente override manuale prezzo, quello prevale sul listino;
2. in quel caso si salva:
   - `prezzo_snapshot = prezzo_documento`,
   - `prezzo_bloccato = TRUE`,
   - `listino_versione_id = versione risolta alla data` (se risolvibile, per audit comparativo),
   - riferimento motivazione override in `meta`;
3. se non c'e override manuale, il prezzo viene dal resolver listino.

### 7.3 Caso preventivo LIBERO modificato dopo push

**Decisione**:

1. se il preventivo e ancora `LIBERO` e il prezzo viene modificato post-push:
   - la riga `commesse_attivita` viene marcata `prezzo_da_riallineare = TRUE`,
   - il prezzo non viene aggiornato in modo silenzioso;
2. il riallineamento avviene su conferma esplicita (ricalcolo su conferma);
3. dopo conferma, si aggiorna `prezzo_snapshot` sulla commessa e si mantiene audit della revisione.
4. allineamento con commesse-v2:
   - non si introduce nuovo stato business di commessa,
   - si usa flag tecnico di riallineamento + log evento.

**Caso non ammesso**: se il documento non e piu `LIBERO` (es. convertito/confermato), il prezzo documento non puo alterare la commessa gia consolidata.

### 7.4 Propagazione `prezzo_bloccato` verso `attivita_fatturabili`

**Decisione**:

1. `prezzo_bloccato` deve essere propagato come snapshot anche su `attivita_fatturabili`;
2. lo step 1 pipeline fatturazione legge il flag direttamente su `attivita_fatturabili`;
3. `commessa_attivita` resta la sorgente di verita, ma la copia su attivita evita join pesanti e ambiguita runtime.
4. DB-L3 ha introdotto esplicitamente il campo `attivita_fatturabili.prezzo_bloccato`.

**Motivazione**:

1. semplifica e rende deterministico il controllo prezzi nello step di fatturazione,
2. riduce dipendenze runtime dal dominio commessa durante la fase fiscale.

---

## 8) Rettifiche prezzi — RIMANDO

Il motore rettifiche (canali manuale + automatico, ricerca impatti retroattivi, delta tracciato) e' trattato nel documento dedicato:

**[sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md)** — DB-L4 della roadmap pricing, stato: **DA IMPLEMENTARE**.

Sintesi del contratto con il dominio listini:

1. nessuna riscrittura distruttiva di fatture emesse,
2. rettifica sempre tramite delta tracciato,
3. motore unico per canale `MANUALE` (operatore) e `AUTOMATICA` (job su UPDATE retroattivo di `listini_versioni`/`listini_righe`),
4. i campi tecnici `prezzo_bloccato` (su `commesse_attivita` e `attivita_fatturabili`) e `prezzo_da_riallineare` sono gia' in schema (DB-L3) come predisposizione.

---

## 9) Evoluzione v2 formule/scaglioni (non bloccante v1)

Predisposizione consigliata:

1. tabella regole formula separata da `listini_righe`,
2. tabella scaglioni separata per consumi/ore,
3. mapping di input formula (letture, fasce, indici, coefficenti),
4. output sempre normalizzato a `prezzo_snapshot` per commessa.

**Motivazione**:

1. separa complessita matematica dal core listino,
2. facilita test e rollback.

---

## 10) Backend — Listini (vendite)

### 10.1 Repository: `apps/vendite/db/listini_repository.py`

| # | Metodo | SQL | Note |
| --- | --- | --- | --- |
| 1 | `list_listini()` | SELECT da `vendite.listini` con filtri, search, paginazione | Filtri: `dominio`, `attivo`, `search` su codice+descrizione |
| 2 | `get_listino()` | SELECT listino + count versioni + count associazioni | Dettaglio singolo |
| 3 | `create_listino()` | INSERT INTO `vendite.listini` | codice, descrizione, dominio |
| 4 | `update_listino()` | UPDATE `vendite.listini` SET ... WHERE id | descrizione, dominio, attivo |
| 5 | `list_versioni()` | SELECT da `vendite.listini_versioni` WHERE listino_id ORDER BY valido_dal DESC | Con conteggio righe per versione |
| 6 | `get_versione()` | SELECT singola versione | |
| 7 | `create_versione()` | INSERT INTO `vendite.listini_versioni` | valido_dal, valido_al, priorita, stato=BOZZA. No-overlap gestito da constraint GIST |
| 8 | `update_versione()` | UPDATE `vendite.listini_versioni` SET ... WHERE id | Date, priorita'. Stato gestito da azione dedicata |
| 9 | `cambia_stato_versione()` | UPDATE `vendite.listini_versioni` SET stato WHERE id | Transizioni ammesse: BOZZA→ATTIVA, ATTIVA→CHIUSA |
| 10 | `list_righe()` | SELECT da `vendite.listini_righe` JOIN articoli JOIN unita_misura WHERE versione_id | Con display fields articolo e UoM |
| 11 | `create_riga()` | INSERT INTO `vendite.listini_righe` | articolo_id, uom_id, prezzo, contesto opzionale (BA, utility, emittente) |
| 12 | `update_riga()` | UPDATE `vendite.listini_righe` SET ... WHERE id | prezzo, contesto |
| 13 | `delete_riga()` | DELETE FROM `vendite.listini_righe` WHERE id | |
| 14 | `list_associazioni()` | SELECT da `vendite.listini_associazioni` WHERE listino_id | Con display fields BA, utility, emittente |
| 15 | `create_associazione()` | INSERT INTO `vendite.listini_associazioni` | perimetro (BA, utility, emittente), priorita' |
| 16 | `update_associazione()` | UPDATE `vendite.listini_associazioni` SET ... WHERE id | |
| 17 | `delete_associazione()` | DELETE FROM `vendite.listini_associazioni` WHERE id | |
| 18 | `get_articolo_uom_validation()` | SELECT di validazione articolo + UoM in un round-trip | Helper interno |
| 19 | `test_resolver()` | SELECT `vendite.fn_resolve_prezzo_listino(...)` | Wrapper per test prezzo da UI. Restituisce prezzo, match_level, listino/versione usati |

### 10.2 Service: `apps/vendite/services/listini_service.py`

| # | Metodo | Orchestrazione |
| --- | --- | --- |
| 1 | `list_listini()` | Delega con validazione filtri |
| 2 | `get_listino_dettaglio()` | Listino + versioni + associazioni |
| 3 | `crea_listino()` | Validazione codice univoco, INSERT |
| 4 | `aggiorna_listino()` | UPDATE con validazione |
| 5 | `gestisci_versione()` | CRUD versione con validazione no-overlap |
| 6 | `cambia_stato_versione()` | Transizione stato con guard: BOZZA→ATTIVA (deve avere almeno 1 riga), ATTIVA→CHIUSA |
| 7 | `gestisci_riga()` | CRUD riga con validazione articolo attivo e UoM coerente |
| 8 | `gestisci_associazione()` | CRUD associazione con validazione perimetro |
| 9 | `test_resolver_prezzo()` | Chiama `fn_resolve_prezzo_listino`, formatta risultato per UI |

Totale: 18 funzioni `fn_*` nel service.

### 10.3 API: `apps/vendite/api/views_listini.py`

| # | Metodo | Path | Scopo |
| --- | --- | --- | --- |
| 1 | GET | `/api/v1/vendite/listini/` | Lista listini paginata |
| 2 | POST | `/api/v1/vendite/listini/` | Crea listino |
| 3 | GET | `/api/v1/vendite/listini/{id}/` | Dettaglio listino |
| 4 | PATCH | `/api/v1/vendite/listini/{id}/` | Aggiorna listino |
| 5 | GET | `/api/v1/vendite/listini/{id}/versioni/` | Lista versioni del listino |
| 6 | POST | `/api/v1/vendite/listini/{id}/versioni/` | Crea versione |
| 7 | GET | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/` | Dettaglio versione |
| 8 | PATCH | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/` | Aggiorna versione |
| 9 | POST | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/stato/` | Cambia stato versione |
| 10 | GET | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/` | Lista righe prezzo della versione |
| 11 | POST | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/` | Crea riga prezzo |
| 12 | PATCH | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/` | Aggiorna riga |
| 13 | DELETE | `/api/v1/vendite/listini/{id}/versioni/{ver_id}/righe/{riga_id}/` | Elimina riga |
| 14 | GET | `/api/v1/vendite/listini/{id}/associazioni/` | Lista associazioni |
| 15 | POST | `/api/v1/vendite/listini/{id}/associazioni/` | Crea associazione |
| 16 | PATCH | `/api/v1/vendite/listini/{id}/associazioni/{assoc_id}/` | Aggiorna associazione |
| 17 | DELETE | `/api/v1/vendite/listini/{id}/associazioni/{assoc_id}/` | Elimina associazione |
| 18 | POST | `/api/v1/vendite/listini/test-prezzo/` | Test resolver prezzo |

Totale: 10 classi view, 18 metodi HTTP, 10 rotte in `urls_listini.py`.

### 10.4 Errori applicativi

Codici registrati in `error_policies.py`:

* `E_VENDITE_VALIDATION`
* `E_VENDITE_LISTINO_NOT_FOUND`
* `E_VENDITE_VERSIONE_NOT_FOUND`
* `E_VENDITE_RIGA_NOT_FOUND`
* `E_VENDITE_ASSOCIAZIONE_NOT_FOUND`
* `E_PREZZO_LISTINO_NON_TROVATO` (dal DB)
* `E_PREZZO_LISTINO_AMBIGUO` (dal DB)

### 10.5 Regole seguite

1. `DomainAPIView` con `area_funzionale = "vendite"` su tutte le 10 view
2. `is_search_endpoint = True` sulla lista
3. `@extend_schema` su tutti i 18 metodi HTTP
4. Helper condivisi `_prepare_insert_parts` e `_prepare_update_parts` nel repository (riduce duplicazione)
5. Validazione articolo/UoM in un solo round-trip (`get_articolo_uom_validation`)
6. Display fields via JOIN diretti (non lookup client-side)
7. PATCH usa `request.data` (non `handle_post_json`)

### 10.6 Test

**29 test verdi**: 8 service + 21 API.

| File | Contenuto |
| --- | --- |
| `apps/vendite/tests/services/test_listini_service.py` | CRUD listino, ciclo versioni, righe, associazioni, test resolver |
| `apps/vendite/tests/api/test_listini_api.py` | Tutti gli endpoint §10.3 |

Strategia: `unittest.TestCase` con mock DB per compatibilita' CI.

---

## 11) Frontend — Listini

### 11.1 Struttura file

```
frontend/src/vendite/
├── api/
│   └── listini.js                    # 17 funzioni API listini
├── stores/
│   └── listini.js                    # Store Pinia listini
├── components/
│   ├── ListiniSearchTable.vue        # Lista listini con filtri (dominio + attivo)
│   ├── ListinoDrawer.vue             # Drawer crea/modifica listino (COMPLEX 800px, 2 tab + test resolver)
│   ├── ListinoVersioniTab.vue        # Tab versioni del listino
│   ├── ListinoAssociazioniTab.vue    # Tab associazioni perimetro (CRUD inline)
│   ├── VersioneDrawer.vue            # Sub-drawer versione con righe prezzo CRUD (guard BOZZA)
│   └── TestResolverDialog.vue        # Dialog test resolver prezzo
└── views/
    └── ListiniView.vue               # Pagina completa
```

### 11.2 ListiniSearchTable

| Colonna | Sorgente | Note |
| --- | --- | --- |
| Codice | `codice` | Link che apre il drawer |
| Descrizione | `descrizione` | |
| Dominio | `dominio` | Badge UTILITY / COMMERCIO |
| Versioni attive | count | Numero versioni in stato ATTIVA |
| Attivo | `attivo` | Badge stato |

Filtri:

1. `search` — ILIKE su codice + descrizione
2. `dominio` — dropdown (Tutti / UTILITY / COMMERCIO)
3. `attivo` — dropdown (Tutti / Si / No), default Si

### 11.3 ListinoDrawer — Dati principali

Form con campi:

| Campo | Tipo | Note |
| --- | --- | --- |
| `codice` | InputText | Obbligatorio |
| `descrizione` | InputText | Obbligatorio |
| `dominio` | Select | UTILITY / COMMERCIO |

In modalita' modifica: 2 tab sotto il form + pulsante test prezzo:

1. **Versioni** (ListinoVersioniTab)
2. **Associazioni** (ListinoAssociazioniTab)

Pulsante globale "Test prezzo" → apre TestResolverDialog.

### 11.4 ListinoVersioniTab

DataTable con le versioni del listino selezionato:

| Colonna | Note |
| --- | --- |
| Stato | Badge BOZZA (giallo) / ATTIVA (verde) / CHIUSA (grigio) |
| Valido dal | Data |
| Valido al | Data o "—" (open-ended) |
| Priorita' | Numerico |
| Righe | Count righe prezzo |
| Azioni | Apri dettaglio, cambia stato |

Click su riga → apre VersioneDrawer con righe prezzo della versione.

### 11.5 VersioneDrawer

| Campo | Tipo | Note |
| --- | --- | --- |
| `stato` | Badge readonly | Visualizzazione. Cambio stato via azione dedicata |
| `valido_dal` | Calendar | Obbligatorio |
| `valido_al` | Calendar | Facoltativo |
| `priorita` | InputNumber | Default 0 |

Azioni stato nella toolbar:

* BOZZA → "Attiva" (guard: almeno 1 riga)
* ATTIVA → "Chiudi"
* CHIUSA → nessuna azione

Contiene CRUD inline delle **righe prezzo** (solo in stato BOZZA via `isBozza`):

| Colonna | Note |
| --- | --- |
| Articolo | codice + descrizione (da JOIN) |
| UoM | codice UoM |
| Prezzo | Formattato con fino a 10 decimali |
| BA | codice BA (se presente) |
| Utility | descrizione utility (se presente) |
| Emittente | descrizione emittente (se presente) |
| Azioni | Modifica, elimina |

Campi form riga:

| Campo | Tipo | Note |
| --- | --- | --- |
| `articolo_id` | `ArticoloLookup` | Obbligatorio — building block cross-dominio |
| `uom_id` | Select | Popolato dalle UoM operative dell'articolo selezionato via `/api/v1/catalogo/articoli/{id}/uom/` |
| `prezzo` | InputNumber | Obbligatorio, precision 10 decimali |
| `billing_account_id` | AutoComplete BA | Facoltativo |
| `utility_id` | Select utility | Facoltativo |
| `emittente_soggetto_ruolo_id` | AutoComplete emittente | Facoltativo |

### 11.6 ListinoAssociazioniTab

DataTable con le associazioni del listino + form inline per aggiunta rapida:

| Colonna | Note |
| --- | --- |
| BA | codice BA (se presente) |
| Utility | descrizione utility (se presente) |
| Emittente | descrizione emittente (se presente) |
| Priorita' | Numerico |
| Valido dal | Data |
| Valido al | Data o "—" |
| Azioni | Modifica, elimina |

### 11.7 TestResolverDialog

Dialog modale per testare il resolver prezzo:

| Campo input | Tipo | Note |
| --- | --- | --- |
| `articolo_id` | `ArticoloLookup` | Obbligatorio |
| `uom_id` | Select UoM | Obbligatorio, popolato da articolo |
| `data_riferimento` | Calendar | Obbligatorio, default oggi |
| `billing_account_id` | AutoComplete BA | Facoltativo |
| `utility_id` | Select | Facoltativo |
| `emittente_soggetto_ruolo_id` | AutoComplete | Facoltativo |

Output:

| Campo | Note |
| --- | --- |
| Prezzo risolto | Formattato con decimali |
| Match level | 1-7 con descrizione del livello |
| Listino usato | Codice + descrizione |
| Versione usata | Date validita' + priorita' |
| Associazione | Dettaglio perimetro |

Errori visualizzati: `E_PREZZO_LISTINO_NON_TROVATO`, `E_PREZZO_LISTINO_AMBIGUO` con messaggio leggibile.

### 11.8 Regole seguite

1. Riuso di `useSearchTable`, `useDrawerState`, `useTabFreshness`, `useApiHandler`, `useInjectReadonly`, `useLookup`
2. `VersioneDrawer` e `TestResolverDialog` usano `ArticoloLookup` (BB cross-dominio dal dominio catalogo)
3. Lookup UoM via `lookupCodici('catalogo.unita_misura')` (generico, non dedicato)
4. Righe prezzo CRUD solo su versioni in stato BOZZA (guard `isBozza`)
5. PATCH backend usa `request.data`
6. Tutti i testi via `$t()`, nessun hardcoded
7. Build frontend OK, nessun testo hardcoded verificato

### 11.9 Navigazione e i18n

`src/core/navigation.js`: voce L2 vendite → "Listini" (rotta `vendite-listini`).

`router/index.js`: rotta `vendite-listini`, `vendite` in `domainsWithRoutes`.

i18n: sezione `listini` (62 chiavi) in `it.json` + `en.json`, `nav_menu.vendite`.

---

## 12) Test

Totale backend: **29 test verdi** (listini) + 49 (catalogo) = **78 test verdi complessivi**.

### 12.1 Backend listini

| File | Numero | Contenuto |
| --- | --- | --- |
| `apps/vendite/tests/services/test_listini_service.py` | 8 | CRUD listino, ciclo versioni, righe, associazioni, test resolver |
| `apps/vendite/tests/api/test_listini_api.py` | 21 | Tutti gli endpoint §10.3 |

---

## 13) Tracking avanzamento

### 13.1 DB-L1 Schema base listini — COMPLETATO

- [x] creare tabelle `listini`, `listini_versioni`, `listini_righe`, `listini_associazioni`
- [x] introdurre campo `listini_associazioni.priorita`
- [x] introdurre campo `listini.dominio` con valori v1 (`UTILITY`, `COMMERCIO`)
- [x] vincoli date e no-overlap versioni (GIST `ex_listini_versioni_no_overlap`)
- [x] pgtap DDL base verde

### 13.2 DB-L2 Resolver pricing — COMPLETATO

- [x] creare `fn_resolve_prezzo_listino(...)` con `p_data_riferimento` obbligatoria
- [x] implementare precedenze utility + non-utility (7 livelli)
- [x] implementare tie-break multi-listino con `listini_associazioni.priorita`
- [x] errore `AMBIGUOUS_PRICE_MATCH` su pareggio totale
- [x] creare `fn_resolve_commessa_prezzi(lotto_id)`
- [x] pgtap resolver verde

### 13.3 DB-L3 Integrazione commessa — COMPLETATO

- [x] estendere `commesse_attivita` con `pricing_mode`
- [x] estendere `commesse_attivita` con `prezzo_da_riallineare`
- [x] estendere `attivita_fatturabili` con `prezzo_bloccato`
- [x] aggiornare `fn_emit_attivita_fatturabili_da_commessa` per propagare `prezzo_bloccato`
- [x] gestire override documento (`prezzo_bloccato=TRUE`, `listino_versione_id` audit)
- [x] pgtap integrazione commessa verde

### 13.4 Backend listini — COMPLETATO

- [x] `listini_repository.py` (19 metodi)
- [x] `listini_service.py` (18 funzioni fn_*)
- [x] `views_listini.py` (10 classi, 18 metodi HTTP) + `urls_listini.py` (10 rotte)
- [x] lista + dettaglio listini (con count versioni/associazioni)
- [x] CRUD listino + versioni (con cambio stato BOZZA/ATTIVA/CHIUSA)
- [x] righe prezzo (CRUD con display fields via JOIN)
- [x] associazioni (CRUD con display fields via JOIN)
- [x] test resolver prezzo (wrapper `fn_resolve_prezzo_listino`)
- [x] codici errore registrati in `error_policies.py`
- [x] PATCH usa `request.data`
- [x] test service (8) + test API (21) = 29 test verdi

### 13.5 Frontend listini — COMPLETATO

- [x] API client `vendite/api/listini.js` (17 funzioni)
- [x] store Pinia `vendite/stores/listini.js`
- [x] `ListiniSearchTable.vue` + `ListiniView.vue`
- [x] `ListinoDrawer.vue` (tab versioni + associazioni + pulsante test resolver)
- [x] `ListinoVersioniTab.vue` (lista, crea inline, azioni stato)
- [x] `ListinoAssociazioniTab.vue` (CRUD inline)
- [x] `VersioneDrawer.vue` (sub-drawer con righe prezzo CRUD, guard BOZZA)
- [x] `TestResolverDialog.vue` (dialog modale con ArticoloLookup BB)
- [x] `navigation.js` + `router/index.js`
- [x] i18n `listini` (62 chiavi) + `nav_menu.vendite`
- [x] build OK, nessun hardcoded

### 13.6 DB-L4 Rettifiche — DA IMPLEMENTARE

Trasferito in documento dedicato: vedi **[sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md)** §7 per la checklist completa (motore delta, canali, audit, pgtap).

### 13.7 Consolidamento e test di flusso — APERTO

- [x] test unitari backend catalogo (49) + listini (29) = 78 test verdi
- [x] verifica envelope API, naming campi e ordinamenti whitelist (conforme a api.md)
- [x] verifica lookup articoli riusabile da frontend `catalogo` e `vendite` (ArticoloLookup BB in core/)
- [x] verifica PATCH usa `request.data` su tutti gli endpoint (catalogo + vendite)
- [x] navigazione sidebar + routing (catalogo 2 voci, vendite 1 voce, 3 rotte)
- [x] registrazione whitelist lookup: `catalogo.unita_misura` gia' in whitelist, tipologie/gruppi/spesa gia' presenti
- [ ] **verifica permessi, readonly mode e pattern tab/drawer (test UI reale)**
- [ ] **documentazione API listini in `docs/it/backend/vendite/manual/`**

### 13.8 Gate di chiusura DB (dopo DB-L4)

- [ ] tutti i test pgtap listini/commessa verdi
- [ ] ownership campi/funzioni allineata con `gestione-commesse-v2.md`
- [ ] chiusura bloccanti §14

---

## 14) Bloccanti da chiudere

Aggiornati al aprile 2026. I punti 1-6 erano bloccanti prima dello sviluppo DB e ora sono **chiusi**:

1. ~~conferma finale precedenze resolver (inclusi casi non-utility)~~ **chiuso** (7 livelli)
2. ~~conferma ruolo operativo `listini_associazioni` nel resolver~~ **chiuso** (filtro candidati)
3. ~~conferma gerarchia prezzo documento override vs listino~~ **chiuso** (vedi §7.2)
4. ~~conferma `p_data_riferimento` obbligatoria nella funzione resolver~~ **chiuso**
5. ~~conferma domini enum `pricing_mode` e canale rettifica~~ **chiuso** (FIXED in v1)
6. ~~conferma strategia multi-listino: specificita riga cross-listino + tie-break priorita associazione~~ **chiuso**

I bloccanti residui riguardano il dominio **rettifiche** (perimetro retroattivo, formato audit, perimetro v1 `FIXED`, segmentazione listini) e sono stati trasferiti in **[sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md)** §6 come gate di avvio DB-L4.

**Nota**: il tema "da riallineare" si considera chiuso (flag tecnico `prezzo_da_riallineare` presente nello schema).

---

## 15) Cosa resta fuori da questa fase

1. formula engine completo utilities,
2. scaglioni avanzati multi-fascia,
3. simulazioni tariffarie previsionali.

Queste parti sono previste nella v2 pricing, non bloccano la partenza del modello.

---

## 16) Building block riutilizzabili

Produzione di questa fase:

| Componente | Tipo | Consumatori previsti |
| --- | --- | --- |
| `/api/v1/vendite/listini/test-prezzo/` | API REST | Verifica pricing cross-dominio |
| `VersioneDrawer.vue` | Componente | Riusato da gestione pratiche (se servira') |

Consumati da questa fase (ereditati da catalogo):

| Componente | Origine |
| --- | --- |
| `ArticoloLookup.vue` | `frontend/src/core/components/` (dominio catalogo) |
| `/api/v1/catalogo/articoli/lookup/` | Backend catalogo |
| `/api/v1/catalogo/articoli/{id}/uom/` | Backend catalogo |
| `lookupCodici('catalogo.unita_misura')` | API generica core |

---

## 17) Riepilogo prossimi passi

In ordine di priorita' per chiudere il dominio listini v1:

1. **Test UI reale** sul drawer listino, versioni, righe, test resolver (verifica permessi, readonly mode, flussi completi)
2. **Documentazione API** in `docs/it/backend/vendite/manual/` a partire dallo schema OpenAPI
3. **Rettifiche (DB-L4)** — perimetro trasferito in [sviluppo-rettifiche.md](../work-in-progress/sviluppo-rettifiche.md), lo sviluppo parte dopo la chiusura dei bloccanti in quel documento
4. **Importazione guida utente** in `docs/it/guide/gestione-listini.md` (gia' scritta, da allineare con nomenclatura `bigint` al posto di `UUID` nei PK)

---

*Sviluppo Listini — ZeroERP (aprile 2026, consolidato)*
