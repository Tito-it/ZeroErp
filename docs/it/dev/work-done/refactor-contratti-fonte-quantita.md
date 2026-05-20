# Refactor contratti — esposizione `fonte_quantita_attesa` e gestione condizionale `quantita`

**Data apertura**: 2026-05-19
**Branch atteso**: `dev/backend-tid` (FE+BE) + `dev/db-tid` (brief DB scritto da Tid).
**Stato**: piano operativo. Implementazione non avviata.
**Trigger**: discussione 2026-05-19 — osservazione di Tid che la `quantita` sul drawer riga contratto non altera il `prezzo_unitario` e potrebbe essere fuorviante. Analisi ha rivelato un disallineamento UI/modello: il DB ammette 5 valori per `fonte_quantita_attesa` (`FISSA`, `MANUALE`, `TIMESHEET`, `LETTURE`, `DERIVATA_COMPONENTI`) ma la UI non li espone, e tutti i contratti creati hanno `fonte_quantita_attesa = NULL`.

---

## 1) Scopo

Allineare la UI del drawer riga contratto al modello DB di `vendite.contratti_righe`, esponendo il select `fonte_quantita_attesa` e mostrando/nascondendo `quantita` in base alla fonte. Eliminare l'ambiguita' UX attuale ("modifico la qta e il prezzo non cambia") sostituendola con una semantica esplicita: la `quantita` ha significato solo quando la fonte e' `FISSA`; per le altre 4 fonti il valore reale nasce downstream (letture, manuale, timesheet, derivata dai componenti).

## 2) Decisioni chiuse (sessione 2026-05-19)

1. **Combinazioni 🟡 rare ammesse**: la UI non filtra strict; tooltip "uso atipico" sulle combinazioni non-default. La realta' ha eccezioni legittime.
2. **Combinazioni ❌ vietate hard in DB**: nuova CHECK constraint dichiarativa rifiuta le 5 combinazioni semanticamente inconsistenti. Nessuna preoccupazione di compatibilita' dati esistenti (no produzione — vedi memoria [project_no_produzione_solo_sviluppo](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/project_no_produzione_solo_sviluppo.md)).
3. **Cambio `tipo_erogazione` in EDIT**: reset automatico di `fonte_quantita_attesa` al default SOLO se la fonte corrente diventa ❌ con il nuovo tipo. Meno invadente; preserva scelte legittime dell'utente.

## 3) Matrice naturale (riferimento)

Legenda: ✅ default · 🟢 valida secondaria · 🟡 rara/edge · ❌ vietata (CHECK DB).

| tipo_erogazione \ fonte | FISSA | MANUALE | TIMESHEET | LETTURE | DERIVATA_COMPONENTI |
| --- | --- | --- | --- | --- | --- |
| **CANONE** | ✅ | 🟡 | ❌ | ❌ | 🟢 |
| **UNA_TANTUM** | ✅ | 🟢 | ❌ | ❌ | 🟢 |
| **ORARIO** | 🟡 | 🟢 | ✅ (modulo futuro) | ❌ | 🟡 |
| **CONSUMO** | ❌ | 🟢 | ❌ | ✅ | 🟢 |

7 combinazioni ❌ totali:

- `CANONE+TIMESHEET`, `CANONE+LETTURE`
- `UNA_TANTUM+TIMESHEET`, `UNA_TANTUM+LETTURE`
- `ORARIO+LETTURE`
- `CONSUMO+FISSA`, `CONSUMO+TIMESHEET`

### Default proposti

```text
tipo_erogazione = CANONE     → fonte_quantita_attesa = FISSA
tipo_erogazione = UNA_TANTUM → fonte_quantita_attesa = FISSA
tipo_erogazione = ORARIO     → fonte_quantita_attesa = MANUALE  (TIMESHEET quando il modulo esistera')
tipo_erogazione = CONSUMO    → fonte_quantita_attesa = LETTURE
```

### Comportamento UI

| Fonte selezionata | `quantita` mostrata? | Note UX |
| --- | --- | --- |
| `FISSA` | Sì, obbligatoria | Label "Q.tà contrattualizzata" |
| `DERIVATA_COMPONENTI` (padre composito) | No | Tag "Derivata dai componenti" |
| `MANUALE` | No | Tag "Definita sul documento" |
| `TIMESHEET` | No | Tag "Da rendicontazione ore" (modulo futuro) |
| `LETTURE` | No | Tag "Da letture utility" |

---

## 4) Piano operativo step-by-step

### Step 1 — Brief DB

> **Riservato a Tid.** Il brief al team `dev/db-tid` verra' inserito qui prima di partire con BE/FE.

Contenuto atteso del brief (a titolo di promemoria, da raffinare a cura di Tid):

- Nuova CHECK constraint `chk_contrighe_coerenza_fonte_erogazione` su `vendite.contratti_righe` che vieti le 7 combinazioni ❌ della matrice.
- (Opzionale) Trigger normalize `trgfn_contratti_righe_default_fonte_qta` che applica la matrice default se `fonte_quantita_attesa IS NULL` al momento di INSERT/UPDATE su `tipo_erogazione`. Decisione: lasciare la difensiva al BE o duplicare in DB? — Tid decide.
- Conferma che la rinomina `quantita_fissa → quantita` ([migration `20260511-31`](../../../../db/changelog/migrations_v2/00_schema/vendite/20260511-31-alter-contratti-righe-rename-quantita-fissa-mctit.yaml)) e' compatibile con le helper `script.trgfn_componenti_*` per il caso `DERIVATA_COMPONENTI`.
- Aggiornare doc concettuale [contratti_righe.md](../../../../docs/it/dbzero/vendite/manual/contratti_righe.md) sezione "Campi chiave" + nuova sezione "Matrice tipo_erogazione × fonte_quantita_attesa".

### Step 2 — BE service (`contratti_service.py`)

#### Sotto-step 2.1 — Guard coerenza coppia

In [`_build_data_riga`](../../../../backend/apps/vendite/services/contratti_service.py) (sia create che update), aggiungere prima dell'INSERT/UPDATE:

```python
# Scopo: validare coerenza (tipo_erogazione, fonte_quantita_attesa)
# secondo la matrice del modello dominio (refactor 2026-05).
# Le combinazioni vietate sollevano E_VENDITE_VALIDATION parlante;
# il DB applica la stessa regola via chk_contrighe_coerenza_fonte_erogazione
# (defense-in-depth).
_FONTE_VIETATE_PER_TIPO_EROGAZIONE: frozenset[tuple[str, str]] = frozenset({
    ("CANONE", "TIMESHEET"),
    ("CANONE", "LETTURE"),
    ("UNA_TANTUM", "TIMESHEET"),
    ("UNA_TANTUM", "LETTURE"),
    ("ORARIO", "LETTURE"),
    ("CONSUMO", "FISSA"),
    ("CONSUMO", "TIMESHEET"),
})

def _validate_coerenza_fonte_erogazione(self, data: dict) -> None:
    tipo = data.get("tipo_erogazione")
    fonte = data.get("fonte_quantita_attesa")
    if tipo is None or fonte is None:
        return  # default applicato altrove, niente da validare
    ErrorManager.require(
        (tipo, fonte) not in _FONTE_VIETATE_PER_TIPO_EROGAZIONE,
        code=E_VENDITE_VALIDATION,
        message=_MESSAGE_RIGA,
        detail=(
            f"Combinazione vietata: tipo_erogazione='{tipo}' non e' compatibile "
            f"con fonte_quantita_attesa='{fonte}'. Vedi matrice nel refactor "
            f"docs/it/dev/work-in-progress/refactor-contratti-fonte-quantita.md."
        ),
        context={"tipo_erogazione": tipo, "fonte_quantita_attesa": fonte},
    )
```

#### Sotto-step 2.2 — Default applicato lato BE

In `_build_data_riga`, se `fonte_quantita_attesa` non e' nel payload, applicare il default dalla matrice in funzione di `tipo_erogazione`:

```python
_FONTE_DEFAULT_PER_TIPO_EROGAZIONE: dict[str, str] = {
    "CANONE": "FISSA",
    "UNA_TANTUM": "FISSA",
    "ORARIO": "MANUALE",   # cambierà a TIMESHEET con il modulo dedicato
    "CONSUMO": "LETTURE",
}
```

#### Sotto-step 2.3 — Quantita normalizzata per fonte

- `fonte == 'FISSA'`: `quantita` obbligatoria > 0. Guard esplicita.
- `fonte in ('MANUALE', 'TIMESHEET', 'LETTURE')`: forzare `quantita = NULL` in `_build_data_riga` (anche se il client la invia, viene scartata silenziosamente — la fonte e' il driver).
- `fonte == 'DERIVATA_COMPONENTI'`: comportamento speciale per i compositi. Il bug fixato 2026-05-19 (`quantita = qta_operativa` derivato silenziosamente) viene SOSTITUITO da: se `is_articolo_composito(articolo_id)` e fonte `DERIVATA_COMPONENTI`, `quantita = 1` (simbolico, 1 kit). I figli del BoM portano la quantita reale via `coeff_qta`.

#### Sotto-step 2.4 — Test BE

Aggiungere in [`test_contratti_service.py`](../../../../backend/apps/vendite/tests/services/test_contratti_service.py) classe `ContrattiServiceTests` (o nuova classe dedicata):

- `test_build_data_riga_applica_default_fonte_per_tipo_erogazione` (4 test, uno per ogni tipo)
- `test_build_data_riga_combinazione_vietata_solleva` (7 test, uno per ogni combinazione ❌)
- `test_build_data_riga_quantita_richiesta_se_fonte_fissa`
- `test_build_data_riga_quantita_forzata_null_se_fonte_non_fissa` (3 test: MANUALE, TIMESHEET, LETTURE)
- `test_build_data_riga_quantita_simbolica_uno_se_composito_derivata`
- `test_update_riga_cambio_tipo_erogazione_reset_solo_se_fonte_diventa_vietata` (decisione 3)

### Step 3 — FE drawer (`ContrattoRigheDrawer.vue`)

#### Sotto-step 3.1 — Nuovo Select `fonte_quantita_attesa`

Aggiungere accanto al Select `tipo_erogazione` esistente:

```vue
<div class="form-field">
  <label>{{ t('contratti.field_fonte_quantita_attesa') }} *</label>
  <Select v-model="form.fonte_quantita_attesa"
    :options="fonteQuantitaOptions"
    option-label="label" option-value="value"
    :placeholder="t('contratti.select_fonte_quantita')"
    class="w-full" />
  <small v-if="fonteCorrente?.severity === 'warn'" class="app-hint-warn">
    {{ t('contratti.fonte_quantita_uso_atipico') }}
  </small>
</div>
```

Options data-driven dalla matrice (filtrate per `tipo_erogazione` corrente, marcate con severity):

```javascript
// Combinazioni della matrice — ogni entry: { value, label, default?, severity }
// severity: 'success' = default, undefined = valida, 'warn' = uso atipico (🟡)
// Le vietate (❌) NON appaiono nell'array.
const FONTI_PER_TIPO_EROGAZIONE = {
  CANONE: [
    { value: 'FISSA', default: true },
    { value: 'MANUALE', severity: 'warn' },
    { value: 'DERIVATA_COMPONENTI' },
  ],
  UNA_TANTUM: [
    { value: 'FISSA', default: true },
    { value: 'MANUALE' },
    { value: 'DERIVATA_COMPONENTI' },
  ],
  ORARIO: [
    { value: 'FISSA', severity: 'warn' },
    { value: 'MANUALE', default: true },
    { value: 'TIMESHEET' },         // attivare quando modulo esistera'
    { value: 'DERIVATA_COMPONENTI', severity: 'warn' },
  ],
  CONSUMO: [
    { value: 'MANUALE' },
    { value: 'LETTURE', default: true },
    { value: 'DERIVATA_COMPONENTI' },
  ],
}
```

#### Sotto-step 3.2 — Reset condizionale al cambio `tipo_erogazione`

```javascript
watch(() => form.value.tipo_erogazione, (nuovoTipo, vecchioTipo) => {
  if (nuovoTipo === vecchioTipo) return
  const fontiValide = FONTI_PER_TIPO_EROGAZIONE[nuovoTipo]?.map(f => f.value) ?? []
  if (!fontiValide.includes(form.value.fonte_quantita_attesa)) {
    // La fonte corrente sarebbe vietata col nuovo tipo → reset al default.
    const def = FONTI_PER_TIPO_EROGAZIONE[nuovoTipo]?.find(f => f.default)
    form.value.fonte_quantita_attesa = def?.value ?? null
  }
  // Se la fonte e' compatibile col nuovo tipo, lasciare invariato (decisione 3).
})
```

#### Sotto-step 3.3 — Visibilita' condizionale `quantita`

Sostituire il blocco `<InputNumber v-model="form.qta_operativa" ...>` con render condizionale:

```vue
<div class="form-field" v-if="form.fonte_quantita_attesa === 'FISSA'">
  <label>{{ t('contratti.field_qta_operativa_fissa') }} *</label>
  <InputNumber v-model="form.qta_operativa" class="w-full"
    :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
</div>
<div class="form-field" v-else>
  <label>{{ t('contratti.field_qta_operativa') }}</label>
  <Tag :severity="tagFontiQuantita.severity"
    :value="t(`contratti.fonte_quantita_tag_${form.fonte_quantita_attesa?.toLowerCase()}`)"
    v-tooltip.top="t('contratti.fonte_quantita_tag_tooltip')" />
</div>
```

#### Sotto-step 3.4 — Defaults all'apertura form CREATE

Modificare `defaultForm()` per applicare il default fonte basato su `tipo_erogazione`:

```javascript
function defaultForm() {
  const tipo = 'CANONE'
  const def = FONTI_PER_TIPO_EROGAZIONE[tipo].find(f => f.default)
  return {
    // ... esistenti
    tipo_erogazione: tipo,
    fonte_quantita_attesa: def?.value ?? 'FISSA',
    // ...
  }
}
```

#### Sotto-step 3.5 — Rimozione fix tampone composito

Il fix BE 2026-05-19 in `_build_data_riga` che deriva silenziosamente `quantita = qta_operativa` per i compositi diventa obsoleto: la nuova logica `fonte = DERIVATA_COMPONENTI` → `quantita = 1` simbolico copre il caso in modo esplicito. Rimuovere il fix tampone e i test correlati (rinominare/aggiornare).

### Step 4 — i18n

Aggiungere in [it.json](../../../../frontend/src/locales/it.json) sotto `contratti`:

```json
"field_fonte_quantita_attesa": "Fonte quantità",
"field_qta_operativa_fissa": "Q.tà contrattualizzata",
"select_fonte_quantita": "Seleziona fonte quantità",
"fonte_quantita_uso_atipico": "Combinazione atipica per questo tipo di erogazione. Confermata?",
"fonte_quantita_value_fissa": "Quantità fissa",
"fonte_quantita_value_manuale": "Manuale (definita sul documento)",
"fonte_quantita_value_timesheet": "Da rendicontazione ore",
"fonte_quantita_value_letture": "Da letture utility",
"fonte_quantita_value_derivata_componenti": "Derivata dai componenti BoM",
"fonte_quantita_tag_manuale": "Definita sul documento",
"fonte_quantita_tag_timesheet": "Da rendicontazione ore",
"fonte_quantita_tag_letture": "Da letture utility",
"fonte_quantita_tag_derivata_componenti": "Derivata dai componenti",
"fonte_quantita_tag_tooltip": "La quantità sarà determinata downstream, non si imposta qui."
```

Stessa serie in [en.json](../../../../frontend/src/locales/en.json) tradotta.

### Step 5 — Doc da aggiornare

- [`contratti_righe.md`](../../../../docs/it/dbzero/vendite/manual/contratti_righe.md): nuova sezione "Matrice tipo_erogazione × fonte_quantita_attesa" con la tabella del §3.
- [`gestione-commesse-v2.md`](gestione-commesse-v2.md) §29: gia' aggiornato 2026-05-19 col promemoria `HandlerContratti`. Link incrociato da qui (futuro lavoro motore commesse).
- [`sviluppo-fatturazione.md`](sviluppo-fatturazione.md): gia' creato 2026-05-19 col promemoria UI preview fatturazione. Link incrociato da qui.

### Step 6 — Smoke + checklist browser

Aggiornare [`test-contratto-composito.md`](test-contratto-composito.md):

- Caso 1 sub-test esistente sul composito DERIVATA_COMPONENTI: aggiornare label colonna q.ta' attesa = "—" o tag, NON valore numerico.
- Aggiungere casi 6-7-8 per le combinazioni `MANUALE/LETTURE/TIMESHEET`: form mostra solo tag, salva, verifica DB `quantita IS NULL`.
- Caso 9: tenta combinazione ❌ via API curl, atteso 422 `E_VENDITE_VALIDATION` parlante.

---

## 5) Fuori scope (rinvii espliciti)

1. **Modulo timesheet**: nessuna implementazione in questo refactor. `TIMESHEET` resta come opzione valida nell'enum DB e nella matrice; il default per `ORARIO` resta `MANUALE` finche' il modulo non esiste. Aggiornare il default quando il modulo arrivera'.
2. **`HandlerContratti` push contratto → commessa**: scheletro vuoto oggi, vedi [gestione-commesse-v2.md §29](gestione-commesse-v2.md). Lavoro coordinato con questo refactor ma in altra sessione.
3. **UI preview fatturazione contratto**: non esiste, vedi [sviluppo-fatturazione.md PROMO-1](sviluppo-fatturazione.md). La sua assenza pesa sulla decisione UX di questo refactor (il drawer riga resta l'unico punto in cui l'utente vede `quantita`), ma non blocca.
4. **Backfill dati esistenti**: in dev tutti i contratti hanno `fonte_quantita_attesa = NULL`. Decisione: lasciare NULL (compatibile con il modello) e applicare il default solo a INSERT/UPDATE futuri, oppure backfillare via UPDATE batch al deploy della migration. Da decidere col brief DB.

---

## 6) Ordine raccomandato di esecuzione

1. Tid scrive il brief DB (Step 1) — `dev/db-tid`.
2. Team DB applica CHECK constraint + (opz.) trigger default + aggiornamento doc.
3. BE service: implementazione 2.1+2.2+2.3 + test 2.4 — `dev/backend-tid`.
4. FE drawer: implementazione 3.1+3.2+3.3+3.4 + rimozione fix tampone 3.5.
5. i18n it+en (Step 4).
6. Doc + smoke checklist (Step 5+6).
7. Smoke E2E in browser sui 4 tipi erogazione + edge case combinazioni 🟡 e ❌.
8. Commit per fase coordinato con autorizzazione esplicita.

---

## 7) Riferimenti

- Analisi originale (chat 2026-05-19): osservazione di Tid + ricostruzione modello + scelta opzione B.
- Sessione 2026-05-19 (refactor `ComponentiPanel` + Stream 3 composito): [handoff_20260519_note_categoria_compositi](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/handoff_20260519_note_categoria_compositi.md).
- Memorie applicabili:
  - [feedback_simmetria_modello_no_meta_scope](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/feedback_simmetria_modello_no_meta_scope.md) — abbracciare la simmetria piena subito, non rinviare a fase 2.
  - [feedback_no_quick_fix_soluzione_assoluta](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/feedback_no_quick_fix_soluzione_assoluta.md) — soluzione sul merito.
  - [feedback_db_actions_passaggio_team](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/feedback_db_actions_passaggio_team.md) — DB sempre via brief al team.
  - [project_no_produzione_solo_sviluppo](../../../../../../.claude/projects/-home-tid-apps-ZeroErp/memory/project_no_produzione_solo_sviluppo.md) — niente compat shim, breaking change ammessi.
- Codice toccato:
  - BE: [`contratti_service.py`](../../../../backend/apps/vendite/services/contratti_service.py), [`test_contratti_service.py`](../../../../backend/apps/vendite/tests/services/test_contratti_service.py).
  - FE: [`ContrattoRigheDrawer.vue`](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue), [`it.json`](../../../../frontend/src/locales/it.json), [`en.json`](../../../../frontend/src/locales/en.json).
  - DB: brief in arrivo (vedi Step 1).
