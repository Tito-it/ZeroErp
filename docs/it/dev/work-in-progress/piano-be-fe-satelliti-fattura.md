# Piano BE/FE — satelliti della fattura (indirizzi + piano rate)

> ⚠️ **REVISIONE 2026-07-30 — leggere prima
> [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md).**
> La verifica critica sui due brief ha cambiato alcune premesse di questo piano:
>
> | § di qui | Cosa cambia | Rif. |
> |---|---|---|
> | §4 Fase 2 | Il **fallback «transitorio»** del context builder alla vista live **non si scrive**: non siamo in produzione, le 7 fatture di test si cancellano e rigenerano. Era codice che nasceva già da rimuovere | §3.8 |
> | §4 Fase 5 | Cade la **bonifica/esclusione** delle fatture storiche prima di accendere il guard `FATT`, per lo stesso motivo | §3.8 |
> | §4 Fase 4 | Il follow-up temuto sui **«gruppi con termini misti» non serve**: un gruppo fatturabile è **un solo** documento sorgente (o gli oneri di **una** commessa), quindi porta un solo termine per costruzione. D-7 non può spaccarlo. Resta vero che una corsa su tutto il mese può produrre **più fatture** di prima: è lo smoke §3.3 a sorvegliarlo | C-10 |
> | §4 Fase 1 | Il mixin `IndirizziDocumentoRepositoryMixin` va **ripuntato** su `script.fn_resolve_indirizzo_documento`: oggi `find_indirizzo_ruolo_per_tipi` preferisce l'indirizzo generico e **ignora l'istanza** del documento. È una **correzione**, non un refactor estetico | C-14c |
> | **nuovo** | La riforma **D-I** elimina due campi dal `ClienteDrawer` (`tipo_gg_scadenza_ft`, `nr_giorni_scadenza`) con le 4 opzioni `opt_gg_*` e le relative chiavi i18n. Lavoro FE non previsto qui | D-I |
> | **nuovo** | Fase 6 DB aggiunge un verbo al `LottoDrawer` (ritorno a DRAFT / estrazione fattura) e una **lista «estratte»** nel cockpit | D-N-bis |
>
> **Owner:** BE (`dev/backend-tid`)
> **Stato:** in attesa dei prerequisiti DB
> **Prerequisiti (bloccanti):**
> [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) ·
> [brief-db-generazione-scadenze-fattura.md](brief-db-generazione-scadenze-fattura.md)
>
> Questo documento è il **piano di lavoro applicativo**: cosa si tocca, in quale
> ordine, e come si verifica. Le decisioni di dominio e le richieste al team DB
> stanno nei due brief, non qui (regola: modello / brief / piano separati).

---

## 1. Perché serve un piano e non si parte "a sentimento"

Il lavoro applicativo è **cablaggio**, non logica: due handler di pipeline, due
wrapper di repository, un mixin da agganciare, un context builder da ripuntare.
Poche ore di codice. Il valore sta tutto in **tre cose che vanno decise prima**:

1. **l'ordine**, perché una sequenza sbagliata blocca la fatturazione (il guard di
   obbligatorietà `FATT` acceso prima che il popolamento funzioni ferma la pipeline);
2. **cosa consideriamo "fatto"**, perché i satelliti sono esattamente il tipo di
   cosa che «sembra funzionare» e invece è vuota — ce lo siamo già trovati due
   volte (la stampa fattura a trattini, `fn_generate_fatture_righe` mai eseguita);
3. **le regressioni attese**, perché D-7 (termine in chiave di aggregazione)
   **cambia il numero di fatture generate**: va sorvegliato, non scoperto.

## 2. Cosa NON si può anticipare (e va detto)

| Attività | Perché è bloccata |
|---|---|
| Handler + wrapper repository | Devono chiamare funzioni DB di cui non conosciamo ancora nome e firma definitivi |
| Codice degli smoke | Le asserzioni sono già definite (§3), ma il codice tocca le firme reali: scriverlo ora vorrebbe dire riscriverlo |
| Context builder PDF sullo snapshot | Richiede che `fatture_indirizzi` sia popolata, altrimenti la stampa peggiora invece di migliorare |
| Endpoint gestione indirizzi fattura | Dipende da una decisione FE ancora aperta (§7) |

Niente di sostanziale è anticipabile: è cablaggio su superfici che il DB deve
ancora creare. **L'unica cosa utile da fare adesso è questo piano.**

---

## 3. Definizione di «fatto»: gli smoke di accettazione

Sono il **criterio di collaudo del brief DB**, non un complemento del BE: oggi
sarebbero **rossi**, dopo l'apply devono essere verdi. Vanno scritti come primo
atto del lavoro applicativo, prima degli handler, perché descrivono cosa stiamo
cercando di ottenere.

Passano **dalla pipeline reale** (non chiamano le funzioni DB direttamente): così
verificano la catena intera, che è il punto in cui abbiamo già trovato due volte
codice morto con i test verdi.

### 3.1 `smoke-fattura-indirizzi-snapshot.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro DRAFT, ogni fattura del lotto ha **almeno la riga `FATT`** in `fatture_indirizzi` |
| 2 | Lo `snapshot` ha lo shape canonico (`intestazione, via, cap, citta, prov, stato, display`) e **non è vuoto** |
| 3 | `origine_indirizzo_id` valorizzato quando l'indirizzo viene dall'anagrafica (tracciabilità della provenienza) |
| 4 | I tipi opzionali (`CON`, `FORNITURA`, `RES`) **non fanno fallire** il giro se assenti |
| 5 | **Ristampa conforme**: il PDF stampa l'indirizzo dello **snapshot**; modificando l'indirizzo in anagrafica e ristampando, il documento **non cambia** ⟵ *l'asserzione che giustifica tutto il lavoro* |
| 6 | Idempotenza: rigenerando il giro non nascono righe duplicate |

### 3.2 `smoke-fattura-scadenze.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro EMESSA, ogni fattura ha **almeno una rata** in `fatture_scadenze` |
| 2 | `Σ importo` delle rate **quadra** con `fatture.totale_a_pagare` (base corretta, non `totale_doc`) |
| 3 | Su un piano non divisibile (es. 100,00 / 3) la differenza è **sull'ultima rata** |
| 4 | `numero_rata` progressivo da 1, nessun buco |
| 5 | `meta.modalita_codice` popolato — è il campo che il contesto PDF legge già |
| 6 | Testata: `termine_pagamento_id`, `modalita_pagamento_id`, `termine_pagamento_snapshot` **valorizzati** |
| 7 | Il **PDF stampa il piano rate** (sezione non vuota, date e importi presenti) |
| 8 | Percorso coppia legacy (cliente con giorni): **una sola rata**, data = data fattura + giorni, spostata a fine mese quando previsto |
| 9 | Idempotenza: doppia esecuzione → stesse rate, nessun duplicato |

### 3.3 `smoke-fattura-aggregazione-termini.py` — il presidio di D-7

Lo smoke **più importante**, perché D-7 cambia quante fatture nascono:

| # | Asserzione |
|---|---|
| 1 | Due attività dello stesso BA con **termini diversi** → **due fatture** |
| 2 | Due attività dello stesso BA con **termine uguale** → **una fattura** |
| 3 | Riesecuzione del giro → **nessuna fattura in più** (chiave e lookup allineati) |
| 4 | Due attività con **utility diverse** → due fatture (regressione sul bug chiave/lookup del brief §4.2) |

Modello per tutti e tre: `backend/scripts/tests/smoke-fatturazione-aggregazione-righe.py`
(fixture in transazione + `set_rollback(True)`, nessun dato persistito).

---

## 4. Fasi, in ordine obbligato

### Fase 1 — Task snapshot indirizzi (dopo apply brief indirizzi)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` | agganciare `IndirizziDocumentoRepositoryMixin` con `_indirizzi_table="vendite.fatture_indirizzi"`, `_indirizzi_fk_documento="fattura_id"`, `_indirizzi_ambito="FATTURE"`, `_indirizzi_documento_table="vendite.fatture"`, `_indirizzi_doc_sr_column=None` (risoluzione via billing account) |
| stesso file | wrapper `run_snapshot_indirizzi_lotto_task(*, lotto_id, batch_size)` |
| `backend/apps/vendite/db/pipeline_repository.py` | voce in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/services/pipeline_step_executor.py` | handler `_handle_snapshot_indirizzi_lotto_task` + entry nel `handler_registry` (modello: `_handle_ricalcola_iva_lotto_task`) |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py` | 2 test (esecuzione + skip in dry-run), indice test nel docstring, mappa `ALLOWED_TASK_FUNCTIONS` mockata |

Verifica di fase: smoke §3.1 casi 1-4 e 6 verdi.

### Fase 2 — Ristampa conforme (il motivo per cui esiste la Fase 1)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py:1564-1573` | l'indirizzo cliente **non** più dalla vista live `vw_indirizzi_resolved_ruolo`, ma dallo **snapshot** `fatture_indirizzi` (tipo `FATT`) |
| `backend/apps/vendite/services/fattura_document_context_builder.py:206-208` | consumare il nuovo campo |
| — | modello già fatto: `DdtDocumentContextBuilder` è l'unico context builder che legge gli snapshot |

⚠️ **Fallback obbligatorio**: le 7 fatture storiche non hanno snapshot. Se il
lettore non trova la riga, deve ricadere sulla vista live invece di stampare un
vuoto — altrimenti «migliorare la conformità» significa **rompere la ristampa dei
documenti esistenti**. Il fallback va dichiarato nel codice come transitorio, con
il criterio per rimuoverlo (nessuna fattura senza snapshot).

Verifica di fase: smoke §3.1 caso 5 (il test di conformità) + ristampa di una
fattura storica che continua a funzionare.

### Fase 3 — Task generazione scadenze (dopo apply brief scadenze)

Stessa forma della Fase 1, sui punti di intervento gemelli
(`run_genera_scadenze_lotto_task`, `_handle_genera_scadenze_lotto_task`).

⚠️ **Attenzione all'ordine dentro lo step**: il task va **dopo**
`ricalcola_iva_lotto` (prima i totali non esistono). L'ordine è nel seed DB, ma i
test dell'executor devono asserirlo, non fidarsi.

Verifica di fase: smoke §3.2 completo.

### Fase 4 — Regressioni di D-7 (contestuale alla Fase 3)

Il termine in chiave cambia **quante** fatture nascono. Da sorvegliare:

| Cosa | Azione |
|---|---|
| Test e smoke esistenti che contano le fatture di un lotto | rileggere le aspettative: `smoke-fatturazione-aggregazione-righe.py` oggi assume che le attività dello stesso BA finiscano in una fattura |
| Cockpit / dashboard competenza | i **gruppi fatturabili** e i contatori riflettono l'aggregazione: verificare che il perimetro mostrato resti coerente con le fatture prodotte |
| Emissione mirata per gruppi | la `gruppo_key` non contiene il termine: verificare che un gruppo con termini misti si comporti come atteso (probabile follow-up) |

Verifica di fase: smoke §3.3 + suite completa vendite.

### Fase 5 — Accensione del guard `FATT` obbligatorio (coordinata col DB)

Il guard sta nel brief DB, ma la **sequenza è condivisa**: si accende **solo dopo**
che la Fase 1 gira su tutte le fatture nuove, altrimenti blocca la pipeline. Le 7
fatture storiche senza snapshot vanno bonificate o escluse.

Prima dell'accensione: contare le fatture emettibili senza `FATT`. Se > 0, non si
accende.

### Fase 6 — Frontend

| Cosa | Stato |
|---|---|
| Piano rate nel drawer | ✅ **nessun lavoro**: `ScadenzeSintesi` e il campo «Prossima rata» esistono e mostrano `—` finché le rate non arrivano. Dopo la Fase 3 si popolano da soli |
| Campi «Modalità di pagamento» e «Termine» | ✅ già nel drawer, oggi sempre vuoti perché la testata è NULL. Dopo la Fase 3 vanno **verificati a video** (è il primo momento in cui mostrano un valore) |
| Sezione indirizzi nel drawer fattura | ⏸️ decisione aperta, §7 |

---

## 5. Verifiche trasversali (a ogni fase)

- `./manage-test.sh apps.vendite.tests apps.core.tests` verde;
- `python3 scripts/check_i18n_keys.py` pulito (se si aggiungono etichette FE);
- build Vite + eslint (solo se si tocca il FE);
- `scripts/pgtap-baseline.sh vendite` — confronto con la baseline, per non
  attribuirsi rossi preesistenti né mascherare regressioni;
- gli smoke §3 **rieseguiti**, non solo la prima volta: sono il presidio contro il
  ritorno del difetto.

## 6. Rischi noti

| Rischio | Mitigazione |
|---|---|
| Guard `FATT` acceso troppo presto → pipeline bloccata | Fase 5 esplicita, con conteggio preventivo |
| Ristampa storica peggiorata dal passaggio allo snapshot | fallback transitorio alla vista live (Fase 2) |
| D-7 frammenta le fatture più del previsto | smoke §3.3 + revisione delle aspettative sui test esistenti (Fase 4) |
| `fatture_indirizzi` letta nel dettaglio API senza RLS | la tabella **non ha policy**: se la esponiamo, la protezione resta l'ordine «testata prima → 404» già presidiato da `test_note_non_contate_se_testata_none` e gemelli. Valutare l'estensione delle policy satelliti |
| Storicizzazione gonfiata dalle rigenerazioni | `DELETE+INSERT` su `fatture_scadenze` scrive in `storico.fatture_scadenze_id` a ogni giro: atteso, da tenere presente nei conteggi |

## 7. Decisioni FE ancora aperte

1. **L'operatore deve poter correggere un indirizzo su fattura DRAFT?**
   - **Sì** → serve l'endpoint (factory `build_indirizzi_documento_views` già
     pronta) + `stati_modificabili = {"DRAFT"}` + un lettore di stato
     (`get_stato_codice` **assente** su `VenditeRepository`, da scrivere) + montare
     `DocumentoIndirizziSection` nel drawer.
   - **No** → la tabella è scritta solo dalla pipeline; nel drawer gli indirizzi si
     mostrano in sola lettura (o non si mostrano affatto).
2. **Gli indirizzi vanno esposti nel dettaglio fattura?** Se sì, il payload cresce
   di una chiave e vale l'avvertenza RLS del §6.
3. **Badge documenti** nella barra azioni del drawer: il payload ha già
   `contatori` come dict proprio per questo — se serve, si aggiunge un contatore
   senza cambiare la shape.

---

## 8. Stima

| Fase | Effort |
|---|---|
| 3 — smoke di accettazione (3 file) | mezza giornata (è la parte che richiede pensiero) |
| 1 — task indirizzi | ~2 ore |
| 2 — ristampa conforme | ~2 ore |
| 3 — task scadenze | ~2 ore |
| 4 — regressioni D-7 | variabile, dipende da quanto emerge |
| 6 — FE | 0 se la decisione §7.1 è «No» |

Il grosso del tempo non è scrivere il cablaggio: è **verificare che i satelliti
esistano davvero** e che il documento stampato dica la verità.
