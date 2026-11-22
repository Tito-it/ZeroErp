# Brief DB — Accesso write editing strutturale BOZZA (prerequisito Slice 2)

> **✅ RISOLTO (2026-07-04)** dal team DB via **Option C** (changeset `20260704-01/-02/-03/-04`):
> grant DML su `template_flussi_handler_eventi` (Problema 1); nuovo predicato
> `fn_check_definizione_struttura_bloccata` (edit-lock = `stato <> 'BOZZA' AND emittente NOT NULL`)
> con guard riscritti INSERT/UPDATE→struttura_bloccata, DELETE→congelata; **RITIRATA edit-locked +
> delete consentito** (Problema 3, come proposto). Msg 514 generalizzato (sottostringhe stabili
> `per-emittente`/`congelata`). **Validato dal BE** sotto ruolo `zeroerp_app` (probe non-distruttiva
> in rollback): BOZZA editabile (incl. side-write storico/audit — Problema 2 coperto), PUBBLICATA/RITIRATA
> struttura→514 con `descrizione` correggibile («Leggera»), DELETE RITIRATA consentito. pgTAP team:
> `test-definizione-ritirata-edit-freeze.sql`. Residuo BE: marker 514 in `_KNOWN_DB_ERROR_MARKERS`
> (substring `per-emittente`) alla scrittura della BE editing Slice 2.
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🟠 MEDIA
> (prerequisito Slice 2 «editing strutturale BOZZA»; oggi il consumatore non esiste ancora
> → si sblocca il DB, poi BE/FE, memoria `feedback_be_fe_attende_prerequisiti_db`). ·
> **Data**: 2026-07-04.
> **Origine**: audit accessi/trigger sul percorso di scrittura di `template_flussi` + figli,
> fatto validando E2E Slice 1b (i preset con step, tipi 9002/9003/9004, sono pubblicabili;
> serve poterli **editare** in BOZZA per fork davvero utili).
> **Correlato**: `brief-db-accesso-be-definizioni-workflow.md` (P0 `GRANT SELECT` + P1
> DEFINER ciclo di vita — CHIUSO, in `work-done/`); `brief-design-workflow-definizioni-versionate.md`
> Fase 2 (immutabilità «Leggera»); tabella `template_flussi` + trigger `trgfn_template_flussi_guard_immutabile`.

---

## Contesto — cosa NON serve (rettifica dell'handoff)

L'handoff Slice 2 parlava genericamente di «accesso write ai guard immutabilità». L'audit
mostra che **i guard non sono il blocco**:

* `trgfn_template_flussi_guard_immutabile` / `..._figli_guard_immutabile` sono `INVOKER` ma
  leggono **solo `workflow_definizioni`** (via `fn_check_definizione_congelata`), su cui il
  ruolo app ha già `SELECT` (P0). Quindi **non falliscono** per permessi durante un write in BOZZA.
* `fn_check_definizione_congelata` ⇒ `congelata = (stato='PUBBLICATA' AND emittente_fiscale_id IS NOT NULL)`.
  Perciò **BOZZA è già editabile** by design (e anche il preset PUBBLICATA, `emittente NULL`,
  è editabile — coerente con la manutenzione via seed CSV).

Il blocco reale è di **grant DML** e di **audit del percorso di scrittura**.

## Problema 1 — 🟠 grant DML mancante su un figlio

I 6 figli di una definizione (copiati da `fn_copia_definizione`) e i loro grant per
`zeroerp_app`:

| Tabella figlia | Grant attuale app | Serve per editing BOZZA |
|---|---|---|
| `template_flussi` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| `template_flussi_canali` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| `template_flussi_prerequisiti` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| `competenze_flussi` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| `formule_tempo` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| `regole_generazione` | `SELECT,INSERT,UPDATE,DELETE` ✅ | ok |
| **`template_flussi_handler_eventi`** | **`SELECT` soltanto** ❌ | **manca `INSERT/UPDATE/DELETE`** |

`template_flussi_handler_eventi` è l'unica tabella del set senza DML: qualunque editing di
handler-eventi in BOZZA fallirebbe con «permesso negato». **Serve `GRANT INSERT, UPDATE,
DELETE ON pratiche.template_flussi_handler_eventi TO zeroerp_app`** (allineandola agli altri 5 figli).

## Problema 2 — 🟠 audit preventivo del percorso di scrittura (no bug-per-bug)

`template_flussi` ha **molti trigger `INVOKER`** che scattano su INSERT/UPDATE/DELETE e che,
sotto il ruolo web, potrebbero leggere/scrivere tabelle collaterali non grant-ate — il
classico downstream mai esercitato (memoria `feedback_audit_db_preventivo_smoke`: audit
completo PRIMA dello smoke, non a colpi di errore). In particolare:

* `trgfn_storico_generic` (z90, UPDATE/DELETE) → **scrive lo storico**: il ruolo app deve
  avere `INSERT` sulla tabella di storico di `template_flussi` **e di ciascuno dei 6 figli**.
* `trgfn_child_requires_active_parent`, `trgfn_prevent_deactivate_if_children`,
  `trgfn_template_flussi_guard_modalita_esito`, `trgfn_template_flussi_default_definizione`
  (INVOKER) → leggono tabelle padre/figlie: confermare che tutte le letture siano coperte da grant.
* `trgfn_template_flussi_default_definizione` (INSERT) **defaulta `definizione_id` al preset
  del tipo**: nell'editing di una BOZZA il BE passerà `definizione_id` esplicito, ma va
  confermato che il default non sovrascriva un valore esplicito (altrimenti gli step nuovi
  finirebbero sul preset invece che sulla BOZZA in editing).

### Cosa serve

Un **audit dei grant** (DML + storico + audit side-tables) su tutto il set editabile
(`template_flussi` + 6 figli) per il ruolo `zeroerp_app`, così che un INSERT/UPDATE/DELETE
su una BOZZA passi l'intera catena trigger senza «permesso negato». *Il come* (grant diretti
vs fn `SECURITY DEFINER` di editing mediato) è vostra scelta: i grant diretti sono coerenti
col fatto che il guard immutabilità è già la rete di sicurezza (blocca la PUBBLICATA-emittente).

## Problema 3 — 🟠 (modello) RITIRATA è editabile: voluto?

`congelata` esclude la RITIRATA (`stato='PUBBLICATA'` soltanto). Quindi una **RITIRATA**
(edizione storica, con pratiche pinnate) resta **strutturalmente editabile**. Sembra un bug
logico: editare i `template_flussi` di una RITIRATA cambierebbe retroattivamente la struttura
riferita da pratiche già pinnate a quella versione (memoria `feedback_bug_logici_modello`).
Proposta: `congelata` = `stato IN ('PUBBLICATA','RITIRATA') AND emittente_fiscale_id IS NOT NULL`
(il preset resta manutenibile via seed). **Da confermare con Tid/design-of-record** prima di
toccare la fn: se le RITIRATA vanno invece potute *cancellare* (housekeeping), è un asse
diverso (DELETE) dall'*editare*.

## Criteri di accettazione

1. Il ruolo `zeroerp_app` può fare INSERT/UPDATE/DELETE di uno **step + relativi figli** su
   una definizione **BOZZA** (compresi gli handler-eventi) attraversando tutta la catena
   trigger senza errori di permesso.
2. Le **stesse** operazioni su una definizione **PUBBLICATA-emittente** sono rifiutate con
   `TEMPLATE_DEFINIZIONE_CONGELATA` (immutabilità invariata).
3. Comportamento su **RITIRATA** deciso e coerente col punto 3 (freeze o editabile, esplicito).
4. INSERT di uno step in BOZZA con `definizione_id` esplicito → lo step resta sulla BOZZA
   (il default trigger non lo re-parenta al preset).
5. pgTAP: editing completo di una BOZZA (aggiunta/rimozione step, modifica prerequisiti,
   canali, handler-eventi, competenze, formule, regole) come `zeroerp_app` → verde; stesso
   editing su PUBBLICATA-emittente → rosso (guard).

## Fuori scope

* Guard `≤1 BOZZA per scope` e stato-sorgente di `nuova-versione` — vedi
  `brief-db-guard-bozza-unica-nuova-versione.md`.
* Le fn/endpoint BE e la UI di editing (Slice 2 BE/FE): partono **dopo** che questo accesso
  è pronto.
* Bootstrap definizione su nuovo `tipo_prestazione`
  (`trgfn_tipi_prestazione_bootstrap_definizione`, P1 storico) — nessun consumatore qui.
