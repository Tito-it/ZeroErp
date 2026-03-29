## Documentazione Concettuale -- Tabella `config.token_monouso`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_log](/dbzero/config/tabelle/email_log)
> [config.email_template](/dbzero/config/tabelle/email_template)

---

### 🎯 Scopo Principale

La tabella `config.token_monouso` implementa un **meccanismo generico di token monouso** riutilizzabile per qualsiasi flusso che richieda un link sicuro con scadenza: invito operatore, reset password, conferma email, attivazione account.

---

### Sicurezza: hash-only

Il token in chiaro **non viene mai salvato** nel database. Il flusso:

1. Il sistema genera un token casuale (32 bytes, 64 caratteri hex)
2. Salva nel DB solo l'**hash SHA-256** del token
3. Invia il token in chiaro all'utente (via email)
4. Alla ricezione, il sistema calcola SHA-256 del token ricevuto e cerca il match

Questo impedisce che un accesso al DB (backup, dump, SQL injection) esponga token validi.

---

### Ciclo di vita

```
Creazione → token attivo (utilizzato = false)
  → Utente lo usa → utilizzato = true, utilizzato_at + ip_utilizzo registrati
  → Token scaduto → ignorato in fase di validazione
  → Cleanup periodico → fn_cleanup_token_scaduti() elimina i vecchi
```

---

### Tipi previsti

| tipo               | Fase   | Scadenza | Uso                               |
| ------------------ | ------ | -------- | --------------------------------- |
| `INVITO_OPERATORE` | 3      | 72 ore   | Link di attivazione primo accesso |
| `RESET_PASSWORD`   | 2      | 1 ora    | Link reset password dimenticata   |
| `CONFERMA_EMAIL`   | futuro | 24 ore   | Conferma cambio indirizzo email   |

---

### Invalidazione

Quando si crea un nuovo token dello stesso tipo per lo stesso utente, il `TokenService` invalida automaticamente i token precedenti (marca come utilizzati). Questo impedisce che link vecchi restino attivi.

---

### Pulizia periodica

La funzione `config.fn_cleanup_token_scaduti(p_giorni_retention)` elimina:

* Token scaduti da piu' di N giorni
* Token utilizzati da piu' di N giorni

Eseguibile come job pgAgent notturno. Default retention: 30 giorni.

---

### Indici

* `(tipo, auth_user_id, utilizzato)` -- lookup per validazione e invalidazione
* `scadenza` -- per cleanup periodico
* `token_hash` UNIQUE -- per match rapido
