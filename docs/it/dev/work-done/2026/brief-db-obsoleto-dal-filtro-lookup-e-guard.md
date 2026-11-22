# Brief DB — `obsoleto_dal`: filtro selezione nel lookup generico + guard creazione

> **Tipo**: brief DB (cosa serve + piano deciso) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟡 media · **Data**: 2026-06-30 · **Scope**: **solo DB** (BE/FE fuori scope)
> **Stato**: 🟢 **DB FATTO + pgTAP VERDE + applicato (2026-06-30)** — D1..D5 (`20260630-03/04/05`
> + codice errore 500 + 2 pgTAP). `runOnChange` riportato a `false` su tutti e 3 i changeSet DDL.
> Restano: 1 fix dato seed (vedi §"Conseguenze a valle"), il BE (fuori scope), il commit.
> **Origine**: introdotta la colonna `obsoleto_dal` su `tipi_prestazione`/`template_flussi`
> ([brief-db-deprecabilita-catalogo-vs-istanze.md](brief-db-deprecabilita-catalogo-vs-istanze.md), P1 chiuso).
> Resta da far sì che un record **obsoleto** non venga più **offerto per il nuovo** e non
> possa essere **usato per nuove istanze**.

---

## Contesto in una frase

`obsoleto_dal` separa "riferimento ancora valido" (per le istanze storiche) da
"selezionabile per il nuovo". La parte "storia intatta" è fatta. Manca chiudere il
secondo asse: **nasconderlo nella selezione** e **vietarne l'uso nel nuovo** — e che
valga **per ogni catalogo** che adotta il pattern, non solo per le pratiche.

---

## Obiettivo 1 — La selezione "per il nuovo" non offre i record obsoleti (generico)

Le liste di scelta dei cataloghi sono servite dal **lookup generico** (`rel=`), che già
esclude i record non `attivo`. Serve che **nello stesso punto generico** vengano esclusi
anche i record con `obsoleto_dal` raggiunto, **per qualunque catalogo** che abbia quella
colonna (non una soluzione per-tabella).

**Cosa serve**:
- un record con `obsoleto_dal IS NULL` o `obsoleto_dal > oggi` → **selezionabile**;
- un record con `obsoleto_dal <= oggi` → **non offerto** nella selezione per il nuovo;
- il filtro deve attivarsi **da solo** quando la tabella ha la colonna `obsoleto_dal`
  (come già accade per `attivo`), senza configurazione per-tabella;
- se la tabella **non ha** la colonna → il lookup restituisce comunque la lista intera
  (degradazione trasparente, identica a come `attivo` è opzionale).

**Vincolo importante — serve poter includere gli obsoleti in alcuni contesti**: lo stesso
lookup è usato anche per **filtrare liste/storico** (es. filtrare le pratiche esistenti per
tipo, incluso un tipo ormai obsoleto). In quei contesti gli obsoleti **devono comparire**,
altrimenti non si filtra più lo storico. Serve quindi un **interruttore** (gemello del
"solo attivi" già esistente) che il chiamante usa.

**Criteri di accettazione**:
- una nuova pratica non offre più `PREVENTIVI_IMMEDIATA/DIFFERITA` (9002/9003, obsoleti) ma
  offre `PREVENTIVI` (9004);
- un filtro "per tipo" su una lista di pratiche esistenti mostra **anche** i tipi obsoleti;
- le **letture storiche** (apertura di una pratica già su un tipo obsoleto) non sono
  influenzate dal filtro.

## Obiettivo 2 — Vietare l'uso di un catalogo obsoleto per nuove istanze (difesa in profondità)

La selezione lo nasconde, ma serve l'ultima linea: impedire via API/forzatura la
**creazione** di una nuova istanza (pratica/flusso, e in generale figli) che referenzia un
catalogo **obsoleto**. È coerente con il pattern guard del progetto ("la UI nasconde, il DB
rifiuta").

**Cosa serve**:
- la creazione di una **nuova** pratica/flusso su un tipo/template con `obsoleto_dal <= oggi`
  è **rifiutata** con errore parlante;
- le istanze **esistenti** su cataloghi obsoleti restano valide (nessun blocco su update di
  lifecycle che non cambiano il riferimento al catalogo).

**Criterio di accettazione**: tentare di creare una pratica sul tipo 9002/9003 (obsoleti)
fallisce con errore semantico; creare sul 9004 riesce; far avanzare una pratica storica su
9002/9003 continua a funzionare.

> ⚠️ **Chiarimento (vs deprecabilità §6.4)**: il trigger **REQUIRE** della regola ATTIVO
> **non** copre questo caso. Tutto il senso di P1 è che il record obsoleto resta
> `attivo=true` → il REQUIRE non scatta sull'asse `obsoleto_dal`. L'Obiettivo 2 richiede un
> guard **nuovo**, su un asse diverso da `attivo`.

---

## Piano di sviluppo (deciso 2026-06-30)

### Decisioni bloccate

1. **Interruttore lookup** = `p_includi_obsoleti boolean DEFAULT true`.
   - Default `true` = **preserva il comportamento attuale** (oggi nessun filtro → tutto
     visibile). Un default "nascondi" cambierebbe **silenziosamente** ogni chiamata esistente
     (inclusi i contesti storico/filtro) prima che il BE impari a passare l'interruttore →
     regressione. La policy "nascondi nel nuovo" è una scelta del **chiamatore** (passa
     `false`), non del DB → separazione DB-first.
   - **Bonus retro-compat (DB-only)**: 7° parametro con default in coda → la chiamata
     posizionale a 6 argomenti del repository **continua a risolversi** senza modifiche BE.
   - Asimmetria voluta vs `attivo_only` (`DEFAULT true` = restringi): da documentare nel
     `COMMENT ON FUNCTION` e nel manuale.

2. **Approccio guard** = **Tier 2 — cervello unico + fili sottili** (NON il framework
   generatore, NON il concreto duplicato).
   - **Tier 1** (concreto duplicato, logica copiata in ogni guardia) → scartato: non scala.
   - **Tier 2** (questo): la **logica** scritta una volta in una funzione `fn_check_*` pura;
     ogni tabella-figlia ha un trigger sottile che la chiama. Aggiungere un catalogo (es.
     `iva`) = un trigger sottile in più, **zero logica duplicata**.
   - **Tier 3** (generatore config-driven, stile regola ATTIVO + job notturno) → **rinviato**.
     Si giustifica solo quando i punti-guardia diventano *davvero* tanti (es. l'IVA è
     referenziata da molte tabelle-figlie × molti cataloghi). Il cervello del Tier 2 ne sarà
     la base naturale: **non si butta nulla**.

3. **Wiring guard** = **trigger function generica + 2 trigger espliciti** (uno per relazione).
   In fase di sviluppo si è scoperto che il REQUIRE-ATTIVO è già una **trigger function
   generica parametrica** (`dbops.trgfn_child_requires_active_parent`, cablata per relazione
   via `CREATE TRIGGER` con `TG_ARGV`). Il Tier 2 corretto è la sua **gemella sull'asse
   obsoleto_dal**: una sola funzione-cervello generica, 2 trigger espliciti (le "2 guardie
   separate") che la richiamano. Onora "2 guard separate" (2 trigger) e "no logica duplicata"
   (cervello unico), ed è l'idioma di progetto già provato. IVA domani = un `CREATE TRIGGER` in
   più, zero logica nuova.

### Razionale Tier 2 (sintesi della discussione)

- L'**Obiettivo 1 è già il framework**: la funzione di lookup è una sola e scopre da sola
  `obsoleto_dal`. Il giorno in cui l'IVA prende `obsoleto_dal`, l'aliquota obsoleta sparisce
  dalle tendine **senza una riga di codice in più**. I "casi a bizzeffe" per la *selezione*
  sono coperti gratis.
- La pressione di scala riguarda **solo il guard**, e non viene dal numero di cataloghi ma
  dal numero di **tabelle-figlie per catalogo**. Il Tier 2 (un trigger sottile per punto,
  cervello condiviso) la regge senza duplicazione; il Tier 3 si valuta se/quando esplode.

### Deliverable DB (e solo DB)

| ID | Deliverable | File | Note |
| --- | --- | --- | --- |
| **D1** | Estensione `dbops.fn_get_lookup_codici` (Obiettivo 1) | `20_code/dbops/20260630-03-update-fn-get-lookup-codici-obsoleto-dal-mctit.yaml` | DROP+ricreazione (7° arg `p_includi_obsoleti DEFAULT true`), introspezione `obsoleto_dal` opzionale + type-check `date`, WHERE ad accumulatore. Vedi "trappole D1" |
| **D2** | Funzione-cervello generica `dbops.trgfn_child_requires_non_obsolete_parent()` (gemella di `trgfn_child_requires_active_parent`, parametrica via `TG_ARGV`) | `20_code/dbops/20260630-04-create-trgfn-child-requires-non-obsolete-parent-mctit.yaml` | Legge la FK da `NEW` via `to_jsonb`; su UPDATE salta se la FK non cambia; blocca se `obsoleto_dal <= CURRENT_DATE` con `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` |
| **D3** | 2 trigger espliciti `_a10_` che cablano D2 su `pratiche.pratiche` e `pratiche.flussi` | `20_code/pratiche/20260630-05-create-triggers-require-non-obsolete-parent-pratiche-flussi-mctit.yaml` | Vedi "convenzioni D3" |
| **D4** | Codice errore `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (id 500) | `80_data/sql/config/messaggi_errore.csv` (riga appesa; upsert via `20250717-22`) | No `E_GENERICO`; template a un solo `%s` |
| **D5** | pgTAP (lookup + guard) | `db/pgtap/dbops/test-fn-get-lookup-codici-obsoleto-v1.sql`, `db/pgtap/pratiche/test-guard-non-obsolete-parent-v1.sql` | `BEGIN/ROLLBACK`; copre anche "tabella senza colonna → lista intera" |

### Trappole D1 (estensione lookup) — da rispettare

- **Cambio firma = DROP + ricreazione**, non `CREATE OR REPLACE`: aggiungere un argomento
  crea un *overload* e lascia viva la 6-arg. Serve
  `DROP FUNCTION dbops.fn_get_lookup_codici(regclass,text,text,boolean,integer,integer)` +
  ricreazione in **nuovo file numerato** (mai toccare `20260520-04` già mergiato). Aggiornare
  anche il `COMMENT ON FUNCTION` con la nuova firma.
- **`obsoleto_dal` colonna OPZIONALE**: introspezione via `pg_attribute` come `attivo`
  (mai sollevare se manca — al contrario di `id`/`descrizione`). Verificare anche il tipo
  `date` (come `attivo` verifica `bool`).
- **Refactor composizione predicati**: oggi `v_sql || ' WHERE t.attivo IS TRUE'` regge con un
  solo predicato. Con due serve un **accumulatore** (`WHERE` per il primo, `AND` per i
  successivi), altrimenti SQL rotto nei casi "tabella con `obsoleto_dal` ma senza `attivo`"
  o `attivo_only=false`. Predicato: `(t.obsoleto_dal IS NULL OR t.obsoleto_dal > CURRENT_DATE)`,
  applicato solo `IF NOT p_includi_obsoleti AND v_has_obsoleto`.
- **Filtro dentro la funzione, non a valle**: il repository usa `COUNT(*) OVER()` e il tetto
  10k *dopo* la funzione → filtrare fuori falserebbe count e paginazione.
- **Whitelist**: verificare che `pratiche.tipi_prestazione` e `pratiche.template_flussi` siano
  in `_REL_CONSENTITE` (BE), altrimenti l'Obiettivo 1 non li raggiunge. *(Verifica, non
  modifica DB.)*

### Convenzioni D3 (come-costruito)

- **Trigger function generica** (D2): `dbops.trgfn_child_requires_non_obsolete_parent()` —
  una sola, parametrica via `TG_ARGV` `(parent_schema, parent_table, parent_obsoleto_col,
  fk_col [, parent_ref_col])`. È la copia esatta del pattern `trgfn_child_requires_active_parent`
  sull'asse `obsoleto_dal`.
- **2 trigger espliciti** (fase `_a10_`):
  `trg_pratiche_a10_tipi_prestazione_require_non_obsoleto_ins_upd` su `pratiche.pratiche`
  (`tipo_prestazione_id`) e
  `trg_flussi_a10_template_flussi_require_non_obsoleto_ins_upd` su `pratiche.flussi`
  (`template_flusso_id`). Nomi paralleli ai gemelli `*_require_attivo_*` già presenti.
- **`AFTER INSERT OR UPDATE OF <fk_catalogo>`**: si è scelto **AFTER** (non BEFORE) per
  **mirroring esatto del REQUIRE-ATTIVO** — legge la FK già finale (dopo i BEFORE che potrebbero
  valorizzarla) ed evita incoerenze d'ordine con i gemelli `_a10_` AFTER sulle stesse tabelle.
  `UPDATE OF <fk>` + lo skip "FK invariata" nella trgfn garantiscono che gli avanzamenti di
  lifecycle non vengano mai bloccati.

### Dipendenza temporale (intenzionale)

Sia il lookup sia il guard dipendono da `CURRENT_DATE`: una insert legale oggi diventa
illegale domani se `obsoleto_dal` cade nel mezzo (ritiro programmato). Comportamento voluto —
da scrivere nei test e nel manuale per non sembrare un bug.

### Test pgTAP (D5)

- **Lookup**: obsoleto **escluso** con `includi_obsoleti=false`; **incluso** di default
  (`true`); `obsoleto_dal` **futuro** resta selezionabile; **tabella senza colonna → lista
  intera** (test dedicato); regressione `attivo_only` invariata.
- **Guard**: insert su 9002/9003 **fallisce** con errore parlante; su 9004 **riesce**;
  avanzamento di una pratica storica su 9002/9003 **continua a funzionare**.

---

## Nota a valle (verificata 2026-06-30) — non è un problema del design

Per scrupolo si è verificato se qualche `regola_generazione` punti ancora a un tipo obsoleto:

```sql
SELECT rg.id, tp.codice_interno, tp.obsoleto_dal
FROM pratiche.regole_generazione rg
JOIN pratiche.tipi_prestazione tp ON tp.id = rg.tipo_prestazione_dest_id
WHERE tp.obsoleto_dal IS NOT NULL AND tp.obsoleto_dal <= CURRENT_DATE;
-- → 9001 | PREVENTIVI_DIFFERITA | 2026-06-30
```

**Che `PREVENTIVI_DIFFERITA` sia obsoleto e non più usato è l'obiettivo, non un bug.** Il guard
che bloccherebbe una sua nuova generazione fa la cosa giusta. La regola `9001` è **dato di
smoke-test** (`80_data/sql/pratiche/regole_generazione.csv`, changeset
`20260612-01-seed-regole-generazione-test-smoke`), non config di un flusso reale:

- se non viene mai eseguita → impatto **zero** (config inerte);
- se uno **smoke test** la esegue → ora fallisce col guard (giusto, ma rumoroso).

**Azione: opzionale, igienica.** Eventualmente ritirare quella riga smoke-test nel seed
(`loadUpdateData`, `runOnChange: true`) così un test futuro non inciampa nel guard. Non è un fix
del guard né un blocco per la chiusura del brief.

---

## Fuori scope (BE/FE)

- **Niente filtro lato BE per la selezione**: la lista passa dal lookup generico DB → il
  filtro vive lì. Il BE deve solo, dove serve la "selezione per il nuovo", **passare**
  `includi_obsoleti=false` (default DB = `true` = mostra tutto).
- Messaggistica utente sull'errore di creazione (BE/FE) oltre al codice errore del guard.

## Note

- Pattern `obsoleto_dal` riusabile cross-dominio: l'Obiettivo 1 è già generico per
  costruzione; l'Obiettivo 2 lo diventa via cervello condiviso (D2), pronto per il Tier 3 se
  servirà.
- Coerenza con il guard `prevent_deactivate_if_children`: qui non si tocca `attivo`, si lavora
  sull'asse `obsoleto_dal`.
- Memoria correlata: `reference_deprecabilita_catalogo_obsoleto_dal`.
