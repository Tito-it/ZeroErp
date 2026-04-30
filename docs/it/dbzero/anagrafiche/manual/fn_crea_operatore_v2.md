# fn_crea_operatore_v2

### Scopo

Orchestratore transazionale per la **creazione completa di un operatore**:
crea l'utente Django, il soggetto persona fisica (se nuovo), la risorsa
umana con identita digitale OPERATORE, l'eventuale binding SUPER_ADMIN
e gli indirizzi RESID/DOMFISC opzionali.

Sostituisce `fn_crea_operatore` v1 (droppata in Fase 7, 2026-04-29):
v1 aveva firma con `p_ruolo_sistema config.ruolo_sistema` (enum legacy).
La v2 espone la stessa logica con **firma multi-face native**:
`p_is_super_admin boolean` + `p_attivo boolean`, e chiama internamente
`fn_crea_risorsa_umana_v2` invece di v1.

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_crea_risorsa_umana_v2](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana_v2) — building block chiamato
> - [fn_crea_auth_user](/dbzero/anagrafiche/manual/fn_crea_auth_user)
> - [fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf)
> - [fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto)

## Schema

`anagrafiche` (orchestratore di dominio).

## Firma

```sql
anagrafiche.fn_crea_operatore_v2(
    p_soggetto_id                    anagrafiche.soggetti.id%TYPE,
    p_cognome                        anagrafiche.soggetti.cognome%TYPE,
    p_nome                           anagrafiche.soggetti.nome%TYPE,
    p_codice_fiscale                 anagrafiche.soggetti.codice_fiscale%TYPE,
    p_username                       text,
    p_email                          text,
    p_password_hash                  text,
    p_qualifica_id                   config.qualifiche.id%TYPE,
    p_unita_organizzativa_id         config.unita_organizzative.id%TYPE,
    p_data_nascita                   anagrafiche.soggetti.data_nascita%TYPE,
    p_sesso                          anagrafiche.soggetti.sesso%TYPE,
    p_is_super_admin                 boolean,
    p_attivo                         anagrafiche.identita_digitali.attivo%TYPE,
    p_valido_dal                     anagrafiche.risorse_umane.valido_dal%TYPE,
    p_valido_al                      anagrafiche.risorse_umane.valido_al%TYPE,
    p_comune_nascita_id              config.comuni.id%TYPE,
    p_indirizzo_resid_dettaglio_id   anagrafiche.indirizzi_dettaglio.id%TYPE,
    p_indirizzo_domfisc_dettaglio_id anagrafiche.indirizzi_dettaglio.id%TYPE
) RETURNS integer
```

Tutti i parametri hanno default `NULL` (eccetto `p_sesso` default `'M'`,
`p_is_super_admin` default `false`, `p_attivo` default `true`,
`p_valido_dal` default `CURRENT_DATE`).

## Due flussi

| Flusso | Trigger | Step principali |
|---|---|---|
| **A** — soggetto nuovo | `p_soggetto_id IS NULL` | guard cognome/nome/CF obbligatori → `fn_crea_soggetto_pf` → ... |
| **B** — soggetto esistente | `p_soggetto_id` valorizzato | guard tipo PF → riusa il soggetto |

In entrambi i flussi la sequenza completa è:

1. Guard comuni: `p_username`, `p_email`, `p_password_hash`, `p_qualifica_id` obbligatori.
2. **Step 1** — `fn_crea_auth_user`: crea l'utente Django con username/email/password hash + first_name/last_name.
3. **Step 2** — biforcazione flusso A/B sul soggetto.
4. **Step 3** — `fn_crea_risorsa_umana_v2(... p_is_super_admin, p_attivo, ...)`: building block che costruisce RU + identita OPERATORE (+ binding SA opzionale).
5. **Step 4** (se `p_indirizzo_resid_dettaglio_id` valorizzato): `fn_crea_indirizzo_soggetto` per RESID + DOMFISC (DOMFISC fallback su RESID).

Ritorna `auth_user.id` dell'utente creato.

## Differenze vs v1 (droppata)

| Aspetto | v1 (droppata 2026-04-29) | v2 (questa) |
|---|---|---|
| Firma capability | `p_ruolo_sistema config.ruolo_sistema` | `p_is_super_admin boolean` + `p_attivo boolean` |
| Building block chiamato | `fn_crea_risorsa_umana` v1 | `fn_crea_risorsa_umana_v2` |
| Stato attivo identita | non parametrizzabile (sempre attiva) | `p_attivo` propagato fino al building block |
| Dipendenza enum legacy | sì (`config.ruolo_sistema`) | no — abilita `DROP TYPE` finale (Fase 7 step 9) |

## Codici errore

Tutti via `script.fn_log_and_raise_error`:

| Codice | Quando |
|---|---|
| `E_ADMIN_VALIDAZIONE` | parametri obbligatori mancanti, soggetto inesistente, soggetto non PF, qualifica non trovata, auth_user inesistente |
| `E_ADMIN_UO_NON_TROVATA` | UO non esistente o disattiva (delegato da building block v2) |

(Errori del sub-call `fn_crea_auth_user`/`fn_crea_soggetto_pf`/`fn_crea_risorsa_umana_v2` propagati.)

## Dipendenze

- `anagrafiche.fn_crea_auth_user` (Django user)
- `anagrafiche.fn_crea_soggetto_pf` (flusso A)
- `anagrafiche.fn_crea_risorsa_umana_v2` (building block multi-face)
- `anagrafiche.fn_crea_indirizzo_soggetto` (RESID/DOMFISC opzionali)
- `script.fn_log_and_raise_error`

## Chi la chiama

- BE: `apps.amm_software.services.amm_software_service.create_operatore` (post-Fase 7 LANDED, chiama direttamente v2 con `p_is_super_admin`/`p_attivo`)
- pgTAP: `db/pgtap/anagrafiche/test-fn-crea-operatore.sql` (post-Fase 7 step 4, in pending al momento della scrittura)

## Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/anagrafiche/20260429-13-create-fn-crea-operatore-v2-mctit.yaml`
- Drop v1: `db/changelog/migrations_v2/20_code/anagrafiche/20260429-17-drop-fn-crea-operatore-v1-mctit.yaml`
- Brief Fase 7: handoff BE refactor `analisi-refactor.frontend-amm-software` (2026-04-29 LANDED)

## Esempio

```sql
-- Onboarding nuovo operatore standard (flusso A — soggetto nuovo)
SELECT anagrafiche.fn_crea_operatore_v2(
    p_cognome           := 'Rossi',
    p_nome              := 'Mario',
    p_codice_fiscale    := 'RSSMRA80A01F205X',
    p_username          := 'm.rossi',
    p_email             := 'm.rossi@example.com',
    p_password_hash     := '...',
    p_qualifica_id      := 1,
    p_data_nascita      := DATE '1980-01-01',
    p_comune_nascita_id := 12345
);
-- → ritorna auth_user.id del nuovo operatore

-- Promozione iniziale a super admin
SELECT anagrafiche.fn_crea_operatore_v2(
    p_cognome        := 'Bianchi', p_nome := 'Anna',
    p_codice_fiscale := 'BNCNNA75A41L219Y',
    p_username       := 'a.bianchi', p_email := 'a.bianchi@ex.com',
    p_password_hash  := '...',
    p_qualifica_id   := 1,
    p_is_super_admin := true
);
-- → operatore + binding SUPER_ADMIN
```
