# Brief DB — listini_versioni: la BOZZA non è una versione operativa + preview contratto con bundle

> Destinatario: team DB (`dev/db-tid`)
> Mittente: backend agent (`dev/backend-tid`)
> Data: 2026-05-16
> Stato: da applicare, blocca smoke contratti

---

## 1. TL;DR

Due bug emersi nello smoke contratti 2026-05-16, entrambi DB-first. Da
applicare insieme in un'unica sessione:

**Bug A** — i lookup operativi pescano in modo non-deterministico le righe
di una versione listino in stato `BOZZA` quando sovrapposta in validità
alla `ATTIVA`. Fix: i lookup filtrano `attivo=TRUE AND stato IN ('ATTIVA','CHIUSA')
AND validita @> data_riferimento`.

**Bug B** — il preview righe contratto non mostra i bundle compositi del
listino (vivono in `listini_righe_componenti`, non in `listini_righe`).
Fix: nuova funzione DB `fn_contratto_righe_preview` che ritorna riga
padre con array `componenti` JSONB annidato, per UI espandibile uniforme
ai preventivi.

Scelte architetturali confermate da Tid: **Strategia B** (whitelist
`stato IN ('ATTIVA','CHIUSA')`, non no-overlap totale), `attivo` boolean
mantiene semantica soft-delete invariata.

Razionale completo, sintomo concreto, downstream BE/FE e note in §7..§14.

---

## 2. Modifiche DB richieste

### 2.1 `vendite.fn_resolve_prezzo_listino_v2` (Bug A)

File corrente: `20260515-15-update-fn-resolve-prezzo-listino-v2-mctit.yaml`.
Nuovo file `runOnChange: true` (es. `20260516-XX-update-fn-resolve-prezzo-listino-v2-bozza-non-operativa-mctit.yaml`).

Due lookup `listini_versioni` interni alla funzione, identico fix per entrambi.

**Stadio CONTRATTO_LISTINO** (corpo funzione, lookup versione operativa quando
contratto non ha versione fissata):

```sql
-- AS-IS
SELECT lv.id
  INTO v_listino_versione_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = v_contr_listino_id
   AND lv.validita  @> p_data_riferimento
   AND lv.attivo    = TRUE
 LIMIT 1;

-- TO-BE
SELECT lv.id
  INTO v_listino_versione_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = v_contr_listino_id
   AND lv.attivo     = TRUE
   AND lv.stato      IN ('ATTIVA','CHIUSA')
   AND lv.validita  @> p_data_riferimento
 LIMIT 1;
```

**Stadio CATEGORIA** (lookup versione operativa del listino della matrice
categoria_cliente_listini): identico pattern, stesso fix.

Nota: `LIMIT 1` resta come fail-safe; con la whitelist sullo stato
l'invariante no-overlap diventa effettivo e il `LIMIT 1` non maschera più
non-determinismo.

### 2.2 `vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino` (Bug A)

File corrente: `20260515-12-create-trg-contratti-righe-guard-aggiunta-mctit.yaml`.
Nuovo file `runOnChange: true` (es. `20260516-YY-update-trgfn-contratti-righe-guard-aggiunta-bozza-mctit.yaml`).

La guard verifica che un articolo `AGGIUNTA` non sia già nel listino del
contratto. Il lookup interno sul listino deve applicare la stessa regola §2.1:
una BOZZA non deve far scattare la guard "articolo presente in listino"
perché la BOZZA non è operativa.

Allineare la SELECT interna su `listini_versioni` alla forma:

```sql
WHERE lv.listino_id = c.listino_id
  AND lv.attivo     = TRUE
  AND lv.stato      IN ('ATTIVA','CHIUSA')
  AND lv.validita  @> CURRENT_DATE
```

Aggiornare anche il commento header che oggi cita
"`listini_versioni WHERE validita @> CURRENT_DATE AND attivo`".

### 2.3 `vendite.fn_contratto_righe_preview` (Bug B) — nuova funzione

Nuovo file `runOnChange: true` (es. `20260516-ZZ-create-fn-contratto-righe-preview-mctit.yaml`).

Sostituisce integralmente lo SQL inline oggi in
`apps/vendite/db/contratti_repository.py::list_righe_preview`. Il BE
diventa thin wrapper.

**Signature**:

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
RETURNS TABLE (
    -- Identificazione articolo (padre)
    articolo_id            uuid,
    articolo_codice        varchar,
    articolo_descrizione   varchar,
    is_composito           boolean,
    uom_id                 bigint,
    uom_codice             varchar,
    uom_descrizione        varchar,

    -- Pricing padre
    prezzo_listino         numeric,
    tipo_variazione        varchar,
    valore_variazione      numeric,
    override_riga_id       bigint,
    override_prezzo        numeric,
    tipo_eccezione         vendite.tipo_eccezione_contratto,
    origine                varchar,   -- 'DA_LISTINO'/'OVERRIDE'/'ESCLUSIONE'/'AGGIUNTA'
    prezzo_finale          numeric,

    -- Bundle: array figli per padre composito; NULL per non-bundle
    componenti             jsonb
)
LANGUAGE plpgsql STABLE
```

**Logica interna**:

* **Parte 1 — Righe dal listino** del contratto (versione fissata
  `c.listino_versione_id` se ATTIVO; corrente con regola §2.1 se DRAFT):
  * 1a) Righe standalone da `listini_righe` (filtro
    `articoli.is_composito = FALSE`) — equivalente alla Parte 1 oggi
    inline nel repository
  * 1b) Righe bundle da `listini_righe_componenti` raggruppate per
    `articolo_padre_id`: padre = riga "virtuale" del bundle parent
    (`is_composito = TRUE`, `prezzo_listino = NULL`, prezzo aggregato
    derivato lato FE); `componenti` = `jsonb_agg` dei figli con
    `articolo_componente_id, codice, descrizione, uom_id, uom_codice,
    coeff_qta_snapshot, prezzo_figlio, obbligatorio, esposto_in_fattura`
    (shape simile a `fn_preventivo_riga_componenti_preview`).
  * LEFT JOIN su `contratti_righe` per overlay OVERRIDE/ESCLUSIONE
    (identico al pattern attuale).

* **Parte 2 — Eccezioni AGGIUNTA** da `contratti_righe` (articoli
  fuori-listino):
  * 2a) Standalone (`articoli.is_composito = FALSE`): `componenti = NULL`
  * 2b) Bundle persistito: figli da `contratti_righe_componenti`
    aggregati con `jsonb_agg`.

**Razionale pricing padre bundle**: lasciare `prezzo_finale = NULL` per i
padri bundle e demandare al FE l'aggregazione `SUM(prezzo_figlio × coeff_qta)`.
Mantiene coerenza con il resolver bundle-prioritario (`fn_resolve_prezzo_listino_v2`
con `p_articolo_padre_contesto`) che non espone mai un prezzo "padre"
fisico. In alternativa: aggregare in funzione e popolare anche
`prezzo_finale` del padre — da decidere se utile per export/PDF.

**Funzioni esistenti da non confondere** (restano invariate):

* `vendite.fn_contratto_riga_componenti_preview()` — preview di un
  **singolo** padre bundle per form quando l'operatore aggiunge una
  AGGIUNTA. Non sostituisce §2.3.
* `vendite.fn_contratto_riga_componenti_init()` — persiste i figli in
  `contratti_righe_componenti` quando viene creata una riga AGGIUNTA
  bundle.

### 2.4 Audit altri lookup `listini_versioni` (Bug A — trasversale)

Audit suggerito sul team DB: grep su
`db/changelog/migrations_v2/20_code/` per ogni SELECT su
`vendite.listini_versioni` con filtro `attivo=TRUE` + `validita`.

Esclusi dall'audit (semantica diversa, NON toccare):

* `dbops.trgfn_child_requires_active_parent`
* `dbops.trgfn_prevent_deactivate_if_children`

Controllano solo `attivo` come soft-delete per integrità referenziale,
non come "operativa". Il loro filtro `attivo=TRUE` è corretto così.

Report atteso al backend agent: lista dei lookup operativi che richiedono
l'allineamento §2.1.

### 2.5 Decisione modello — ESCLUSIONE su singolo figlio bundle

Aperta nel test §3 caso 7: contratto che esclude un singolo componente
figlio di un bundle. Comportamento ammesso o vietato?

Razionale per **vietarlo** (proposta): l'esclusione opera sul padre del
bundle (il padre composito è il "prodotto venduto"). Un figlio escluso
sotto un padre fatturabile crea una incoerenza di modello (il padre
sarebbe parzialmente fatturabile). Più pulito: l'ESCLUSIONE è ammessa
solo per `articolo_id = padre_bundle`; per i figli, l'unica eccezione
ammessa è OVERRIDE sul prezzo del singolo componente.

Eventuale aggiornamento di
`trgfn_contratti_righe_guard_aggiunta_fuori_listino` o nuovo guard
dedicato. Decisione da prendere dal team DB.

---

## 3. Suite pgTAP

File suggerito: `db/pgtap/vendite/test_listini_versioni_bozza_e_preview.sql`

Indice test:

1. `fn_resolve_prezzo_listino_v2` con BOZZA in overlap su ATTIVA →
   resolver pesca SEMPRE la ATTIVA (deterministico)
2. `fn_resolve_prezzo_listino_v2` con solo BOZZA che copre la data
   (nessuna ATTIVA) → raise `E_LISTINO_VERSIONE_NON_ATTIVA`
3. `fn_resolve_prezzo_listino_v2` con CHIUSA in range + BOZZA in overlap
   → resolver pesca la CHIUSA (fatturazione retroattiva)
4. `trgfn_contratti_righe_guard_aggiunta_fuori_listino`: BOZZA che
   contiene l'articolo → AGGIUNTA su contratto BOZZA NON deve essere
   bloccata dal guard come "articolo presente in listino"
5. `fn_contratto_righe_preview`: contratto BOZZA con listino che contiene
   2 bundle e 1 standalone → ritorna 3 righe (2 bundle con `componenti`
   non-vuoto + 1 standalone con `componenti IS NULL`)
6. `fn_contratto_righe_preview` con eccezione OVERRIDE sul padre bundle:
   `prezzo_finale` = prezzo override, `componenti` resta dal listino
   (l'override sul padre non sovrascrive i figli)
7. ESCLUSIONE su singolo componente figlio bundle: verificare il
   comportamento atteso definito in §2.5

---

## 4. Documentazione DB da aggiornare

| Documento | Modifica |
|---|---|
| [`linee-guida-sql.md` §7c](../../linee-guida-sql.md) | Estendere il principio fail-safe: i lookup operativi applicano `attivo=TRUE + stato IN (lista_operativi) + validita @> data`. La whitelist degli stati operativi è dichiarata nella manual della tabella |
| [`dbzero/vendite/manual/listini_versioni.md`](../../dbzero/vendite/manual/listini_versioni.md) | Rimuovere "il resolver prezzi non filtra per stato — le date comandano" (riga ~59-63). Sostituire con regola §6: stati operativi = `('ATTIVA','CHIUSA')`, BOZZA = preparazione, esclusa dai lookup applicabilità |
| `dbzero/vendite/funzioni/fn_contratto_righe_preview.md` | Nuovo manual per la funzione §2.3 (auto-generata, ma manual concettuale separato) |
| [`modello-contratti.md`](../../backend/vendite/manual/modello-contratti.md) | Glossario §9: aggiornare "versione attiva del listino" → "versione operativa" (= ATTIVA o CHIUSA in range) |
| [`api_contratti.md`](../../backend/vendite/manual/api_contratti.md) | Esempio response del preview righe con bundle annidato (shape JSONB) |
| [`modello-componenti-bom.md`](../../backend/vendite/manual/modello-componenti-bom.md) | Riga "preview contratti = pattern uniforme con preventivi via `fn_contratto_righe_preview`" |

---

## 5. Checklist team DB

**Bug A — BOZZA non operativa**:

* [ ] Nuovo file `20260516-XX-update-fn-resolve-prezzo-listino-v2-bozza-non-operativa-mctit.yaml` (`runOnChange: true`) — §2.1
* [ ] Nuovo file `20260516-YY-update-trgfn-contratti-righe-guard-aggiunta-bozza-mctit.yaml` (`runOnChange: true`) — §2.2
* [ ] Audit §2.4: report al backend agent dei lookup operativi che richiedono allineamento

**Bug B — Preview contratto con bundle padre+figli**:

* [ ] Nuovo file `20260516-ZZ-create-fn-contratto-righe-preview-mctit.yaml` (`runOnChange: true`) — funzione §2.3
* [ ] Decisione modello §2.5 (ESCLUSIONE su singolo figlio) → eventuale aggiornamento guard

**Trasversale**:

* [ ] Suite pgTAP §3
* [ ] Aggiornamento doc §4
* [ ] Conferma scritta al backend agent → applicazione fix Python §11 + FE §12

---

## 6. Step 2 — addendum post-handoff (2026-05-16)

**Stato Step 1**: chiuso lato DB. Migrations `20260516-01..04` + suite pgTAP
`test-bozza-non-operativa-e-preview-contratto-v1.sql` applicate su
`dev/db-tid` (non ancora pushate). Bug A esteso a 3 funzioni:
`fn_resolve_prezzo_listino_v2`,
`trgfn_contratti_righe_guard_aggiunta_fuori_listino` e
**`trgfn_contratti_freeze_listino_versione`** (quest'ultimo non era nel
brief iniziale, congelava una BOZZA come snapshot al passaggio
DRAFT→ATTIVO contratto). Bug B chiuso con `fn_contratto_righe_preview`
che aggrega anche `prezzo_finale` per bundle (decisione DB: prezzo
aggregato lato DB invece che lato FE, per coerenza export/PDF).

**Step 2 — cosa serve aggiungere**:

### 6.1 Guard ESCLUSIONE su figlio bundle (chiusura §2.5)

Decisione confermata da Tid 2026-05-16: **VIETATO** l'ESCLUSIONE su un
singolo componente figlio di un bundle. Razionale: il bundle è un
prodotto venduto come unità; varianti diverse vivono come bundle
distinti in anagrafica articoli, non come "bundle parziali" per
cliente.

**Nuovo file `runOnChange: true`** (es.
`20260516-NN-create-trgfn-contratti-righe-guard-esclusione-figlio-bundle-mctit.yaml`).

Trigger BEFORE INSERT OR UPDATE OF `tipo_eccezione, articolo_id` su
`vendite.contratti_righe`, fase `_a10_`:

```sql
-- Pseudo-logica:
IF NEW.tipo_eccezione = 'ESCLUSIONE' THEN
    -- Cerca se NEW.articolo_id è un figlio bundle attivo in qualche
    -- listino (la verifica è cross-listino: un articolo che è figlio
    -- in un qualunque bundle non può essere ESCLUSIONE in un contratto).
    IF EXISTS (
        SELECT 1
          FROM vendite.listini_righe_componenti lrc
         WHERE lrc.articolo_componente_id = NEW.articolo_id
           AND lrc.attivo = TRUE
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME::text,
            'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA',
            jsonb_build_object(
                'contratto_id', NEW.contratto_id,
                'articolo_id',  NEW.articolo_id
            ),
            NEW.tx_id,
            NEW.articolo_id::text
        );
    END IF;
END IF;
```

**Codice errore nuovo** da registrare in `config.messaggi_errore`:

| Codice                                          | HTTP | Messaggio IT                                                                                                          | Note                |
| ----------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`  | 422  | "L'articolo è un componente di un bundle: l'esclusione si applica al bundle padre, non al singolo componente."        | Aggiungere anche EN |

Allineare la voce in
[`apps/core/services/error_policies.py`](../../../../backend/apps/core/services/error_policies.py)
nel mapping codice → HTTP → UI action (lato BE viene fatto post-DB).

**Edge case da decidere**: cosa fare se un articolo è figlio in un
listino A ma standalone in un listino B (caso ammesso dal modello)?
Proposta: vietato comunque (un articolo "è" un componente nel sistema,
indipendentemente da quale listino lo riferisce). In alternativa:
controllo limitato al listino del contratto (`lrc.listino_versione_id`
nella versione operativa del listino di `NEW.contratto_id`). Da
chiarire col team DB prima dell'implementazione.

### 6.2 Test pgTAP aggiuntivo

Aggiungere alla suite `test-bozza-non-operativa-e-preview-contratto-v1.sql`
(o file separato):

1. Inserire `contratti_righe` con `tipo_eccezione='ESCLUSIONE'` su
   articolo che è figlio in `listini_righe_componenti` → guard raise
   `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`
2. Inserire `contratti_righe` con `tipo_eccezione='ESCLUSIONE'` su
   articolo padre del bundle (standalone) → ammesso
3. UPDATE `contratti_righe` per cambiare `tipo_eccezione` da OVERRIDE
   a ESCLUSIONE su un figlio bundle → guard raise

### 6.3 Aggiornamento doc

* [`modello-contratti.md`](../../backend/vendite/manual/modello-contratti.md)
  glossario §9 o sezione eccezioni: aggiungere "ESCLUSIONE: ammessa solo
  su articoli standalone o padre bundle; vietata sui figli bundle."
* [`api_contratti.md`](../../backend/vendite/manual/api_contratti.md):
  documentare il codice errore nuovo nella sezione errori.

### 6.4 Checklist team DB (Step 2)

* [ ] Decisione edge case 6.1 (cross-listino vs limitato al listino contratto)
* [ ] Nuovo file `20260516-NN-create-trgfn-contratti-righe-guard-esclusione-figlio-bundle-mctit.yaml`
* [ ] Seed codice errore `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` (IT + EN) in `config.messaggi_errore`
* [ ] Test pgTAP 6.2 (3 casi)
* [ ] Aggiornamento doc 6.3
* [ ] Conferma scritta al backend agent → aggiornamento `error_policies.py` + i18n FE

**Punti 3 e 4 del recap BE (alert scadenze listino + autoclose precedente)
non hanno controparte DB**: vivono in `apps/vendite/db/listini_repository.py`
come SQL inline. Sono già nell'audit Python paritetico §11.2 estesa e
verranno chiusi nel commit BE downstream — nessuna azione richiesta al
team DB su questi 2 punti.

---

# Razionale e contesto

---

## 7. Sintomo concreto

Smoke contratti 2026-05-16, contratto `CNT0000027` (BOZZA) con listino
`sadasdfa`:

| versione | stato | attivo | valido_dal | valido_al | validita |
|---|---|---|---|---|---|
| v1 | ATTIVA | TRUE | 2026-05-01 | NULL | `[2026-05-01,infinity)` |
| v1-clone | BOZZA | TRUE | 2026-05-16 | NULL | `[2026-05-16,infinity)` |

Entrambe le versioni hanno le stesse 3 righe non-composite attive in
`listini_righe`. Il listino contiene anche 1 padre composito (bundle)
che vive solo in `listini_righe_componenti`.

Preview righe contratto su `CNT0000027`:

* ritorna **6 righe** (3 non-composite × 2 versioni: fanout → Bug A);
* la riga del bundle composito **non appare** (la query legge solo
  `listini_righe`: Bug B).

---

## 8. Causa root — Bug A

Il filtro applicabilità usato in tutti i punti operativi è
`lv.attivo = TRUE AND lv.validita @> data_riferimento`. Il flag `attivo`
boolean ha però semantica di **soft-delete** (default TRUE per le righe
inserite, TRUE anche per le BOZZA in lavorazione, gestito dai trigger
`trgfn_prevent_deactivate_if_children` / `trgfn_child_requires_active_parent`);
**non** discrimina lo stato del ciclo vita.

L'index parziale `ex_listini_versioni_no_overlap`
(fix [`20260409-01`](../../../../db/changelog/migrations_v2/00_schema/vendite/20260409-01-fix-listini-versioni-overlap-stato-mctit.yaml))
vieta overlap **solo** quando `attivo IS TRUE AND stato = 'ATTIVA'`.
Quindi:

* Due `ATTIVA` con validità sovrapposte: impedite → invariante OK
* `BOZZA` + `ATTIVA` con validità sovrapposte: ammesse per design
  (workflow clone+publish documentato in [`listini_versioni.md`](../../dbzero/vendite/manual/listini_versioni.md))

Il workflow clone+publish prevede che la BOZZA abbia `valido_dal`
**futura** (es. oggi+30) e l'autoclose della ATTIVA precedente avvenga
nella stessa transazione di attivazione. **L'invariante "BOZZA non copre
`CURRENT_DATE`" non è enforced**: l'operatore può clonare una BOZZA con
`valido_dal = oggi` (è il caso §6).

Conseguenze sui lookup operativi:

* `fn_resolve_prezzo_listino_v2` → `LIMIT 1` senza ORDER BY → resolve
  non-deterministico (può ritornare il prezzo della BOZZA).
* `contratti_repository.list_righe_preview` → nessun LIMIT → fanout
  cartesiano 3→6.

---

## 9. Causa root — Bug B

`vendite.listini_righe` contiene solo articoli standalone
(`is_composito = FALSE`). I padri bundle non sono persistiti come riga
listino: vivono come `articolo_padre_id` in
`vendite.listini_righe_componenti`, dove ogni riga rappresenta un
componente figlio con il suo prezzo unitario.

Il preview `list_righe_preview` oggi legge solo `listini_righe` → il
bundle è invisibile.

Fix in §2.3: la nuova funzione `fn_contratto_righe_preview` unifica i due
modelli (standalone + bundle) e ritorna un padre virtuale per ogni
bundle, con i figli serializzati in `componenti` JSONB.

---

## 10. Tensione con la dottrina §7c e decisione architetturale

[`docs/it/linee-guida-sql.md` §7c](../../linee-guida-sql.md) sancisce:

> "Applicabilità operativa = date. Resolver, lookup di business, filtri
> di efficacia usano **solo** `validita @> data_riferimento`. **Non**
> filtrare per `stato` nella logica operativa."

La dottrina presuppone implicitamente l'invariante "no-overlap su date
operative tra righe applicabili". Per le ATTIVA l'index lo garantisce.
Per le BOZZA no: il workflow clone+publish le ammette in overlap
deliberatamente, e §7c non distingue il caso.

**La dottrina §7c oggi è incompleta**. Due strategie possibili:

* **Strategia A** — irrigidire il modello (no-overlap totale). Vieta
  qualsiasi sovrapposizione, anche per BOZZA. Coerente con "date
  comandano", **rompe** il workflow clone+publish documentato (BOZZA con
  `valido_dal` futuro non potrebbe convivere con ATTIVA aperta a
  `valido_al=NULL`).
* **Strategia B** — esplicitare che la BOZZA è "preparazione", non
  versione operativa. La BOZZA ha `validita` come **intent** (calendario
  futuro post-publish), ma i lookup operativi la escludono per stato.

**Strategia B adottata** (conferma di Tid): più coerente con il modello
reale (la BOZZA è uno scratchpad pre-pubblicazione, non una versione
operativa). La dottrina §7c viene estesa, non riscritta: "le date
comandano, lo stato discrimina **operativa** (ATTIVA/CHIUSA) da
**preparazione** (BOZZA). I lookup operativi filtrano
`stato IN ('ATTIVA','CHIUSA') AND validita @> data_riferimento`."

Whitelist esplicita `('ATTIVA','CHIUSA')` invece di `!= 'BOZZA'`: più
resiliente all'aggiunta futura di stati intermedi (es. `SOSPESA` non
sarebbe automaticamente considerata operativa).

`attivo` boolean: semantica **invariata** (soft-delete, parent
integrity). I trigger `trgfn_*_active_parent` continuano a controllare
solo `attivo`. Nessun cambio nei trigger di integrità.

---

## 11. Downstream backend Python (post fix DB)

### 11.1 `contratti_repository.list_righe_preview` — diventa thin wrapper

File: `backend/apps/vendite/db/contratti_repository.py` righe 573-674.

```python
def list_righe_preview(self, contratto_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM vendite.fn_contratto_righe_preview(%s)",
            [contratto_id],
        )
        return rows_to_list(cursor)
```

Lo SQL inline (Parte 1 + Parte 2 attuali) viene rimosso. Il `componenti`
JSONB viene deserializzato da psycopg3 come dict/list Python nativi.

### 11.2 Audit Python paritetico

Grep su `backend/apps/vendite/db/` e `backend/apps/catalogo/db/` per
query che fanno lookup operativo su `listini_versioni` con `attivo=TRUE`.
Allineare al filtro §2.1 se la modifica DB non li copre già (cioè se
sono SQL inline e non chiamano `fn_resolve_prezzo_listino_v2`).

---

## 12. Downstream frontend Vue (post fix DB)

* `frontend/src/vendite/components/ContrattoRigheDrawer.vue`: introdurre
  DataTable expander analogo a
  `frontend/src/vendite/preventivi/components/PreventiviRigheTable.vue`,
  condizione chevron `data.is_composito === true && data.componenti?.length > 0`
* Riuso building block esistente
  `frontend/src/vendite/_shared/componenti/ComponentiPanel.vue`
  (prop `readonly=true` per il preview contratti — le righe del listino
  non sono editabili, solo le eccezioni AGGIUNTA persistite lo sono)
* i18n del drawer righe contratto allineata alle chiavi preventivi
  dove possibile (`vendite.componenti.bundle.*`)

Pattern target identico ai preventivi: riga padre + figli annidati
espansibili, padding sinistra sub-tabella, chevron down/right.

---

## 13. Note operative

* **Niente migration di dato**: la modifica è solo `runOnChange: true`
  su funzioni esistenti + 2 nuovi file (trigger guard §2.2 + funzione
  preview §2.3). Nessuna ALTER TABLE, nessun fix di dati storici (in
  dev, breaking change ammesso — vedi
  `feedback project_no_produzione_solo_sviluppo`).
* **Coerenza con `chiusura_scadenze_daily`**: il job notturno chiude
  `ATTIVA → CHIUSA` per `valido_al < CURRENT_DATE`. Una versione appena
  chiusa resta operativamente applicabile per le fatture con data dentro
  il suo range (CHIUSA in §9).
* **Workflow clone+publish**: non cambia. La BOZZA può continuare a
  essere creata con `valido_dal` qualsiasi (anche `CURRENT_DATE`);
  semplicemente non viene mai vista dai lookup operativi finché resta
  BOZZA. Al publish l'autoclose della precedente + cambio stato
  avvengono nella stessa transazione.
* **Pattern uniforme cross-dominio**: il preview contratti adotta lo
  stesso shape del preview preventivi (padre + `componenti` JSONB
  annidato). UI uniforme tra i 2 domini, riuso del building block FE
  `ComponentiPanel.vue`.

---

## 14. Riferimenti

* [Linee guida SQL §7c](../../linee-guida-sql.md) — ciclo stato +
  finestra di validità
* [Manual `listini_versioni`](../../dbzero/vendite/manual/listini_versioni.md)
  — workflow clone+publish, regole stato
* [Manual `modello-contratti`](../../backend/vendite/manual/modello-contratti.md)
  — modello unificato post-refactor 2026-05-15
* [Manual `modello-componenti-bom`](../../backend/vendite/manual/modello-componenti-bom.md)
  — pattern bundle padre+figli
* [Brief DB refactor contratti completo](brief-db-refactor-contratti-completo.md)
  — brief precedente (Bug A vive su questo modello)
* [`api_contratti.md`](../../backend/vendite/manual/api_contratti.md)
  — contratto HTTP post-refactor
