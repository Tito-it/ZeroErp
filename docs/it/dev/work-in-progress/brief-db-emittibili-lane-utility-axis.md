# Brief DB — Aggiungere `utility_id` alla grana di `fn_list_emittibili_lane`

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; il *come* (changeset, pgTAP) è del team DB.
>
> **Data**: 2026-06-19 · **Stato**: 🟢 **DECISIONE PRESA (2026-06-19)** — vedi §3.
>
> **Origine**: **smoke live** del batch a RLS enforced (run reale, 2026-06-19). Chiuso il
> gap tipo_doc, il primo run reale è fallito con
> `E_PARAMETRO_INVALIDO: utility_id obbligatoria` da `fn_create_fatturazione_lotto`.
> Follow-up diretto di [brief-db-emittibili-lane-tipo-doc-fiscale.md](brief-db-emittibili-lane-tipo-doc-fiscale.md)
> (stessa fn, un asse in più). **Indipendente** dal brief tipo_doc normalize+guard.
>
> **Prerequisito di**: il BE del driver
> [brief-be-driver-batch-lane-utility.md](brief-be-driver-batch-lane-utility.md).

---

## 1. Contesto e problema

Un **lotto di fatturazione è segregato anche per `utility_id`**:

- `fn_create_fatturazione_lotto` **pretende** `utility_id` non-null (diretto o derivato da
  BA): con BA e utility entrambi NULL solleva
  `E_PARAMETRO_INVALIDO: utility_id obbligatoria`.
- `fn_select_attivita_fatturabili` **filtra** le AF per `ba.utility_id = lotto.utility_id`.

Quindi la grana reale del lotto è **(emittente, tipo_doc, utility, competenza)**. Ma
`fn_list_emittibili_lane` oggi raggruppa solo su **(emittente, tipo_doc, competenza)** e
usa `utility_id` solo come **filtro opzionale** in input, senza restituirlo. Il driver,
non avendo l'utility dalla discovery e non avendo un BA da cui derivarla (il lotto è
per-emittente, multi-BA), passa `utility_id = NULL` → errore.

> ⚠️ Differenza sostanziale dal gap tipo_doc: **`commesse.utility_id` è NOT NULL** (e
> `commesse_attivita.istanza_utility_id` pure). Quindi **non c'è alcun problema di
> integrità** da guardare: l'utility è sempre presente. Serve **solo esporla** nella grana
> della discovery. Niente normalize, niente guard, niente backfill.

---

## 2. Cosa serve (risultato atteso)

Estendere `vendite.fn_list_emittibili_lane` perché la grana includa `utility_id`:

- **Output**: aggiungere `utility_id` alla `RETURNS TABLE`, diventando
  `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, **utility_id**, competenza_mese,
  total_candidate)`.
- **GROUP BY**: raggruppare anche per `c.utility_id` (la fn già fa JOIN su
  `vendite.commesse c` e filtra `c.utility_id` — è già disponibile, va solo aggiunta a
  SELECT + GROUP BY).
- **Filtro `p_utility_id`**: resta invariato (restringe la discovery a una utility).
- Tutto il resto invariato: criterio `APPROVATA + NON_EMESSA`, esclusione tipo_doc NULL,
  competenza cumulativa `<=` con output `max(...)`, filtro corsia `fatturazione_immediata`,
  `p_limit` sulle coppie (ora **terne+**), `STABLE`.

`utility_id` è NOT NULL a monte → in output **non sarà mai NULL** (nessun caso da escludere).

---

## 3. Decisione presa (2026-06-19)

- **Grana per-utility confermata (opzione A).** Il sistema **già** impone utility non-null
  sul lotto (`fn_create`) e segrega le AF per utility (`fn_select`): la fatturazione è
  **per-utility** (gas/ee/idrico = documenti distinti). Scartata l'opzione B (rilassare la
  guard per lotti cross-utility): contraddirebbe il filtro del select.
- **Solo discovery**, nessun guard/normalize/backfill (utility è già NOT NULL).
- `fn_list_commesse_emittibili` (usata dalla pull) resta **invariata**.

---

## 4. Criteri di accettazione

- Emittente E con righe APPROVATA+NON_EMESSA su utility U1 e U2 (stesso tipo_doc) →
  discovery restituisce **due terne** distinte `(E, tipo_doc, U1)` e `(E, tipo_doc, U2)`,
  ciascuna col proprio `total_candidate` e `competenza_mese = max(...)`.
- `utility_id` in output **mai NULL**.
- Filtro `p_utility_id` rispettato (se fornito, restringe a quella utility).
- Nessuna regressione sugli altri criteri (tipo_doc NULL escluso, competenza `<=`,
  corsia, APPROVATA+NON_EMESSA).
- pgTAP: caso multi-utility per stesso (emittente, tipo_doc); coerenza con i test
  esistenti della lane fn.

---

## 5. Piano DB (deliverable)

| # | Deliverable | Path (indicativo) | Note |
| --- | --- | --- | --- |
| U1 | Update `fn_list_emittibili_lane`: `utility_id` in `RETURNS TABLE` + SELECT + GROUP BY | `20_code/vendite/20260619-NN-update-fn-list-emittibili-lane-utility-…` | DROP/CREATE (cambia RETURNS TABLE); `runOnChange:false` + `validCheckSum:[ANY]`; partire dal corpo della doc auto-gen |
| U2 | pgTAP: terne multi-utility + non-regressione | `db/pgtap/vendite/test-fn-list-emittibili-lane.sql` (estendere) | aggiungere fixture multi-utility |
| U3 | Doc manuale companion (autogen via `gen_db_docs.py`) | `docs/it/dbzero/vendite/manual/fn_list_emittibili_lane.md` | — |

---

## 6. Fuori scope

- BE del driver (iterazione sulle terne, passaggio `utility_id` al lotto): vedi
  [brief-be-driver-batch-lane-utility.md](brief-be-driver-batch-lane-utility.md).
- Integrità tipo_doc (normalize+guard): brief separato, concerne diverso.
