# Brief DB — Push commessa "già inviato" non rilevato: predicato di esclusione ancorato alla fatturazione + cecità BoM

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🔴 ALTA (bug logico del modello, famiglia già
> corretta per i preventivi)
> **Stato**: ☐ DA REALIZZARE
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
`stato_emissione = 'EMESSA'`.)

Semantica ANNULLATA invariata rispetto alla decisione preventivi: attività
annullata = riga instradata, non ri-pushabile (eventuale "annulla e ri-pusha"
è un flusso da progettare a parte, non qui).

### 4b. Capability: distinguere "già inviato" da "già fatturato"

Con la 4a le righe pushate spariscono dalla lista → serve la reason corretta
al posto dell'attuale fallback (`ORDINE_NESSUNA_RIGA_PUSHABILE` /
`DDT_NON_PUSHABILE`, fuorvianti su documento già instradato):

- `ORDINE_GIA_INVIATO` (pushato, in attesa fatturazione) distinta da
  `ORDINE_GIA_FATTURATO`; entrambi i rami con match anche a prefisso `#CMP:%`;
- analogo per il DDT (es. `DDT_GIA_INVIATO`).

Forma già decisa nel [brief capability](brief-db-guard-righe-avanzamento-stato.md)
§1a: azione **disabled + `reason`/`reason_key`**, mai omessa.

### 4c. Contratti: conferma di semantica (domanda al team DB)

Per ordini/DDT il push è one-shot per riga ed è pacifico che "allocata =
esclusa". Per i contratti confermare che valga lo stesso (la `segment_key`
`CONTR:<uid>:R:<riga>` è fissa per riga, quindi il modello attuale è già
one-shot: l'esclusione su EMESSA non abilita alcuna ricorrenza — se in futuro
servisse un push ricorrente per competenza, sarà una `segment_key` diversa,
non questo predicato).

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
| 1 | Predicato allocazione + prefisso `#CMP:%` su `fn_list_{ordini,ddt,contratti}_da_pushare`; solo `stato_emissione` su `fn_list_consumi_da_pushare` (§4a) | ☐ |
| 2 | Capability: reason "già inviato" vs "già fatturato" (ordine + DDT), match `#CMP` anche su `ORDINE_GIA_FATTURATO` (§4b) | ☐ |
| 3 | Conferma semantica contratti (§4c) | ☐ |
| 4 | Apply dev + comunicazione reason/firme a BE/FE (§6) + verifica §7 | ☐ |

## 9. Riferimenti

- Precedente (stessa famiglia, preventivi): `../work-done/brief-db-gate-evaso-commessa-asimmetria.md`
- Design EVASO eleggibile al push: `../work-done/piano-db-fix-orfano-push-ordine-confermato.md`
- Definizioni vive: `docs/it/dbzero/vendite/funzioni/fn_list_*_da_pushare.md`,
  `docs/it/dbzero/script/funzioni/fn_available_actions_{ordine,ddt}.md`
- Upsert idempotente + guard `E_COMMESSA_ATTIVITA_GIA_EMESSA`:
  `docs/it/dbzero/vendite/funzioni/fn_upsert_commessa_attivita.md`
- Ponte approvazione post-push: `backend/apps/vendite/services/commesse_service.py::_rendi_commessa_emittibile`
