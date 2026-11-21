# Brief BE — Driver batch: iterazione sulle terne (emittente, tipo_doc, utility)

> **Tipo documento**: piano **backend**. Dipende da una modifica DB già consegnata al team.
>
> **Data**: 2026-06-19 (chiuso 2026-06-20) · **Stato**: 🟢 **COMPLETATO** — BE committato
> (`8824cafc7` su `dev/backend-tid`); **smoke E2E verde dal vivo** (lotto 117 MASSIVO →
> `DEFINITIVA/CHIUSO`, fattura 210 `DEFINITIVA` numerata 1/2026/R2). La catena per-step
> `1→2→8` gira end-to-end (vedi [piano-fix-stato-fattura-pipeline-per-step.md](piano-fix-stato-fattura-pipeline-per-step.md)).
>
> **Prerequisito**: [brief-db-emittibili-lane-utility-id.md](brief-db-emittibili-lane-utility-id.md)
> — `fn_list_emittibili_lane` restituisce `utility_id` nella grana. ✅ **ATTERRATO**
> (DB implementato e testato), quindi il BE è sbloccato ([feedback_be_fe_attende_prerequisiti_db]).
>
> **Origine**: smoke live 2026-06-19 — il run reale fallisce su `utility_id obbligatoria`
> perché il driver crea il lotto senza utility. Seguito del fix tipo_doc (già committabile).

---

## 1. Contesto

Il driver `run_fatturazione_batch` itera già sulle **coppie (emittente, tipo_doc)** prodotte
da `CommesseRepository.list_emittibili_lane` e crea un lotto per coppia. Lo smoke ha
mostrato che **manca l'asse utility**: il lotto è segregato anche per `utility_id`
(`fn_create_fatturazione_lotto` lo pretende non-null; `fn_select_attivita_fatturabili`
filtra per utility). La grana corretta è **(emittente, tipo_doc, utility, competenza)**.

Una volta che la lane fn ritorna `utility_id` (prereq DB), il BE deve solo **propagarlo**.

---

## 2. Modifiche BE (a valle del prereq DB)

### 2.1 `apps/vendite/types.py` — `CommessaEmittibileLane`
Aggiungere il campo `utility_id: int` (NOT NULL a monte → `int`, non `int | None`).
Aggiornare il commento (grana ora a 4 assi).

### 2.2 `apps/vendite/db/commesse_repository.py` — `list_emittibili_lane`
- Aggiungere `utility_id` alla SELECT e al mapping del risultato (`int(row[...])`).
- Ordine colonne allineato alla nuova `RETURNS TABLE`:
  `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id, competenza_mese, total_candidate)`.
- Docstring: grana a 4 assi.

### 2.3 `apps/vendite/management/commands/run_fatturazione_batch.py`
- Il loop itera sulle **terne**; per ogni lane passare a `run_lotto_pipeline_until_done`
  **`utility_id=lane["utility_id"]`** (oggi passa il `utility_id` di livello comando, di
  norma `None`). `run_lotto_pipeline_until_done` **accetta già** `utility_id` — nessuna
  modifica al pipeline service.
- `--utility-id` resta **filtro di discovery** (passato a `list_emittibili_lane`), non più
  l'unica fonte dell'utility del lotto.
- Output/log riga: includere `utility=…` accanto a `emittente=…` `tipo_doc=…`.
- Dry-run: stampare anche l'utility per terna.
- `meta`/riepilogo: la chiave resta `lane` (ora conta le terne); nessun cambio strutturale.

### 2.4 Test
- `test_commesse_repository.py::test_list_emittibili_lane`: righe mock a 5 colonne (con
  `utility_id`); asserire il mapping del nuovo campo.
- `test_run_fatturazione_batch_command.py`: helper `_lane(...)` con `utility_id`; asserire
  che `run_lotto_pipeline_until_done` riceva `utility_id` **dalla lane** (non dal comando);
  caso multi-utility per stesso emittente → due run distinti.

---

## 3. Criteri di accettazione (BE)

- Smoke live a RLS enforced: il run reale crea il lotto per ogni terna e genera fatture
  (niente più `utility_id obbligatoria`).
- Emittente con righe su due utility (stesso tipo_doc) → **due lotti** distinti.
- `--utility-id` restringe la discovery a quella utility.
- Suite vendite verde (`manage.py test apps.vendite`).

---

## 4. Fuori scope (separato)

- **Osservabilità guard tipo_doc**: alerting/riepilogo dei push falliti per
  `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO` (dipende dal brief tipo_doc normalize+guard,
  §6 di quel brief). Concerne diverso, BE piccolo a sé.
- Nessuna modifica a pull / `fn_list_commesse_emittibili` / pipeline service.
