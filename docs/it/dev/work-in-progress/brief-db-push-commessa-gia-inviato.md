# Brief DB — Push commessa "già inviato" non rilevato: predicato di esclusione ancorato alla fatturazione + cecità BoM

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🔴 ALTA (bug logico del modello, famiglia già
> corretta per i preventivi)
> **Stato**: **APPLICATO + TEST VERDI** (2026-07-19) — migrations `20260719-05..11`
> EXECUTED su dev; pgTAP `test-push-list-gia-inviato-v1` plan(10) VERDE (il primo
> run aveva 2 rossi da visibilità: insert e assert nella stessa statement, il
> classificatore STABLE non vedeva le righe appena inserite — corretti col
> pattern a due passi). Restano: verifica §7 su ORD0000227 vivo, comunicazione
> §6 a BE/FE, rigen doc auto-gen, commit su «procedi».
> · **Rev 1**: 2026-07-19 (analisi critica lato DB, fatti verificati tutti sulle
> definizioni vive) — tre integrazioni: §4b riformulato su **classificatore
> condiviso** (la capability ordine ha GIÀ due fonti di verità: fn_list per
> can_push + query inline per GIA_FATTURATO — aggiustare la query inline
> perpetuerebbe la duplicazione curata con fn_check_ddt_emittibile); nota
> indice/LIKE in §4a; aggiornamento COMMENT consumi in §4a.
> **Origine**: rilievo in-app di Tid — su ORD0000227 (stato `EVASO`, trigger
> `CONFERMATO`) l'azione «Invia a commessa» resta visibile e rieseguibile
> **dopo** che il push è già avvenuto (attività già in commessa).
> **Vedi anche**: [brief-db-guard-righe-avanzamento-stato.md](brief-db-guard-righe-avanzamento-stato.md)
> (stessa famiglia UX "azione non pertinente non va offerta", causa radice
> diversa) · [brief-db-gate-evaso-commessa-asimmetria.md](../work-done/brief-db-gate-evaso-commessa-asimmetria.md)
> (precedente: stesso bug diagnosticato e corretto per i preventivi, 2026-06-28).

## 1. Sintomo (dati vivi, DB dev 2026-07-19)

ORD0000227:

| stato | trigger | righe attive | attività già pushate | di cui EMESSE | `fn_list_ordini_da_pushare` | `can_push_commessa` |
|---|---|---|---|---|---|---|
| EVASO | CONFERMATO | 1 | **3** (componenti BoM `#CMP:`, tutte `NON_EMESSA`) | 0 | **1 riga "pushabile"** | **true** |

Le 3 attività (`commesse_attivita` id 536-538, `segment_key`
`ORD:<uid>:R:241#CMP:<componente>`, `APPROVATA`/`NON_EMESSA`) provano che il
push è già stato consumato; la capability continua a offrirlo e il batch
continua a ri-elencare la riga a ogni giro.

Nota: che un ordine **EVASO** sia eleggibile al push è **per design**
(rev 2026-07-10, decoupling fatturazione/spedizione,
`piano-db-fix-orfano-push-ordine-confermato.md`) e NON va toccato.
Il bug è solo il mancato rilevamento del "già inviato".

## 2. Causa — due difetti sovrapposti nel predicato di esclusione

`fn_list_ordini_da_pushare` (fonte unica di `fn_available_actions_ordine`)
esclude una riga così:

```sql
AND NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                 WHERE ca.segment_key = 'ORD:' || o.uid::text || ':R:' || or_r.id::text
                   AND ca.stato_emissione = 'EMESSA')
```

1. **Ancoraggio sbagliato** — esclusa solo quando l'attività è `EMESSA`
   (= fatturata), non quando è stata **pushata** (allocata). È l'identica
   asimmetria allocazione/fatturazione del brief preventivi, dove la decisione
   di modello è stata: *instradata = esclusa appena allocata, qualunque
   `stato_emissione`* (ANNULLATA inclusa: conta come instradata).
2. **Cecità BoM** — match per **uguaglianza** sulla `segment_key` di riga: le
   attività delle righe composite hanno suffisso `#CMP:<componente>` e non
   matchano **mai**, nemmeno dopo la fatturazione. Stesso §4 del brief
   preventivi, lì risolto col match a prefisso `#CMP:%`.

Conseguenze: azione ri-offerta dopo il consumo (anti-pattern UX del brief
capability); ri-listing perpetuo nel batch fino alla fatturazione; per righe
BoM, **dopo** la fatturazione il pulsante resta comunque visibile e il click
fallisce con `E_COMMESSA_ATTIVITA_GIA_EMESSA` (banner errore su azione che non
doveva essere offerta). Anche il ramo reason `ORDINE_GIA_FATTURATO` della
capability usa lo stesso match per uguaglianza → per righe BoM non scatta mai.

Oggi il re-click è innocuo sui dati (upsert idempotente su
`(commessa_id, segment_key)` + ponte di ri-approvazione post-push), quindi
niente urgenza dati: l'urgenza è di modello/UX.

## 3. Perimetro (verificato sulle definizioni vive)

| Funzione | Difetto 1 (EMESSA) | Difetto 2 (BoM `#CMP`) |
|---|---|---|
| `fn_list_ordini_da_pushare` | ✗ | ✗ (caso ORD0000227) |
| `fn_list_ddt_da_pushare` | ✗ | ✗ (predicato identico) |
| `fn_list_contratti_da_pushare` | ✗ | ✗ (predicato identico) |
| `fn_list_consumi_da_pushare` | ✗ | ✅ già a prefisso (`LIKE 'CONS:<uid>:%'`) |
| `fn_list_preventivi_da_pushare` | ✅ | ✅ (vista `vw_preventivi_righe_smistabili_commessa`, fix 2026-06-28) |

Le capability che specchiano le push-list: `fn_available_actions_ordine`
(push + ramo `ORDINE_GIA_FATTURATO`) e `fn_available_actions_ddt`
(push, reason `DDT_NON_PUSHABILE`).

## 4. Cosa serve (NON come)

### 4a. Allineare le 4 push-list alla semantica decisa per i preventivi

Esclusione su **esistenza** dell'attività (allocazione), qualunque
`stato_emissione`, e match che veda anche i componenti BoM — la forma già
applicata alla vista preventivi:

```sql
AND NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                 WHERE ca.segment_key = '<PFX>:' || uid || ':R:' || riga_id
                    OR ca.segment_key LIKE '<PFX>:' || uid || ':R:' || riga_id || '#CMP:%')
```

(`fn_list_consumi_da_pushare`: già a prefisso, basta togliere il filtro
`stato_emissione = 'EMESSA'` — ⚠️ e aggiornare COMMENT + manuale nello stesso
changeset: la semantica dichiarata passa da «esclude già emessi» a «esclude già
allocati», altrimenti la doc torna a mentire.)

> **Nota performance (Rev 1)**: su `commesse_attivita.segment_key` c'è solo un
> btree standard — con collazione non-C il `LIKE '...#CMP:%'` non lo usa, e nel
> `NOT EXISTS` correlato del batch è una scansione per riga candidata. Il
> precedente preventivi ha già accettato questo costo (a scala attuale non si
> vede): NON è un blocker. Se il batch rallenta, la cura è un indice
> `varchar_pattern_ops` su `segment_key`, non tornare all'uguaglianza.

Semantica ANNULLATA invariata rispetto alla decisione preventivi: attività
annullata = riga instradata, non ri-pushabile (eventuale "annulla e ri-pusha"
è un flusso da progettare a parte, non qui).

### 4b. Capability: distinguere "già inviato" da "già fatturato" — via classificatore CONDIVISO

Con la 4a le righe pushate spariscono dalla lista → serve la reason corretta
al posto dell'attuale fallback (`ORDINE_NESSUNA_RIGA_PUSHABILE` /
`DDT_NON_PUSHABILE`, fuorvianti su documento già instradato):

- `ORDINE_GIA_INVIATO` (pushato, in attesa fatturazione) distinta da
  `ORDINE_GIA_FATTURATO`;
- analogo per il DDT (`DDT_GIA_INVIATO` / `DDT_GIA_FATTURATO`).

**⛔ Vincolo di forma (Rev 1) — NON aggiustare la query inline.** La capability
ordine ha già oggi **due fonti di verità**: `fn_list_ordini_da_pushare` per il
`can_push` e una query inline *diversa* per il ramo `ORDINE_GIA_FATTURATO`.
Correggere il match della query inline perpetuerebbe la duplicazione — è la
stessa malattia curata sull'emissione DDT con `fn_check_ddt_emittibile`
(brief capability, Rev 2). Con la 4a gli stati da distinguere diventano **tre**
(pushabile / allocata / emessa): si estrae **un classificatore condiviso** —
una `fn_check_*` pura (o vista) che classifica lo stato-push delle righe di un
documento con l'UNICO predicato (uguaglianza OR prefisso `#CMP:%`) — consumato
sia dalle push-list (esclusione = riga allocata) sia dai rami reason delle
capability (allocata e non emessa → GIA_INVIATO; emessa → GIA_FATTURATO).
Al prossimo cambio di semantica si tocca UN posto. Senza questo vincolo, il
terzo brief di questa famiglia sarà «il ramo reason non vede X».

Forma già decisa nel [brief capability](brief-db-guard-righe-avanzamento-stato.md)
§1a: azione **disabled + `reason`/`reason_key`**, mai omessa.

### 4c. Contratti: conferma di semantica — RISOLTA IN VERIFICA (Rev 1)

**La premessa della domanda era errata**: la `segment_key` contratti NON è
`CONTR:<uid>:R:<riga>` — è `CONTR:<uid>:R:<riga>:M:<YYYY-MM>` (verificato sul
corpo vivo di `fn_list_contratti_da_pushare`): il push contratti è **già
ricorrente per mese di competenza**, non one-shot. La ricorrenza che il §4c
temeva di abilitare esiste già, ed è governata dalla chiave, non dal predicato.
Conseguenze:

- il fix 4a per i contratti esclude «il MESE già allocato» (chiave completa
  con `:M:`), che è esattamente la semantica giusta: il mese successivo ha
  chiave diversa e resta pushabile;
- la base del match (uguaglianza + `#CMP:%`) è la **segment_key emessa dalla
  lista** — che per i contratti include `:M:` — perché il BE appende
  `#CMP:<componente_id>` proprio a quella
  (`commesse_source_handlers.py:251`): il predicato uniforme funziona per
  tutti i tipi senza casi speciali.

## 5. Fuori perimetro

- Eleggibilità dell'ordine EVASO al push (design 2026-07-10): invariata.
- Idempotenza dell'upsert su `segment_key` (cintura): invariata.
- Preventivi e (per il difetto 2) consumi: già corretti.
- Flusso "annulla attività e ri-pusha": da progettare a parte.

## 6. Cosa comunicare indietro a BE/FE

- Codici reason nuovi (`ORDINE_GIA_INVIATO`, `DDT_GIA_INVIATO`, o nomi scelti)
  + `reason_key` i18n, per il mapping messaggi/tooltip FE.
- Conferma che le firme delle 4 `fn_list_*_da_pushare` restano invariate
  (solo predicato più preciso): in tal caso zero tocchi BE
  (`CommesseRepository.fetch_pushable_rows` e handler invariati).

## 7. Verifica post-fix

```sql
-- ORD0000227: attese 0 righe pushabili e can_push_commessa=false
SELECT count(*) FROM vendite.fn_list_ordini_da_pushare(p_ordine_id := <id>);
SELECT (script.fn_available_actions_ordine(<id>))->>'can_push_commessa';
```

Più smoke esistenti push ordini/DDT (batch: un giro dopo il push non deve
ri-elencare le stesse righe; re-push singolo → azione disabled con reason
"già inviato").

## 8. Avanzamento

| # | Step | Stato |
|---|---|---|
| 0 | **Classificatore condiviso** `script.fn_get_stato_push_segment` (LIBERA/ALLOCATA/EMESSA, match `#CMP:%`) + manuale — `20260719-05` | ☑ |
| 1 | Push-list su ALLOCAZIONE via classificatore: ordini `-06`, DDT `-07`, contratti `-08` (chiave con `:M:`); consumi `-09` (solo drop filtro `stato_emissione` + COMMENT) | ☑ |
| 2 | Capability: `ORDINE_GIA_INVIATO`/`ORDINE_GIA_FATTURATO` (`-10`) e `DDT_GIA_INVIATO`/`DDT_GIA_FATTURATO` (`-11`), entrambe via classificatore — sparita la query inline | ☑ |
| 3 | Semantica contratti: **risolta in verifica** (§4c — chiave `:M:` = ricorrenza mensile by design, il fix esclude il mese allocato) | ☑ |
| 4 | Apply dev + pgTAP — **FATTO 2026-07-19** (migrate applicato, plan(10) verde); restano verifica §7 su ORD0000227 e comunicazione §6 a BE/FE | ☑ |

## 9. Riferimenti

- Precedente (stessa famiglia, preventivi): `../work-done/brief-db-gate-evaso-commessa-asimmetria.md`
- Design EVASO eleggibile al push: `../work-done/piano-db-fix-orfano-push-ordine-confermato.md`
- Definizioni vive: `docs/it/dbzero/vendite/funzioni/fn_list_*_da_pushare.md`,
  `docs/it/dbzero/script/funzioni/fn_available_actions_{ordine,ddt}.md`
- Upsert idempotente + guard `E_COMMESSA_ATTIVITA_GIA_EMESSA`:
  `docs/it/dbzero/vendite/funzioni/fn_upsert_commessa_attivita.md`
- Ponte approvazione post-push: `backend/apps/vendite/services/commesse_service.py::_rendi_commessa_emittibile`
