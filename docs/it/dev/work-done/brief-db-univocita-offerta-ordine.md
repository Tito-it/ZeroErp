# Brief DB — Univocità `offerta → ordine` (1:1 permanente) + azione `genera_ordine` data-driven

> **Stato**: ✅ **CHIUSO (2026-06-08)** — DB (migration + fn + pgTAP 15/15 su
> `dev/db-tid`) **e** cablaggio **BE/FE** completati e verdi (BE 28+579 test,
> FE ESLint+build). Dettaglio in §9 «Stato avanzamento».
>
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data brief**: 2026-06-07 — agg. 2026-06-08 (consegna DB).
>
> **Ambito**: **solo offerta commerciale**. Il caso `preventivo → ordine` ha un
> modello *diverso* (split per natura di riga, orchestrato dalla pratica) ed è
> trattato in un documento dedicato: [brief-preventivi-ordini.md](../work-in-progress/brief-preventivi-ordini.md).
> **Non** applicare nulla di questo brief al preventivo.
>
> **Origine**: bug operativo segnalato da Tid. Da un'offerta `ACCETTATA`,
> premendo "Genera ordine" l'ordine viene creato correttamente
> (`documento_origine = ('OFFERTA', id)`), **ma nessun vincolo impedisce di
> rigenerarlo**: ripremendo il bottone nascono ORD duplicati, senza errore e
> senza segnale UI.
>
> **Decisione di modello ratificata (Tid, 2026-06-07)**: un'offerta commerciale
> genera **al massimo UN ordine**, in blocco (1:1 a livello testata). È una
> scelta **strutturale e permanente**, non un ripiego: vedi §4 per il «perché».
>
> **Modelli di riferimento già implementati**:
>
> - [`script.fn_available_actions_offerta`](../../dbzero/script/funzioni/fn_available_actions_offerta.md) — azione speciale `push_contratto` con guard idempotenza cross-dominio
> - [`vendite.fn_push_offerta_a_contratto`](../../dbzero/vendite/funzioni/fn_push_offerta_a_contratto.md) — idempotenza strutturale (UNIQUE `vendite.contratti.offerta_id`)

---

## 1. Inquadramento — stato di fatto verificato

`vendite.ordini` traccia l'origine via `documento_origine_tipo`
(`'PREVENTIVO'`/`'OFFERTA'`) + `documento_origine_id`, **senza UNIQUE** (scelta
A1 in [analisi-ordini-vendita.md §1.bis](../work-in-progress/analisi-ordini-vendita.md)). Verificato
su [`vendite/tabelle/ordini.md`](../../dbzero/vendite/tabelle/ordini.md): gli
unici CHECK sono `chk_ordini_documento_origine_tipo` (vocabolario) e
`chk_ordini_documento_origine_copres` (co-presenza `(tipo IS NULL) = (id IS
NULL)`); **nessun UNIQUE** sulla coppia.

Verificato nel codice BE:

- [`crea_ordine_da_offerta`](../../../../backend/apps/vendite/services/ordini_service.py)
  controlla solo `stato = ACCETTATA` e copia **tutte** le righe espanse
  (`fn_offerta_righe_espanse`). Niente impedisce la seconda generazione.
- Il bottone "Genera ordine" è **hardcoded** lato FE su `stato = ACCETTATA` in
  [`OffertaDrawer.vue`](../../../../frontend/src/vendite/offerte/components/OffertaDrawer.vue):
  resta visibile anche dopo la conversione.

Verificato che l'offerta **non ha uno stato terminale tipo EVASO**: gli stati
sono BOZZA / EMESSA / ACCETTATA / RIFIUTATA / SUPERATA / ANNULLATA
([stati_doc_offerte.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/stati_doc_offerte.csv)).
Dopo `push_contratto` e dopo `genera_ordine` l'offerta **resta ACCETTATA** →
il gate `ACCETTATA + nessun ordine` è la storia completa, senza interazioni di
stato (a differenza del preventivo, che ha EVASO — vedi brief dedicato).

Per contro, `push_contratto` su `fn_available_actions_offerta` è **già**
idempotente e data-driven, blindata a DB dall'UNIQUE `vendite.contratti.offerta_id`.
Questo brief chiude l'asimmetria portando lo stesso pattern su `genera_ordine`,
su 2 livelli DB: integrità hard (indice) + capability data-driven (fn).

## 2. Cosa serve (DB)

### 2.1 Indice UNIQUE parziale su `vendite.ordini` (integrità hard)

Vincolo 1:1 **solo per origine `OFFERTA`** (`PREVENTIVO` resta fuori — modello
diverso, vedi brief dedicato):

```sql
CREATE UNIQUE INDEX uq_ordini_v_documento_origine_offerta
    ON vendite.ordini (documento_origine_tipo, documento_origine_id)
 WHERE documento_origine_tipo = 'OFFERTA';
```

- Naming coerente con gli indici esistenti (`uq_ordini_v_*`).
- Parziale: non vincola `PREVENTIVO` né gli ordini nativi
  (`documento_origine_tipo IS NULL`). Il CHECK `chk_ordini_documento_origine_copres`
  garantisce che con `tipo='OFFERTA'` l'`id` è NOT NULL → **nessuna insidia sui
  NULL**.
- È la rete di sicurezza strutturale (anche contro race concorrenti). Il BE
  mapperà la violazione a `E_ORD_OFFERTA_GIA_CONVERTITA` (§7).
- **Nota di onestà sull'integrità** (≠ `push_contratto`): qui l'idempotenza è una
  UNIQUE parziale su colonne *polimorfiche* (`documento_origine_*`), **senza FK**
  verso `offerte_commerciali` — `documento_origine_id` resta un bigint non
  referenziato. È una proprietà *preesistente* di A1 (link polimorfico per
  design), non introdotta qui; aggiungere una FK tipizzata duplicherebbe la
  provenienza. Quindi: **stesso pattern di capability** di `push_contratto`, ma
  integrità referenziale più debole sull'`id` per design.

### 2.2 `script.fn_available_actions_offerta` — nuova azione speciale `genera_ordine`

Aggiungere `genera_ordine` come **azione speciale hardcoded non-cambio-stato**,
mirror di `push_contratto`.

**Costante azione** (accanto a `c_action_push_contratto`):

```sql
c_action_genera_ordine CONSTANT jsonb := jsonb_build_object(
    'key',                  'genera_ordine',
    'target_state',         NULL,                                  -- azione speciale, non cambio stato
    'label_key',            'vendite.offerte.azione_genera_ordine', -- i18n già esistente (it.json/en.json)
    'severity',             'info',
    'icon',                 'pi pi-shopping-cart',                  -- NAV_ICONS.ORDINI
    'requires_confirm',     true,
    'requires_motivazione', false
);
```

**Guard idempotenza** (dentro il ramo `v_stato_cod = 'ACCETTATA'`): l'azione
appare **solo** se nessun ordine è già nato da questa offerta.

```sql
-- can_genera_ordine: ACCETTATA + nessun ordine già generato.
-- Specchio del blocco can_push_contratto e dell'UNIQUE parziale §2.1.
IF v_stato_cod = 'ACCETTATA' THEN
    IF NOT EXISTS (
        SELECT 1 FROM vendite.ordini
         WHERE documento_origine_tipo = 'OFFERTA'
           AND documento_origine_id   = p_offerta_id
    ) THEN
        v_can_ordine        := true;
        v_ordine_reason     := NULL;
        v_ordine_reason_key := NULL;
        v_actions := v_actions || jsonb_build_array(c_action_genera_ordine);
    ELSE
        v_can_ordine        := false;
        v_ordine_reason     := 'OFFERTA_ORDINE_GIA_GENERATO';
        v_ordine_reason_key := 'offerte.push_reason.ordine_gia_generato';
    END IF;
ELSE
    v_can_ordine        := false;
    v_ordine_reason     := 'OFFERTA_NON_ACCETTATA';
    v_ordine_reason_key := 'offerte.push_reason.non_accettata';  -- riuso chiave esistente
END IF;
```

> `push_contratto` e `genera_ordine` sono **indipendenti**: un'offerta ACCETTATA
> può esporre entrambe, ognuna con la propria idempotenza. Nessuna mutua
> esclusione.

**Estendere l'output `jsonb`** con i tre flag (mirror dei `can_push_contratto*`):

```jsonc
{
  // ... campi esistenti invariati ...
  "can_genera_ordine":            false,  // true solo in ACCETTATA + nessun ordine generato
  "can_genera_ordine_reason":     null,   // reason machine-readable se can=false
  "can_genera_ordine_reason_key": null    // chiave i18n associata se can=false
}
```

### 2.3 Matrice reason `can_genera_ordine`

| Caso | `can_genera_ordine` | `_reason` | `_reason_key` |
|------|---------------------|-----------|---------------|
| `ACCETTATA` **e** nessun ordine da questa offerta | `true` | `null` | `null` |
| `ACCETTATA` **ma** esiste già ordine `('OFFERTA', id)` | `false` | `'OFFERTA_ORDINE_GIA_GENERATO'` | `'offerte.push_reason.ordine_gia_generato'` |
| stato ≠ `ACCETTATA` | `false` | `'OFFERTA_NON_ACCETTATA'` | `'offerte.push_reason.non_accettata'` |

### 2.4 Convenzione `target_state`

`genera_ordine` ritorna `target_state: null` come `push_contratto`/`crea_revisione`:
è routing speciale (genera un secondo oggetto), non una transizione di stato.
L'offerta **resta `ACCETTATA`**. Il FE distingue l'azione dal `key`.

## 3. Cosa NON cambia a DB

- **State machine offerta**: i 6 stati e il guard di transizione restano
  invariati. L'offerta **non** acquisisce uno stato "CONVERTITA": la generazione
  ordine è un effetto, non un cambio stato (coerente con `push_contratto`).
- `fn_available_actions_offerta` resta **pura lettura**: non solleva, ritorna
  `NULL` su offerta inesistente.
- Nessuna modifica a `vendite.ordini_righe`, nessuna selezione righe: il 1:1 di
  testata rende l'offerta atomica (§4).

## 4. Il «perché» del modello — offerta 1:1 *strutturale e permanente*

> Da riportare anche in doc divulgativa. Per l'offerta **non** si prevede alcuna
> evoluzione verso 1:N: è la natura dell'oggetto.

L'offerta commerciale **non ha righe materializzate**: le sue righe "effettive"
sono *calcolate al volo* da `fn_offerta_righe_espanse` (intero listino +
variazione + eccezioni OVERRIDE/ESCLUSIONE/AGGIUNTA — vedi
[analisi-ordini-vendita.md §7.4](../work-in-progress/analisi-ordini-vendita.md)). L'offerta non è un
carrello di articoli da pescare uno alla volta: è **una proposta commerciale
unica** ("ecco le condizioni che ti propongo, in blocco").

Conseguenze che si rafforzano:

1. **Non c'è un'identità di riga stabile** su cui ancorare un eventuale "questa
   riga è già stata ordinata". Lo split per riga sull'offerta sarebbe
   semanticamente forzato e tecnicamente fragile.
2. È la stessa natura per cui **offerta → contratto è 1:1**
   ([analisi-offerta-commerciale.md §5.1](analisi-offerta-commerciale.md)):
   l'offerta è *"una singola condizione quadro"*, atomica. Lì il 1:N è stato
   scartato perché introdurrebbe stati di "esecuzione parziale" e una macchina a
   stati dedicata.

→ Per l'offerta **1:1 non è un cerotto: è la natura dell'oggetto**. Chi vuole "6
caldaie ora e 4 dopo" fa **due offerte**; chi vuole articoli diversi su ordini
diversi fa **offerte diverse**. Spacchettare un'offerta su più ordini non avrà
mai senso.

**Reversal di A1 (solo OFFERTA)**: l'indice §2.1 inverte, per la sola origine
`OFFERTA`, la scelta A1 "documento_origine senza UNIQUE". Voluto e ratificato
(Tid, 2026-06-07). `PREVENTIVO` non è toccato qui (modello diverso → brief
dedicato). L'agente BE aggiornerà [analisi-ordini-vendita.md §1.bis](../work-in-progress/analisi-ordini-vendita.md)
con l'addendum (non competenza del team DB).

## 5. Pulizia dati preesistenti (PRE-migration, obbligatoria)

Il bug è *già live*: nei DB di sviluppo/test ci sono **già** ordini duplicati con
la stessa `documento_origine = ('OFFERTA', id)`. Su quei DB la `CREATE UNIQUE
INDEX` **fallirebbe** (e farebbe fallire `make db-migrate` e la CI). I dati sono
**solo di test** → pulizia consentita (Tid, 2026-06-07: «soprattutto offerte
andate su ordini si può fare pulizia totale»).

**Detection**:

```sql
SELECT documento_origine_id, count(*) AS n_ordini
  FROM vendite.ordini
 WHERE documento_origine_tipo = 'OFFERTA'
 GROUP BY documento_origine_id
HAVING count(*) > 1
 ORDER BY n_ordini DESC;
```

**Cleanup** — dati test, due opzioni a scelta del team DB:

- **(a) Dedup**: tenere l'ordine più vecchio per ogni offerta, eliminare i
  successivi (eliminando prima le righe figlie `ordini_righe_componenti` /
  `ordini_righe` per via di FK e trigger di storicizzazione).
- **(b) Pulizia totale**: eliminare tutti gli ordini con `documento_origine_tipo
  = 'OFFERTA'` e relative righe, ripartendo pulito.

> One-off documentato, **non** changeSet versionato: da eseguire manualmente
> prima del `make db-migrate` sui DB già usati. Su DB fresco (CI) non serve.

## 6. Test pgTAP (suggeriti)

Estendere la suite di `fn_available_actions_offerta`:

- offerta `ACCETTATA` **senza** ordine → `available_actions` contiene
  `genera_ordine`, `can_genera_ordine = true`, `_reason IS NULL`.
- offerta `ACCETTATA` **con** ordine `('OFFERTA', id)` → `genera_ordine`
  **assente**, `can_genera_ordine = false`, `_reason = 'OFFERTA_ORDINE_GIA_GENERATO'`.
- offerta non `ACCETTATA` → `can_genera_ordine = false`,
  `_reason = 'OFFERTA_NON_ACCETTATA'`.

Più test sull'indice §2.1:

- due `vendite.ordini` con `('OFFERTA', X)` → il secondo INSERT viola
  `uq_ordini_v_documento_origine_offerta`.
- due con `('PREVENTIVO', Y)` → **consentiti** (l'indice non li vincola).
- due ordini nativi (`documento_origine_tipo IS NULL`) → **consentiti**.

## 7. Integrazione lato BE/FE (post-consegna — competenza agente BE)

Dopo che indice + fn sono su `dev/db-tid`, l'agente BE cabla (additivo):

- **BE guard** in `crea_ordine_da_offerta`
  ([ordini_service.py](../../../../backend/apps/vendite/services/ordini_service.py)):
  nuovo metodo `OrdiniRepository.get_ordine_by_documento_origine('OFFERTA', id)`
  (oggi **non esiste**: esistono `set_documento_origine` e `delete_ordine`) +
  `ErrorManager.require(... is None ...)` → nuovo codice
  `E_ORD_OFFERTA_GIA_CONVERTITA` (409) registrato in
  [error_policies.py](../../../../backend/apps/core/services/error_policies.py) +
  [messaggi_errore.csv](../../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv).
  Mappare anche la violazione dell'UNIQUE §2.1 allo stesso codice nel blocco
  `_db_errors` (rete per la race). `set_documento_origine` resta dentro la stessa
  `transaction.atomic()` (oggi lo è) → il perdente di una race fa rollback completo.
- **FE data-driven**: `OffertaDrawer.vue` smette di costruire l'azione
  `genera-ordine` da `stato === ACCETTATA` hardcoded e la prende da
  `available_actions` (come già fa per `push_contratto`), così sparisce a
  conversione avvenuta. Dialog parlante su `E_ORD_OFFERTA_GIA_CONVERTITA` con
  deep-link all'ordine esistente (mirror del dialog
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`).
- **i18n**: `vendite.offerte.azione_genera_ordine` **esiste già** (verificato);
  aggiungere `offerte.push_reason.ordine_gia_generato` ("Un ordine è già stato
  generato da questa offerta."). `offerte.push_reason.non_accettata` esiste già.

## 8. Sequenza (team DB)

1. **Pulizia dati preesistenti** §5 (one-off, prima di tutto, sui DB già usati).
2. Indice UNIQUE parziale §2.1. Migration nuova, numerazione successiva.
3. `script.fn_available_actions_offerta` — nuova migration `update-fn-...`
   (`runOnChange: true`) con azione + flag `can_genera_ordine*` §2.2 (precedente
   reale: `20260528-02-update-fn-available-actions-preventivo-add-hardcoded-actions`;
   il corpo va ripetuto per intero, il docstring del `create-...` originale
   resta storico → rigenerare il doc auto-gen dopo il merge).
4. Test pgTAP §6.
5. Verifica `make db-migrate` locale.
6. Push su `dev/db-tid` + PR verso `Tito-dev`.

I punti 2-3 sono indipendenti; il cablaggio BE/FE §7 è **bloccato** finché
entrambi non sono su `dev/db-tid`.

## 9. Stato avanzamento (agg. 2026-06-08)

### ✅ Fatto (DB)

| # | Artefatto | Note |
| --- | --- | --- |
| 1 | Pulizia dati test | Duplicato reale rimosso: offerta 84 aveva 2 ordini (ORD0000046/47, id 55+56), tenuto il più vecchio. SQL one-off (no changeSet) — vedi §5 e nota sotto. |
| 2 | `00_schema/vendite/20260607-07-create-uq-ordini-documento-origine-offerta-mctit.yaml` | Indice UNIQUE parziale `uq_ordini_v_documento_origine_offerta` + rollback. |
| 3 | `20_code/script/20260607-08-update-fn-available-actions-offerta-genera-ordine-mctit.yaml` | `runOnChange`, CREATE OR REPLACE fn con azione `genera_ordine` + flag `can_genera_ordine*`. |
| 4 | `db/pgtap/script/test-fn-available-actions-offerta-v1.sql` | Esteso a `plan(15)`: test 8 corretto + 11-15 (fn + indice). |
| 5 | `make db-migrate` + pgTAP | **15/15 verde** (eseguito dall'utente: l'agente non è autorizzato all'applicazione DB). |

### ⚠️ Correzioni emerse durante la consegna (non previste nel brief originale)

- **Pulizia bloccata dal guard trigger**: la `DELETE` semplice sull'ordine
  fallisce perché la cascata su `ordini_righe` è bloccata da
  `trgfn_dlt_block_ordrig_ddtrig` (`E_DELETE_NOT_ALLOWED`). La pulizia corretta
  disabilita i trigger utente della sola `ordini_righe`
  (`ALTER TABLE vendite.ordini_righe DISABLE TRIGGER USER` … `ENABLE`) dentro la
  transazione. Colonne figlie: `ordini_righe_componenti.riga_ordine_id`,
  `ordini_righe_fulfillment.ordine_riga_id` (FK RESTRICT → eliminare prima),
  `note_ordini.target_id`, `ordini_indirizzi.ordine_id`.
- **Conseguenza sul test 8 esistente**: ACCT-2 (ACCETTATA + contratto) ora espone
  `genera_ordine` (non ha ordini) → l'assert `available_actions = []` non vale
  più; il test verifica ora che `push_contratto` sia **assente** (mantenendo
  `can_push_contratto=false` + reason).
- **pgTAP `throws_ok`**: per verificare solo lo SQLSTATE serve la forma a 4
  argomenti `throws_ok(sql, '23505', NULL, descrizione)` (con 3 arg il terzo è
  interpretato come messaggio atteso).

### ✅ Fatto (cablaggio BE/FE — 2026-06-08)

| # | Artefatto | Note |
| --- | --- | --- |
| 1 | `OrdiniRepository.get_ordine_by_documento_origine(tipo, id)` | Nuovo metodo (SELECT id+numero, `ORDER BY id LIMIT 1`). |
| 2 | `ordini_service.crea_ordine_da_offerta` | Guard fail-fast `E_ORD_OFFERTA_GIA_CONVERTITA` dopo il check `ACCETTATA`, prima dell'espansione righe. `repo` unificato (una sola istanza). |
| 3 | `ordini_service._UNIQUE_CONSTRAINTS` | Map `uq_ordini_v_documento_origine_offerta` → `E_ORD_OFFERTA_GIA_CONVERTITA` (rete sulla race, via `map_integrity_error` in `_db_errors`). |
| 4 | `error_policies.py` | Registrato `E_ORD_OFFERTA_GIA_CONVERTITA` (409, `show_error_banner`). |
| 5 | `OffertaDrawer.vue` | Azione `genera_ordine` **data-driven** da `available_actions` (rimosso il bottone hardcoded `stato===ACCETTATA` + import `STATO_OFFERTA`); confirm via `confirmAction` (`requires_confirm`); `refreshDetail()` post-successo → il bottone sparisce. |
| 6 | i18n `it.json`/`en.json` | `vendite.offerte.genera_ordine_titolo`/`_messaggio`/`_conferma` per il confirm. |
| 7 | Doc API | `api_ordini.md` (modello univocità + tabella errori) e `api_offerte.md` (endpoint genera-ordine + capability blob `can_genera_ordine*`). |
| 8 | Test | BE `test_ordini_service` 28/28 (+ caso «già convertita»), `apps.core.tests` 579/579; FE ESLint pulito + `vite build` ok. |

### ℹ️ Divergenze consapevoli dal §7 (annotate)

- **`messaggi_errore.csv` non toccato**: `E_ORD_OFFERTA_GIA_CONVERTITA` è
  **sollevato dal BE** (`ErrorManager` + `map_integrity_error`), non da un RAISE
  di trigger DB. Quella tabella serve solo ai codici emessi dal DB → nessuna riga
  necessaria. `user_message` parlante vive in `error_policies.py`.
- **Dialog deep-link → ordine esistente non implementato** (semplificato a toast
  parlante). Il caso normale è già coperto dalla guard data-driven (il bottone
  sparisce). Resta solo la **race cross-tab**, in cui il 409
  `E_ORD_OFFERTA_GIA_CONVERTITA` viene mostrato come toast con `user_message`.
  Il mirror completo del dialog `gia_generato` richiederebbe di esporre il link
  all'ordine sul dettaglio offerta (LEFT JOIN `vendite.ordini` su
  `documento_origine`, gemello di `contratto_id`): **follow-up opzionale** se si
  vuole simmetria piena con `push_contratto`.

---

*Brief DB — univocità offerta→ordine (1:1 permanente) + azione `genera_ordine`
data-driven. **CHIUSO 2026-06-08**: DB (pgTAP 15/15) + BE/FE cablati e verdi. Il
caso preventivo è in [brief-preventivi-ordini.md](../work-in-progress/brief-preventivi-ordini.md).*
