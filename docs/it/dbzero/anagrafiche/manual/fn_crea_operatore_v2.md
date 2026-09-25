# fn_crea_operatore_v2

### Scopo

Orchestratore transazionale per la **creazione di un operatore**: la
credenziale (riusata o creata), il soggetto persona fisica (se nuovo), la
risorsa umana con la sua veste OPERATORE, l'eventuale binding SUPER_ADMIN e
gli indirizzi di residenza e domicilio fiscale.

Quattro regole la governano, dal 2026-09-25
(brief-db-blocco-login-per-credenziale §5.2 e §12):

1. **Una persona, una credenziale** (D-6). Se l'email ha già una credenziale —
   perché la persona è già cliente del portale o dello shop — la madre la
   **riusa**: non ne tocca password, username e nome. La cerca
   [`script.fn_get_auth_user_id_for_email`](/dbzero/script/funzioni/fn_get_auth_user_id_for_email),
   senza distinguere maiuscole e minuscole. Solo se non c'è la crea
   [`fn_crea_auth_user`](/dbzero/anagrafiche/manual/fn_crea_auth_user).
2. **La veste OPERATORE nasce spenta**, sempre: la accende l'attivazione
   dell'invito (regola unica dell'invito, uguale per ogni veste). Finché non è
   accesa la credenziale nuova ha `is_active = false`, e l'operatore è
   **invitabile** ([`fn_check_operatore_invitabile`](/dbzero/script/manual/fn_check_operatore_invitabile)).
   Il binding SUPER_ADMIN nasce comunque attivo: porta e profili sono due
   domande diverse, e i lettori dei permessi le chiedono entrambe (vedi
   [automazione DB](/guide/automazione-db), §4.2 «Le eccezioni»).
3. **Una credenziale che ha già una veste OPERATORE si rifiuta**, attiva o
   spenta, con `E_CREDENZIALE_GIA_OPERATORE`: una veste spenta è un invito
   pendente o un operatore disattivato, e il rimedio è il reinvito, non un
   secondo operatore sulla stessa persona. Le vesti col ruolo `DISABILITATO`
   non contano (il valore è in ritiro).
4. **Il riuso non è mai silenzioso** (dal 2026-09-25, `20260925-51`, §12.7 del
   brief). Un'email sbagliata non deve poter collegare la veste all'accesso di
   un'altra persona:
   - **dove il modello sa dire chi è la persona**, cioè quando la credenziale
     ha una veste su un soggetto **persona fisica**, quel soggetto dev'essere
     l'operatore: nel flusso B lo stesso soggetto, nel flusso A lo stesso
     codice fiscale. Altrimenti `E_CREDENZIALE_ALTRA_PERSONA`. Con lo stesso
     CF nel flusso A parla `fn_crea_soggetto_pf` (`E_ADMIN_CF_DUPLICATO`): la
     persona esiste già, e si sceglie il soggetto esistente;
   - **negli altri casi** (vesti su un cliente azienda, o nessuna veste) decide
     l'admin, con una **dichiarazione**: `p_riusa_auth_user_id` dev'essere la
     credenziale trovata. Senza, o con un'altra, `E_CREDENZIALE_DA_CONFERMARE`,
     con `auth_user_id`, `username` e `vesti` della credenziale nel contesto,
     per il dialog; il backend rimanda con l'id. Un id e non un sì/no: dice *a
     cosa* si è detto sì, e una credenziale cambiata fra il dialog e l'invio
     ferma di nuovo. Stampo: la dichiarazione di `pagamenti.fn_posta_contabile`.
     Il controllo sta **dopo** il soggetto, così i rifiuti definitivi parlano
     prima e l'admin non conferma qualcosa che sarebbe rifiutato comunque.

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [fn_crea_risorsa_umana_v2](/dbzero/anagrafiche/manual/fn_crea_risorsa_umana_v2) — building block chiamato
> - [fn_crea_auth_user](/dbzero/anagrafiche/manual/fn_crea_auth_user)
> - [fn_crea_soggetto_pf](/dbzero/anagrafiche/manual/fn_crea_soggetto_pf)
> - [fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto)

## Il contratto

Firma e ritorno sono nella doc auto-generata. Due cose da sapere:

- ritorna `TABLE(auth_user_id, username, credenziale_riusata)`, e si legge con
  `SELECT * FROM anagrafiche.fn_crea_operatore_v2(…)`. ⚠️ `SELECT fn(…)`
  consegnerebbe la tupla intera in un campo solo: un valore plausibile e falso;
- lo **username è quello effettivo**: su una credenziale riusata è il suo, non
  quello passato. Con `credenziale_riusata = true` anche la **password passata
  è ignorata**, e chi chiama deve dirlo a chi ha compilato il modulo.

`p_username` e `p_password_hash` servono solo quando la credenziale va creata:
li valida allora `fn_crea_auth_user`. L'email e la qualifica si validano
sempre.

## I passi

| Passo | Cosa |
|---|---|
| Guard | email e qualifica obbligatorie |
| 1 — credenziale | cerca per email: se c'è, `FOR UPDATE` sulla riga (due creazioni sulla stessa persona si serializzano), rifiuto se ha già una veste OPERATORE, rifiuto se una sua veste sta su un'altra persona fisica; altrimenti `fn_crea_auth_user` |
| 2 — soggetto | flusso **A** (nessun `p_soggetto_id`: cognome, nome e CF obbligatori, `fn_crea_soggetto_pf`) o **B** (soggetto esistente, dev'essere persona fisica) |
| 2-bis — consenso | `p_riusa_auth_user_id` deve dichiarare la credenziale trovata (`NULL` se l'email era nuova) |
| 3 — risorsa umana | `fn_crea_risorsa_umana_v2(…, p_attivo := false)`: risorsa umana attiva, veste OPERATORE **spenta**, binding SUPER_ADMIN se richiesto |
| 4 — indirizzi | se c'è `p_indirizzo_resid_dettaglio_id`: residenza e domicilio fiscale (fallback sulla residenza) |

Tutto in un'istruzione: se un passo fallisce non resta niente, neppure sulla
credenziale riusata.

## Codici errore

| Codice | Quando |
|---|---|
| `E_ADMIN_VALIDAZIONE` | email o qualifica mancanti; nel flusso A cognome, nome o CF mancanti; nel flusso B soggetto inesistente o non persona fisica |
| `E_CREDENZIALE_GIA_OPERATORE` | l'email appartiene a una credenziale che ha già una veste OPERATORE (attiva o spenta) |
| `E_CREDENZIALE_EMAIL_AMBIGUA` | più credenziali con la stessa email a meno delle maiuscole (dove l'indice unico non c'è) |
| `E_CREDENZIALE_ALTRA_PERSONA` | la credenziale ha una veste su una persona fisica che non è l'operatore |
| `E_CREDENZIALE_DA_CONFERMARE` | la credenziale esiste e `p_riusa_auth_user_id` non la dichiara (assente o diversa) |

Più quelli propagati da `fn_crea_auth_user`, `fn_crea_soggetto_pf` e
`fn_crea_risorsa_umana_v2`.

## Chi la chiama

- BE: `amm_software_repository.crea_operatore` (dal 2026-09-25 deve passare
  senza `p_attivo` e leggere la `TABLE`: lotto L-3 del piano BE/FE).
- DB: `dbops.fn_pgtap_crea_operatore_umano` (fixture pgTAP: dopo la madre fa
  il passo dell'attivazione, accende la veste).
- pgTAP: `test-fn-crea-operatore`, `test-crea-operatore-riusa-credenziale-v1`,
  `test-risorse-umane-guard-identita-attiva-v1`,
  `test-fn-check-operatore-invitabile`, `test-automazione-attivo-eccezioni-v1`.

## Storia

- 2026-04-29: nasce la v2 (firma con `p_is_super_admin`), la v1 con l'enum
  `config.ruolo_sistema` è ritirata.
- 2026-09-25 (`20260925-42`): riuso della credenziale, veste spenta,
  `p_attivo` fuori dalla firma, ritorno `TABLE`.
- 2026-09-25 (`20260925-51`): il riuso non è più silenzioso — altra persona
  rifiutata, consenso dichiarato con `p_riusa_auth_user_id` (in coda alla firma).

## Esempio

```sql
-- Operatore nuovo (flusso A). Se l'email e' gia' di un cliente del portale la
-- prima chiamata si ferma con E_CREDENZIALE_DA_CONFERMARE (username e vesti nel
-- contesto); confermato, si rimanda con p_riusa_auth_user_id := <auth_user_id
-- mostrato>: credenziale_riusata = true, password ignorata.
SELECT *
  FROM anagrafiche.fn_crea_operatore_v2(
         p_cognome           := 'Rossi',
         p_nome              := 'Mario',
         p_codice_fiscale    := 'RSSMRA80A01F205X',
         p_username          := 'm.rossi',
         p_email             := 'm.rossi@example.com',
         p_password_hash     := '...',
         p_qualifica_id      := 1,
         p_is_super_admin    := false);
-- → (auth_user_id, username effettivo, credenziale_riusata); veste spenta,
--   l'operatore riceve l'invito che la accende.
```
