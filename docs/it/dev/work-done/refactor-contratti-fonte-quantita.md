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
2. **Combinazioni ❌ vietate hard in DB**: nuova CHECK constraint dichiarativa rifiuta le 5 combinazioni semanticamente inconsistenti. Nessuna preoccupazione di compatibilita' dati esistenti (no produzione — vedi memoria interna `project_no_produzione_solo_sviluppo.md`).
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

### Step 1 — Brief DB (APPLICATO)

**Status**: applicato dal team `dev/db-tid` 2026-05-19. Migrations `20260519-05` (`00_schema/vendite/`) + `20260519-06` (`20_code/vendite/`).

#### 1.a — `fonte_quantita_attesa` diventa NOT NULL

Campo non piu' nullable. Valori ammessi: `FISSA`, `MANUALE`, `TIMESHEET`, `LETTURE`, `DERIVATA_COMPONENTI`. Backfill applicato sulle righe esistenti (in dev tutti i contratti avevano NULL, default applicati come da matrice).

#### 1.b — Nuovo CHECK `chk_contrighe_coerenza_fonte_erogazione`

Vieta le 7 combinazioni ❌:

| tipo_erogazione | fonti vietate |
| --- | --- |
| CANONE | TIMESHEET, LETTURE |
| UNA_TANTUM | TIMESHEET, LETTURE |
| ORARIO | LETTURE |
| CONSUMO | FISSA, TIMESHEET |

#### 1.c — Nuovo trigger `trg_contratti_righe_a10_default_fonte_qta_ins_upd`

- INSERT senza `fonte_quantita_attesa` → imposta automaticamente il default dalla matrice.
- UPDATE che cambia `tipo_erogazione` → resetta `fonte_quantita_attesa` SOLO se la combo nuova diventa vietata (= decisione 3 della sessione 2026-05-19, identica a quella prevista per la UI).

Default applicati:

| tipo_erogazione | fonte default |
| --- | --- |
| CANONE / UNA_TANTUM | FISSA |
| ORARIO | MANUALE |
| CONSUMO | LETTURE |

#### 1.d — `quantita` per `DERIVATA_COMPONENTI` gestita da `z90_propaga_qta_componenti`

**Importante**: per le righe padre con `fonte = DERIVATA_COMPONENTI`, la colonna `quantita` viene scritta automaticamente dal trigger `z90_propaga_qta_componenti` (derivata dai componenti). Non e' NULL ma non e' editabile dall'utente. Conseguenza: la logica BE "quantita = 1 simbolica" prevista nel sotto-step 2.3 originale **non serve** (il DB fa tutto).

#### 1.e — Punti pregressi gia' chiusi (riepilogo dal team DB)

- ~~Rinomina `quantita_fissa → quantita`~~: chiusa dalla migration `20260511-32` (`trgfn_qta_from_operativa` allineato).
- Punto del brief originale sulle migration `20260519-01..04` (categoria_cliente + note_stili): **non rientrano in questo refactor**. Erano gia' integrate nella sessione 2026-05-19 (Stream 1 Note partizionate + Stream 2 categoria_cliente Phase A/B), nel working tree non ancora committato.

#### 1.f — Doc DB

Da aggiornare a cura del team: [contratti_righe.md](../../../../docs/it/dbzero/vendite/manual/contratti_righe.md) — sezione "Campi chiave" + nuova "Matrice tipo_erogazione × fonte_quantita_attesa" + nota su `z90_propaga_qta_componenti`.

#### 1.g — Estensione `fn_contratto_righe_preview` (APPLICATA)

**Status**: applicata dal team `dev/db-tid` 2026-05-19. Aggiunte 4 colonne in coda al `RETURNS TABLE`: `quantita`, `qta_operativa`, `tipo_erogazione`, `fonte_quantita_attesa` (tutte `%TYPE` da `contratti_righe`). Popolate via i LEFT/JOIN su `cr` gia' esistenti nei 4 blocchi `RETURN QUERY` — NULL per Parte 1a/1b senza eccezione, valorizzate per OVERRIDE/ESCLUSIONE/AGGIUNTA.

**Impatto BE**: zero. `contratti_repository.list_righe_preview` usa `rows_to_list(cursor)` schema-agnostic — le colonne nuove arrivano automaticamente come proprieta' dell'oggetto riga.

**Impatto FE**: zero deploy. `ContrattoRigheDrawer._onEditRigaPersistita` legge gia' i 4 campi per nome (con fallback). Dopo l'apply della migration il form EDIT mostra i valori corretti.

**Motivo**: chiude il bug di display "modifico la quantita, salvo, riapro, vedo ancora il vecchio valore" — il BE salvava correttamente, ma la preview non esponeva `qta_operativa`/`tipo_erogazione`/`fonte_quantita_attesa`, quindi il form cadeva su fallback.

#### 1.h — Estensione `script.trgfn_qta_from_operativa` fonte-aware (APPLICATA)

**Status**: applicata dal team `dev/db-tid` 2026-05-19. Trigger generico esteso con 4° argomento opzionale = **nome della colonna** che porta `fonte_quantita_attesa` (es. `'fonte_quantita_attesa'`), NON un booleano.

Il trigger legge dinamicamente `NEW.<colonna>` e applica logica condizionale:

- `fonte IN ('MANUALE', 'TIMESHEET', 'LETTURE', 'DERIVATA_COMPONENTI')` → `qta_operativa NULL` ammessa, `RETURN NEW`.
- `fonte = 'FISSA'` → check `qta_operativa NOT NULL` resta attivo, raise `E_QTA_MISSING` se NULL.

Trigger `trg_contratti_righe_a10_qta_from_operativa_ins_upd` aggiornato con i 4 args:

```text
EXECUTE FUNCTION script.trgfn_qta_from_operativa(
    'true', 'false', 'quantita', 'fonte_quantita_attesa'
)
```

Tabelle che NON hanno `fonte_quantita_attesa` (preventivi_righe, ordini_righe, ecc.) restano sul comportamento legacy a 3 args (4° omesso) — zero impatto, retrocompatibile.

**Impatto BE**: zero. Allineamento gia' presente in [`_apply_fonte_quantita_logic`](../../../../backend/apps/vendite/services/contratti_service.py):

- Fonti downstream → BE forza `qta_operativa = None` (gia' fa).
- DERIVATA_COMPONENTI → BE no-op, payload arriva con `qta_operativa = None`.
- FISSA → BE guard `qta_operativa > 0` blocca prima del DB.

**Nota self-correzione**: il brief iniziale che avevo passato proponeva `'true'` come 4° arg (bypass cieco). La versione applicata dal team DB e' piu' sicura — passa il nome colonna e il trigger discrimina per valore. La mia proposta avrebbe ammesso silenziosamente `FISSA+NULL` (= bug nascosto), contraddicendo il pgTAP richiesto. Decisione corretta del team DB.

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
            f"docs/it/dev/work-done/refactor-contratti-fonte-quantita.md."
        ),
        context={"tipo_erogazione": tipo, "fonte_quantita_attesa": fonte},
    )
```

#### Sotto-step 2.2 — Default applicato lato BE (defense-in-depth + UX)

Il **DB applica gia' il default** via trigger `trg_contratti_righe_a10_default_fonte_qta_ins_upd` (vedi Step 1.c). Lato BE manteniamo comunque la mappa per due ragioni:

1. **UX form CREATE**: il FE deve pre-compilare il select `fonte_quantita_attesa` con il default in base a `tipo_erogazione` (l'utente vede la scelta predefinita, non un campo vuoto). Esponiamo la mappa al FE via API form-defaults o constants.
2. **Defense-in-depth lato service**: se il payload arriva senza fonte e con un `tipo_erogazione` valido, applichiamo comunque il default in `_build_data_riga` per coerenza errore-parlante (validazione coppia in 2.1 funziona anche su payload minimi). Senza default qui, il payload arriverebbe a DB con NULL e il trigger normalize "salverebbe la situazione" — meglio rendere esplicito.

```python
_FONTE_DEFAULT_PER_TIPO_EROGAZIONE: dict[str, str] = {
    "CANONE": "FISSA",
    "UNA_TANTUM": "FISSA",
    "ORARIO": "MANUALE",   # cambierà a TIMESHEET con il modulo dedicato
    "CONSUMO": "LETTURE",
}
```

#### Sotto-step 2.3 — Quantita normalizzata per fonte

- `fonte == 'FISSA'`: `quantita` obbligatoria > 0. Guard esplicita BE (in piu' del CHECK).
- `fonte in ('MANUALE', 'TIMESHEET', 'LETTURE')`: forzare `quantita = NULL` in `_build_data_riga` (anche se il client la invia, viene scartata silenziosamente — la fonte e' il driver).
- `fonte == 'DERIVATA_COMPONENTI'`: **gestita interamente dal DB** via trigger `z90_propaga_qta_componenti` (vedi Step 1.d). Il BE non deve toccare `quantita`: ne' forzarla a NULL ne' a 1. Il fix tampone 2026-05-19 (`quantita = qta_operativa` derivato silenziosamente per compositi) va rimosso in sotto-step 3.5 senza sostituto: e' il trigger DB che scrive il valore corretto post-INSERT dei figli.

#### Sotto-step 2.4 — Test BE

Aggiungere in [`test_contratti_service.py`](../../../../backend/apps/vendite/tests/services/test_contratti_service.py) classe `ContrattiServiceTests` (o nuova classe dedicata):

- `test_build_data_riga_applica_default_fonte_per_tipo_erogazione` (4 test, uno per ogni tipo)
- `test_build_data_riga_combinazione_vietata_solleva` (7 test, uno per ogni combinazione ❌)
- `test_build_data_riga_quantita_richiesta_se_fonte_fissa`
- `test_build_data_riga_quantita_forzata_null_se_fonte_non_fissa` (3 test: MANUALE, TIMESHEET, LETTURE)
- `test_build_data_riga_derivata_componenti_non_tocca_quantita` (lascia passare il valore del payload — il DB ci pensa)
- `test_update_riga_cambio_tipo_erogazione_reset_solo_se_fonte_diventa_vietata` (decisione 3, coerente col trigger DB)
- Aggiornare/rinominare `test_create_riga_articolo_composito_auto_init` per riflettere che il valore `quantita` non e' piu' settato dal service.

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

#### Sotto-step 3.6 — Relabeling azione kebab per `tipo_eccezione` (UX scope minimo)

**Trigger**: discussione 2026-05-19 — osservazione di Tid che "Elimina" su una riga `OVERRIDE` e' fuorviante (semanticamente l'articolo non viene rimosso dal contratto, viene resettato al prezzo di listino).

**Scope deliberatamente minimo**: solo relabeling + icon swap. Niente nuovo endpoint BE, niente azioni di transizione 1-click `OVERRIDE → ESCLUSIONE` (decisione: rinviare a eventuale futuro refactor; oggi il BE gia' fa la cosa giusta col DELETE, basta chiamare le cose col loro nome).

**Stato attuale** ([buildRigaActions](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue) `:757`):

- `DA_LISTINO`: kebab "Escludi" (corretto, lasciare invariato).
- `OVERRIDE` / `ESCLUSIONE` / `AGGIUNTA`: kebab "Elimina" generico (fuorviante per 2 casi su 3).

**Stato target**:

| `tipo_eccezione` | Label kebab | Icona | Severity | Azione (invariata: DELETE riga) |
| --- | --- | --- | --- | --- |
| `OVERRIDE` | "Ripristina prezzo di listino" | `pi pi-replay` o `pi pi-undo` | `secondary` | DELETE → torna `DA_LISTINO` in preview |
| `ESCLUSIONE` | "Ripristina articolo nel contratto" | `pi pi-replay` o `pi pi-undo` | `secondary` | DELETE → torna `DA_LISTINO` in preview |
| `AGGIUNTA` | "Rimuovi dal contratto" | `pi pi-trash` (= `MANAGE_ICONS.DELETE`) | `danger` | DELETE → l'articolo sparisce |
| `DA_LISTINO` | "Escludi articolo" (gia' presente) | `pi pi-ban` (gia' presente) | `warn` | crea ESCLUSIONE — invariato |

**Implementazione**:

```javascript
function buildRigaActions(data) {
  if (data.origine === 'DA_LISTINO') {
    return [/* invariato — escludi */]
  }
  if (data.origine === 'OVERRIDE') {
    return [{
      key: 'ripristina-listino',
      label: t('contratti.azione_ripristina_listino'),
      icon: 'pi pi-replay',
      severity: 'secondary',
      visible: !isReadonly.value,
      command: () => onRipristina(data),
    }]
  }
  if (data.origine === 'ESCLUSIONE') {
    return [{
      key: 'ripristina-articolo',
      label: t('contratti.azione_ripristina_articolo'),
      icon: 'pi pi-replay',
      severity: 'secondary',
      visible: !isReadonly.value,
      command: () => onRipristina(data),
    }]
  }
  // AGGIUNTA — "Elimina" semanticamente corretto: l'articolo non e' nel listino,
  // sparisce davvero.
  return [{
    key: 'rimuovi-aggiunta',
    label: t('contratti.azione_rimuovi_aggiunta'),
    icon: MANAGE_ICONS.DELETE,
    severity: 'danger',
    visible: !isReadonly.value,
    command: () => onDelete(data),
  }]
}
```

`onRipristina(data)` puo' essere lo stesso `onDelete` esistente, con confirm dialog dedicato che spieghi il vero effetto (es. "L'articolo tornera' al prezzo di listino. Confermi?"). Il backend non cambia (DELETE su `/righe/<id>/`).

**i18n nuove chiavi** (sotto `contratti`):

```json
"azione_ripristina_listino": "Ripristina prezzo di listino",
"azione_ripristina_articolo": "Ripristina articolo nel contratto",
"azione_rimuovi_aggiunta": "Rimuovi dal contratto",
"ripristina_listino_dialog_titolo": "Ripristina prezzo di listino",
"ripristina_listino_dialog_messaggio": "L'articolo {articolo} tornerà al prezzo di listino. L'override personalizzato verrà rimosso. Confermi?",
"ripristina_listino_dialog_conferma": "Ripristina",
"ripristina_articolo_dialog_titolo": "Ripristina articolo nel contratto",
"ripristina_articolo_dialog_messaggio": "L'articolo {articolo} tornerà disponibile nel contratto al prezzo di listino. L'esclusione verrà rimossa. Confermi?",
"ripristina_articolo_dialog_conferma": "Ripristina",
"riga_ripristinata": "Riga ripristinata al listino"
```

Rimuovere la chiave generica `common.delete` solo da questo punto (resta usata altrove). La chiave `contratti.riga_eliminata` resta per `AGGIUNTA`.

**Test smoke**: aggiungere in [test-contratto-composito.md](test-contratto-composito.md) un caso 10:

- Crea OVERRIDE su articolo X → riga compare con origine OVERRIDE.
- Kebab → "Ripristina prezzo di listino" (NON "Elimina").
- Click → dialog parlante → conferma → l'articolo torna `DA_LISTINO` in preview con prezzo listino.
- Stesso flusso per ESCLUSIONE.
- AGGIUNTA: kebab mostra "Rimuovi dal contratto" + icona `pi pi-trash` (cosmetico ma esplicito).

**Out-of-scope esplicito** (rinviati a sessione futura, se servira'):

- Azione 1-click `OVERRIDE → ESCLUSIONE` (oggi l'operatore deve fare 2 step: ripristina + escludi). Richiederebbe nuovo endpoint BE `POST /righe/<id>/cambia-tipo-eccezione/` con transazione atomica. Non urgente.
- Azione 1-click `ESCLUSIONE → OVERRIDE`. Stesso discorso.

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
- Sessione 2026-05-19 (refactor `ComponentiPanel` + Stream 3 composito): handoff interno `handoff_20260519_note_categoria_compositi.md`.
- Memorie applicabili:
  - `feedback_simmetria_modello_no_meta_scope.md` — abbracciare la simmetria piena subito, non rinviare a fase 2.
  - `feedback_no_quick_fix_soluzione_assoluta.md` — soluzione sul merito.
  - `feedback_db_actions_passaggio_team.md` — DB sempre via brief al team.
  - `project_no_produzione_solo_sviluppo.md` — niente compat shim, breaking change ammessi.
- Codice toccato:
  - BE: [`contratti_service.py`](../../../../backend/apps/vendite/services/contratti_service.py), [`test_contratti_service.py`](../../../../backend/apps/vendite/tests/services/test_contratti_service.py).
  - FE: [`ContrattoRigheDrawer.vue`](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue), [`it.json`](../../../../frontend/src/locales/it.json), [`en.json`](../../../../frontend/src/locales/en.json).
  - DB: brief in arrivo (vedi Step 1).
