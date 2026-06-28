# Brief DB — Gate EVASO ramo commessa: asimmetria con ramo ordine (bug logico)

> **Stato**: ✅ **APPLICATO dal team DB** (2026-06-28) — verificato runtime via smoke
> 1a/1b (preventivo → EVASO al push, `DOMINIO_PREVENTIVO_EVASO`, re-push su EVASO bloccato).
> **Scostamenti rispetto al brief originale** (migliorie, nessuna azione BE):
> 1. Fatto anche il **§4 BoM** (non solo §3): la vista esclude la riga sia sul `segment_key`
>    esatto sia sui componenti `#CMP:%` → anche preventivi con righe composite raggiungono EVASO.
> 2. **Semantica ANNULLATA**: una riga la cui unica attività è annullata conta come instradata
>    → non blocca EVASO e non è ri-pushabile (già vietato da `fn_upsert_commessa_attivita`).
>    Un eventuale flusso "annulla e ri-pusha" andrà progettato a parte.
>
> Contratti delle 3 fn consumer invariati (stessa firma, predicato più preciso).
>
> **Tipo**: brief DB (azione DDL eseguita dal team DB su `dev/db-tid`). · **Priorità**: 🔴 ALTA (bug logico del modello). · **Data**: 2026-06-28.
> **Origine**: smoke E2E `a-test-push-commesse-fatturazione.md` §1 (preventivo → push → fatturazione). Entrambi gli smoke 1a (`smoke-test-pratica-preventivi-conferma.sh`) e 1b (`smoke-test-preventivi-smistamento-ordine.sh`) falliscono allo **stesso** punto: il preventivo resta `ACCETTATO`, non passa mai a `EVASO`, a smistamento commessa **completo**.

---

## 1. Sintomo

A smistamento completo (merce→ordine, servizio→commessa, attività create e `COMPLETATO`):

```
righe-smistabili-ordine = 0            ✓ (ramo ordine ok)
giornale: DOMINIO_ORDINE_CREATO        ✓
giornale: DOMINIO_COMMESSA_CREATA      ✓
preventivo stato = ACCETTATO           ✗ atteso EVASO
giornale: DOMINIO_PREVENTIVO_EVASO     ✗ assente
```

Riprodotto anche con re-push idempotente (1b §13) e multi-sorgente (1b §14, 2° preventivo CONFLUITO nella stessa commessa): **mai EVASO**.

## 2. Causa — asimmetria tra le due gemelle del predicato di residuo

Il gate EVASO (`apps/vendite/services/_smistamento_gate_helpers.py::transiziona_a_evaso_se_smistato`) richiede **entrambi** i predicati falsi:

- `fn_preventivo_ha_residuo_ordine(id)` → legge `vw_preventivi_righe_smistabili_ordine`
- `fn_preventivo_ha_residuo_commessa(id)` → legge `vw_preventivi_righe_smistabili_commessa`

Le due viste gemelle **non sono simmetriche** nella condizione di esclusione (idempotenza di riga):

| Ramo | Una riga è esclusa (= NON più residuo) quando… | Effetto al push |
|---|---|---|
| **ORDINE** (`vw_..._ordine`) | esiste l'**allocazione**: `NOT EXISTS ordini_righe.preventivo_riga_id` | esclusa appena **pushata** → residuo=0 ✓ |
| **COMMESSA** (`vw_..._commessa`) | esiste un'attività con **`stato_emissione = 'EMESSA'`** | esclusa solo dopo **fatturazione** → residuo resta TRUE ✗ |

Il push crea le `commesse_attivita` in stato **`NON_EMESSA`** (default `fn_upsert_commessa_attivita`; `stato_emissione='EMESSA'` arriva solo a valle, in `fn_emit_attivita_fatturabili_da_commessa`). Quindi il ramo commessa àncora il "residuo" alla **fatturazione**, mentre il ramo ordine all'**allocazione**. Il preventivo non raggiunge mai EVASO al push.

Il commento della vista stessa lo tradisce: dice *"non già **EMESSA in commessa**"* (= già pushata/allocata) ma la SQL implementa `stato_emissione = 'EMESSA'` (= già fatturata). **Commento ≠ codice.**

Contraddice il modello documentato — `gestione-pratiche-come-procedere.md §1.1` passo 2: *"Commessa→`PRONTA_FATTURAZIONE`, preventivo→`EVASO`"* **come parte del push/CONFERMA**, prima della fatturazione. EVASO = "tutte le righe instradate alla loro destinazione documentale", **non** "tutto fatturato".

## 3. Fix richiesto — rendere simmetrica la vista commessa

File: `db/changelog/migrations_v2/20_code/vendite/20260612-02-create-vw-preventivi-righe-smistabili-commessa-mctit.yaml` (nuovo changeset `runOnChange`/update, non modificare lo storico).

Nella `NOT EXISTS` (righe 78-82 dell'attuale DDL) **rimuovere** il filtro `stato_emissione`:

```sql
-- PRIMA (bug):
AND NOT EXISTS (
  SELECT 1 FROM vendite.commesse_attivita ca
   WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
     AND ca.stato_emissione = 'EMESSA'      -- ⬅ da rimuovere
);

-- DOPO (simmetrico al ramo ordine: esclude appena allocata, qualsiasi stato):
AND NOT EXISTS (
  SELECT 1 FROM vendite.commesse_attivita ca
   WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
);
```

### Perché il fix è sicuro e propaga correttamente

La vista è **predicato unico** condiviso da 3 consumer; il fix li allinea tutti senza tocchi BE:

1. **`fn_preventivo_ha_residuo_commessa`** (gate EVASO + capability) → torna `false` dopo il push → **EVASO scatta** + `can_push_commessa` si disabilita (come `genera_ordine` lato merce).
2. **`fn_list_preventivi_da_pushare`** (push-list) → dopo il push non ri-elenca le righe già pushate. L'idempotenza resta garantita (upsert su `segment_key` UNIQUE), ma ora è "alla sorgente" come per il ramo ordine — più pulito, niente ri-listing perpetuo.
3. **Pannello Smistamento** → progress verso EVASO coerente.

Il BE non cambia: `transiziona_a_evaso_se_smistato` è già chiamato nell'handler push (`swallow_db_error=False`, transazione unica CONFERMA) e nei percorsi standalone.

## 4. Punto secondario (pre-esistente, BoM) — da valutare, non bloccante per lo smoke

Il match è per **uguaglianza** `ca.segment_key = 'PREV:<uid>:R:<riga_id>'`. Per le righe **BoM** le attività hanno `segment_key` con suffisso `#CMP:<componente_id>` (`...:R:<id>#CMP:<cmp>`), quindi l'uguaglianza **non le intercetta**: una riga composita non viene mai esclusa (oggi mascherato dall'upsert idempotente; col fix §3 una riga BoM resterebbe comunque "residuo" perpetuo → preventivo con sole righe BoM non andrebbe EVASO).

Valutare un match per **prefisso** simmetrico al concetto di riga:

```sql
WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
   OR ca.segment_key LIKE 'PREV:' || p.uid::text || ':R:' || pr.id::text || '#CMP:%'
```

(da confermare col team DB: collazione/escape di `#`, eventuale `like_escape`). Gli smoke 1a/1b usano righe servizio **non** composite, quindi il §3 da solo li sblocca; il §4 è per non lasciare il debito BoM.

## 5. Verifica post-fix

Ri-eseguire (super admin):

```bash
cd backend
./scripts/tests/smoke-test-pratica-preventivi-conferma.sh '<pwd>'      # §8 atteso: EVASO + DOMINIO_PREVENTIVO_EVASO
./scripts/tests/smoke-test-preventivi-smistamento-ordine.sh '<pwd>'    # §13/§14 atteso: EVASO
```

Attesi verdi: preventivo `EVASO`, giornale con `DOMINIO_PREVENTIVO_EVASO`, `can_push_commessa=false` post-push.

## 6. Riferimenti

- DDL attuale vista: `db/changelog/migrations_v2/20_code/vendite/20260612-02-create-vw-preventivi-righe-smistabili-commessa-mctit.yaml`
- Gemella ordine (pattern corretto): `vw_preventivi_righe_smistabili_ordine` (esclude su `ordini_righe.preventivo_riga_id`)
- Gate BE: `apps/vendite/services/_smistamento_gate_helpers.py`
- Modello: `gestione-pratiche-come-procedere.md §1.1`; checklist: `a-test-push-commesse-fatturazione.md §1`
