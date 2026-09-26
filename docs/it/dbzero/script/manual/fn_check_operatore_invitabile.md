# fn_check_operatore_invitabile

### Scopo

Dice se un operatore puo' ricevere l'**invito che accende la sua veste
OPERATORE**. Ritorna un JSONB con esito, motivo (codice macchina e chiave
i18n) e indirizzo email, e non solleva mai.

⭐ **La regola unica dell'invito** (dal 2026-09-25, `20260925-43`;
brief-db-blocco-login-per-credenziale §12, D-8 dell'analisi accessi): la veste
OPERATORE **nasce spenta** ([`fn_crea_operatore_v2`](/dbzero/anagrafiche/manual/fn_crea_operatore_v2))
e la accende l'attivazione dell'invito; il reinvito riapre una veste spenta.
Quindi si invita chi ha una veste **spenta**, e una veste gia' attiva si
rifiuta: l'accesso c'e' gia', e per una password dimenticata c'e' il reset.

Fino a quel giorno la regola era il contrario — veste attiva, `is_active`
vero, `last_login` vuoto — e con la veste che nasce spenta un operatore appena
creato non sarebbe mai stato invitabile.

La chiamano il backend prima di preparare l'invito, e
`script.fn_get_operatore_detail` per la capability `can_invite` (`reason` e
`reason_key` diventano `invite_reason` e `invite_reason_key`).

## Condizioni di invitabilita'

Tutte devono essere soddisfatte, in quest'ordine (il primo motivo vince):

| # | Condizione | `reason` se non soddisfatta | `reason_key` |
|---|-----------|-----------------------------|--------------|
| 1 | `auth_user` esiste (id non `NULL`, > 0) | `UTENTE_NON_TROVATO` | `amministrazione.operatori.invito_reason.utente_non_trovato` |
| 2 | almeno una veste OPERATORE | `SENZA_VESTE_OPERATORE` | `amministrazione.operatori.invito_reason.senza_veste_operatore` |
| 3 | **nessuna** veste OPERATORE attiva | `VESTE_GIA_ATTIVA` | `amministrazione.operatori.invito_reason.veste_gia_attiva` |
| 3-bis | **una sola** veste OPERATORE | `PIU_VESTI_SPENTE` | `amministrazione.operatori.invito_reason.piu_vesti_spente` |
| 4 | la veste nella sua finestra (`valido_dal`/`valido_al`) | `VESTE_FUORI_FINESTRA` | `amministrazione.operatori.invito_reason.veste_fuori_finestra` |
| 5 | `auth_user.email` valorizzata | `SENZA_EMAIL` | `amministrazione.operatori.invito_reason.senza_email` |

⭐ **Il motivo è un codice, non una frase** (dal 2026-09-27, `20260927-01`;
brief-db-blocco-login-per-credenziale §16). Il testo vive nei `locales` del
frontend, sotto la `reason_key`: è la regola del trasporto delle capability
([linee-guida-sql §12](/linee-guida-sql)). Fino a quel giorno la funzione
restituiva `motivo`, una frase italiana che arrivava tale e quale al drawer e al
messaggio d'errore dell'invito; quella chiave non c'è più. I codici non hanno il
prefisso `E_`: sono motivi, non codici a catalogo.

⛔ **Non contano piu'**:

- `last_login` (D-8): l'ultimo accesso non decide chi si invita;
- `auth_user.is_active`: e' **derivato** dalle vesti
  (`fn_sync_auth_user_is_active`), quindi con la sola veste spenta e' `false`
  per costruzione.

⚠️ Il modello ammette piu' vesti OPERATORE spente sulla stessa credenziale
(l'unicita' e' solo fra le attive; la madre dal 2026-09-25 non ne crea piu'):
la funzione le **aggrega** invece di prenderne una a caso. E con piu' di una
(nessuna attiva) **non invita** (condizione 3-bis, dal 2026-09-25,
`20260925-53`): l'invito riaccende **una** veste, e niente dice quale. Fino a
quel giorno la funzione rispondeva «invitabile», e l'invito del backend poi
rifiutava: il pulsante c'era e l'azione falliva.

## Caratteristiche

- **STABLE**, plpgsql (nomina `django.auth_user`: niente `%TYPE` su Django)
- **Non solleva**: `p_auth_user_id` NULL o <= 0 → `{invitabile: false, reason: UTENTE_NON_TROVATO}`

## Risultato

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `invitabile` | boolean | `true` se tutte le condizioni sono soddisfatte |
| `reason` | text | Codice del primo motivo di rifiuto (NULL se invitabile) |
| `reason_key` | text | Chiave i18n del motivo (NULL se invitabile) |
| `email` | text | Indirizzo email della credenziale |

## Esempio

```sql
-- Operatore appena creato: veste spenta
SELECT script.fn_check_operatore_invitabile(42);
-- {"invitabile": true, "reason": null, "reason_key": null, "email": "mario.rossi@azienda.it"}

-- Operatore con la veste gia' accesa
SELECT script.fn_check_operatore_invitabile(10);
-- {"invitabile": false, "reason": "VESTE_GIA_ATTIVA",
--  "reason_key": "amministrazione.operatori.invito_reason.veste_gia_attiva",
--  "email": "luca@azienda.it"}
```

Presidio: `db/pgtap/script/test-fn-check-operatore-invitabile.sql`.
