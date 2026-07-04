# Brief DB — Accesso ruolo BE alle definizioni workflow (prerequisito Fase 2 consumi)

> **STATO (2026-07-03)** — **§0 P0 ✅ RISOLTO** dal team DB via `GRANT SELECT` su
> `workflow_definizioni` + `vw_definizioni_drift` al ruolo `zeroerp_app`: creazione pratica
> di nuovo funzionante, **letture aperte**.
>
> **✅ P1 — RISOLTO (2026-07-03)**: il team DB ha convertito `fn_fork_definizione` /
> `fn_nuova_versione_definizione` / `fn_pubblica_definizione` a `SECURITY DEFINER` +
> `SET search_path=pg_catalog, pratiche, script, config, dbops, pg_temp` (path allargato
> ma fisso — motivato: la catena trigger cross-schema audit/tx_id/storico/lock+guard eredita
> quel path; `pg_catalog`-only la romperebbe; l'app non ha CREATE su quegli schemi → hardened).
> `fn_copia_definizione` resta INVOKER (interna, chiamata solo dai wrapper DEFINER → eredita
> il contesto). Verificato dal BE: `fn_fork_definizione` **supera "permesso negato"** e
> raggiunge il trigger tx_id → accesso DML risolto. La scrittura E2E persistita si testa via
> app (contesto tx_id/dblink per-request). Gate: **AdminAPIView (super-admin)**. Bootstrap
> tipo + guard immutabilità restano deferiti (nessun consumatore).
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: ~~🔴 ALTA~~
> → **P0 + P1 chiusi**. · **Data**: 2026-07-03.
> **Correlato**: `brief-db-step-dominio-e-definizioni-versionate.md` (Parte 2),
> `brief-be-fe-step-dominio-e-definizioni-versionate.md` (BE-2.3 / FE-2.4),
> `brief-design-workflow-definizioni-versionate.md` §5 (Fase 3 UI admin).

---

## 0. 🔴 CRITICO — la creazione di pratica è rotta (regressione Fase 1)

Il pin di Fase 1 fa fallire **ogni** `INSERT` di pratica dal web. Catena reale
(request_id `d8d33015-…`, riprodotta creando una nuova pratica):

```text
trgfn_pratiche_default_definizione()   -- pin su INSERT pratica (Fase 1)
  → fn_risolvi_definizione(tipo, emittente)   [SECURITY INVOKER]
     → SELECT wd.id FROM pratiche.workflow_definizioni wd ...   → permesso negato
```

`fn_risolvi_definizione` gira con i privilegi del **chiamante** (`zeroerp_app`, ruolo web),
che non ha `SELECT` su `pratiche.workflow_definizioni` → il trigger di pin aborta l'INSERT →
il BE lo restituisce come `E_DATABASE` generico (non è un marker noto).

**Fix (minimo, sicuro)**: `fn_risolvi_definizione` deve poter leggere `workflow_definizioni`
a prescindere dal chiamante → renderla **`SECURITY DEFINER`** (legge solo per risolvere
l'edizione; nessuna scrittura). In alternativa `GRANT SELECT` sulla tabella al ruolo app.
Questo sblocca sia la creazione (pin trigger) sia la **generazione** cross-pratica
(`fn_genera_pratica_da_flusso` risolve la definizione via la stessa fn).

**Raggio d'azione completo (incoerenza sistemica)**: `workflow_definizioni` è senza grant al
ruolo app, ma **tutte e 9** le funzioni che la toccano sono `SECURITY INVOKER` → falliscono
tutte se invocate dal web. Vanno rese accessibili (DEFINER o grant mirati) secondo il percorso:

| Funzione | Accesso | Percorso che si rompe | Prio |
| --- | --- | --- | --- |
| `fn_risolvi_definizione` | legge | **creazione + generazione pratica** | 🔴 P0 |
| `trgfn_tipi_prestazione_bootstrap_definizione` | scrive | creazione nuovo tipo_prestazione | 🟠 P1 |
| `trgfn_template_flussi_guard_immutabile` | legge | editing `template_flussi` | 🟠 P1 |
| `trgfn_template_flussi_figli_guard_immutabile` | legge | editing figli template (prereq/canali/handler/…) | 🟠 P1 |
| `trgfn_workflow_definizioni_guard` | legge | modifica edizioni (admin) | 🟠 P1 |
| `fn_copia_definizione` / `fn_fork_definizione` | scrive | fork edizione (Fase 2) | 🟠 P1 |
| `fn_nuova_versione_definizione` | legge/scrive | nuova versione (Fase 2) | 🟠 P1 |
| `fn_pubblica_definizione` | scrive | pubblicazione (Fase 2) | 🟠 P1 |
| `fn_check_definizione_congelata` | legge | usata dai guard immutabilità | 🟠 P1 |

> Nota: la scelta "tabella schermata + funzioni SECURITY DEFINER" (strada B in §2) risolve
> tutto in un colpo e resta coerente con la postura di sicurezza. In quel caso **niente**
> grant diretto sulla tabella: solo le funzioni la toccano, come definer.

**Accettazione §0**: creare una nuova pratica dal web (ruolo `zeroerp_app`) **riesce**; il pin
`definizione_id` viene risolto senza "permesso negato". (P0 sblocca il core; le P1 sbloccano
admin/config e Fase 2.)

---

## 1. Problema

I consumi Fase 2 (UI admin edizioni: lista + drift + fork/nuova-versione/pubblica) girano,
a livello DB, come il **ruolo applicativo web `zeroerp_app`** (unico role della connessione
BE, anche per gli endpoint admin). Verificato sul DB vivo che quel ruolo **non ha alcun
accesso** all'oggetto centrale:

- `SELECT` su `pratiche.workflow_definizioni` → **permesso negato**;
- `SELECT` su `pratiche.vw_definizioni_drift` → **permesso negato**;
- `information_schema.role_table_grants`: **nessun grant** (né SELECT né DML) per
  `zeroerp_app`/`PUBLIC` su questi oggetti.
- Le fn azione `fn_fork_definizione`, `fn_nuova_versione_definizione`,
  `fn_pubblica_definizione` sono **`SECURITY INVOKER`** (non DEFINER): `zeroerp_app` può
  chiamarle (`EXECUTE` ok) ma la loro **DML interna** su `workflow_definizioni` fallirebbe
  (il chiamante non ha privilegi sulla tabella).

Nessuna fn di **lettura** (list/get) delle definizioni esiste oggi.

Finché questo non è risolto, il BE non può né listare le edizioni né eseguire le azioni:
lo Slice 1 di Fase 2 è **bloccato**.

## 2. Cosa serve (accesso, non implementazione specifica)

Il BE deve poter, come `zeroerp_app` (mantenendo il gate di autorizzazione dove preferite —
vedi §3):

1. **Leggere** l'elenco delle edizioni per (tipo prestazione [, emittente]) con: `id`,
   `tipo_prestazione_id`, `emittente_fiscale_id` (NULL = preset), `versione`, `stato`
   (BOZZA/PUBBLICATA/RITIRATA), `descrizione`, provenance (`preset_origine_id`,
   `versione_origine`), audit.
2. **Leggere il drift** da `vw_definizioni_drift` (`versioni_indietro`, `preset_corrente_id`,
   `versione_preset_corrente`, `stato_edizione`…) per il banner "preset aggiornato".
3. **Eseguire end-to-end** `fn_fork_definizione`, `fn_nuova_versione_definizione`,
   `fn_pubblica_definizione` (la DML interna deve andare a buon fine).

Il **come** è vostra scelta; due strade tipiche:

- **A. Grant + RLS**: `GRANT SELECT` su tabella/vista al ruolo app (+ eventuale policy RLS
  coerente col resto), e `GRANT`/riscrittura in `SECURITY DEFINER` delle 3 fn azione (o
  grant DML mirati) così la DML interna passa.
- **B. Fn SECURITY DEFINER dedicate**: una `fn_list_definizioni(...)` (+ lettura drift) e le
  3 azioni rese `SECURITY DEFINER`, esponendo al BE **solo** le fn (nessun grant diretto
  sulla tabella). Coerente con la postura "tabella di config non toccabile direttamente".

Preferenza BE (non vincolante): **B** — superfici funzione esplicite, tabella schermata,
niente RLS nuova da ragionare. Ma seguite la convenzione di casa.

## 3. Nota permessi (coordinamento, non blocca la scelta DB)

L'autorizzazione **applicativa** (chi può gestire le edizioni) è ortogonale all'accesso DB:
a livello connessione resta `zeroerp_app`. Lato app la gestiremo con `AdminAPIView`
(super-admin) oppure un permesso di processo dedicato — decisione in corso con l'owner. Se
scegliete la strada **A** con RLS, valutate se la visibilità/scrittura deve dipendere dal
contesto operatore (GUC `app.*`) o restare aperta al ruolo app con gate solo applicativo.

## 4. Criteri di accettazione

1. `zeroerp_app` può leggere l'elenco definizioni + drift (via grant o via fn dedicata).
2. `zeroerp_app` può invocare `fn_fork_definizione` / `fn_nuova_versione_definizione` /
   `fn_pubblica_definizione` **end-to-end** (nessun "permesso negato" sulla DML interna).
3. Nessuna regressione di sicurezza: gli operatori normali non ottengono un accesso non
   voluto (se strada A+RLS, policy coerente; se strada B, EXECUTE mirato).

## 5. Fuori scope

- Editing strutturale di una BOZZA (`template_flussi` + figli scoped a definizione): Slice 2,
  brief a parte quando serve.
- Scelta app-layer AdminAPIView vs permesso di processo: decisione owner, non DB.

---

*Brief DB — prerequisito accesso: il ruolo BE `zeroerp_app` deve poter leggere le edizioni
workflow (+ drift) ed eseguire fork/nuova-versione/pubblica end-to-end. Oggi permesso negato
su `workflow_definizioni`/`vw_definizioni_drift` e fn azione non SECURITY DEFINER.*
