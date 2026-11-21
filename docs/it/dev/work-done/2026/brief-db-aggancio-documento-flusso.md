# Brief DB — `flusso_id` su `pratiche_sorgenti` + ROOT unico per-flusso

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; il *come* (nome colonna/indice/constraint,
> changeset, strategia backfill) è scelta del team DB.
>
> **Data**: 2026-06-16 (smoke 2026-06-17) · **Stato**: ✅ COMPLETATO — DB applicato,
> BE/FE implementato, smoke E2E OK. Vedi §6 (decisioni + deliverable) e §7.
>
> **Origine/Design**: [brief-design-aggancio-documento-flusso.md](brief-design-aggancio-documento-flusso.md).
> **Prerequisito di**: refactor BE/FE "aggancio documento↔flusso" (non iniziano
> prima di questa colonna).

---

## 1. Contesto

Il legame documento↔pratica vive in `pratiche.pratiche_sorgenti`. Per i preventivi
aperti dal percorso pratica-first il legame è `ruolo_link='ROOT'`, oggi ancorato alla
**pratica**:

```sql
uq_pratiche_sorgenti_pratica_tipo_uid_ruolo
  UNIQUE (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
```

Dato (dbdev): 13 righe `PREVENTIVO`/`ROOT`; 10 `COMMESSA` + 10 `ORDINE_VENDITA`,
entrambe `COLLEGATO` (link a valle dai push handler).

**Problema**: il documento appartiene concettualmente al **flusso di preventivazione**
(un'istanza in `pratiche.flussi`), non a tutta la pratica. L'ancoraggio per-pratica
permette **due ROOT** sulla stessa pratica e costringe il BE a *cercare* il flusso da
completare all'emissione. Spostando l'ancora sul flusso, il modello diventa esatto.

## 2. Cosa serve (risultato atteso)

1. **Nuova colonna** su `pratiche.pratiche_sorgenti`: un riferimento al flusso
   d'origine del link — **FK → `pratiche.flussi(id)`**, **NULLABLE**.
   - Valorizzata per i link **ROOT** nati da un'attività UI di flusso (preventivo).
   - **NULL** per i link **COLLEGATO** a valle (commessa/ordine): non nascono da un
     flusso, non devono essere vincolati.

2. **Vincolo di unicità "max 1 ROOT per flusso"**: per un dato flusso non può esistere
   più di un documento ROOT. Forma suggerita (il team DB sceglie l'esatta):
   indice unico **parziale** su `flusso_id` con predicato `ruolo_link='ROOT' AND
   flusso_id IS NOT NULL`. (Se preferite granularità per tipo documento, includere
   `sorgente_tipo_id`.)
   - Il vincolo per-pratica esistente può restare (non in conflitto) o essere
     rivalutato: indicare voi cosa è coerente con lo standard.

3. **Backfill** dei 13 ROOT PREVENTIVO esistenti: valorizzare `flusso_id` con il
   flusso di **preventivazione** della pratica — l'istanza in `pratiche.flussi` il cui
   `template_flusso_id` ha `azione_ui_key = 'APRI_PREVENTIVO'`
   (`pratiche.template_flussi.azione_ui_id → pratiche.azioni_ui`). Atteso 1 per
   pratica; in caso di ambiguità/assenza, lasciare NULL e segnalare le righe (sono
   poche, gestibili a mano).

## 3. Criteri di accettazione

- `pratiche_sorgenti.flusso_id` esiste, FK a `pratiche.flussi`, nullable.
- Inserire un **secondo** ROOT sullo stesso `flusso_id` **viola** il vincolo (errore),
  mentre un secondo ROOT su flussi diversi è ammesso.
- I link COLLEGATO (commessa/ordine) restano inseribili con `flusso_id` NULL, non
  toccati dal vincolo.
- I 13 ROOT PREVENTIVO esistenti hanno `flusso_id` valorizzato col flusso di
  preventivazione corretto (o NULL motivato e segnalato).
- Copertura pgTAP nello stile dei test pratiche/sorgenti (presenza colonna+FK,
  enforcement del vincolo, COLLEGATO non vincolato).

## 4. Decisione da concordare (DB + Tid)

- **Granularità del vincolo**: "1 ROOT per flusso" (su `flusso_id`) vs "1 ROOT per
  flusso *per tipo documento*" (su `flusso_id, sorgente_tipo_id`). Un flusso apre un
  solo documento → la prima basta; la seconda è più difensiva verso futuri usi misti.
- **Sorte del vincolo per-pratica** `uq_..._pratica_tipo_uid_ruolo`: mantenerlo o
  sostituirlo. (Lato BE l'upsert idempotente attuale usa questa chiave in
  `ON CONFLICT`; se la cambiate, lo allineiamo nel refactor BE.)

## 5. Fuori scope (BE/FE — dopo questo brief)

- `collega_pratica` che passa `flusso_id`; resolver riapertura per-flusso;
  auto-completamento dell'emissione via reverse diretto `flusso_id` (sostituisce la
  ricerca per `azione_ui_key`): **solo BE**.
- Percorso/registry/host che propagano `flusso_id` e garantiscono il flusso avviato
  all'apertura del documento: **solo FE**.
- Allineamento handler `accetta_preventivo`/`push_preventivo` a risolvere per-flusso:
  **solo BE**, opzionale/non bloccante.

## 6. Implementazione DB (2026-06-16)

**Decisioni prese** (§4):

- **Granularità vincolo**: solo `flusso_id` (NON `+sorgente_tipo_id`). Un flusso = una
  attività UI = un documento → "max 1 ROOT per flusso" è la garanzia corretta;
  includere `sorgente_tipo_id` ammetterebbe due ROOT di tipi diversi sullo stesso
  flusso, indebolendo il punto 1 del design.
- **Vincolo per-pratica** `uq_..._pratica_tipo_uid_ruolo`: **mantenuto** (il BE ci fa
  `ON CONFLICT` per l'idempotenza). Coesiste senza conflitto con il per-flusso.
- **Aggiunta oltre il brief**: guard trigger di coerenza `pratica_id ↔
  flussi.pratica_id` — la FK garantisce solo che `flusso_id` punti a un flusso
  esistente, non che sia un flusso *di quella pratica*. Un `CHECK` non può fare
  subquery cross-tabella → guard fail-fast (scatta solo se `flusso_id IS NOT NULL`;
  flusso inesistente → lascia sollevare la FK).
- **Backfill**: NON eseguito (no produzione, dato dbdev rigenerabile).

**Deliverable** (changeset SCRITTI, non applicati — numerazione globale per data):

- `00_schema/pratiche/20260616-04-alter-pratiche-sorgenti-add-flusso-id` — colonna
  `flusso_id` (FK → `pratiche.flussi`, `ON DELETE RESTRICT`, nullable) + indice unico
  parziale `uq_pratiche_sorgenti_flusso_root` (`WHERE ruolo_link='ROOT' AND flusso_id
  IS NOT NULL`).
- `20_code/pratiche/20260616-05-create-trgfn-pratiche-sorgenti-guard-coerenza-flusso`
  — `trgfn_pratiche_sorgenti_guard_coerenza_flusso` + trigger
  `trg_pratiche_sorgenti_a10_guard_coerenza_flusso_ins_upd`.
- `80_data/changelog/20260616-06-upsert-messaggi-errore-sorgenti-flusso-incoerente` +
  riga CSV `PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE` (id 493).
- pgTAP: `db/pgtap/pratiche/test-pratiche-sorgenti-flusso.sql` (13 asserzioni).

**Nota rollout**: l'indice parziale morde solo quando `flusso_id` è valorizzato. Col
refactor BE/FE (sotto) il BE ora **propaga** `flusso_id` sui nuovi aggancio → il vincolo
"doppio ROOT impossibile" è pieno per i preventivi nuovi (lo storico resta NULL, vedi
backfill non eseguito).

## 7. Stato esecuzione (2026-06-16)

- **DB**: changeset **applicati su dbdev**. Protezioni verificate end-to-end (tx in
  rollback): 2° ROOT su stesso flusso → bloccato dall'indice unico; flusso di altra
  pratica → guard `PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE` (493). pgTAP verde.
- **BE/FE**: implementato e testato (313 test verdi, build FE ok). Dettaglio nel design
  → [brief-design-aggancio-documento-flusso.md](brief-design-aggancio-documento-flusso.md) §10.
- **Residuo**: commit + smoke E2E in-app. Backfill 13 ROOT storici **non eseguito** di
  proposito (dato dbdev rigenerabile, no produzione).
</content>
