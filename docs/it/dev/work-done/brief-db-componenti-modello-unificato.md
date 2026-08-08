# Brief DB — Modello unificato componenti BoM + simmetria listino

> **Data**: 2026-05-12 sera — **Applicato**: 2026-05-13
>
> **Branch**: `dev/db-tid`
>
> **Razionale e modello**: vedi [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md).
> Questo brief contiene SOLO le modifiche DB da applicare.
>
> **Stato**: ✅ MIGRATION FILES PRONTI — da committare e applicare.
> Migration 20260513-01..24 in `db/changelog/migrations_v2/`.
> Vedere §13 per ordine e file corrispondenti.
>
> **Pendente post-DB**: backfill manuale BoM IVA incoerenti e righe listino su compositi;
> BE aggiornare `pricing_repository.py` + `pricing_service.py` prima del DROP `fn_resolve_prezzo_composito`;
> BE aggiornare `fetch_pushable_rows` se tocca `esposto_in_fattura`;
> pgTAP suite da aggiornare per i 4 guard nuovi (§14 brief).

---

## Sintesi della transizione

| Aspetto | Stato prima | Stato dopo |
| --- | --- | --- |
| `esposto_in_fattura` | Gate di pricing (filtra figli da persistere) | Solo flag presentazione fattura |
| Padre composito | CASO A vs CASO B (due modi) | Sempre SUM(figli × coeff_qta) |
| CHECK `<> 0` su `*_righe_componenti` | Universale | Condizionale: obbligatori `<> 0`, opzionali liberi |
| CHECK `<> 0` su `*_righe` (padre) | Universale | Rilassato (somma figli puo' essere 0/negativa) |
| `articoli_componenti` `attivo` figli in init | Solo `esposto=TRUE` inseriti | Tutti i figli inseriti; obbligatori `attivo=TRUE`, opzionali `attivo=FALSE` |
| Listino su padre composito | Inesistente / non gestito | Vietato in `listini_righe`; nuova tabella `listini_righe_componenti` |
| Resolver pricing | Solo standalone | Bundle-aware (parametro `p_articolo_padre_contesto`) |
| IVA padre-figli | Non vincolata | Coerente (trigger guard catalogo) |
| `fn_resolve_prezzo_composito` | Attivo (2 rami CASO A/B) | Deprecato |

---

## 1. `script.trgfn_componenti_guard_coerenza_bom` — rimozione guard 4 ✅

> **Migration**: `20_code/script/20260513-08-update-trgfn-componenti-guard-coerenza-bom-remove-esposto-mctit.yaml`

**Cosa**: rimuovere il guard "esposto_in_fattura = TRUE" e l'errore
`E_DOC_COMPONENTE_NON_ESPOSTO`. Restano i 4 guard (is_composito padre,
appartenenza BoM, coerenza componente_id, validita BoM).

**Caller di questo trigger**: 4 tabelle `<sorgente>_righe_componenti` +
nuova `listini_righe_componenti` (vedi §6).

## 2. 4 fn `_init` + 4 fn `_preview` — rimozione filtro `esposto`

**Cosa**: rimuovere `AND ac.esposto_in_fattura = TRUE` dal loop sui
componenti in:

- `vendite.fn_preventivo_riga_componenti_init`
- `vendite.fn_preventivo_riga_componenti_preview`
- 3 omologhi (ordini, contratti, ddt) per `_init` e `_preview`

**Default `attivo` in `_init`**: per ogni componente inserito:

- `articoli_componenti.obbligatorio = TRUE` → `attivo = TRUE`
- `articoli_componenti.obbligatorio = FALSE` → `attivo = FALSE`

**Proiezione `_preview`**: aggiungere `obbligatorio` (boolean) e
`esposto_in_fattura` (boolean) tra le colonne ritornate.

**Caller resolver**: passare `p_articolo_padre_contesto = riga.articolo_id`
al resolver bundle-aware (vedi §7).

## 3. CHECK prezzo `<> 0` — rilassamento condizionale

**3.1 — `*_righe_componenti`** (4 tabelle):

Rimuovere il CHECK universale `CHECK (prezzo_unitario <> 0)`.
Sostituire con trigger
`script.trgfn_componenti_check_prezzo_obbligatorio` BEFORE INSERT OR
UPDATE:

- JOIN su `articoli_componenti(NEW.articolo_componente_id)` → leggi
  `obbligatorio`
- Se `obbligatorio = TRUE` e `NEW.prezzo_unitario = 0` → raise
  `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`
- Altrimenti pass (ammessi 0 e negativi)
- `prezzo_unitario` resta `NOT NULL`

**3.2 — `*_righe`** (4 tabelle, riga padre):

Rilassare CHECK `<> 0` su `prezzo_unitario` (per i compositi e' SUM
figli, puo' essere 0/negativo).

Decisione team DB: ammettere qualsiasi numero ovunque (anche per
articoli non-compositi) oppure CHECK condizionale `non-composito →
<> 0`. La validazione applicativa nel service Python copre il caso
operativo. Proposta: ammettere qualsiasi numero, semplificare.

## 4. Guard obbligatorio non disattivabile

**Nuovo trigger** `script.trgfn_componenti_guard_obbligatorio`
BEFORE UPDATE su 4 `*_righe_componenti` (TG_ARGV parametrizzato):

- Se `OLD.attivo = TRUE` e `NEW.attivo = FALSE`:
  - JOIN su `articoli_componenti(OLD.articolo_componente_id)`
  - Se `obbligatorio = TRUE` → raise `E_DOC_COMPONENTE_OBBLIGATORIO`

## 5. Errore BoM vuota

**Cosa**: nelle 4 fn `_init`, al termine del loop:

- Se `is_composito = TRUE` e `v_inserted = 0` (nessun componente
  valido alla data) → raise `E_DOC_COMPOSITO_BOM_VUOTA`

Messaggio: "Articolo composito {codice} senza componenti validi alla
data {data_riferimento}: BoM scaduta o non configurata."

**Idempotenza preservata**: se i componenti sono gia' presenti
(re-init) il loop scopre 0 nuove righe ma la fn ritorna 0 senza
sollevare (no-op come oggi). Lo `E_DOC_COMPOSITO_BOM_VUOTA` scatta
solo al PRIMO init.

## 6. Coerenza IVA padre-figli

**6.1 — Nuovo trigger** `catalogo.trgfn_articoli_componenti_guard_iva`
BEFORE INSERT OR UPDATE su `catalogo.articoli_componenti`:

- Verifica `articoli(NEW.componente_id).iva_id = articoli(NEW.prodotto_id).iva_id`
- Se diverso → raise `E_BOM_IVA_DISCORDANTE`

**6.2 — Nuovo trigger** `catalogo.trgfn_articoli_guard_iva_bom_attiva`
BEFORE UPDATE OF `iva_id` su `catalogo.articoli`:

- Se articolo e' padre in righe BoM attive → tutti i figli devono
  avere `iva_id = NEW.iva_id`; altrimenti raise
- Se articolo e' figlio in righe BoM attive → il padre deve avere
  `iva_id = NEW.iva_id`; altrimenti raise

**Backfill**: nessuna migrazione automatica. In dev verificare
manualmente eventuali BoM incoerenti pre-trigger; correggere a mano.

## 7. Resolver pricing bundle-aware

**7.1 — `vendite.fn_resolve_prezzo_listino_v2`**: nuovo overload (o
estensione firma con DEFAULT) che aggiunge
`p_articolo_padre_contesto UUID DEFAULT NULL`.

Comportamento:

- NULL → invariato (STADIO 1-3 come oggi)
- NOT NULL → STADIO 0 nuovo, prima di STADIO 1:
  1. Identifica `listino_versione_id` corrente per (BA, utility, data)
  2. Cerca `listini_righe_componenti(versione, padre, figlio, validita @> data, attivo=TRUE)`
  3. Se trovato → ritorna prezzo + `origine = 'LISTINO_BUNDLE'`
  4. Altrimenti → fallback STADIO 1 standalone

**7.2 — Origine prezzo**: aggiungere codice `LISTINO_BUNDLE` agli
ammessi. Aggiornare config.parameters / tabella enum se esistente.

**7.3 — Interazione promo / contratti**:

- **Promo articoli**: di default NON si applica nel contesto bundle
  (decisione di dominio). Override via flag su tabella promo
  `vale_in_contesto_padre BOOLEAN DEFAULT FALSE` (se team DB vuole
  introdurlo subito o lasciarlo per fase 2)
- **Contratti modalita' C**: la negoziazione puntuale BA-emittente
  vince sempre sul prezzo bundle (negoziazione esplicita). Comportamento
  attuale del resolver invariato, controllare che la priorita' funzioni
  anche col nuovo STADIO 0.

## 8. Nuova tabella `vendite.listini_righe_componenti`

**Schema**:

```sql
CREATE TABLE vendite.listini_righe_componenti (
    id                       BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    listino_versione_id      BIGINT NOT NULL REFERENCES vendite.listini_versioni(id),
    articolo_componente_id   UUID   NOT NULL REFERENCES catalogo.articoli_componenti(id),
    articolo_padre_id        UUID   NOT NULL REFERENCES catalogo.articoli(id),
    articolo_figlio_id       UUID   NOT NULL REFERENCES catalogo.articoli(id),
    prezzo                   NUMERIC(18,6) NOT NULL,
    iva_id                   BIGINT REFERENCES config.iva(id),
    validita                 DATERANGE NOT NULL,
    attivo                   BOOLEAN NOT NULL DEFAULT TRUE,
    meta                     JSONB NOT NULL DEFAULT '{}'::jsonb,
    tx_id                    UUID,
    user_insert              TEXT,
    data_insert              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_update              TEXT,
    data_update              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Vincoli**:

- UNIQUE/GIST exclusion `(listino_versione_id, articolo_componente_id)`
  con `validita` daterange per non-overlap nella stessa versione
- CHECK `attivo = TRUE` o `prezzo IS NOT NULL` (qualsiasi numero, anche
  0/negativi; coerente con regole prezzi figli)

**8.1 — Trigger guard coerenza** (riusa pattern §1):

`script.trgfn_listini_righe_componenti_guard_coerenza_bom` BEFORE
INSERT OR UPDATE:

- `articolo_componente_id` esiste in `catalogo.articoli_componenti` e
  i denorm `articolo_padre_id` / `articolo_figlio_id` coincidono
- `padre.is_composito = TRUE`
- `figlio.iva_id = padre.iva_id` (coerenza F)
- `validita_listino_riga_comp ⊆ validita_bom_riga`
- `validita_listino_riga_comp ⊆ validita_versione_listino`

Errore unico: `E_LISTINO_COMPONENTE_COERENZA_BOM` con causa specifica
nel JSON.

**8.2 — Immutabilita' v5** (estensione pattern listini esistente):

Hook ai trigger esistenti `trgfn_*_versione_attiva_block` o nuovi
trigger paralleli:

- INSERT consentito solo se `versione_listino.attiva = FALSE`
- UPDATE `prezzo`, `iva_id`, `validita` bloccato se versione attiva
- DELETE bloccato sempre → usare `attivo = FALSE`

## 9. Listino diretto su padre composito vietato

**Nuovo trigger** `catalogo.trgfn_listini_righe_guard_no_composito`:

- BEFORE INSERT su `vendite.listini_righe`: se
  `articoli(NEW.articolo_id).is_composito = TRUE` → raise
  `E_LISTINO_RIGA_COMPOSITO_VIETATO`
- BEFORE UPDATE su `catalogo.articoli` SET `is_composito = TRUE`: se
  articolo ha gia' righe in `vendite.listini_righe` → raise stesso
  errore

**Backfill dev**: censimento + correzione manuale di eventuali righe
listino su compositi esistenti.

## 10. Deprecazione `fn_resolve_prezzo_composito`

**Cosa**: il branching CASO A / CASO B non ha piu' significato col
modello unificato (padre = sempre SUM figli, no prezzo singolo padre).

**Procedura**:

- Censimento caller (search in trigger, fn, view, pgTAP)
- Se 0 caller → DROP funzione
- Se caller residui → marcare DEPRECATED nel COMMENT, pianificare
  rimozione in iterazione successiva

## 11. Vista lookup articolo

**11.1 — `catalogo.vw_articoli_dettaglio`** (o equivalente lookup
articolo del FE): aggiungere colonna `has_componenti_alla_data`
BOOLEAN:

- TRUE se `is_composito = TRUE` AND esiste almeno una riga
  `articoli_componenti(prodotto_id = articolo.id, validita @> CURRENT_DATE, attivo = TRUE)`
- Permette al FE di evitare apertura Dialog componenti su compositi
  con BoM scaduta (mostra subito errore parlante)

## 12. Nuovi error code in `config.messaggi_errore` ✅

> **Migration**: `80_data/changelog/20260513-01-delete-messaggi-errore-deprecati-bom-mctit.yaml` (DELETE fisico);
> `80_data/sql/config/messaggi_errore.csv` aggiornato (6 nuovi, 2 rimossi).

Aggiunto al seed:

| Codice | Messaggio (IT) |
| --- | --- |
| `E_DOC_COMPOSITO_BOM_VUOTA` | "Articolo composito {codice} senza componenti validi alla data {data_riferimento}: BoM scaduta o non configurata." |
| `E_DOC_COMPONENTE_OBBLIGATORIO` | "Componente obbligatorio {codice}: non puo' essere disattivato dalla riga." |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | "Componente obbligatorio {codice}: il prezzo deve essere diverso da zero." |
| `E_BOM_IVA_DISCORDANTE` | "BoM incoerente: padre {codice_padre} IVA {iva_padre} != figlio {codice_figlio} IVA {iva_figlio}." |
| `E_LISTINO_RIGA_COMPOSITO_VIETATO` | "Articolo composito {codice}: il prezzo si gestisce via listini_righe_componenti." |
| `E_LISTINO_COMPONENTE_COERENZA_BOM` | "Riga listino componenti incoerente: {dettaglio}." |

Da rimuovere (deprecati):

| Codice | Motivazione |
| --- | --- |
| `E_DOC_COMPONENTE_NON_ESPOSTO` | Gate `esposto_in_fattura` abbandonato |
| `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` | (gia' rimosso post form atomic) |

## 13. Ordine di applicazione — file migration ✅

| Step | File migration | Stato |
| --- | --- | --- |
| 1. messaggi_errore nuovi | `80_data/changelog/20260513-01-delete-messaggi-errore-deprecati-bom-mctit.yaml` + CSV | ✅ |
| 2. Trigger IVA catalogo | `20_code/catalogo/20260513-02` (articoli_componenti) + `20260513-03` (articoli) | ✅ |
| 3. Trigger listino composito | `20_code/vendite/20260513-04` + `20_code/catalogo/20260513-05` | ✅ |
| 4a. CHECK rilassati *_righe_componenti | `00_schema/vendite/20260513-06` | ✅ |
| 4b. Trigger check prezzo obbligatorio | `20_code/script/20260513-07` (fn + 4 trigger) | ✅ |
| 5. trgfn_componenti_guard_coerenza_bom | `20_code/script/20260513-08` | ✅ |
| 6a. 4 fn `_init` modello unificato | `20_code/vendite/20260513-09..12` | ✅ |
| 6b. 4 fn `_preview` DROP+CREATE | `20_code/vendite/20260513-13..16` | ✅ |
| 7. Trigger guard obbligatorio | `20_code/script/20260513-17` (fn + 4 trigger) | ✅ |
| 8a. DDL listini_righe_componenti | `00_schema/vendite/20260513-18` + audit triggers | ✅ |
| 8b. Guard coerenza BoM listino | `20_code/script/20260513-19` | ✅ |
| 8c. Guard immutabilita' v5 listino | `20_code/vendite/20260513-20` | ✅ |
| 9a. ALTER origine LISTINO_BUNDLE | `00_schema/vendite/20260513-21` (4 tabelle) | ✅ |
| 9b. Resolver bundle-aware | `20_code/vendite/20260513-22` | ✅ |
| 10. COMMENT DEPRECATED fn_resolve_prezzo_composito | `20_code/vendite/20260513-24` | ✅ |
| 11. Vista has_componenti_alla_data | `20_code/catalogo/20260513-23` | ✅ |

**Pendente (non automatizzabile con migration)**:

- Backfill manuale: BoM con IVA incoerenti + righe listino su compositi
- Aggiornare caller resolver: 4 fn `_init` + `_preview` passare `p_articolo_padre_contesto` (dopo smoke test)
- pgTAP: aggiornare suite esistenti + aggiungere test §14

## 14. Test pgTAP suggeriti

- Trigger IVA (catalogo): INSERT BoM con IVA diversa → raise
- Trigger IVA: UPDATE `articoli.iva_id` su padre/figlio in BoM attiva → raise
- Trigger listino composito: INSERT `listini_righe` con `is_composito=TRUE` → raise
- Fn `_init`: BoM scaduta → raise `E_DOC_COMPOSITO_BOM_VUOTA`
- Fn `_init`: BoM mista → obbligatori `attivo=TRUE`, opzionali `attivo=FALSE`
- Trigger obbligatorio: UPDATE `attivo=FALSE` su obbligatorio → raise
- Check prezzo obbligatorio: INSERT con prezzo=0 su `obbligatorio=TRUE` → raise; lo stesso INSERT con `obbligatorio=FALSE` → OK
- Trigger ricalcola_padre: SUM figli con segni misti = 0 → padre = 0 ammesso
- `listini_righe_componenti` immutabilita': UPDATE prezzo su versione attiva → raise
- Resolver bundle-aware: con `p_articolo_padre_contesto` valorizzato → STADIO 0 hit prima di STADIO 1

## 15. Fuori scope

- `partecipa_qta` / `determina_qta_padre`: campi scheletro non usati
  runtime, restano invariati
- Snapshot `esposto_in_fattura` in catena `commesse_attivita` /
  `fatture_righe`: non necessario (BoM immutabile, JOIN runtime
  sicuro)
- Modifica template fattura / generazione FatturaPA per aggregazione
  padre+esposti: riguarda fase BE/FE, non DB

## 16. Riferimenti

- Razionale e modello logico: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md)
- Storico decisioni: [`manual/changelog-decisioni-componenti.md`](../manual/changelog-decisioni-componenti.md)
- Piano operativo BE/FE: [`refactor-componenti.md`](refactor-componenti.md)
- Brief precedenti (atterrati, work-done): `brief-db-preventivi-righe-componenti-override.md`, `brief-db-componenti-relaxed-override.md`, `brief-db-componenti-form-atomic.md`
