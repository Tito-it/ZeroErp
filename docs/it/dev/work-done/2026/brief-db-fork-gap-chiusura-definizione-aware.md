# Brief DB — Gap fork (Fase 1 incompleta): chiusura/auto-chiusura ancora per TIPO, non per DEFINIZIONE

> ✅ **RISOLTO / APPLICATO (2026-07-03)** dal team DB (commit `25922d602`, pgTAP eseguito).
> Verificato sul DB vivo: `fn_check_chiusura_pratica` → `JOIN ON p.definizione_id =
> tf.definizione_id`; `trgfn_flussi_autochiusura_pratica` → legge `p.definizione_id` e scopa
> chiusura + gate obbligatori per `tf.definizione_id`. Ri-scan cross-schema: **nessuna**
> selezione template per-tipo residua. Documento mantenuto come storia del gap fork.
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🟠 **media-alta**
> — **latente** (oggi corretto: 1 definizione per tipo, 0 fork nei dati) ma **bloccante**: morde
> alla PRIMA fork/versione, capacità appena abilitata dalla Fase 2. Da chiudere **prima** che
> venga pubblicata la prima edizione forkata. · **Data**: 2026-07-03.
> **Origine**: audit di correttezza fork-aware dei consumi + oggetti DB, dopo i merge
> Fase 0/1/2 (`d21b68f2e`, `2834a43aa`, `207b0a261`).
> **Correlato**: `brief-db-step-dominio-e-definizioni-versionate.md` (Parte 2),
> `brief-design-workflow-definizioni-versionate.md` §3.2 (re-parent template + pin).

---

## 1. Contesto

La Fase 1 ha re-parentato `template_flussi` sotto `workflow_definizioni` e pinnato la
definizione sulla pratica (`pratiche.definizione_id`, NOT NULL). La regola è: per una
pratica si considerano i `template_flussi` della sua **definizione pinnata**, non di tutte
le definizioni del tipo. Con la Fase 2 (fork/versioni) esistono **più definizioni per lo
stesso tipo**, quindi ogni selezione `template_flussi ↔ pratica` fatta per
`tipo_prestazione_id` restituisce i template di **tutte** le edizioni del tipo → sbagliato.

L'audit ha trovato **esattamente due** oggetti DB ancora per-tipo (scan cross-schema su
tutte le funzioni/procedure: nessun altro; nessuna vista). Tutto il resto è già fork-safe
(vedi §5). Il consumo BE del percorso (`get_percorso_pratica`) è già stato reso
definizione-aware; queste due funzioni sono l'analogo DB non aggiornato dalla Fase 1.

## 2. Oggetti da correggere (2)

### 2.1 `pratiche.fn_check_chiusura_pratica(p_pratica_id)`
Selezione dei template della pratica per tipo:

```sql
FROM pratiche.template_flussi tf
JOIN pratiche.pratiche p ON p.tipo_prestazione_id = tf.tipo_prestazione_id
WHERE p.id = p_pratica_id
```

→ deve agganciare per **definizione pinnata**: `ON tf.definizione_id = p.definizione_id`.
È chiamata (LEFT JOIN) da `get_percorso_pratica`: su una pratica di una definizione forkata
il calcolo del ramo di chiusura considererebbe i template di altre edizioni.

### 2.2 `pratiche.trgfn_flussi_autochiusura_pratica()` — **il più critico**
Trigger di auto-chiusura pratica (COMPLETATO di un flusso → verifica se la pratica può
chiudersi). Usa il tipo in **due** punti:

```sql
-- (a) template di chiusura della pratica → SELECT ... INTO v_chiusura_tmpl
FROM pratiche.template_flussi tf
WHERE tf.tipo_prestazione_id = v_tipo_id AND tf.chiude_pratica
-- (b) gate "almeno un obbligatorio"
SELECT 1 FROM pratiche.template_flussi tf
 WHERE tf.tipo_prestazione_id = v_tipo_id AND tf.obbligatorio
```

→ entrambi devono scopare per **definizione pinnata della pratica**
(`tf.definizione_id = <definizione_id della pratica>`), non per `v_tipo_id`.

Perché è il più grave, con evidenza rafforzata dall'unique: l'indice
`uq_template_flussi_chiusura_definizione` garantisce **una** riga `chiude_pratica`
**per definizione**. Quindi con N definizioni dello stesso tipo il `SELECT ... INTO
v_chiusura_tmpl` (a) legge **N righe** → errore "more than one row" o pick arbitrario; il
gate (b) conta obbligatori di **edizioni diverse**. Netto: una pratica forkata **si
auto-chiude prematuramente, non si chiude mai, o il trigger va in errore**. Corruzione
silenziosa (stessa classe dell'incidente `PRA-0000243`).

> Nota implementativa (fix minimo): `v_tipo_id` è già letto dalla pratica; basta leggere
> **anche** `p.definizione_id` nello stesso SELECT e usarlo nei due WHERE (in 2.1 il join è
> già sulla pratica → sostituire solo il predicato). Il **come** resta scelta del team DB.

## 3. Stato: latente, non attivo

Verificato sul DB vivo: **nessun tipo ha oggi più di una definizione** (0 fork nei dati);
per il tipo 9004 (PREVENTIVI) una sola definizione (id 7, 6 template, 0 `chiude_pratica`,
4 obbligatori). Con una definizione per tipo il join per-tipo ≡ per-definizione ⇒ **oggi il
comportamento è corretto**. Nessuna corruzione in corso, **nessun dato da riparare**. Il
bug si manifesta alla **prima** `fn_fork_definizione` / `fn_nuova_versione_definizione` +
`fn_pubblica_definizione` di un tipo che abbia una pratica in volo.

## 4. Criteri di accettazione

1. Su una pratica di una definizione **forkata** (Fase 2): `get_percorso_pratica`,
   `fn_check_chiusura_pratica` e l'auto-chiusura considerano **solo** i template della sua
   definizione (nessuna riga da altre edizioni del tipo).
2. Comportamento **invariato** con una definizione per tipo (verificato lato BE: 6 step per
   la pratica 317, identici per tipo e per definizione).
3. Auto-chiusura: una pratica forkata si chiude quando (e solo quando) i **suoi** obbligatori
   + chiusura sono completi; nessuna chiusura prematura, nessun errore su chiusura multipla.
4. **pgTAP nuovo**: caso con due definizioni dello stesso tipo (preset + fork pubblicata) e
   una pratica per ciascuna, con set di obbligatori/chiusura **diversi** fra le edizioni,
   verificando l'isolamento in chiusura e auto-chiusura. I test attuali
   (`test-autochiusura-pratica.sql`, `test-workflow-definizioni-fase2*.sql`) non lo coprono
   (passano perché non incrociano due definizioni con auto-chiusura).

## 5. Cosa è GIÀ corretto (audit positivo — scope del fix è ristretto)

Verificato corretto e completo, **nessun intervento richiesto**:

- Backfill `definizione_id` NOT NULL su `template_flussi` e `pratiche`.
- Unique migrati a definizione: `uq_template_flussi_definizione_codice (definizione_id, codice)`
  e `uq_template_flussi_chiusura_definizione (definizione_id) WHERE chiude_pratica`.
- `fn_risolvi_definizione`: risoluzione emittente-PUBBLICATA → preset-PUBBLICATA →
  `DEFINIZIONE_NON_TROVATA` (design §3.4).
- Pin: `trgfn_pratiche_default_definizione` pinna via `fn_risolvi_definizione(tipo, emittente)`.
- Guard flusso↔definizione: `trgfn_flussi_guard_definizione` (`FLUSSI_TEMPLATE_FUORI_DEFINIZIONE`).
- Immutabilità strutturale PUBBLICATA (design C4/C6): guard su `template_flussi` **e tutti i
  figli** (`_prerequisiti`, `_canali`, `_handler_eventi`, `competenze_flussi`,
  `formule_tempo`, `calcoli_tempo`, `regole_generazione`) + pin pratica immutabile.
- `fn_genera_pratica_da_flusso` resa definizione-aware; `fn_copia_definizione`,
  `fn_fork_e_nuova_versione_definizione`, `fn_pubblica_definizione`, `fn_check_definizione_
  congelata` presenti.
- `fn_check_prerequisiti_flusso` e `fn_check_ripetibilita_flusso`: già fork-safe (per
  `template_flusso_id`).

## 6. Fuori scope

- Consumi BE/FE: già fork-safe (`get_percorso_pratica` corretto; audit BE+FE completo →
  nessun altro punto seleziona template per tipo). **Nessun intervento BE/FE** da questo brief.
- Endpoint admin fork/pubblica (Fase 2, cantiere V4/V5): non toccati qui.

---

*Brief DB — completamento fork-aware di Fase 1: `fn_check_chiusura_pratica` e
`trgfn_flussi_autochiusura_pratica` devono scopare i template per `definizione_id`, non per
`tipo_prestazione_id`. Latente (0 fork oggi) ma bloccante alla prima fork. Tutto il resto
della Fase 0/1/2 è verificato corretto. Scoperto auditando dopo i merge Fase 2.*
