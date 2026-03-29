## Documentazione Concettuale -- Tabella `config.email_log`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_account](/dbzero/config/tabelle/email_account)
> [config.email_template](/dbzero/config/tabelle/email_template)
> [config.email_outbox](/dbzero/config/tabelle/email_outbox)
> [config.email_allegato](/dbzero/config/tabelle/email_allegato)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---

### Scopo Principale

La tabella `config.email_log` registra **ogni email inviata dal sistema**, conservando il corpo esattamente come inviato (dopo eventuali modifiche manuali dall'outbox), lo stato di invio, il contesto e l'ambito di visibilita'.

---

### Ciclo di vita (stato)

```
PENDING → SENT     (invio riuscito)
PENDING → FAILED   (invio fallito)
FAILED  → RETRY    (tentativo successivo schedulato)
RETRY   → SENT     (retry riuscito)
RETRY   → FAILED   (retry fallito, tentativi < max_tentativi → nuova RETRY)
```

Il management command `send_pending_emails` processa le email PENDING e RETRY.

---

### Ambito di visibilita'

Ogni email ha un `ambito` che determina chi puo' consultarla:

| Ambito | Visibilita' |
|--------|------------|
| `SISTEMA` | Solo admin (email transazionali: inviti, reset, notifiche) |
| `REPARTO` | Tutti gli operatori dell'unita' organizzativa + admin |
| `OPERATORE` | Solo l'operatore che l'ha creata + admin |

Le email con `pratica_id` valorizzato sono inoltre visibili dalla scheda pratica, indipendentemente dall'ambito.

---

### Corpo inviato fedele

I campi `corpo_inviato_html` e `corpo_inviato_testo` conservano il testo **esattamente come inviato**. Questo e' diverso dal ri-renderizzare il template con le variabili originali (`contesto_json`): se l'operatore ha modificato il testo nell'outbox prima di inviare, il log riflette le modifiche.

---

### Collegamento a pratica

Il campo `pratica_id` collega l'email a una pratica. Dalla scheda pratica (tab "Comunicazioni") si vedono tutte le email inviate nel suo contesto, ricostruendo la storia comunicativa.

---

### Collegamento a outbox

Il campo `email_outbox_id` collega il log alla bozza che lo ha generato (se l'invio e' passato dall'outbox). Per invii diretti (senza anteprima, es. reset password self-service) il campo e' NULL.

---

### Indici principali

* `(stato, prossimo_tentativo)` -- per il command di retry
* `(ambito, unita_organizzativa_id)` -- per filtro reparto
* `pratica_id` -- per consultazione dalla pratica
* `auth_user_id` -- per filtro operatore destinatario
