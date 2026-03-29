# fn_get_user_profile — aggiornamento auth flags

### Scopo

Documenta l'aggiornamento della funzione `script.fn_get_user_profile` (changeset -26) che aggiunge la chiave `deve_cambiare_password` al JSONB di ritorno.

> La documentazione principale della funzione e' in
> [fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile).
> Questa pagina documenta solo le modifiche introdotte per la gestione autenticazioni.

## Modifiche rispetto alla versione precedente

### Nuova variabile DECLARE

```sql
v_deve_cambiare_password  anagrafiche.risorse_umane_auth_user.deve_cambiare_password%TYPE;
```

### Modifica SELECT sezione 2

La query su `risorse_umane_auth_user` legge anche `deve_cambiare_password`:

```sql
SELECT rau.id,
       rau.ruolo_sistema,
       rau.risorsa_umana_id,
       rau.deve_cambiare_password    -- NUOVO
  INTO v_rau_id,
       v_ruolo_sistema,
       v_risorsa_umana_id,
       v_deve_cambiare_password      -- NUOVO
  FROM anagrafiche.risorse_umane_auth_user rau
 WHERE rau.auth_user_id = p_auth_user_id;
```

### Nuova chiave nel risultato finale (sezione 5)

```sql
v_result := jsonb_build_object(
    ...chiavi esistenti...,
    'deve_cambiare_password',  COALESCE(v_deve_cambiare_password, false)   -- NUOVO
);
```

## Nuova chiave nel JSONB di risposta

| Chiave | Tipo | Default | Descrizione |
|--------|------|---------|-------------|
| `deve_cambiare_password` | boolean | `false` | Se `true`, l'operatore deve cambiare password al prossimo login. Il frontend blocca la navigazione e mostra la pagina di cambio password |

## Flusso backend

```text
1. POST /api/v1/auth/login/
2. Backend chiama fn_get_user_profile(auth_user_id)
3. Se deve_cambiare_password = true:
   → Response include password_change_required: true
   → Middleware blocca tutti gli endpoint tranne:
     - POST /api/v1/auth/change-password/
     - POST /api/v1/auth/logout/
     - GET /api/v1/core/me/
4. Dopo cambio password:
   → deve_cambiare_password resettato a false
   → Nuovi token JWT rilasciati
```

## Retrocompatibilita'

Aggiunta pura: nuova chiave nel JSONB, nessuna chiave rimossa o rinominata. I consumer che non leggono `deve_cambiare_password` continuano a funzionare.

## Evoluzione futura (Fase 4 — 2FA)

Quando verra' implementata la Fase 4, un nuovo changeset aggiungera' le chiavi:

- `totp_abilitato` (boolean) — 2FA configurato e attivo
- `totp_obbligatorio` (boolean) — 2FA obbligatorio per l'operatore

Queste chiavi dipendono dalla tabella `config.auth_totp_device` che verra' creata in Fase 4.
