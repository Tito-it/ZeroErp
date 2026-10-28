# Analisi refactor frontend anagrafiche

<!-- markdownlint-disable MD036 MD031 -->

> Obiettivo: identificare cosa nei drawer/store anagrafiche e' logica di dominio
> mascherata da codice di presentazione, e quindi va spostata su backend/DB
> (filosofia DB-first: il frontend e' solo presentazione + UX).
>
> L'analisi distingue tre categorie:
> A. Da spostare davvero (logica di business in JS)
> B. Casi controversi (sfumature, UX defense-in-depth, refactor di pulizia)
> C. Bug logici di modello (incoerenze tra componenti causate da ambiguita' del dominio)

---

## A. Logica di business da spostare a backend/DB

### A1. API contract: ruoli JSONB normalizzato a valle (PRIORITA' ALTA, quick win)

- `frontend/src/anagrafiche/stores/soggetti.js:70`
- `frontend/src/core/components/SoggettoResolver.vue:52`

Entrambi i punti fanno la stessa cosa: il backend ritorna `ruoli` come stringa
JSON (a volte) invece che come array. Il frontend e' costretto a fare
`JSON.parse` con try/catch.

E' un **bug del contratto API**, non del frontend. La fix sta nel
serializer/repository backend: la colonna JSONB va sempre castata e serializzata
come array JSON. Una volta sistemato il backend, le due normalizzazioni nel
frontend spariscono.

### A2. Normalizzazioni payload pagamento/fiscali (PRIORITA' ALTA)

- `frontend/src/anagrafiche/components/ClienteDrawer.vue:286`

  ```js
  nr_giorni_scadenza: ['G', 'F'].includes(f.tipo_gg_scadenza_ft) ? (f.nr_giorni_scadenza || 0) : null
  ```

  Regola: "se il tipo scadenza non e' G o F, i giorni scadenza non hanno senso
  → NULL".

- `frontend/src/anagrafiche/components/FornitoreDrawer.vue:135`

  ```js
  ritenuta_aliquota: f.ritenuta_acconto ? f.ritenuta_aliquota : null
  ```

  Regola: "se non c'e' ritenuta, l'aliquota va a NULL".

Sono regole di dominio (pagamenti / fiscalita' fornitore) replicate in JS. Vanno
applicate nei service backend (`clienti_service`, `fornitori_service`) e
idealmente da trigger DB di consistenza, esattamente come gia' fatto per
contratti / promo articoli (ref: pattern data-driven cessazione).
Il pre-clean frontend e' duplicazione che drifta non appena la regola
backend cambia.

### A3. Default tipo soggetto cablato in JS (PRIORITA' ALTA)

- `frontend/src/core/components/SoggettoResolver.vue:80`

  ```js
  const privato = dettagli.find(d => d.codice_interno === 'PR')
  return privato ? privato.id : dettagli[0].id
  ```

La scelta "default privato" e' una decisione di dominio cablata nel componente.
Va esposta come campo nella response di `getConfigResolver`:

```json
{
  "tipi_soggetto_dettaglio": [...],
  "nature_ammesse": [...],
  "default_tipo_soggetto_id": 42
}
```

Senza questo, cambiare la policy richiede deploy frontend.

### A4. Stato operativo cliente calcolato lato Vue (PRIORITA' MEDIA)

- `frontend/src/anagrafiche/components/ClienteDrawer.vue:367`

  ```js
  return sosp > riatt
    ? { label: t('clienti.col_sospeso_il'), date: sosp }
    : { label: t('clienti.col_riattivato_il'), date: riatt }
  ```

Lo "stato corrente" (sospeso vs riattivato) e' un calcolo di dominio. Il pattern
gia' adottato per cessazione data-driven (contratti, listini-versioni, promo
articoli — vedi work-done) prevede che il backend esponga sul detail:

- `evento_stato_corrente` (es. `SOSPESO`, `ATTIVO`)
- `data_evento_stato`
- `tipo_evento_stato`

Il frontend si limita a mostrare i campi gia' risolti.

### A5. Config-resolver da arricchire (mancante nel doc originale)

`getConfigResolver(tipoRuolo)` oggi ritorna `tipi_soggetto_dettaglio` e
`nature_ammesse`. E' insufficiente: il frontend deve cablare ulteriori scelte
(default tipo, soglia min_search_length = 3, ecc.). Aggiungere all'API:

- `default_tipo_soggetto_id` (vedi A3)
- `min_search_length` (oggi cablato a 3 in `SoggettoResolver:41`)
- eventualmente `editable_in_edit` (vedi B3)

---

## B. Casi controversi (sfumature, refactor di pulizia)

### B1. Filtro nature_ammesse e marker ruolo duplicato (refactor cosmetico)

- `frontend/src/core/components/SoggettoResolver.vue:50`

Il dato `nature_ammesse` arriva gia' dal backend (config-resolver). Il frontend
lo usa per **decorare visivamente** la lista (icona ban, opacity 50%, warning
ruolo gia' presente).

**Non viola la filosofia DB-first**: e' presentation che si appoggia a dati
backend. La proposta architetturalmente piu' pulita ("API ritorna `selectable` +
`reason` per ogni hit") e' migliore ma richiede di rendere
`listSoggetti` role-aware. Refactor di pulizia, non di principio. Bassa
priorita'.

L'unico vero problema in questo punto e' la **duplicazione** della
normalizzazione `ruoli`, che si risolve da sola con A1.

### B2. canSave (categoria + admin globale) — DEFENSE-IN-DEPTH, NON DUPLICAZIONE

- `frontend/src/anagrafiche/components/ClienteDrawer.vue:355`

Qui l'analisi originale e' troppo aggressiva. Sono due cose diverse:

- `ba_categoria_cliente_id` obbligatoria in create: e' **validazione UX** che
  disabilita il pulsante. Il backend valida comunque. Il commento del file lo
  dichiara: "F3-FE-04: categoria cliente obbligatoria in creazione".
- `auth.isAdminGlobale` blocca save: e' UX guard su un'autorizzazione che il
  backend rifiuta gia' (guard service + trigger DB). Il commento lo dichiara
  esplicitamente: "defense-in-depth UI: il guard backend e il trigger DB sono
  comunque la difesa primaria".

**Non e' un punto da spostare**. E' UX legittima e va mantenuta. Spostarla
significherebbe far diventare il pulsante salvabile finche' la chiamata API non
torna errore, peggiorando l'esperienza utente per zero guadagno
architetturale.

### B3. Mutabilita' tipo soggetto in edit (refactor opzionale)

- `frontend/src/core/components/SoggettoForm.vue:42`

La regola "in edit puoi cambiare tipo soggetto solo verso la stessa
`natura_soggetto`" e' un invariante di dominio probabilmente gia' enforciato da
trigger DB. Il pre-filtro frontend e' UX corretta MA duplica la regola
silenziosamente.

Due strade:

- Pulita: backend espone, sul detail soggetto, l'array `tipi_modificabili`. Il
  frontend filtra con quello (no duplicazione regola).
- Pragmatica: rimuovi il filtro, lascia che il backend rifiuti. Costo UX:
  l'utente scopre il vincolo solo al salvataggio.

Non urgente. Se lasci il pre-filtro, almeno aggiungi un commento che cita il
trigger DB di riferimento per evitare drift silenziosi.

### B4. Immutabilita' CF/PIVA in edit (mancante nel doc originale)

- `frontend/src/core/components/SoggettoForm.vue:39-40`

  ```js
  const cfDisabled = computed(() => props.isEdit && !!props.form.codice_fiscale?.trim())
  const pivaDisabled = computed(() => props.isEdit && !!props.form.partita_iva?.trim())
  ```

Stessa natura di B3: regola di immutabilita' di dominio (analoga a Profilo A
contratti) cablata in JS. Andrebbe esposta come metadata
`editable_fields` dal backend, almeno per uniformita' con il pattern di
immutabilita' adottato altrove. Bassa priorita'.

---

## C. Bug logici di modello (priorita' MASSIMA — non e' "solo frontend")

### C1. Definizione di "contatto compilato" incoerente tra i drawer anagrafiche

**Stato verificato sul codice (3 drawer + 1 caso a parte)**:

| Drawer | Riga | Regola attuale | Diagnosi |
| --- | --- | --- | --- |
| ClienteDrawer | `:313-320` | "qualunque campo valorizzato → contatto in compilazione" | OK (regola A) |
| FornitoreDrawer | `:162` | "solo `nominativo` conta" | Bug: scarta dati silenziosamente |
| SoggettoDrawer | `:292` | Invia SEMPRE `contatto: {...}` nel payload | Funziona "per caso" grazie all'auto-fill nominativo |
| ContattiSoggettoDrawer | (drawer dedicato) | Entry esplicita "Aggiungi contatto" | OK, non e' caso ambiguo |

**Conseguenza pratica del bug Fornitore**: se l'utente scrive solo l'email
del contatto e clicca Salva, l'email viene scartata senza alcun avviso.
Sul Cliente la stessa azione produce una validazione che chiede i campi
obbligatori mancanti. Tre drawer fratelli, tre comportamenti diversi.

Il composable `frontend/src/core/composables/useContattoForm.js` esiste gia'
ed e' usato da tutti e quattro i drawer, MA non espone la regola "il contatto
e' vuoto / parziale / valido". Ogni drawer la reinventa nella sua `onSave()`.

Non e' "incoerenza frontend": e' **ambiguita' del modello dominio**. Nessuno ha
definito cosa significa "l'utente ha iniziato a compilare un contatto".

#### Decisione (confermata)

Regola canonica: **versione Cliente**. Se almeno un campo
(`nominativo`, `tipo_contatto_id`, `email`, `telefono`, `cellulare`, `pec`) e'
valorizzato → il contatto e' in compilazione → richiede gli obbligatori
(`nominativo` + `tipo_contatto_id`).

Implementazione: pattern A + A2 (defense-in-depth).

#### Piano implementativo

**Backend — nuovo metodo classificatore in `apps/anagrafiche/services/contatti_service.py`**

```python
def classify_contatto_payload(data) -> str:
    """Ritorna 'EMPTY' | 'PARTIAL' | 'VALID'."""
```

Regola:

- `EMPTY` = tutti i campi (`nominativo`, `email`, `telefono`, `cellulare`,
  `pec`, `tipo_contatto_id`) sono `None` o stringa vuota
- `PARTIAL` = almeno un campo valorizzato MA mancano `nominativo` o
  `tipo_contatto_id`
- `VALID` = `nominativo` + `tipo_contatto_id` presenti + email/pec con
  formato valido (se compilati)

Le API che ricevono un contatto inline (create cliente, fornitore, soggetto)
applicano la classificazione:

- `EMPTY` → ignora il blocco contatto, non crearlo (no errore)
- `PARTIAL` → ritorna errore strutturato (es. `code: CONTATTO_INCOMPLETO`,
  `missing: ["nominativo", "tipo_contatto_id"]`)
- `VALID` → crea il contatto

**Frontend — estendere `useContattoForm`**

Aggiungere al composable:

```js
function classify()  // 'EMPTY' | 'PARTIAL' | 'VALID'
function isEmpty()
function isFilled()  // !isEmpty()
```

Stessa regola del backend. Serve per UX immediata (disabilita Salva, mostra
errori) — il backend resta la verita' unica.

**Aggiornare i 3 drawer**:

- ClienteDrawer: sostituire `hasAnyContatto` (inline) con `contatto.isFilled()`
- FornitoreDrawer: stesso, si allinea automaticamente alla regola corretta
- SoggettoDrawer: prima di includere `contatto: {...}` nel payload, verificare
  `contatto.isFilled()`. Se `isEmpty()`, non includere affatto il blocco
  contatto

**Bonus UX**: aggiungere in tutti e tre i drawer un pulsantino "pulisci
contatto" (icona x) per svuotare la sezione contatto senza perdere il resto
del form. Necessario perche' con la regola A "qualunque campo" e' facile
attivare per sbaglio la sezione contatto.

#### Perche' A + A2 e non solo A

La regola scritta solo nel composable frontend si dimentica appena un nuovo
endpoint backend riceve un payload contatto (es. import massivo, API esterna).
Scriverla nel service backend la rende patrimonio del dominio: qualunque
ingresso di dati viene classificato in modo coerente.

---

## Priorita' di refactor (ordine concentrico)

1. **A1** — Fix API contract `ruoli` JSONB. Quick win, elimina due punti di
   duplicazione frontend in un colpo solo.
2. **A2** — Normalizzazioni payload (`nr_giorni_scadenza`, `ritenuta_aliquota`)
   nei service backend + trigger DB di consistenza.
3. **A3 + A5** — Arricchire la response `getConfigResolver`
   (`default_tipo_soggetto_id`, `min_search_length`, ecc.) e rimuovere i
   cablati frontend.
4. **A4** — Stato corrente cliente esposto dal detail backend
   (`evento_stato_corrente`, `data_evento_stato`).
5. **C1** — Decidere e centralizzare la regola "contatto compilato" (bug
   logico modello: priorita' massima sul piano architetturale, anche se
   tecnicamente "piccolo").
6. **B3** — Mutabilita' tipo soggetto: refactor opzionale, basso valore se
   trigger DB c'e' gia'.
7. **B4** — Immutabilita' CF/PIVA come metadata: refactor di pulizia, basso
   valore.
8. **B1** — Marker resolver: refactor cosmetico, valore bassissimo.

**Da NON spostare**: B2 (`canSave`). E' UX defense-in-depth corretta. Toccarla
peggiora l'esperienza utente per zero guadagno architetturale.

---

## Nota di metodo

Tre punti del documento originale — A2 (#4 e #7 della lista vecchia), A4 (#6),
A3 (#2) — sono esattamente lo stesso pattern gia' applicato con successo su
contratti / listini-versioni / promo articoli (cessazione data-driven, vedi
`work-done/`). Riusare lo stesso schema:

- backend espone fields gia' risolti (stato corrente, data evento, default
  configurazione)
- service normalizza il payload coerentemente
- trigger DB enforcing l'invariante

evita di reinventare la ruota e mantiene coerenza tra domini.

---

## D. Piano di sviluppo (suddivisione DB / Backend / Frontend)

> Ordine di esecuzione: concentrico bottom-up. Per ogni fase si parte dal DB
> (trigger/viste/funzioni), poi il backend Django (service/API), infine il
> frontend (rimozione duplicazioni). Le azioni DB sono di competenza del team
> DB su `dev/db-tid` — il backend agent NON esegue DDL/trigger/migrations.

### Fase 1 — Fix API contract `ruoli` JSONB (A1, quick win) — **LANDED 2026-04-27**

> **Stato**: chiusa BE+FE il 2026-04-27. DB nessuna modifica (caso A).

**DB (`dev/db-tid`)** — CHIUSO (caso A): nessuna modifica

- Verificato 2026-04-27: la lista `ruoli` non passa per una vista o funzione
  DB dedicata. E' costruita in SQL inline dal repository soggetti
  ([`soggetti_repository.py:51-97`](../../../../backend/apps/anagrafiche/db/soggetti_repository.py))
  tramite `(SELECT COALESCE(jsonb_agg(jsonb_build_object(...) ORDER BY ...),
  '[]'::jsonb) FROM anagrafiche.soggetti_ruoli sr ...) AS ruoli`. Il DB
  ritorna gia' un valore `jsonb` ben formato con shape
  `[{soggetto_ruolo_id, codice, descrizione}, ...]`.
- Causa del bug: il driver psycopg in alcune configurazioni ritorna `jsonb`
  come stringa Python invece che dict/list (cfr. commento in
  [`auth_helpers.py:70`](../../../../backend/apps/core/services/auth_helpers.py)
  e helper esistente
  [`email_repository._parse_jsonb_field`](../../../../backend/apps/core/db/email_repository.py)).
- Nessun DDL/trigger/funzione DB richiesta.

**Backend Django**

- In `apps/anagrafiche/db/soggetti_repository.py::list_soggetti()`, dopo
  `extract_paginated(cursor)`, parsare il campo `ruoli` se arriva come
  stringa: `if isinstance(r["ruoli"], str): r["ruoli"] = json.loads(...)`.
  Pattern gia' usato in `email_repository._parse_jsonb_field()`.
- Aggiungere test API che verifichi il tipo della risposta
  (`isinstance(data["ruoli"], list)`).
- (Nota futura, fuori scope A1): valutare promozione di `_parse_jsonb_field`
  da `email_repository` a `apps/core/db/_helpers.py` come helper condiviso
  per tutti i repository che restituiscono campi `jsonb` aggregati.

  > ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_parse_jsonb_field` è ritirato. I lettori a dizionari di `apps/core/db/_helpers.py` decodificano da soli le colonne jsonb, dal tipo che il cursore dichiara; le letture per posizione usano `jsonb_out`.


**Frontend**

- Rimuovere normalizzazioni in `stores/soggetti.js:70` e
  `SoggettoResolver.vue:52`. Solo dopo che backend e' a posto.

**Dipendenze**: nessuna verso altre fasi. Si chiude da sola.

---

### Fase 2 — Normalizzazioni payload pagamento/fiscali (A2) — **LANDED 2026-04-27**

> **Stato**: chiusa end-to-end (DB + BE + FE) il 2026-04-27.
> Documento finale: [`work-done/brief-be-clienti-fornitori-normalize-payload.md`](../work-done/brief-be-clienti-fornitori-normalize-payload.md)
>
> **Q&A 2026-04-27 con team DB chiusa**: fornitori gia' coperto dal
> trigger esistente `trgfn_fornitori_guard_normalize` (clausola 4); su
> clienti decise simmetria + backfill + default + CHECK dominio. Brief
> aggiornato qui sotto.

**DB (`dev/db-tid` — brief aggiornato)**

- **Fornitori**: nessuna nuova migration. La regola
  "`ritenuta_acconto = false` → `ritenuta_aliquota = NULL`" e' gia' applicata
  da `trgfn_fornitori_guard_normalize` (clausola 4) e c'e' anche il guard
  simmetrico "se `acconto=true` allora `aliquota > 0`" → solleva
  `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA`. Pattern di riferimento.
- **Clienti — package unico in unica migration**:

  1. Backfill record esistenti incoerenti:

     ```sql
     UPDATE anagrafiche.clienti
        SET nr_giorni_scadenza = NULL
      WHERE tipo_gg_scadenza_ft NOT IN ('G','F')
        AND nr_giorni_scadenza IS NOT NULL;
     ```

     (coerente col principio "ZeroErp non in produzione → niente compat")

  2. Cambio default colonna:

     ```sql
     ALTER TABLE anagrafiche.clienti
       ALTER COLUMN nr_giorni_scadenza DROP DEFAULT;
     ```

     (il default `0` diventa misleading; preferenza al default `NULL`
     implicito).

  3. CHECK constraint dominio `tipo_gg_scadenza_ft` (valori ammessi
     `G`/`M`/`F`/`N` come da baseline):

     ```sql
     ALTER TABLE anagrafiche.clienti
       ADD CONSTRAINT chk_clienti_tipo_gg_scadenza_ft
       CHECK (tipo_gg_scadenza_ft IN ('G','M','F','N'));
     ```

  4. Trigger `trgfn_clienti_normalize_giorni_scadenza` (analogo a
     `trgfn_fornitori_guard_normalize`, simmetrico):

     - se `tipo_gg_scadenza_ft NOT IN ('G','F')` → `nr_giorni_scadenza := NULL`
     - se `tipo_gg_scadenza_ft IN ('G','F')` AND
       `(nr_giorni_scadenza IS NULL OR <= 0)` → solleva
       `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` via
       `script.fn_log_and_raise_error(...)`

  5. Trigger declaration:
     `trg_clienti_normalize_giorni_scadenza_ins_upd BEFORE INSERT OR UPDATE`
     (no prefisso `_a10_`, nome allineato a stile fornitori).

- Test pgTAP per il trigger clienti:
  - `('G', 30)` → ammesso
  - `('F', 60)` → ammesso
  - `('N', 5)` → normalizzato a `('N', NULL)`
  - `('M', 10)` → normalizzato a `('M', NULL)`
  - `('G', NULL)` → solleva `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`
  - `('G', 0)` → solleva `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`
  - `('X', 5)` → fallisce CHECK `chk_clienti_tipo_gg_scadenza_ft`
  - Backfill: verifica post-migration che record legacy siano normalizzati.

**Backend Django**

- Aggiungere mapping `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` in
  `apps/core/services/error_policies.py` (HTTP 422 + azione UI = mostra
  errore campo).
- `apps/anagrafiche/services/clienti_service.py`: NON duplicare la
  normalizzazione (il trigger e' la verita'). Eventuale guard applicativo
  minimale solo se serve early-return prima dell'INSERT.
- Test API: payload `('N', 5)` → 200 con riga `('N', NULL)` letta back;
  payload `('G', NULL)` → 422 `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`.

**Frontend**

- `ClienteDrawer.vue:286` — rimuovere il pre-clean
  `nr_giorni_scadenza: ['G','F'].includes(...) ? ... : null`. Inviare il
  valore raw, il trigger normalizza.
- `FornitoreDrawer.vue:135` — rimuovere il pre-clean
  `ritenuta_aliquota: f.ritenuta_acconto ? ... : null`. Il trigger esistente
  normalizza.
- Gestire UX feedback per nuovo errore `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`
  (highlight campo `nr_giorni_scadenza` con messaggio i18n).

**Dipendenze**: trigger DB landed PRIMA del backend (mapping error_policies)
PRIMA del frontend (rimozione pre-clean).

---

### Fase 3 — Config-resolver arricchito (A3 + A5) — **LANDED 2026-04-27**

> **Stato**: chiusa end-to-end (DB seed+guard + BE arricchimento +
> FE rimozione cablato) il 2026-04-27.
>
> **Q&A 2026-04-27 con team DB chiusa**: scartate opzioni A (is_default
> colonna su `tipi_soggetto_dettaglio`, troppo rigida con multi-ruolo) e C
> (mini-tabella dedicata, perde override gratuito). Scelta finale:
> **opzione B** = `config.parameters` con chiave per ruolo, coerente con
> pattern `DEFAULT_IVA_ID` gia' usato.

#### Inventario punti di lettura (verificato 2026-04-27)

| Ruolo | Dove | Cablato attuale |
| --- | --- | --- |
| `CL` (cliente) | `ClientiSearchTable.vue:124`, `ClienteDrawer.vue:623+633+645` | `PR` (privato) |
| `FO` (fornitore) | `FornitoreDrawer.vue:407+414` | `PR` (privato) |
| Futuri | `EF`, `OP`, `RV` | — |

Numero entry attese: oggi 2, mai oltre 5-6. Override per emittente
(B2B vs B2C) prevedibile entro 6-12 mesi.

**Caso d'uso**: prefill UI (NON validator backend). Quando l'utente clicca
"Crea nuovo soggetto" da SoggettoResolver, il SoggettoDrawer viene aperto
con `tipoDefaultId` pre-selezionato. L'utente puo' cambiarlo.

**DB (`dev/db-tid` — brief, opzione B definitiva)**

- Seed in `config.parameters`:

  ```sql
  INSERT INTO config.parameters (code, default_value, ...) VALUES
    ('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', 'PR', ...),
    ('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO', 'PR', ...);
  ```

  Entrambi `'PR'` perche' e' il valore oggi cablato. Naming preciso:
  `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>` (vive sul `_dettaglio`, non sul
  padre `tipi_soggetto`).

- `default_value` e' un `codice_interno` (varchar stabile via
  `lock_columns`), non un id numerico. Pattern coerente con
  `feedback_no_hardcoded_ids.md`.

- Guard trigger
  `trgfn_parameters_guard_default_tipo_soggetto_dettaglio` che valida
  `default_value ∈ config.tipi_soggetto_dettaglio.codice_interno` quando
  `code LIKE 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'`. Sostituisce la FK
  mancante (codice errore custom es.
  `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID`).

- Test pgTAP:
  - Lookup `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL` → ritorna `'PR'`
  - Override su emittente specifico → ritorna valore override
  - INSERT con `default_value` non esistente in
    `tsd.codice_interno` → guard trigger raise
  - Suffisso `_<STATO>` non implementato oggi (variante futura
    `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>_<STATO>`).

**Backend Django**

- Modificare `apps/anagrafiche/db/soggetti_repository.py::get_config_resolver(tipo_ruolo_codice, emittente_fiscale_id=None)`:
  - aggiungere lookup `script.fn_get_parameter_full(
    'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_' || :ruolo, p_emittente_fiscale_id => :ctx)`
  - JOIN del risultato (`codice_interno`) su `config.tipi_soggetto_dettaglio`
    per risolvere id
  - se chiave assente o codice non matcha → `None` (no errore, fallback FE)
  - aggiungere campo `default_tipo_soggetto_dettaglio_id: int | None` al
    response
- View `views_ruoli_config.py`: passare `emittente_fiscale_id` dal request
  context (se esiste).
- Aggiungere `min_search_length: int = 3` nel response (per ora costante,
  futura parametrizzazione opzionale).
- Aggiornare test API:
  `isinstance(data["default_tipo_soggetto_dettaglio_id"], (int, type(None)))`.

**Frontend**

- `SoggettoResolver.vue:80`: rimuovere `find(d => d.codice_interno === 'PR')`.
  Usare:
  ```js
  return configResolver.value?.default_tipo_soggetto_dettaglio_id
    ?? dettagli[0]?.id  // fallback se backend ritorna null
    ?? null
  ```
- `SoggettoResolver.vue:41`: usare `configResolver.min_search_length || 3`.

**Dipendenze**: seed DB + guard trigger landed PRIMA del backend, backend
PRIMA del frontend.

---

### Fase 4 — Stato corrente cliente data-driven (A4) — **LANDED 2026-04-28**

> **Stato**: chiusa end-to-end (DB fn + BE LATERAL JOIN + FE rimozione computed) il 2026-04-28.
> Documento finale: [`work-done/brief-be-cliente-evento-stato-corrente.md`](../work-done/brief-be-cliente-evento-stato-corrente.md)

**DB (`dev/db-tid` — brief obbligatorio al team DB)**

- Funzione `anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id)`
  che ritorna `(evento_stato_corrente, data_evento_stato, tipo_evento)`
  confrontando `data_sospensione` e `data_riattivazione`. Pattern gia' usato
  per contratti/listini/promo articoli — riprendere lo stesso schema.
- Eventuale vista `vw_clienti_con_stato_corrente` se semplifica il join.
- Test pgTAP che coprano i 4 casi: nessuna data, solo sospensione, solo
  riattivazione, entrambe (con sosp > riatt e sosp < riatt).

**Backend Django**

- `clienti_service.fetch_detail()` include nel response i campi
  `evento_stato_corrente`, `data_evento_stato`, `tipo_evento_stato` letti
  dalla funzione/vista.
- Aggiornare API test del detail.

**Frontend**

- `ClienteDrawer.vue:367`: rimuovere `dataSospRiattDetail` (computed con
  logica `sosp > riatt`). Usare direttamente `detail.evento_stato_corrente` +
  `detail.data_evento_stato` nel template.

**Dipendenze**: DB → backend → frontend, in serie.

---

### Fase 5 — Regola contatto unificata (C1, bug logico modello) — **LANDED 2026-04-28**

> **Stato**: chiusa BE+FE 2026-04-28. DB nessuna modifica richiesta
> (decisione utente: lo schema ha gia' NOT NULL su `nominativo` e
> `tipo_contatto_id`, sufficiente come safety net DB).
> Documento finale: [`work-done/brief-be-classify-contatto-payload.md`](../work-done/brief-be-classify-contatto-payload.md)

**DB (`dev/db-tid`)**

- Nessuna modifica DDL richiesta. Eventuale CHECK constraint su
  `anagrafiche.contatti` per impedire inserimento di contatti con
  `nominativo NULL` e `tipo_contatto_id NULL` (se non gia' presente).

**Backend Django**

- Nuovo modulo `apps/anagrafiche/services/contatti_service.py` con funzione
  pura:
  ```python
  def classify_contatto_payload(data: dict) -> str:
      """Ritorna 'EMPTY' | 'PARTIAL' | 'VALID'."""
  ```
- Le views `cliente_create`, `fornitore_create`, `soggetto_create` chiamano
  la funzione:
  - `EMPTY` → ignora il blocco contatto
  - `PARTIAL` → `ServiceError('CONTATTO_INCOMPLETO', missing=[...])`
  - `VALID` → procede con `contatti_repository.create(...)`
- Mappare `CONTATTO_INCOMPLETO` in `apps/core/services/error_policies.py`
  (HTTP 422 + azione UI = mostra errori per campo).
- Unit test per i tre casi su tutti e tre gli endpoint.

**Frontend**

- Estendere `useContattoForm.js` con:
  ```js
  function classify()  // 'EMPTY' | 'PARTIAL' | 'VALID'
  function isEmpty()
  function isFilled()
  ```
  Stessa regola del backend (defense-in-depth UX).
- Aggiornare i 3 drawer:
  - `ClienteDrawer.vue:313` → `contatto.isFilled()`
  - `FornitoreDrawer.vue:162` → `contatto.isFilled()` (allineamento alla
    regola corretta)
  - `SoggettoDrawer.vue:292` → includere `contatto: {...}` nel payload solo
    se `contatto.isFilled()`
- Aggiungere pulsante "pulisci contatto" (icona x) nei drawer Cliente +
  Fornitore + Soggetto, vicino alla sezione contatto inline.

**Dipendenze**: backend PRIMA del frontend (il frontend deve gestire il nuovo
codice errore `CONTATTO_INCOMPLETO`). DB indipendente.

---

### Fase 6 — Refactor opzionali (B1, B3, B4) — **LANDED 2026-04-28**

> **Stato**: chiusa il 2026-04-28 dopo verifica che B1 era gia' risolto
> dai refactor precedenti (A1 normalize ruoli + A3 nature_ammesse
> data-driven). B3 e B4 implementati come unico passaggio sul detail
> soggetto.

**B3 — Mutabilita' tipo soggetto in edit** ✅ LANDED

- Backend: aggiunto `tipi_modificabili_ids: int[]` al `get_soggetto`
  via sub-query SQL `array_agg(...)` su `tipo_soggetto_id`. Frontend
  (`SoggettoForm`) filtra con questi id invece di ricostruire la regola
  `natura_soggetto` lato client. Fallback compat al vecchio filtro se
  il campo non e' popolato.

**B4 — Immutabilita' CF/PIVA in edit** ✅ LANDED

- Backend: aggiunto `non_editable_fields: str[]` al `get_soggetto` via
  helper `_compute_non_editable_fields()`. Lista cresce se in futuro
  altri campi diventano immutabili. Frontend: `cfDisabled` /
  `pivaDisabled` derivati da `nonEditableFields.includes(...)`.

**B1 — Marker resolver `_naturaBloccata`** ✅ NO-OP (gia' risolto)

- Verifica 2026-04-28: i marker FE (`_naturaBloccata`, `_ruoloDuplicato`)
  sono UX legittima che decora la lista resolver usando dati
  **gia' data-driven**:
  - `nature_ammesse` arriva dal config-resolver (Fase 3)
  - `ruoli` per ogni soggetto arriva normalizzato dal backend (Fase 1)
  Niente regola di business in JS. L'unico refactor possibile sarebbe
  rendere `listSoggetti` role-aware con `selectable`/`reason` calcolati
  server-side, ma e' refactor cosmetico senza cambio di filosofia.
  **Skipped**: il valore non giustifica il costo (nuovo parametro API,
  cambio contratto, refactor 2 punti). Documentato come
  "non-issue post Fase 1+3".

---

## E. Sintesi tabellare per priorita' e team

| Fase | Punti coperti | Team DB | Team Backend | Team Frontend | Priorita' |
| --- | --- | --- | --- | --- | --- |
| 1 | A1 | check viste/cast jsonb | check serializer + test | rimuovi 2 normalizzazioni | ALTA — **LANDED 27-04** |
| 2 | A2 | trigger clienti + pgTAP + backfill + DEFAULT + CHECK dominio | mapping policy errori | rimuovi pre-clean payload | ALTA — **LANDED 27-04** |
| 3 | A3 + A5 | seed config.parameters + guard trigger | arricchimento config-resolver API | usa nuovi campi response | ALTA — **LANDED 27-04** |
| 4 | A4 | funzione `fn_get_evento_stato_corrente_cliente` | LATERAL JOIN nel detail | rimuovi computed `dataSospRiatt` | MEDIA — **LANDED 28-04** |
| 5 | C1 | nessuna modifica | `classify_contatto_payload` + 3 service | estendi composable + drawer Cliente+Fornitore | ALTA (bug logico) — **LANDED 28-04** |
| 6 | B3 + B4 | nessuna | `tipi_modificabili_ids` + `non_editable_fields` su detail | usa metadata invece di cablati | BASSA — **LANDED 28-04** |
| 6 | B1 | nessuna | nessuna | nessuna | NO-OP (gia' risolto in Fase 1+3) |

**Da NON toccare**: B2 (`canSave`). E' UX defense-in-depth corretta. Spostarla
peggiora l'esperienza utente per zero guadagno architetturale.

---

## F. Epilogo (2026-04-28) — chiusura analisi

Analisi avviata 2026-04-27, chiusa 2026-04-28. Tutte le fasi A1-A5, C1,
B3, B4 implementate end-to-end (DB + BE + FE + test). B1 risolto
implicitamente dai refactor A1+A3 (no-op).

### Brief landed

Tutti in `docs/it/dev/work-done/`:

1. [brief-be-soggetti-ruoli-jsonb-fix.md] — Fase 1 (implicito nei modifiche
   `soggetti_repository.list_soggetti`, niente brief separato — cambio
   minimale)
2. [brief-be-clienti-fornitori-normalize-payload.md] — Fase 2
3. [brief-be-config-resolver-default-tipo-soggetto.md] — Fase 3
4. [brief-be-cliente-evento-stato-corrente.md] — Fase 4
5. [brief-be-classify-contatto-payload.md] — Fase 5

### Memorie pattern create

- [feedback_normalize_guard_simmetrico.md] — Fase 2 pattern (terza
  occorrenza)
- [feedback_classify_payload_three_state.md] — Fase 5 pattern nuovo

### Bilancio

- 6 fasi pianificate, 5 implementate + 1 no-op
- ~30 file modificati (BE + FE + test + doc)
- 3 nuove migration DB (Fase 2 trigger clienti, Fase 3 seed+guard, Fase 4 fn)
- 834/834 test verdi, 0 regressione
- 6 nuovi codici errore documentati (E_CONTATTO_INCOMPLETO, E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI, E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA, E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID, +)

### Pattern emersi (riusabili in futuri refactor)

- **classify EMPTY/PARTIAL/VALID** per payload inline opzionali (pattern A2)
- **normalize+guard simmetrico** per coppie `(flag/tipo, value)` con
  trigger DB (terza occorrenza)
- **stato corrente data-driven** via fn DB `(data, tipo)` per il
  consumer detail (quarta variante del pattern)
- **config.parameters override-ready** invece di colonne is_default
  (override gratuito per emittente)
- **defense-in-depth a 3 livelli** (DB trigger / BE service / FE composable
  mirror) come standard di progetto

### Cosa resta intenzionalmente fuori scope

- **B1 marker resolver**: refactor cosmetico senza valore aggiunto post
  Fase 1+3
- **B2 canSave**: UX defense-in-depth, mantenuta com'e'
- **Cambio default colonna `nr_giorni_scadenza`** post-backfill: chiuso
  in Fase 2

Documento spostato in `work-done/` a chiusura.
