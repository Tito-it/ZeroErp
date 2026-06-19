# Brief DB — Assegnazione del flusso a operatore/reparto + giornale

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟢 normale — prerequisito di coerenza per il filone
> "assegnazione flusso a operatore/reparto" (il BE `assegna_flusso` può iniziare prima, ma
> la semantica completa — presa libera, coda reparto, tracciamento — dipende da qui).
> **Data**: 2026-06-18 (chiuso 2026-06-19) · **Stato**: ✅ **COMPLETATO** — DB `20260618-05..08`
> applicati e committati; BE+FE implementati, testati e documentati (vedi
> [brief-design-assegnazione-flusso-user-reparto.md](brief-design-assegnazione-flusso-user-reparto.md) §esito).
>
> **Design autorevole**:
> [brief-design-assegnazione-flusso-user-reparto.md](brief-design-assegnazione-flusso-user-reparto.md)
> (policy §2.2). Questo brief contiene **solo** ciò che serve a DB.
>
> **Decisioni prese (2026-06-18)**: DEC-1 caso C → livello **LIBERO** all'operatore della pratica ·
> DEC-2 **due** codici (`FLUSSI_COMPETENZA_MANCANTE` A/D, `FLUSSI_PRESA_NON_ELIGIBILE` 496 per B) ·
> DEC-3 **(a)** `FLUSSO_ASSEGNAZIONE_CAMBIATA` (ALTER CHECK) · DEC-4 `origine='UTENTE'` (pratica resta SISTEMA) ·
> DEC-5 `competenze_flussi.unita_organizzativa_id` non più usata qui (voluto) · DEC-6 nessun guard `attivo`.
> Refinement: **skill-lock = competenza ATTIVA** (non "qualsiasi riga") per evitare flussi non prendibili.
>
> **Deliverable scritti**: `20_code/pratiche/20260618-05` (prendi_in_carico eligibilità A/B/C/D) ·
> `-06` (coda 4 livelli, REPARTO anagrafico + LIBERO) · `-07` (ALTER chk_giornale_azione) ·
> `-08` (trigger giornale assegnazione flusso) · codice 496 in `messaggi_errore.csv` (loader runOnChange) ·
> pgTAP `db/pgtap/pratiche/test-assegnazione-flusso-eligibilita.sql` (plan 10). **Applicati e committati.**

---

## 1. Contesto e modello deciso

Le colonne di routing **esistono già** su `pratiche.flussi`: `risorsa_umana_id` (operatore)
e `unita_organizzativa_id` (reparto), nullable, con FK. Esiste anche
`risorse_umane.unita_organizzativa_id` (reparto **anagrafico** dell'operatore, FK
`fk_risorse_umane_unita_organizzative`). **Nessuna modifica di schema** richiesta.

Policy di eligibilità decisa (**reparto-first + competenza opzionale**) — per un flusso `F`
`DA_ESEGUIRE` non assegnato e operatore `O`:

- **skill-lock** = ∃ riga `competenze_flussi` per `F.template_flusso_id`;
- **competente** = ∃ riga `competenze_flussi(template=F.template, operatore=O, attivo)`;
- **nel-reparto** = `F.unita_organizzativa_id IS NOT NULL AND O.unita_organizzativa_id = F.unita_organizzativa_id`.

| Caso | F | Eligibile se |
|---|---|---|
| A — reparto + skill | reparto valorizzato, skill-lock presente | `competente` |
| B — reparto, no skill | reparto valorizzato, skill-lock assente | `nel-reparto` |
| C — niente configurato | reparto NULL, skill-lock assente | **libero** (chiunque) |
| D — skill senza reparto | reparto NULL, skill-lock presente | `competente` |

Cambio rispetto a oggi: ① la competenza passa da **obbligatoria** a **condizionale**;
② il livello REPARTO della coda usa il reparto **anagrafico**, non i reparti-da-competenza.

## 2. Intervento 1 — `fn_prendi_in_carico_flusso` (competenza condizionale)

Oggi (`docs/it/dbzero/pratiche/funzioni/fn_prendi_in_carico_flusso.md`) la regola 4 richiede
**sempre** competenza per i flussi template-based (errore `FLUSSI_COMPETENZA_MANCANTE`).
Sostituire quel blocco con la **policy §1** (recuperare anche `F.unita_organizzativa_id` nel
`SELECT ... FOR UPDATE` iniziale e il reparto anagrafico dell'operatore):

```sql
-- Pseudologica (dopo i guard stato/già-assegnato esistenti):
-- has_skill_lock = EXISTS(competenze_flussi WHERE template = v_template_id)
-- competente     = EXISTS(competenze_flussi WHERE template = v_template_id
--                          AND risorsa_umana_id = p_risorsa_umana_id AND attivo)
-- nel_reparto    = v_unita_org IS NOT NULL
--                  AND v_unita_org = (SELECT unita_organizzativa_id
--                                       FROM anagrafiche.risorse_umane
--                                      WHERE id = p_risorsa_umana_id)
-- eligibile = CASE
--    WHEN has_skill_lock THEN competente           -- casi A, D
--    WHEN v_unita_org IS NOT NULL THEN nel_reparto  -- caso B
--    ELSE true                                       -- caso C (presa libera)
-- END
-- IF NOT eligibile -> raise FLUSSI_PRESA_NON_ELIGIBILE (nuovo codice, vedi sotto)
```

- Nuovo codice errore parlante suggerito **`FLUSSI_PRESA_NON_ELIGIBILE`** (sostituisce/affianca
  `FLUSSI_COMPETENZA_MANCANTE`, che resta valido come sotto-caso A/D). Registrarlo nei
  messaggi errore se serve un HTTP/azione UI dedicato.
- Resta invariato: lock `FOR UPDATE`, guard stato `DA_ESEGUIRE`, guard già-assegnato,
  noop se stesso operatore.

## 3. Intervento 2 — `fn_coda_lavoro_operatore` (REPARTO su reparto anagrafico)

Oggi (`docs/it/dbzero/pratiche/funzioni/fn_coda_lavoro_operatore.md`) tutti e 3 i livelli
sono filtrati dalla matrice; il livello REPARTO usa `competenze_op.unita_organizzativa_id`.
Allineare alla policy §1:

- **ASSEGNATO** — invariato (`f.risorsa_umana_id = p_risorsa_umana_id`).
- **COMPETENZA** — invariato (non assegnato, `DA_ESEGUIRE`, operatore competente per il
  template) → "posso prenderlo per skill" (casi A/D).
- **REPARTO** — ridefinire: flussi non assegnati il cui `f.unita_organizzativa_id` =
  **reparto anagrafico** dell'operatore (`risorse_umane.unita_organizzativa_id`), per i
  quali NON esiste skill-lock (caso B) — così appaiono in coda solo dove la presa è
  effettivamente libera nel reparto. (Con skill-lock presente, la riga emerge come
  COMPETENZA per i soli competenti, non come REPARTO per tutti.)
- Mantenere la mutua esclusività dei livelli (priorità ASSEGNATO > COMPETENZA > REPARTO).
- Il reparto anagrafico si risolve con un JOIN a `risorse_umane` su `p_risorsa_umana_id`.

## 4. Intervento 3 — Trigger giornale assegnazione flusso

Su `pratiche.flussi` mancano i giornali del cambio assegnazione (la pratica ha
`trgfn_pratiche_giornale_assegnazione`). Aggiungere mirror:

```text
trg_flussi_z90_giornale_assegnazione_upd
  AFTER UPDATE OF risorsa_umana_id, unita_organizzativa_id ON pratiche.flussi
  → trgfn_flussi_giornale_assegnazione()
```

- Scrive in `pratiche.giornale` con `pratica_id = NEW.pratica_id`, `flusso_id = NEW.id`,
  `origine` UTENTE, `dettaglio` JSONB con OLD/NEW di `risorsa_umana_id` +
  `unita_organizzativa_id`; `tx_id` valorizzato.
- Guard `IS DISTINCT FROM` su almeno uno dei due campi (no righe a vuoto).

**Azione giornale — decisione richiesta** (CHECK `chk_giornale_azione`, oggi 11 valori):

| | Opzione | Pro | Contro |
|---|---|---|---|
| **(a) consigliata** | nuovo valore `FLUSSO_ASSEGNAZIONE_CAMBIATA` | simmetrico a `FLUSSO_STATO_CAMBIATO`; rendering/filtri chiari | ALTER del CHECK + label i18n FE (`pratiche.giornale_azioni.*` + `azioneGiornaleStyle`) |
| (b) | riuso `ASSEGNAZIONE_CAMBIATA` con `flusso_id` valorizzato | nessun ALTER | rompe simmetria pratica/flusso; FE distingue per `flusso_id IS NOT NULL` |

## 5. Test pgTAP

- **prendi_in_carico**: casi A (competente ok / non competente ko), B (membro reparto ok /
  non membro ko), C (chiunque ok), D (competente ok / non competente ko); più i guard
  esistenti (stato, già-assegnato, noop).
- **coda lavoro**: un flusso appare nel livello corretto per ciascun caso A–D; mutua
  esclusività; esclusione pratiche terminali invariata.
- **giornale**: riga scritta su cambio `risorsa_umana_id` e/o `unita_organizzativa_id`;
  nessuna riga se invariati; `dettaglio`/`flusso_id`/`pratica_id` corretti; (opz. a) valore
  azione ammesso dal CHECK.

## 6. Coordinamento audit utente (Part B)

⚠️ Allinearsi con [brief-db-audit-user-pratiche.md](../work-in-progress/brief-db-audit-user-pratiche.md)
(**Part B**): il giornale è append-only e attribuisce a `zeroerp_app` finché il default
`user_insert` non è GUC-aware
(`COALESCE(NULLIF(current_setting('app.jwt_user',true),''),CURRENT_USER)`). La riga
giornale dell'assegnazione flusso eredita lo stesso percorso — nessun lavoro extra qui, solo
consapevolezza che i due interventi toccano lo stesso meccanismo.

## 7. Cosa NON serve

- Nessuna modifica di schema su `pratiche.flussi` / `risorse_umane` (colonne + FK presenti).
- Nessun guard "operatore appartiene al reparto" sull'UPDATE di `flussi`: in questa fase è un
  vincolo UX (picker filtrato), non DB.
