# Estensione PostgreSQL: pgcrypto

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: chi pensa di cifrare, firmare o calcolare un hash dentro il database
>
> **Vedi anche**:
>
> * [Estensioni utilizzate](/postgresql/estensioni-utilizzate) — l'elenco completo e chi le crea
> * [Sicurezza e qualità statica](/dev/sicurezza-e-qualita-statica) — §«Le chiavi dei dati cifrati»: dove stanno davvero cifratura e chiavi
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — perché i segreti non vanno in un GUC

`pgcrypto` fornisce primitive crittografiche dentro PostgreSQL: hash (`digest`), HMAC (`hmac`), byte
casuali (`gen_random_bytes`), hash di password (`crypt` + `gen_salt`) e cifratura PGP simmetrica e
asimmetrica (`pgp_sym_*`, `pgp_pub_*`).

---

## Lo stato nel progetto

L'estensione è **installata** (la crea la baseline, `001-01-create-extensions`) ma, al 25 ottobre
2026, **nessun oggetto del database la usa**. Le cose per cui di solito la si installa stanno altrove:

| Bisogno | Dove sta |
| --- | --- |
| UUID | `uuidv7()` nei default delle colonne `uid`, `gen_random_uuid()` dove serve un UUID casuale: tutte e due sono del motore, non di `pgcrypto` |
| Password degli utenti | Django (hash e validatori), mai nel database applicativo |
| Segreti salvati nel DB (per esempio il segreto TOTP) | cifrati dal backend con chiavi **Fernet** (`crypto_service`, `DJANGO_FIELD_ENCRYPTION_KEYS`); la rotazione la fa il comando `ricifra_campi_cifrati` |
| Impronte e HMAC applicativi | il backend (`hashlib`, `salted_hmac`) |

---

## Se un lavoro nuovo ne ha bisogno

* **Chiavi e passphrase non stanno nel database**: né in una tabella, né nel codice SQL, né in un GUC.
  I GUC `app.*` portano l'identità della richiesta, non i segreti; un `ALTER DATABASE … SET` con una
  chiave la rende leggibile a chiunque legga le impostazioni.
* **Cifrare nel DB vuol dire che la chiave arriva al DB.** Prima di farlo, chiedersi perché non basti la
  cifratura del backend, che tiene le chiavi fuori dal database.
* **Password**: mai `md5()`/`sha1()`; se mai servisse un hash di password nel DB, `crypt()` con
  `gen_salt('bf')`.
* **Hash per la ricerca** (trovare una riga dalla sua impronta): `digest(…, 'sha256')` in una colonna
  `bytea` indicizzata; l'hash è CPU-bound, quindi si calcola una volta alla scrittura.
* **Dove si dichiara**: la funzione che la usa sta in `20_code`, e un pgTAP prova il risultato; se la
  si usa in un default di colonna, l'estensione deve esistere prima del changeSet della tabella.

---

## Troubleshooting

* `function digest(…) does not exist`: l'estensione manca nel **database corrente**, oppure lo schema in
  cui vive (`public`) non è nel `search_path` della funzione; nelle funzioni con `search_path` fissato
  si qualifica (`public.digest(…)`).
* `Wrong key or corrupt data`: passphrase o chiave sbagliata, o dato danneggiato.

---
{% include-markdown "signature-core.md" %}
