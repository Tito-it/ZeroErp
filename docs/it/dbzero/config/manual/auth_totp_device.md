## Documentazione Concettuale -- Tabella `config.auth_totp_device`

> Vedi anche
>
> Approfondimento tabelle:
>
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)

---

### 🎯 Scopo Principale

La tabella `config.auth_totp_device` gestisce i **device TOTP** per l'autenticazione a due fattori (2FA). Relazione 1:1 con `auth_user`: ogni utente puo' avere al massimo un device TOTP configurato.

---

### Sicurezza

* Il **secret TOTP** e' salvato crittografato con Fernet (chiave derivata da `Django SECRET_KEY`). Non viene mai esposto in chiaro dopo il setup iniziale.
* I **recovery codes** sono salvati come array di hash SHA-256. I codici in chiaro vengono mostrati all'utente una sola volta (al momento della generazione) e non sono mai recuperabili dal DB.
* **Anti-replay**: il campo `ultimo_codice_usato` impedisce il riutilizzo dello stesso codice TOTP nello stesso intervallo temporale (30 secondi).

---

### Ciclo di vita

```
1. Setup: TotpService.setup_device(auth_user_id)
   → genera secret, salva crittografato
   → genera 10 recovery codes, salva hash
   → abilitato=false, confermato=false
   → ritorna QR code + recovery codes (unica volta in chiaro)

2. Conferma: TotpService.confirm_setup(auth_user_id, codice)
   → verifica primo codice TOTP
   → se valido: confermato=true, abilitato=true

3. Login 2FA:
   → Step 1: username+password → two_factor_required=true
   → Step 2: codice TOTP → verifica → rilascio JWT

4. Disabilitazione (admin o utente):
   → abilitato=false, secret e recovery codes cancellati
```

---

### Recovery codes

10 codici monouso generati al setup. Ogni utilizzo:
1. Hash del codice inserito confrontato con l'array
2. Se match: codice rimosso dall'array (monouso)
3. Ritorna quanti codici restano

Rigenerazione possibile solo con verifica codice TOTP corrente (conferma identita').

---

### Vincoli e regole

* UNIQUE su `auth_user_id` — relazione 1:1
* `confermato` diventa `true` solo dopo la prima verifica riuscita durante il setup
* `abilitato AND confermato` = device attivo per il login 2FA
* `ultimo_codice_usato` aggiornato ad ogni verifica riuscita (anti-replay)

---

### Collegamento con risorse_umane_auth_user

Il campo `totp_obbligatorio` su `anagrafiche.risorse_umane_auth_user` determina se l'operatore **deve** configurare il 2FA. Se `totp_obbligatorio=true` e il device non e' configurato (`abilitato=false` o record assente), un middleware blocca la navigazione e forza il setup.
