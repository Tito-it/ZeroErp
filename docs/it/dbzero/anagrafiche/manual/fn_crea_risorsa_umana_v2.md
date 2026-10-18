# fn_crea_risorsa_umana_v2

### Scopo

Building block transazionale per creare una **risorsa umana operatore**:
inserisce contestualmente `risorse_umane`, `identita_digitali` (ruolo
applicativo `OPERATORE`) e — se richiesto — il binding `SUPER_ADMIN` su
`profili_accesso_bindings`.

Sostituisce `fn_crea_risorsa_umana` v1 (droppata in Fase 7, 2026-04-29):
v1 aveva firma con `p_ruolo_sistema config.ruolo_sistema` (enum legacy).
La v2 espone la stessa logica con **firma multi-face native**:
`p_is_super_admin boolean` + `p_attivo boolean`.

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_crea_operatore_v2](/dbzero/anagrafiche/manual/fn_crea_operatore_v2) — orchestratore che la chiama
> - [identita_digitali](/dbzero/anagrafiche/manual/identita_digitali) — tabella scritta
> - [profili_accesso_bindings](/dbzero/config/manual/profili_accesso_bindings) — tabella binding SUPER_ADMIN

## Schema

`anagrafiche` (dominio risorse umane).

## Firma

```sql
anagrafiche.fn_crea_risorsa_umana_v2(
    p_soggetto_id            anagrafiche.soggetti.id%TYPE,
    p_qualifica_id           config.qualifiche.id%TYPE,
    p_unita_organizzativa_id config.unita_organizzative.id%TYPE,
    p_valido_dal             anagrafiche.risorse_umane.valido_dal%TYPE,
    p_valido_al              anagrafiche.risorse_umane.valido_al%TYPE,
    p_auth_user_id           INTEGER,
    p_is_super_admin         BOOLEAN  DEFAULT false,
    p_attivo                 anagrafiche.identita_digitali.attivo%TYPE  DEFAULT true
) RETURNS anagrafiche.risorse_umane.id%TYPE
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_soggetto_id` | `anagrafiche.soggetti.id%TYPE` (uuid) | Sì | Soggetto persona fisica esistente. |
| `p_qualifica_id` | `config.qualifiche.id%TYPE` | Sì, `> 0` | Qualifica attiva (validata). |
| `p_unita_organizzativa_id` | `config.unita_organizzative.id%TYPE` | No | UO attiva, validata se valorizzata. |
| `p_valido_dal` | `risorse_umane.valido_dal%TYPE` | No (default `CURRENT_DATE`) | Inizio finestra temporale risorsa umana. |
| `p_valido_al` | `risorse_umane.valido_al%TYPE` | No | Fine finestra. |
| `p_auth_user_id` | `INTEGER` (django.auth_user.id, no `%TYPE` su django.*) | No | Se valorizzato, crea anche identita digitale OPERATORE + binding opzionale SA. |
| `p_is_super_admin` | `BOOLEAN` | No (default `false`) | Se `true`, crea binding SUPER_ADMIN sull'identita digitale. **Differenza chiave vs v1**: prima si passava `p_ruolo_sistema='ADMIN'` (enum); ora si esprime direttamente la capability boolean. |
| `p_attivo` | `identita_digitali.attivo%TYPE` (boolean) | No (default `true`) | Stato di `identita_digitali.attivo`. **Nuovo in v2**: in v1 era hardcoded `true`. Il chiamante può creare un'identita pre-disattivata (caso onboarding sospeso). |

Ritorna l'`id` della `risorsa_umana` creata.

## Algoritmo

1. **Validazione parametri obbligatori** (raise `E_ADMIN_VALIDAZIONE` se mancanti):
   `p_soggetto_id`, `p_qualifica_id`.
2. **Guard prerequisiti**:
   - qualifica esistente e `attivo=true`,
   - UO esistente e `attivo=true` se valorizzata,
   - auth_user esistente se valorizzato (raise `E_ADMIN_VALIDAZIONE` o `E_ADMIN_UO_NON_TROVATA`),
   - se `p_is_super_admin`: il profilo SUPER_ADMIN si **risolve prima di ogni scrittura** con
     [`config.fn_profilo_super_admin_id`](/dbzero/config/manual/fn_profilo_super_admin_id), che
     solleva `E_CONFIG_MANCANTE` se i profili attivi di quel tipo non sono esattamente uno.
3. **Step 1**: `script.fn_get_or_create_soggetto_ruolo(p_soggetto_id, 'RIS_UMANA')` → upsert ruolo.
4. **Step 2**: `INSERT INTO risorse_umane` (`attivo=true` hardcoded — il flag `p_attivo` riguarda solo l'identita digitale, non la risorsa).
5. **Step 3** (se `p_auth_user_id IS NOT NULL`): `INSERT INTO identita_digitali`
   con `ruolo_applicativo='OPERATORE'` e `attivo=p_attivo`.
6. **Step 4** (se `p_is_super_admin=true`): il legame lo scrive la madre
   [`config.fn_lega_profilo_identita`](/dbzero/config/manual/fn_lega_profilo_identita) sul profilo
   risolto al passo 2 (dal 18-10-2026, `20261018-45`).

## Regole

- Nessuna scrittura su `anagrafiche.risorse_umane_auth_user` (post-cutover §13.3 è una vista; i trigger-ponte sono stati droppati).
- Il profilo del binding SUPER_ADMIN **non è più cablato** (fino al 23-09-2026 era l'id 9100 del seed): si
  risolve per `tipo`, fra i profili attivi, esattamente uno. Dal 18-10-2026 (R-BE-11, `20261019-17`) la regola
  sta nel lettore `config.fn_profilo_super_admin_id`, sede unica: era scritta qui e nel backend.
- La fn è **transazionale**: se uno qualunque degli step fallisce, l'intera operazione è rolled-back (caller responsibility usare `BEGIN…COMMIT`).
- Errori applicativi via `script.fn_log_and_raise_error` (codici stabili `E_ADMIN_VALIDAZIONE`, `E_ADMIN_UO_NON_TROVATA`).

## Differenze vs v1 (droppata)

| Aspetto | v1 (droppata 2026-04-29) | v2 (questa) |
|---|---|---|
| Firma capability | `p_ruolo_sistema config.ruolo_sistema` (enum `ADMIN`/`OPERATIVO`/`DISABILITATO`) | `p_is_super_admin boolean` + `p_attivo boolean` |
| Mapping interno | `IF p_ruolo_sistema='ADMIN' THEN INSERT binding...` | `IF p_is_super_admin THEN INSERT binding...` |
| Stato `identita.attivo` | hardcoded `true` | parametrizzato (`p_attivo`) |
| Tipo enum legacy | richiede `config.ruolo_sistema` | indipendente — abilita `DROP TYPE` finale (Fase 7 step 9) |

## Dipendenze

- `script.fn_get_or_create_soggetto_ruolo` (upsert ruolo)
- `script.fn_log_and_raise_error` (errori standardizzati)
- `config.qualifiche`, `config.unita_organizzative` (lookup)
- `django.auth_user` (FK validation)
- `anagrafiche.risorse_umane`, `anagrafiche.identita_digitali` (write)
- `config.profili_accesso_bindings` (write opzionale binding SA)

## Chi la chiama

- `anagrafiche.fn_crea_operatore_v2` (orchestratore)
- BE: `apps.amm_software.db.amm_software_repository.create_operatore` post-Fase 7 LANDED (nessun `_legacy_ruolo_from_contract` residuo)
- BE: `apps.core.db.risorse_umane_core_repository.create_risorsa_umana`

## Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/anagrafiche/20260429-12-create-fn-crea-risorsa-umana-v2-mctit.yaml`
- Drop v1: `db/changelog/migrations_v2/20_code/anagrafiche/20260429-16-drop-fn-crea-risorsa-umana-v1-mctit.yaml`
- Brief Fase 7: handoff BE refactor `analisi-refactor.frontend-amm-software` (2026-04-29 LANDED)

## Esempio

```sql
-- Operatore standard (non admin)
SELECT anagrafiche.fn_crea_risorsa_umana_v2(
    p_soggetto_id            := '...uuid...',
    p_qualifica_id           := 1,
    p_unita_organizzativa_id := 5,
    p_valido_dal             := CURRENT_DATE,
    p_auth_user_id           := 42
);
-- → crea RU + identita OPERATORE attiva, NO binding SA

-- Operatore super admin
SELECT anagrafiche.fn_crea_risorsa_umana_v2(
    p_soggetto_id    := '...uuid...',
    p_qualifica_id   := 1,
    p_auth_user_id   := 42,
    p_is_super_admin := true
);
-- → crea RU + identita OPERATORE + binding SUPER_ADMIN

-- Operatore pre-disattivato (onboarding sospeso)
SELECT anagrafiche.fn_crea_risorsa_umana_v2(
    p_soggetto_id  := '...uuid...',
    p_qualifica_id := 1,
    p_auth_user_id := 42,
    p_attivo       := false
);
-- → identita_digitali.attivo = false (capability nuova v2)
```
