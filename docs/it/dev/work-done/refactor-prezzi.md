# Refactor prezzi — gate L1/L2/L3 sulle offerte + chiusura bypass push + BB banner L2

> **Data analisi:** 2026-06-01
> **Ambito:** dominio vendite — offerte commerciali (DB + BE + FE), più
> estrazione building block FE del banner errore L2 ("regola del 2" #4) e fix del
> gap L1 sui componenti di contratti/offerte.
> **Stato: COMPLETATO** (2026-06-01).
> - **DB: FATTO** dal team su `dev/db-tid` (migrazioni `20260601-01..05` + pgTAP,
>   applicate al DB, non ancora pushate). Vedi §3.
> - **BE: FATTO** (`dev/backend-tid`): gate offerte L1/L2/L3, estrazione BB L1
>   componenti + fix contratti, endpoint approva/rifiuta offerta. **812 test
>   vendite verdi.** Vedi §4.
> - **FE: FATTO**: BB #4 (`L2ErrorBanner` + `classifyL2Error`), refactor
>   preventivi/contratti (no-op), nuovo consumer offerta, routing approvazioni
>   per-sorgente. **Build + lint verdi.** Vedi §5.
> - **Review critica + API doc: FATTE.** Vedi §9.
> - **Residui non bloccanti** (differiti, NON parte del refactor base): §4.7
>   (lifecycle pratica su revisione SUPERATA — decisione dominio aperta);
>   estrazione opzionale del BB pricing-adapter (3ª occorrenza, serve OK);
>   smoke E2E interattivo (svolti unit + build, non l'E2E su stack avviato).

---

## 0. Sintesi esecutiva

La guida di modello [gestione-offerte-commerciali.md](../../guide/gestione-offerte-commerciali.md)
(rev. 29-mag-2026) afferma in 5 punti distinti (§5.1, §5.3, **§6**, §11.3, §13.2)
che l'offerta commerciale usa **lo stesso modello di pricing dei contratti, con
gli stessi gate L1/L2/L3**. Il codice **non implementa nessuno dei tre gate**
sulle offerte — né backend né frontend. Inoltre `fn_push_offerta_a_contratto`
copiava le condizioni 1:1 a livello DB **bypassando** il gate che gira nel
service layer Python di preventivi/contratti.

Conseguenza concreta: un'offerta (e il contratto che ne nasce via push) poteva
portare un prezzo fuori dai limiti di variazione **senza che L1 (chi), L2
(quanto) o L3 (approvazione) scattassero mai**. È una **divergenza modello↔codice**,
non una scelta di design ([[feedback_bug_logici_modello]]).

Questo intervento porta l'offerta in **conformità simmetrica** con il contratto
([[feedback_simmetria_modello_no_meta_scope]]) e, nel farlo:
- rende l'offerta il **terzo consumer** del banner L2 → chiude la "regola del 2"
  #4 con un'estrazione di building block invece di una terza duplicazione
  ([[feedback_regola_del_2_estrai_bb]]);
- chiude un **terzo buco** emerso durante l'analisi DB: contratti (e offerte) non
  validano l'L1 sugli override dei componenti BoM, mentre preventivi sì (§4.6).

---

## 1. Il problema: divergenza modello documentato ↔ codice

### 1.1 Cosa dice il modello (fonte di verità)

La guida dichiara l'offerta gemella in proposta del contratto:

- **§6** ([righe 287-308](../../guide/gestione-offerte-commerciali.md#L287-L308)):
  *"L'offerta usa lo stesso modello di pricing dei contratti… passa per i tre
  gate"* — L1 ("il backend rifiuta"), L2 ("cascata user → categoria_cliente →
  group → emittente → default", **identica** a `_resolve_soglia_variazione_pct`),
  L3 (pratica `APPROVAZIONE_PREZZO`, prezzo `PENDING`).
- **§5.1 step 2** / **§5.3**: prezzi componenti modificabili *"con i controlli
  L1/L2/L3"* / *"con controlli di autorizzazione"*.
- **§11.3** + **§2.3** + **§6**: l'approvazione L3 ottenuta sull'offerta *"viaggia
  fino al contratto"* (copia 1:1 al push).
- **§13.2**: *"stesso modello di pricing, stessi gate L1/L2/L3"*.

### 1.2 Cosa faceva il codice (verificato pre-intervento)

| Livello | Preventivi | Contratti | Offerte |
|---|---|---|---|
| BE gate L1 prezzo riga (`check_permesso_override_prezzo`) | ✅ | ✅ | ❌ |
| BE gate L2 prezzo riga (`check_limite_variazione_prezzo`) | ✅ | ✅ | ❌ |
| BE gate L3 (pratica + PENDING) | ✅ | ✅ | ❌ |
| BE gate **L1 override componenti** (`_validate_componenti_overrides_authorization`) | ✅ | ❌ | ❌ |
| FE banner L2 + CTA "richiedi approvazione" | ✅ | ✅ | ❌ |

- `offerte_service` **non importava** `_pricing_gate_helpers` e non chiamava
  `resolve_or_check_override_prezzo`. Persisteva `prezzo_unitario` così com'è
  ([offerte_service.py:895-930](../../../../backend/apps/vendite/services/offerte_service.py#L895-L930)).
- L'orchestratore dei 3 gate, `resolve_or_check_override_prezzo`
  ([_pricing_gate_helpers.py:392-525](../../../../backend/apps/vendite/services/_pricing_gate_helpers.py#L392-L525)),
  era cablato solo da `preventivi_service` e `contratti_service`.
- `contratti_service.create_riga` normalizza i `componenti_overrides`
  ([:1157-1159](../../../../backend/apps/vendite/services/contratti_service.py#L1157-L1159))
  ma **non** valida l'L1, a differenza di preventivi
  ([preventivi_service.py:617](../../../../backend/apps/vendite/services/preventivi_service.py#L617)).
- FE [OffertaEccezioniDrawer.vue](../../../../frontend/src/vendite/offerte/components/OffertaEccezioniDrawer.vue)
  salvava con `useApiHandler.execute()` standard: niente `l2Error`, niente CTA.

---

## 2. Verifica: dove vive lo stato approvazione (riga vs componente)

Per le eccezioni **non composite** lo stato approvazione vive a livello riga o
componente? Risposta dalle tabelle `dbzero` (pre-intervento):

| Tabella | `stato_approvazione_prezzo` + `pratica_approvazione_prezzo_id` |
|---|---|
| `preventivi_righe` | ✅ ([righe 25-26](../../dbzero/vendite/tabelle/preventivi_righe.md)) |
| `contratti_righe` | ✅ ([righe 29-30](../../dbzero/vendite/tabelle/contratti_righe.md)) |
| `offerte_commerciali_eccezioni` | ❌ **mancavano** (aggiunte da `20260601-01`) |
| `offerte_commerciali_eccezioni_componenti` | ✅ ([righe 20-21](../../dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti.md)) |
| `contratti_righe_componenti` / `preventivi_righe_componenti` | ✅ |

**Conclusione:** l'asimmetria era **strutturale a livello DB**. La tabella
componenti dell'offerta (costruita dopo, in piena simmetria) aveva già le colonne;
la tabella **righe/eccezioni** no. Conseguenza: un OVERRIDE/AGGIUNTA non composito
dell'offerta non aveva dove registrare l'approvazione, e per questo il push poteva
solo azzerare a NULL lo stato sulle `contratti_righe` mentre lo copiava 1:1 sui
componenti. L'audit pricing leggero (`origine_prezzo`, `prezzo_resolver_context`)
non richiede colonne dedicate: viaggia nel `meta` jsonb che le eccezioni offerta
già hanno. Quindi a livello riga servivano **solo** le due colonne di approvazione
— ed è esattamente ciò che `20260601-01` ha aggiunto.

---

## 3. Modifiche DB — FATTE (team DB, `dev/db-tid`)

> Eseguite dal team DB ([[feedback_db_actions_passaggio_team]]): migrazioni
> `20260601-01..05` + pgTAP, applicate al DB locale (non ancora pushate). Questa
> sezione documenta **ciò che è stato effettivamente fatto** (≠ brief iniziale: il
> team ha migliorato in due punti, evidenziati sotto). Codici errore/ENUM: riuso
> totale (`E_RIGA_PREZZO_PENDENTE`, `config.stato_approvazione_prezzo`).

### 3.1 Colonne approvazione su `offerte_commerciali_eccezioni` — `20260601-01`

Mirror 1:1 di `20260518-01` (contratti_righe):

- `stato_approvazione_prezzo config.stato_approvazione_prezzo` (NULL ammesso);
- `pratica_approvazione_prezzo_id bigint` + FK
  `fk_offerte_eccezioni_pratica_approvazione_prezzo → pratiche.pratiche(id)`;
- indice parziale `ix_vendite_offerte_eccezioni_stato_approvazione
  ... WHERE stato_approvazione_prezzo IS NOT NULL`.

### 3.2 Guard riga PENDING **generico** — `20260601-02/03` (miglioria del team)

> **Δ rispetto al brief iniziale.** Invece di clonare un terzo guard dedicato per
> l'offerta, il team ha **estratto** il building block — regola del 2 applicata
> anche al DB. Scelta corretta e adottata.

- `20260601-02`: nuova `script.trgfn_righe_guard_pending()` generica. Usa una
  **allowlist via `to_jsonb`** (blocca *tutti* i campi tranne quelli di
  workflow/audit: `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`,
  `meta`, `data_update`, `user_update`, `tx_id`). Più robusta delle vecchie
  denylist statiche (immune all'aggiunta di colonne). `TG_ARGV[0]` = colonna FK
  padre; raise `E_RIGA_PREZZO_PENDENTE`.
- `20260601-03`: ripuntati **tutti e tre** i trigger `*_a10_guard_pending_upd`
  (preventivi `'preventivo_id'`, contratti `'contratto_id'`, offerte
  `'offerta_id'`, nome `trg_offerte_eccezioni_a10_guard_pending_upd`) al guard
  generico; **droppate** le due funzioni dedicate
  (`trgfn_preventivi_righe_guard_pending`, `trgfn_contratti_righe_guard_pending`)
  ora codice morto. Equivalenza comportamentale verificata.

### 3.3 `fn_push_offerta_a_contratto`: trasporto 1:1 stato approvazione riga — `20260601-04`

CREATE OR REPLACE (nessun cambio firma): l'INSERT in `contratti_righe` ora copia
`stato_approvazione_prezzo` + `pratica_approvazione_prezzo_id` dalla riga
eccezione sorgente (prima erano NULL). L'approvazione ottenuta in offerta non va
riapprovata sul contratto (guida §6/§11.3).

### 3.4 `fn_crea_revisione_offerta`: carry-forward in revisione — `20260601-05` (aggiunta del team)

> **Δ rispetto al brief iniziale.** Punto che il mio brief non copriva.

CREATE OR REPLACE: la INSERT…SELECT delle eccezioni nella nuova revisione copia
le 2 colonne (carry-forward, **non** reset a NULL). Motivo: lo
`stato_approvazione_prezzo` è l'unico marcatore persistente che un prezzo è
fuori-soglia (i gate scattano solo sull'edit BE, non a emissione/push). Azzerarlo
in revisione lascerebbe un prezzo fuori-policy non marcato. Coerente con "niente
doppia approvazione".

**Caveat → hand-off BE (§4.7):** una riga `PENDING` copiata mantiene la
`pratica_approvazione_prezzo_id` referenziata anche dalla rev.N (che diventa
SUPERATA). Strutturalmente regge (FK many-to-one); il lifecycle della pratica su
una revisione superata è decisione del dominio approvazioni (BE).

### 3.5 pgTAP DB

- aggiornato `test-contratti-righe-guard-pending-v1.sql` #2 (asserisce il guard
  generico); test comportamentali 4-8 invariati;
- nuovo `test-offerte-eccezioni-guard-pending-v1.sql`;
- `liquibase validate` + run guard_pending (no-regressione) verdi.

---

## 4. Piano backend (`dev/backend-tid`)

> Mirror di pattern già esistenti su contratti/preventivi — nessuna logica nuova,
> estensione del wiring all'offerta + estrazione di un BB già esistente. I
> prerequisiti DB §3 sono applicati in locale ([[feedback_be_fe_attende_prerequisiti_db]]).

### 4.1 Costanti — `_approvazioni_prezzo_constants.py`

- `SORGENTE_OFFERTA = "offerta"`
- `META_KEY_RIGA_OFFERTA_ID = "riga_offerta_id"`

### 4.2 Workflow approvazioni — `approvazioni_prezzo_service.py`

Il dispatcher è già sorgente-agnostico via `_SORGENTE_CONFIG`
([:115-138](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py#L115-L138)).
Aggiungere una entry, niente modifiche al dispatcher ([[feedback_concentrico_no_yagni]]):

- adapter `_update_riga_offerta(riga_id, fields)` → `OfferteRepository().update_eccezione(...)`;
- entry `_SORGENTE_CONFIG[SORGENTE_OFFERTA]`;
- funzione pubblica `crea_richiesta_approvazione_offerta(...)` speculare a
  `crea_richiesta_approvazione_contratto`.

> **Decisione (1):** l'enforcement del freeze su riga PENDING è demandato al DB
> (guard generico §3.2): l'adapter Python fa solo l'UPDATE. Routing
> `ApprovazioniPrezzoListView` per sorgente `offerta` → passo FE §5.6.

### 4.3 Resolver prezzo riga offerta — `offerte_service.py`

Non esiste un `offerta_suggerisci_prezzo_riga`. Mirror di
[contratti_suggerisci_prezzo_riga](../../../../backend/apps/vendite/services/contratti_service.py#L2584-L2628):

- `_load_offerta_context_for_pricing(offerta_id, auth_user_id)` → `ba_id`,
  `utility_id`, `data_riferimento (validita_dal)`, `emittente_sr_id` (riuso
  `_resolve_emittente_sr_id_for_offerta`), `listino_versione_id_preferito`;
- `offerta_suggerisci_prezzo_riga(...)` → `PricingService().resolve_prezzo(...)`
  + normalizzazione Decimal/date→str.

### 4.4 Wrapper gate + wiring create/update eccezione

- `resolve_or_check_override_prezzo_riga_offerta(...)` — mirror di
  [resolve_or_check_override_prezzo_riga_contratto](../../../../backend/apps/vendite/services/contratti_service.py#L2643-L2681)
  (`resolver_fn=offerta_suggerisci_prezzo_riga`, `error_code_validazione=E_VENDITE_VALIDATION`,
  alias `data`←`validita_dal`, skip gate se `listino_id` None).
- `_apply_pricing_gate_riga_offerta(...)` — mirror di
  [_apply_pricing_gate_riga](../../../../backend/apps/vendite/services/contratti_service.py#L1299-L1362):
  invoca il wrapper, normalizza `prezzo_unitario`, merge `meta`, e se
  `richiesta_approvazione_pending` orchestra la pratica + popola
  `stato_approvazione_prezzo=PENDING` + `pratica_approvazione_prezzo_id`.
- `_orchestrate_l3_request_offerta(...)` — mirror di
  [_orchestrate_l3_request_contratto](../../../../backend/apps/vendite/services/contratti_service.py#L2690-L2721)
  (`crea_richiesta_approvazione_offerta` + `link_riga_a_pratica(sorgente=SORGENTE_OFFERTA)`).
- Cablare il gate in `crea_eccezione` e `aggiorna_eccezione` di `offerte_service`,
  accettando `richiesta_approvazione` nel payload. Gate attivo solo su
  OVERRIDE/AGGIUNTA con `prezzo_unitario` (ESCLUSIONE → prezzo NULL → no gate).

### 4.5 Push: pulizia eventuale azzeramento BE (verifica)

`fn_push` ora copia lo stato approvazione (§3.3): verificare che nessun layer BE
forzi NULL o si aspetti il vecchio comportamento sulle righe contratto generate.

### 4.6 Fix gap L1 override componenti — estrazione BB + cablaggio (decisione 3 rettificata)

> **Bug di modello** emerso dall'analisi DB ([[feedback_bug_logici_modello]]):
> `preventivi_service` valida l'L1 sugli override dei componenti BoM
> ([:617](../../../../backend/apps/vendite/services/preventivi_service.py#L617)),
> `contratti_service.create_riga` **no**. La decisione 3 ("compositi → allineare a
> contratti") va **rettificata**: per questa specifica validazione contratti è il
> riferimento *sbagliato* (è bucato); il riferimento corretto è **preventivi**.

- **Promuovere** `_validate_componenti_overrides_authorization` (oggi locale a
  `preventivi_service`) a building block condiviso in `_pricing_gate_helpers`
  (single source of truth — regola del 2).
- Cablarlo in **contratti** (`create_riga`, chiude il buco) **e in offerte**
  (`crea_eccezione`), oltre a lasciarlo in preventivi.
- L1 usa `PermissionResolver` Django: **nessun safety-net DB possibile** (azione
  di processo, non un dato di colonna) → l'enforcement è solo BE. Per questo il
  fix è prioritario lato service.

### 4.7 Lifecycle pratica su revisione SUPERATA (caveat §3.4)

Decidere il comportamento della pratica di approvazione quando la rev.N (con riga
PENDING) passa a SUPERATA per via di una nuova revisione: la `pratica_..._id` è
copiata in entrambe. Opzioni: lasciar vivere la pratica (riferita alla rev viva),
o chiuderla/clonare. Da definire nel dominio approvazioni. **Non bloccante** per
il gate base; tracciato come voce a sé.

### 4.8 Test BE

- Mirror dei test contratti (gate riga): L1 negato/concesso, L2 entro/oltre
  soglia, L3 `richiesta_approvazione` → pratica + riga PENDING, superuser bypass,
  AGGIUNTA fuori listino → skip.
- **Nuovi test L1 componenti** su contratti e offerte (regressione del fix §4.6):
  operatore senza `prezzo_override_manuale` + `componenti_overrides` → rifiuto.
- Test push/revisione: eredità + carry-forward stato approvazione 1:1.
- Suite vendite completa verde prima del FE.

---

## 5. Piano frontend (include "regola del 2" #4)

### 5.1 Disegno building block #4 (banner L2)

Banner L2 duplicato ~95% tra
[PreventiviRigaForm.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue)
e [ContrattoRigheDrawer.vue](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue).
Con l'offerta come terzo consumer si **estrae** ([[feedback_regola_del_2_estrai_bb]]).
Modello canonico (come #3): caller-side le differenze di dominio (handler, ref,
watch); nel BB solo l'identico (markup + classificazione). Due pezzi in
`frontend/src/vendite/_shared/pricing/`.

#### 5.1.a Componente `L2ErrorBanner.vue`

Presentazionale puro del blocco `<Message>` + CTA. Rende nulla se `error` falsy.
Centralizza gli import `Message`/`Button`/`vTooltip`.

| Prop | Tipo | Note |
|---|---|---|
| `error` | `Object \| null` | `{ code, message, detail }`; se falsy non rende nulla |
| `loading` | `Boolean` | pilota `:loading` del bottone + swap label |
| `label` | `String` | CTA a riposo |
| `labelLoading` | `String` | CTA in corso |
| `tooltip` | `String` | tooltip CTA |

Emits: `richiedi`. Prefisso i18n caller-side: il caller passa stringhe già
risolte, il componente non conosce le chiavi.

```vue
<!-- frontend/src/vendite/_shared/pricing/L2ErrorBanner.vue -->
<script setup>
import { computed } from 'vue'
import Message from 'primevue/message'
import Button from 'primevue/button'
import vTooltip from 'primevue/tooltip'

const props = defineProps({
  error: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  label: { type: String, required: true },
  labelLoading: { type: String, required: true },
  tooltip: { type: String, default: '' },
})
defineEmits(['richiedi'])
const ctaLabel = computed(() => (props.loading ? props.labelLoading : props.label))
</script>

<template>
  <Message v-if="error" severity="warn" :closable="false">
    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
      <strong>{{ error.message }}</strong>
      <small v-if="error.detail">{{ error.detail }}</small>
      <div>
        <Button
          :label="ctaLabel"
          icon="pi pi-send"
          size="small"
          severity="secondary"
          :loading="loading"
          v-tooltip.bottom="tooltip"
          @click="$emit('richiedi')"
        />
      </div>
    </div>
  </Message>
</template>
```

Sostituisce: PreventiviRigaForm [613-629](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue#L613-L629)
· ContrattoRigheDrawer [1375-1393](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L1375-L1393).

#### 5.1.b Helper `classifyL2Error.js`

Pura, senza side-effect: ritorna l'oggetto banner se codice L2, altrimenti `null`
(il caller fa `notify.error`).

```js
// frontend/src/vendite/_shared/pricing/classifyL2Error.js
import { extractApiError, extractApiErrorCode } from '@/core/utils/apiError'

export function classifyL2Error(err, { fallbackMessage, l2ErrorCodes }) {
  const code = extractApiErrorCode(err)
  if (!l2ErrorCodes.includes(code)) return null
  return {
    code,
    message: extractApiError(err, fallbackMessage),
    detail: err?.response?.data?.error?.detail || '',
  }
}
```

Sostituisce: PreventiviRigaForm [480-491](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue#L480-L491)
· ContrattoRigheDrawer [845-854](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L845-L854).

#### 5.1.c Cosa NON estrarre

- gli **handler** save/richiedi-approvazione (success diverge: preventivi
  `emit('saved')`; contratti `loadPreview+emit('changed')+closeForm`; offerte
  `reload+closeForm`);
- il **ref `l2Error`** e il **watch-reset**: in preventivi intrecciato col badge
  resolver. Resta `l2Error.value = null` nei watch esistenti.
- niente composable `useL2Error`: i tre input divergono troppo poco per
  giustificarlo, e il watch preventivi non sarebbe assorbibile pulito.

### 5.2 Refactor preventivi + contratti (adozione BB, ZERO cambi di comportamento)

Sostituire i due blocchi template col componente e il `catch` con `classifyL2Error`.
Handler, ref, watch, emit invariati. Verifica con build + non-regressione visiva.

### 5.3 Nuovo consumer: `OffertaEccezioniDrawer.vue`

Mirror del wiring contratti:

- `useLimitiPricing()` → `L2_ERROR_CODES`; `const l2Error = ref(null)`;
- watch-reset su `[form.prezzo_unitario, form.articolo_id]` → `l2Error = null`;
- `handleSave` da `execute()` generico a `try/catch` + `classifyL2Error`; success
  path **resta** dell'offerta (`reload()` + `closeForm()`);
- `onRichiediApprovazione()` → ri-salva con `richiesta_approvazione: true` nel
  payload, poi `reload()` + `closeForm()`;
- `<L2ErrorBanner ... @richiedi="onRichiediApprovazione" />`;
- **Decisione (2):** mostra i limiti L2 come gli altri due
  (`watch billingAccountId → loadLimiti`, `limiti` per tooltip/soglie).

### 5.4 i18n

Chiavi `vendite.offerte.*`: `richiedi_approvazione`,
`richiedi_approvazione_in_corso`, `richiedi_approvazione_tooltip`,
`richiesta_approvazione_inviata`, `errore_generico` (se mancante).

### 5.5 Test / build FE

Build verde + smoke manuale: OVERRIDE offerta entro soglia (ok), oltre soglia
senza L1 (errore), oltre soglia con L1 (banner), CTA → pratica + PENDING, push →
contratto eredita.

### 5.6 Routing approvazioni FE

`ApprovazioniPrezzoListView.vue`: aggiungere il caso sorgente `offerta` (link alla
riga eccezione offerta) così l'approvatore agisce sulle pratiche da offerta.

---

## 6. Sequenza ed esecuzione

1. **DB — FATTO** (§3, applicato non pushato).
2. **BE** (§4): costanti → resolver → wrapper/gate → wiring crea/aggiorna →
   workflow sorgente offerta → fix L1 componenti (estrazione BB + contratti+offerte).
   Suite vendite verde.
3. **FE** (§5): estrazione BB #4 + refactor preventivi/contratti (no-op) → nuovo
   consumer offerta → routing approvazioni.
4. Smoke E2E (offerta → gate → approvazione → push → contratto).

Ordine obbligato: il FE non intercetta codici L2 che il BE non emette; il BE
scrive PENDING su colonne ora presenti (DB fatto).

---

## 7. Cosa NON rompere (rischi)

- **Preventivi/contratti**: adozione BB #4 a comportamento invariato (stessi
  handler/emit/watch). Rischio regressione visiva banner → build + markup.
- **Permissività resolver offerta** (guida §5.2): non toccarla. Se il resolver
  torna 0/None (fuori listino) il gate L2 fa skip — corretto.
- **Compositi — Decisione (3) rettificata:** struttura/flusso del gate riga
  composita allineata a contratti (padre derivato), **ma** la validazione L1
  override-componenti allineata a **preventivi** (contratti era bucato — §4.6).
- **Idempotenza push**: invariata.
- **Carry-forward revisione / push 1:1**: nessun test BE deve aspettarsi più il
  vecchio azzeramento NULL.
- **L1 componenti**: enforcement solo BE (Django PermissionResolver), nessun
  safety-net DB → il fix §4.6 è l'unica barriera.

---

## 8. Checklist

**DB (team DB) — FATTO**
- [x] `20260601-01` colonne + FK + indice parziale su `offerte_commerciali_eccezioni`
- [x] `20260601-02` `script.trgfn_righe_guard_pending` generico (allowlist)
- [x] `20260601-03` repoint 3 trigger + drop 2 fn dedicate
- [x] `20260601-04` push: copia 1:1 stato approvazione riga
- [x] `20260601-05` revisione: carry-forward
- [x] pgTAP guard_pending (contratti aggiornato + nuovo offerte) verdi

**BE**
- [x] Costanti `SORGENTE_OFFERTA` / `META_KEY_RIGA_OFFERTA_ID`
- [x] `_SORGENTE_CONFIG[offerta]` + adapter + `crea_richiesta_approvazione_offerta`
- [x] `_load_offerta_context_for_pricing` + `offerta_suggerisci_prezzo_riga`
- [x] `resolve_or_check_override_prezzo_riga_offerta` + `_apply_pricing_gate_eccezione` + `_orchestrate_l3_request_offerta`
- [x] Gate cablato in `crea_eccezione` / `aggiorna_eccezione`
- [x] **Fix L1 componenti**: estrazione `validate_componenti_overrides_authorization` in BB + cablaggio contratti + offerte
- [x] Endpoint `eccezioni-offerta/<id>/approva|rifiuta-prezzo` + URL
- [x] Test gate offerta + test L1 componenti (contratti/offerte) + push/revisione (812 verdi)
- [ ] Decisione lifecycle pratica su rev SUPERATA (§4.7) — **differito, non bloccante**

**FE**
- [x] BB `L2ErrorBanner.vue` + `classifyL2Error` in `_shared/pricing/`
- [x] Refactor preventivi + contratti su BB (no-op funzionale)
- [x] Wiring L2 completo in `OffertaEccezioniDrawer` (terzo consumer)
- [x] i18n `vendite.offerte.*` (it + en)
- [x] Routing `ApprovazioniPrezzoListView` per-sorgente (preventivo/contratto/offerta — chiude anche il gap contratti)
- [x] Build FE + lint verdi (smoke E2E su stack avviato: non eseguito)

---

## 9. Review critica + API doc (post-implementazione)

**Bug corretto**: clobber del `meta` su `aggiorna_eccezione` quando il PATCH
tocca il prezzo — `_apply_pricing_gate_eccezione` ora accetta `fallback_meta`
(= meta esistente) e mergia l'audit invece di sovrascrivere (mirror contratti).
Blindato dal test `apply_gate_eccezione_preserva_meta_esistente`.

**Duplicazione segnalata (NON estratta, serve OK)**: i wrapper di dominio del
pricing sono alla 3ª occorrenza (preventivi/contratti/offerte):
`_load_<dom>_context_for_pricing`, `<dom>_suggerisci_prezzo_riga`,
`resolve_or_check_override_prezzo_riga_<dom>`, `_apply_pricing_gate_*`.
~80% identici (divergono per campo-data testata, repo, messaggio not-found).
Candidati a BB parametrizzato — da dichiarare e approvare prima di astrarre
([[feedback_regola_del_2_estrai_bb]]). L'orchestratore dei gate è già condiviso.

**API doc aggiornate**: [api_offerte.md](../../backend/vendite/manual/api_offerte.md)
(gate su create/update eccezioni, `richiesta_approvazione`, output stato
approvazione, push 1:1) + [api_approvazioni_prezzo.md](../../backend/vendite/manual/api_approvazioni_prezzo.md)
(sezione "Sorgenti e routing" coi 3 endpoint per sorgente).
