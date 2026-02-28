## Documentazione Concettuale – Funzione `config.fn_get_override_scaduti`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> * [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)
> * [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni)

---

### Scopo Principale

(latest review 28-02-2026)
La funzione **`config.fn_get_override_scaduti`** restituisce tutti gli override
utente la cui data `valido_al` e scaduta. Unisce le 3 tabelle override
(aree, oggetti, azioni) in un unico risultato.

Utile per segnalazioni automatiche e pulizia periodica.

---

### Parametri di input

| Parametro | Tipo | Default | Descrizione |
| --------- | ---- | ------- | ----------- |
| `p_giorni_tolleranza` | integer | `0` | Ignora override scaduti da meno di N giorni. `0` = tutti gli scaduti. |

---

### Output

Ritorna una tabella con le colonne:

| Colonna | Tipo | Descrizione |
| ------- | ---- | ----------- |
| `tipo_override` | text | Tabella sorgente (`user_override_aree`, `user_override_oggetti`, `user_override_azioni`). |
| `override_id` | bigint | ID del record override. |
| `auth_user_id` | integer | ID dell'utente. |
| `dettaglio` | text | Descrizione leggibile (area/codice, model/livello, azione/abilitata). |
| `valido_al` | date | Data di scadenza dell'override. |
| `giorni_scaduto` | integer | Giorni trascorsi dalla scadenza. |

Ordinamento: `giorni_scaduto DESC`, `tipo_override`, `auth_user_id`.

---

### Regole principali

* Funzione **STABLE**.
* Filtra solo override con `valido_al IS NOT NULL` e scaduti oltre la tolleranza.
* Pensata per job schedulati (pgAgent) o API di monitoraggio.

---

### Esempio d'uso

```sql
-- Tutti gli override scaduti
SELECT * FROM config.fn_get_override_scaduti(0);

-- Override scaduti da piu di 7 giorni
SELECT * FROM config.fn_get_override_scaduti(7);
```

---

{% include-markdown "signature-core.md" %}
