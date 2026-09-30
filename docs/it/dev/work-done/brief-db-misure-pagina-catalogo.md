# Brief DB — Le misure di pagina in un catalogo: una sede sola per DB, backend e frontend

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-30. **A chi:** team DB; richieste al backend e al
> frontend (`dev/backend-tid`) in §6.
> **Origine:** §9.7 di [brief-db-liste-righe-documento.md](../work-in-progress/brief-db-liste-righe-documento.md).
> ✅ **Decisioni di Tid (2026-09-29):** strada 3 — l'elenco delle misure vive in UNA sede, il
> database, e il frontend lo legge da lì; e **anche le misure di default** stanno nel catalogo.
> **Stato: ✅ CHIUSO il 2026-09-30.** Tutte le parti sono fatte, applicate, committate e
> collaudate; il brief è in `work-done/`.
>
> * **DB**: `20260930-01 → -13` applicati da Tid alle 00:40, **pgTAP verdi col runner** (Tid).
>   Verificato dopo l'apply: il catalogo ha 10 (COMPATTA), 25 (PAGINA), 50, 100 — il loader del
>   CSV ha scritto il token NULL come NULL —, i due trigger ci sono, l'app non scrive il catalogo,
>   `ui.fn_get_misure_pagina()` risponde.
> * **BE/FE** (`dev/backend-tid`, §6-bis, commit `15a407e1b`): Django e Vitest verdi, build e lint
>   puliti.
> * **Collaudo a video** di Tid: ✅ superato il 2026-09-30.
>
> **In una riga:** oggi le misure «righe per pagina» sono scritte in tre posti (una costante del
> frontend, un'altra per il default compatto, e un `25` ripetuto cinque volte nel resolver delle
> liste). Il 28-09 un preset a 15 — misura che il paginatore non offre — ha lasciato il
> selettore vuoto senza nessun errore. Un catalogo le tiene tutte, e il DB rifiuta una misura
> che non ci sta.

---

## 1. Cosa c'è oggi — letto dalla struttura (2026-09-30)

* **Frontend** — `frontend/src/core/constants.js`: `PAGINATION = { DEFAULT_ROWS: 25,
  COMPACT_ROWS: 10, ROWS_OPTIONS: [10, 25, 50, 100] }`, usato in 25 file (non solo liste
  configurabili: tabelle grezze, dialog, dashboard).
* **DB** — la misura sta in `ui.lista_preset.pagina_dimensione integer` (NULL = «il default») e
  nel jsonb `ui.lista_preferenza_utente.configurazione ->> 'pagina_dimensione'`. Nessun vincolo.
* **DB** — `ui.fn_resolve_lista_config` ripiega su `25` **scritto cinque volte**: la terza copia
  del default.
* 🔴 **Un difetto latente nel resolver**: il passo 2a (la preferenza) è un `SELECT … INTO`
  anche quando la preferenza non c'è, e a zero righe azzera `v_pagina_dim`. Se poi la lista non
  ha un preset e si arriva al ripiego sul catalogo delle colonne (2e), la misura esce **NULL**, e
  oggi la salva solo la costante del frontend.

## 2. Il modello

**`ui.misure_pagina`** — il catalogo, posseduto dal CSV (`80_data/sql/ui/misure_pagina.csv`):

| Colonna | Cosa |
| --- | --- |
| `id` | chiave tecnica |
| `misura integer` UNIQUE, `> 0` | la chiave naturale stabile (linee-guida §6b): chi la cita, cita il numero |
| `uso_default varchar(20)` NULL | `COMPATTA` (drawer e dialog) o `PAGINA` (pagine); al più una riga per uso (indice unico parziale) |

Sei regole, e chi le fa rispettare:

1. **Un preset cita solo misure del catalogo** — FK `ui.lista_preset.pagina_dimensione →
   ui.misure_pagina(misura)` (la rete, e il blocco alla cancellazione di una misura in uso) più un
   guard che rifiuta **con un codice parlante** invece di un 23503 grezzo.
2. **Una preferenza utente cita solo misure del catalogo** — guard sul jsonb (una FK non ci
   arriva).
3. **Il resolver non inventa**: la misura che risponde è quella scelta (preferenza o preset) se è
   nel catalogo, altrimenti il default `PAGINA`. Il `25` scritto cinque volte esce; il difetto del
   §1 si chiude con lo stesso passaggio.
4. **Un solo posto risponde «le misure e i default»** all'applicazione: `ui.fn_get_misure_pagina()`.
5. **Il catalogo lo scrive solo il CSV**: all'app solo `SELECT` (tre sedi, linee-guida §11.8).
6. **Ogni uso di default ha la sua riga**: lo pretende il pgTAP (l'indice unico dice «al più
   una», non «almeno una»); e se manca, chi chiede il default riceve un errore tecnico parlante,
   non un NULL.

## 3. ⛔ L'ordine su un database ricostruito da zero

I preset si seminano in `80_data/20260507-08` e il catalogo in `80_data/20260930-02`, che
viene **dopo** nell'ordine dei file. Un vincolo sui preset nato prima del catalogo fermerebbe il
migrate sul primo preset. Quindi la **FK** e il **trigger del guard** su `ui.lista_preset`
nascono in **`90_end`**, a seed già scritti. Le preferenze utente non hanno seed: il loro trigger
nasce in `20_code` come di norma.

## 4. I changeSet (DB)

| # | Dove | Cosa |
| --- | --- | --- |
| `20260930-01` | `00_schema/ui` | `ui.misure_pagina` |
| `-02` | `80_data` | CSV + mirror `runOnChange` |
| `-03` | `20_code/ui` | `ui.fn_misura_pagina_ammessa(misura) → boolean` (la chiedono guard e resolver) |
| `-04` | `20_code/ui` | `ui.fn_misura_pagina_default(uso) → integer` (la chiedono resolver e lettura per l'app) |
| `-05` | `20_code/ui` | `ui.fn_get_misure_pagina() → jsonb` — `{misure, default_compatta, default_pagina}` |
| `-06` | `20_code/ui` | `ui.fn_guard_misura_pagina(misura)` — solleva `E_UI_MISURA_PAGINA_NON_AMMESSA` |
| `-07`, `-08` | `20_code/ui` | le due trigger function (preset, preferenza) |
| `-09` | `20_code/ui` | il trigger sulla preferenza utente |
| `-10` | `20_code/ui` | `fn_resolve_lista_config` dal catalogo (§2, regola 3) |
| `-11` | `90_end` | la FK dei preset |
| `-12` | `90_end` | il trigger sui preset |
| `-13` | `90_end` | la porta (all'app solo `SELECT`), più il loop `ci_apply` e il provisioning |

Codici: `E_UI_MISURA_PAGINA_NON_AMMESSA` (DATO_ERRATO), `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`
(TECNICO). Registro indici FK: `fk_index_policy_ui.csv` (`consentito = false`: il catalogo ha
quattro righe e la FK non è un percorso di lettura).

## 5. Le prove (2026-09-30, prima dell'apply)

✅ **Dopo l'apply (2026-09-30, 00:40)**: corsa col runner di Tid verde, compreso il 16 (come app).

SQL **estratto** dagli YAML, in `BEGIN … ROLLBACK` sul DB di sviluppo, come owner; seed del
catalogo e dei due codici simulato (⚠️ non prova il loader di Liquibase: lo dice l'apply).

* `ui/test-misure-pagina-v1` (18): **17 verdi**; il **16** (UPDATE del catalogo come app → 42501)
  rosso da owner per costruzione.
* **Regressione per asserzione** (stesso file senza e con i changeSet) sui 16 pgTAP di `ui` e sui
  presidi trasversali (`catalogo-messaggi-errore-completo`, `riferimenti-morti`,
  `rubinetto-primo-motivo`, `vw-codici-errore-*`, `pannello-porta`, `codici-errore-identita`,
  `storico-scope-policy`, `stati-check-scrittori`): nessuna asserzione cambia, **salvo**
  `ui/test-fn-resolve-lista-config`, che costruiva una preferenza a **99** e un preset a **77** —
  misure che il catalogo ora rifiuta (è la regola che funziona). Riallineato nello stesso giro a
  100 e 25 (servono solo misure diverse da 10 e 50): 13/13 come prima.
  ⚠️ Lezione: il censimento dei pgTAP che scrivono una misura andava fatto **prima** del guard.
* Guardrail statici verdi; oggetti vivi confrontati prima e dopo: invariati.
* Due trappole prese in prova: `IF CASE … THEN … END THEN` in PL/pgSQL chiude la condizione al
  primo `THEN` (servono le parentesi); il nome del trigger sulla preferenza superava i 63
  caratteri (accorciato).

## 6. ✅ Richieste al BE / FE (`dev/backend-tid`) — evase, esito in §6-bis

1. **BE**: servire `ui.fn_get_misure_pagina()` **a tutta l'applicazione** (non dentro la
   configurazione di una lista): le usano anche tabelle grezze, dialog e dashboard.
2. **FE**: il paginatore prende misure e default da lì; `PAGINATION.ROWS_OPTIONS`,
   `COMPACT_ROWS` e `DEFAULT_ROWS` **si ritirano nello stesso giro** (25 file, regola del 2).
   Finché la risposta non è arrivata, cosa mostra il paginatore è da decidere col FE (una
   chiamata al boot, come le altre configurazioni globali).
3. ✅ **BE**: le policy HTTP dei due codici nuovi — fatte il 2026-09-30 con la rigenerazione
   di `error_policies_generated.py` (brief-db-liste-righe-documento §9.12):
   `E_UI_MISURA_PAGINA_NON_AMMESSA` `DATO_ERRATO`, `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE`
   `TECNICO`, con i ripieghi senza segnaposto.
4. **BE — una quarta sede della regola**: `apps/ui/services/lista_preferenza_service.py` valida
   `pagina_dimensione` da sé («intero positivo, al massimo `MAX_LIMIT`»). È una regola **diversa**
   dal catalogo (ammette 37, che il paginatore non offre) e con il guard a DB diventa
   una copia che diverge: si ritira, e il service traduce `E_UI_MISURA_PAGINA_NON_AMMESSA`. Lo
   stesso per `lista_preset_admin_service` se valida la misura. I due test mock
   (`test_upsert_pagina_dimensione_oltre_max_raises`, `…_non_int_raises`) vanno riletti con lui.
5. **BE**: i limiti di pagina propri del backend (i `limit` di default nelle firme dei repository,
   brief liste §9.6 punto 3) sono un tema vicino ma diverso — quanti record al massimo si chiedono
   — e restano fuori.

## 6-bis. ✅ Esito BE/FE (`dev/backend-tid`, 2026-09-30)

Decisioni di Tid del 30-09: le misure si caricano **nel guard del router, una volta, attese**; se
la chiamata fallisce si apre la pagina «Avvio non riuscito», **senza ripiego** nel FE. Ok ai due BB
nuovi e al ritiro di `PAGINATION` nello stesso giro.

| # | Esito |
| --- | --- |
| 1 | ✅ `GET /api/v1/ui/misure-pagina/` → `UiService.get_misure_pagina` → `UiRepository.get_misure_pagina` (1:1 su `ui.fn_get_misure_pagina()`), `skip_area_check`. Pagina API: `api_ui_liste.md` §6 |
| 2 | ✅ BB FE `core/misurePagina.js`: il guard la carica per il namespace operatore; letture sincrone (`misureOpzioni`, `misuraDefault(uso)`, `misuraPerViewport`). Gli store dichiarano l'**uso** (`misura: USO_MISURA.COMPATTA`), non il numero; l'opzione `limit` del core è ritirata e solleva. Ritirati nello stesso giro: `PAGINATION` (circa 30 file), gli array a mano di `ContrattoRigheDrawer` (`[10, 25, 50]`) e `OffertaEccezioniDrawer` (`[10, 25]`), quattro `limit: 25` scritti a mano (`codeJobs`, `fondiFatturaDaDecidere`, `approvazioniPrezzo`, `resiCoda`) e la regola «compatta sotto il tablet», che era scritta due volte. Il drawer dei preset sceglie da un `Select` sulle misure del catalogo (prima era un `InputNumber` 1-500) e manda sempre la misura, anche `null`: prima tornare al default da video non si poteva |
| 3 | ✅ Le policy dei due codici sono nel file generato (`DATO_ERRATO` → 400, `TECNICO` → 500) con i ripieghi. ⚠️ La rigenerazione conteneva anche i codici di **altri** brief (DDT, reso, TOTP…): nel commit di questo cantiere sono entrate **solo** le quattro righe `E_UI_MISURA_PAGINA_*`; il resto lo committa chi lo ha rigenerato |
| 4 | ✅ Ritirati `MAX_LIMIT` (preferenza) e `_MAX_PAGINA_DIMENSIONE = 500` (preset): resta il solo controllo di forma. Il test mock `…_oltre_max_raises` ora prova il contrario (la misura arriva intatta al repository); `…_non_int_raises` resta com'è, perché prova la forma. Nel preset nessun test provava il tetto. Il trasporto dal DB è provato sul DB vero in `apps/ui/tests/db/test_misure_pagina_db.py`: preset e preferenza fuori catalogo → `E_UI_MISURA_PAGINA_NON_AMMESSA`, 400 |
| 5 | fuori perimetro, come previsto: `DEFAULT_LIMIT` del backend resta; lo dice api.md §Paginazione |

⚠️ **Da sapere**: l'altezza del blocco lista nei dialog (`--app-dialog-lista-h`, theme.css) è
calibrata su dieci righe. Se il CSV sposta la `COMPATTA`, la lista resta giusta ma scorre dentro
la tabella; l'altezza va riallineata a mano.

**Rilettura critica dello stesso giorno (2026-09-30), difetti trovati e corretti:**

* 🔴 **La pagina d'errore cadeva per la stessa causa che doveva mostrare.** Il layout (`AppTopbar` →
  `SearchDrawer` → `usePagination`) legge le misure quando nasce, ma il guard le caricava solo sulle
  rotte non universali: una 404 al ricaricamento, o la stessa «Avvio non riuscito» che era dentro
  `AppLayout`, lanciavano un errore nel layout. Ora il guard carica per **ogni rotta sotto
  `AppLayout`** (veste operatore), la pagina d'errore sta **fuori** dal layout, e `SearchDrawer` si
  monta alla prima apertura (la topbar c'è anche sulle 404/forbidden delle vesti non operatore, per
  cui le misure non si caricano).
* 🟡 `useListaDrawerPaginata`, il BB delle liste **in drawer**, partiva dalla misura di pagina
  contro la regola del 28-09: ora parte dalla `COMPATTA` (il preset, se c'è, vince comunque).
* 🟡 Una quinta copia del 25: `pageSize = 25` di default in tre funzioni di `vendite/api/lotti.js`;
  ora il default viene dal BB.
* 🟢 `registraMisurePagina` rifiuta anche misure non strettamente crescenti o doppie (l'ordine è
  quello del selettore); tolto un wrapper inutile in `useSearchTable`; corretto un commento stantio
  in `listiniRighe`.
