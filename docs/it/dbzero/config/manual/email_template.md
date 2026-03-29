## Documentazione Concettuale -- Tabella `config.email_template`

> Vedi anche
>
> Approfondimento tabelle:
>
> [config.email_account](/dbzero/config/tabelle/email_account)
> [config.email_log](/dbzero/config/tabelle/email_log)
> [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative)
> [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)

---

### 🎯 Scopo Principale

La tabella `config.email_template` contiene i **template email parametrizzabili** con variabili `{{...}}`. Ogni template puo' essere specializzato per reparto, tipo prestazione e lingua, con una catena di fallback a 5 livelli.

---

### Catena di risoluzione (fallback)

Data una richiesta con codice, reparto, tipo prestazione e lingua, il sistema cerca il primo template attivo in quest'ordine:

1. **Reparto + tipo prestazione + lingua** -- massima specializzazione
2. **Reparto + lingua** -- generico per il reparto
3. **Sistema + tipo prestazione + lingua** -- specializzato per tipo, senza reparto
4. **Sistema + lingua** -- generico di sistema
5. **Sistema + lingua `it`** -- fallback finale

Questo permette di avere testi diversi per la stessa azione in contesti diversi. Esempio: "Invia comunicazione" da una pratica di reclamo del reparto Acquisti usa un testo diverso da un'offerta del reparto Commerciale.

---

### Variabili

Il campo `variabili_disponibili` (JSONB array) documenta i placeholder accettati. Esempio:

```json
["nome", "cognome", "azienda", "link", "scadenza_ore"]
```

Il rendering sostituisce `{{nome}}` con il valore passato dal chiamante. Le variabili sono documentative per l'UI admin (non validate a livello DB).

---

### Vincoli e regole

* UNIQUE su `(codice, unita_organizzativa_id, tipo_prestazione_id, lingua)` con `NULLS NOT DISTINCT` -- ogni combinazione e' univoca, anche con NULL.
* `codice` identifica il tipo di template (es. `INVITO_OPERATORE`, `RESET_PASSWORD`, `COMUNICAZIONE_PRATICA`).
* `unita_organizzativa_id = NULL` indica un template di sistema/default.
* `tipo_prestazione_id = NULL` indica un template generico (non legato a un tipo pratica).
* Campi `corpo_html` (obbligatorio) e `corpo_testo` (opzionale, fallback plaintext).

---

### Template di sistema previsti (seed)

| codice                     | Fase | Variabili principali                                    |
| -------------------------- | ---- | ------------------------------------------------------- |
| `INVITO_OPERATORE`         | 3    | nome, cognome, azienda, link, scadenza_ore, invitato_da |
| `RESET_PASSWORD`           | 2    | nome, azienda, link, scadenza_ore                       |
| `CAMBIO_PASSWORD_CONFERMA` | 1    | nome, azienda, data_cambio                              |
| `NOTIFICA_GENERICA`        | 1    | oggetto_custom, corpo_custom                            |

---

### Estensibilita'

* Nuovi template di sistema: inserire con `unita_organizzativa_id = NULL` e `tipo_prestazione_id = NULL`.
* Override per reparto: inserire con lo stesso `codice` ma `unita_organizzativa_id` valorizzato.
* Override per tipo pratica: inserire con `tipo_prestazione_id` valorizzato.
