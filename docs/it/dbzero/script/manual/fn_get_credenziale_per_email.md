# fn_get_credenziale_per_email

### Scopo

Dice **quale credenziale porta un'email, con il suo username e le sue vesti**.
Serve all'amministratore che sta creando un operatore e deve decidere se
**riusare** l'accesso che quella persona ha già, per esempio come cliente del
portale o dello shop.

È la sede unica di questa lettura (regola del 2, dal 2026-09-27,
brief-db-blocco-login-per-credenziale §17). La leggono:

- la madre [`fn_crea_operatore_v2`](/dbzero/anagrafiche/manual/fn_crea_operatore_v2),
  quando rifiuta il riuso non confermato (`E_CREDENZIALE_DA_CONFERMARE`);
- il backend, per il dialog di conferma che mostra all'amministratore la
  credenziale trovata.

Dialog e rifiuto mostrano così **la stessa cosa**. Prima i dati del dialog
stavano solo nel contesto dell'errore, che finisce nel log e al client non
arriva.

## Cosa restituisce

`TABLE(auth_user_id, username, vesti)`:

| L'email… | Risposta |
| --- | --- |
| non ha una credenziale (anche `NULL`, vuota o di soli spazi) | **zero righe** |
| ha una credenziale senza vesti | una riga, con `vesti = []` |
| ha una credenziale con delle vesti | una riga, con le vesti |

`vesti` è un array, in ordine di id, di oggetti con `ruolo_applicativo`,
`attivo` e `soggetto` (la denominazione del soggetto della veste).

La credenziale la trova
[`fn_get_auth_user_id_for_email`](/dbzero/script/manual/fn_get_auth_user_id_for_email):
senza distinguere maiuscole e minuscole, e con `E_CREDENZIALE_EMAIL_AMBIGUA`
se due credenziali hanno la stessa email.

## Chi può chiamarla

**Nessun guard di permesso a DB** (decisione di Tid, 2026-09-27). Dice se
un'email ha un accesso e con quali vesti, quindi è un'informazione da
amministratore: la protegge la porta del backend (`AdminAPIView`, cioè solo i
SUPER_ADMIN). Un guard qui:

- cambierebbe il rifiuto della madre: chi non è SUPER_ADMIN leggerebbe
  `E_PERMESSO_NEGATO` invece di `E_CREDENZIALE_DA_CONFERMARE`;
- non chiuderebbe niente, perché l'applicazione legge già le tabelle da cui
  la funzione prende i dati. Il modello «una scrittura = un verbo» chiude le
  scritture, non le letture.

plpgsql e tipi espliciti perché nomina `django.*`; `STABLE`, `INVOKER`: le
vesti si leggono con la visibilità di chi chiama.

Presidio: `db/pgtap/script/test-fn-get-credenziale-per-email-v1.sql`.

## Esempio

```sql
SELECT * FROM script.fn_get_credenziale_per_email('Mario.Rossi@example.com');
-- → (42, 'mario.rossi@example.com',
--    [{"ruolo_applicativo": "CLIENTE_PORTALE", "attivo": true, "soggetto": "Rossi Srl"}])
```

## Storia

- 2026-09-27 (`20260927-40`): nasce per il dialog di conferma del riuso (§17
  del brief); la madre la legge dal `20260927-41`.
