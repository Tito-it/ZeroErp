# fn_get_auth_user_id_for_email

### Scopo

Dice **quale credenziale** (`django.auth_user.id`) porta un'email, **senza
distinguere maiuscole e minuscole**. `NULL` se nessuna.

È la sede unica di questa regola (regola del 2, dal 2026-09-25,
brief-db-blocco-login-per-credenziale §5): la chiedono il guard di unicità di
[`fn_crea_auth_user`](/dbzero/anagrafiche/manual/fn_crea_auth_user), la madre
[`fn_crea_operatore_v2`](/dbzero/anagrafiche/manual/fn_crea_operatore_v2) per
riusare la credenziale di una persona (D-6), e il backend dell'invito
portale/shop, che fino a quel giorno la riscriveva in Python. Dal 2026-09-27 la
chiama anche
[`fn_get_credenziale_per_email`](/dbzero/script/manual/fn_get_credenziale_per_email),
che aggiunge username e vesti per il dialog di conferma del riuso.

## La regola

- confronto `lower(email) = lower(btrim(p_email))`: la stessa espressione
  dell'indice unico `ix_auth_user_email_lower_unique`, che quindi la serve;
- ⚠️ **l'email vuota non è una chiave**: nel modello di Django la colonna è
  `NOT NULL` e l'email mancante è `''`. Con `p_email` NULL, vuota o di soli spazi
  la risposta è `NULL`, mai «la prima credenziale senza email»;
- ⛔ **due credenziali con la stessa email → `E_CREDENZIALE_EMAIL_AMBIGUA`**
  (TECNICO), non la prima. L'indice unico le impedisce dove c'è; dove non c'è
  (in CI nasce dopo Django, quindi mai) il modello le ammette, e sceglierne una
  sarebbe un'ambiguità, non una scelta.

plpgsql e tipi espliciti perché nomina `django.*`; `STABLE`, `INVOKER`.

Presidio: `db/pgtap/anagrafiche/test-credenziale-email-unica-v1.sql`.
