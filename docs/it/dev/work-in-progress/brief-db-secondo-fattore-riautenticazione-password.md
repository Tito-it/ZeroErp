# Brief BE → DB — Secondo fattore: la password per registrare il device

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`).
> **Origine:** revisione del giro BE/FE del secondo fattore (chiuso in
> [brief-be-fe-sicurezza-header-token-mfa.md](../work-done/brief-be-fe-sicurezza-header-token-mfa.md) §3.4-bis).
> **Decisione di Tid (2026-10-02):** `registra/` chiede la password della credenziale.
> **Stato:** ⏳ in attesa del team DB (R-1). Il BE/FE parte dopo, sul codice applicato.

## 1. Il problema

`POST /api/v1/auth/secondo-fattore/registra/` e `conferma/` chiedono la sola sessione.
Chi tiene una sessione rubata di un utente **senza device** (con o senza obbligo) può
legare il **proprio** telefono: al login dopo, il titolare si ferma al secondo passo e
resta fuori.

È la stessa debolezza che la decisione 7 ha chiuso per la disattivazione («una sessione
rubata da sola non spegne il secondo fattore»), dal verso opposto: qui la sessione da sola
lo **accende per conto di un altro**. Il cambio password chiede già la password attuale;
la registrazione del secondo fattore no.

## 2. Cosa farà il backend (dopo R-1)

* `registra/` vuole `{password}`. Prima di tutto il freno della credenziale
  (`check_blocco_login`), poi `check_password`.
* Password sbagliata = **tentativo fallito** (D-T2, `script.fn_registra_tentativo_login`
  con `successo = false`), come un codice sbagliato: chi tiene la sessione non deve poter
  provare password senza freno. Password giusta: non azzera i tentativi (non è un login).
* La regola vale **sempre**, anche al primo accesso con l'obbligo: una sola regola, e la
  pagina «Sicurezza» chiede la password nello stesso modulo che avvia la configurazione.
* `conferma/` resta com'è: chiude una configurazione che `registra/` ha già protetto.

## 3. Richieste al team DB

| # | Cosa | Perché |
| --- | --- | --- |
| **R-1** | Codice nuovo `E_TOTP_PASSWORD_NON_VALIDA`, classe `DATO_ERRATO`, campo `password`, in `codici_errore.csv` e `messaggi_errore.csv` (it, con causa e soluzione). Proposta di frase: «Password non corretta.» — causa «La password non è quella dell'accesso.», soluzione «Inserire la password con cui si accede.». Lo solleva il **backend** (la verifica della password è di Django), come `E_TOTP_CODICE_NON_VALIDO`; conta come tentativo fallito (D-T2) | Nessun codice a catalogo dice «password sbagliata» fuori dal cambio password: `E_CHANGE_PASSWORD` è di un'altra operazione; `E_AUTHENTICATION_FAILED` è un 401, e un 401 sul frontend fa partire il rinnovo della sessione e poi il logout |

Dopo l'apply il BE rigenera `error_policies_generated.py` e aggiunge il ripiego senza
segnaposto in `error_messages_fallback.py`.

## 4. Ordine

1. DB: R-1 (seed dei due CSV), apply e corsa pgTAP di Tid.
2. BE: `registra/` con la password e il freno; test (password giusta, sbagliata che conta,
   assente, credenziale bloccata); manuale `api_secondo_fattore.md`.
3. FE: il campo password nel modulo di avvio della configurazione in `SicurezzaView`.
