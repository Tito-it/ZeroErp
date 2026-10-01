# Brief DB — Il verbo che ri-cifra il segreto TOTP alla rotazione delle chiavi

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`).
> **Origine:** T-1 di [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md)
> §3.4-bis; decisione 9 di §6 (Tid, 2026-10-01: strada A).
> **Stato:** ✅ **DB consegnato il 2026-10-01**: `20261001-35` applicato da Tid, pgTAP senza
> regressioni (§5). ⏳ Resta il backend (§4).
> Prima riga di stato del giorno: «scritto lato DB, da applicare». Il backend va avanti con
> T-2, che non ne dipende; il segreto entra in `CAMPI_CIFRATI` all'arrivo del verbo, e **prima**
> che T-3 metta in esercizio la registrazione dei device.
>
> **Da leggere per primo: §5** — cosa è stato scritto, cosa è provato, cosa resta a Tid.
>
> **In una riga:** un verbo `script` che sostituisce `config.auth_totp_device.secret_encrypted`
> solo se è ancora il valore letto (confronta e sostituisci), perché il comando di rotazione
> delle chiavi non ha l'`UPDATE` su una tabella chiusa all'app.

---

## 1. Il difetto

* Il segreto TOTP è cifrato dal **backend** (`crypto_service`, `MultiFernet` sulle chiavi di
  `DJANGO_FIELD_ENCRYPTION_KEYS`): il DB non ha le chiavi e non può ri-cifrare.
* Quando le chiavi ruotano, `manage.py ricifra_campi_cifrati` apre ogni token iscritto in
  `CAMPI_CIFRATI` con una chiave qualunque, lo richiude con la prima e lo riscrive. Legge con
  `SELECT … FOR UPDATE` e scrive con un `UPDATE` diretto.
* Su `config.auth_totp_device` l'app ha il **solo `SELECT`** (`20260929-24`, la porta del brief
  `brief-db-secondo-fattore-totp`; verificato sul DB vivo il 2026-10-01: `UPDATE` = `false`).
  Iscritta in `CAMPI_CIFRATI`, la colonna farebbe fallire la rotazione; non iscritta, i segreti
  resterebbero sulla chiave vecchia e diventerebbero **illeggibili** il giorno in cui la si
  toglie: ogni persona col secondo fattore dovrebbe riconfigurare il telefono.

## 2. Il verbo

`script.fn_totp_ricifra_segreto(p_auth_user_id integer, p_secret_atteso varchar, p_secret_nuovo varchar) → boolean`

* **Confronta e sostituisci**, in una istruzione: `UPDATE … SET secret_encrypted = p_secret_nuovo
  WHERE auth_user_id = p_auth_user_id AND secret_encrypted = p_secret_atteso`. `true` se ha
  scritto, `false` se il segreto non è più quello letto (il device è stato riconfigurato o
  disabilitato nel frattempo): il comando lo conta e lo dice, non lo tratta come un errore.
* Vale per un device in **qualunque** stato (`DA_CONFERMARE` compreso: anche quel segreto va
  portato sulla chiave nuova).
* **Non tocca altro**: né `confermato`, né l'anti-replay, né i codici di recupero.
* Parametri `NULL` o vuoti, id `<= 0`, `atteso = nuovo` → `E_AUTH_CHIAMATA_NON_VALIDA` (nessuna
  interfaccia li produce: il chiamante è rotto).
* **Chi agisce: nessuno**, come `fn_totp_registra_uso` e `fn_totp_consuma_recovery`. Lo chiama un
  comando di manutenzione, senza un utente.
* `SECURITY DEFINER`, `search_path` bloccato, `EXECUTE` all'app; la tabella resta in sola lettura.

⚠️ **Il limite, da scrivere nella scheda.** Il verbo lascia al backend sostituire un segreto senza
dire chi è. Non gli dà un potere nuovo: il segreto lo può aprire solo il backend, che ha le chiavi,
e un backend capace di abusarne decide già chi entra. È il limite già scritto per i verbi del
dominio (PROJECT_CONTEXT, «il modello protegge da un backend che **sbaglia**, non da uno
**manomesso**»). Il confronto sul valore atteso protegge dall'errore vero: sovrascrivere un
segreto cambiato fra la lettura e la scrittura.

## 3. Prove (pgTAP)

1. sostituisce quando il valore atteso combacia, e restituisce `true`;
2. non sostituisce e restituisce `false` se il segreto è cambiato o il device non c'è;
3. non tocca `confermato`, `ultimo_passo_usato`, `recovery_codes_hash`;
4. i parametri rotti sollevano `E_AUTH_CHIAMATA_NON_VALIDA`;
5. la porta: l'app esegue il verbo, e continua a **non** avere `UPDATE` sulla tabella.

## 4. Cosa fa il backend dopo

* `CampoCifrato` impara a dire **come si scrive** una colonna: diretto (oggi, `email_account`)
  o attraverso un verbo con confronto (il TOTP). Per il TOTP il comando legge con un `SELECT`
  semplice, senza `FOR UPDATE`, perché il confronto lo fa il verbo;
* `config.auth_totp_device.secret_encrypted` entra in `CAMPI_CIFRATI`;
* `test_ricifra_campi_cifrati_db` aggiunge il caso del device e quello del segreto cambiato nel
  frattempo.

## 5. Consegna DB (2026-10-01)

### 5.1 Cosa è stato scritto

| File | Cosa |
| --- | --- |
| `20_code/script/20261001-35-create-fn-totp-ricifra-segreto-mctit.yaml` | il verbo, come in §2. Numero `-35`: il buco `-27 … -39` del giorno era libero (`-18 … -26` sono del cantiere magazzino, `-40` dell'esigibilità IVA) |
| `db/pgtap/config/test-totp-ricifra-segreto-v1.sql` (nuovo, plan 12) | prove 1-4 di §3: sostituisce e dà `true`; `false` su segreto cambiato e su device assente; non tocca `confermato`, passo, codici, `ultimo_uso_at`, `meta`; un device `DA_CONFERMARE` si ricifra e resta tale; quattro parametri rotti. I device li fabbricano i verbi del ciclo di vita, il verbo gira con `app.current_user_id` vuoto |
| `db/pgtap/config/test-totp-porta-v1.sql` | prova 5 di §3: il verbo entra nell'elenco del test 3 (`DEFINER`), e quindi nei test 4 (search_path), 5 (proprietario) e 6 (`EXECUTE` all'app). Il «niente `UPDATE` sulla tabella» lo provano già i test 1-2 |
| `docs/it/dbzero/script/manual/fn_totp_ricifra_segreto.md` (nuovo) | la scheda, col **limite** di §2 scritto |
| `docs/it/dbzero/config/manual/auth_totp_device.md` | il verbo nei «Vedi anche», nel ciclo di vita e nella storia |

Scelte fatte scrivendo, non dette da §2:

* ⛔ **I segreti non entrano nel contesto del log.** `fn_log_and_raise_error` scrive il
  contesto in `dbops.error_log`: lì vanno solo i segni (`atteso_vuoto`, `nuovo_vuoto`,
  `uguali`), mai i due token, nemmeno cifrati. Un registro degli errori non è un posto
  dove tenere segreti, cifrati o no.
* **Non tocca `ultimo_uso_at`**: ricifrare non è un uso. `data_update`/`user_update` li
  aggiorna il trigger di audit, come per ogni scrittura.
* **Niente `GRANT` né `REVOKE`**: l'`EXECUTE` all'app arriva da PUBLIC e dal loop
  `20260205-41`, come per gli altri sei verbi; la postura della tabella non cambia.
* Parametri tipati `secret_encrypted%TYPE`, come `fn_totp_registra_device`.

### 5.2 Cosa è provato, e dove

Provato su un **cluster PG18 usa-e-getta** (il DB di sviluppo non era raggiungibile senza
credenziali), con l'SQL **estratto** dagli YAML: la tabella (`20260328-20` + `20260929-07`)
e il verbo (`20261001-35`, `COMMENT` compreso), in `BEGIN … ROLLBACK`, il migratore non
superuser come proprietario e l'app con il solo `SELECT`. Come app: le dodici prove del pgTAP
nuovo in forma ridotta (fixture scritte da owner, non dai verbi), la porta (`UPDATE … WHERE
false` → `42501`), `SECURITY DEFINER` col `search_path` bloccato. `plpgsql_check_function`
sul verbo: zero righe. ⚠️ `fn_log_and_raise_error` era uno **stub** dichiarato (solleva
«Chiamata non valida a …» e stampa il contesto), che non è il soggetto: ha fatto vedere che
nel contesto ci sono solo i segni.

**Non coperto dalla prova**, e resta a Tid: l'apply; la corsa del pgTAP nuovo e di
`test-totp-porta-v1.sql` col runner (fixture vere `fn_pgtap_crea_operatore_umano`, catalogo
dei messaggi vero); i due presidi trasversali sulle funzioni nuove,
`dbops/test-riferimenti-morti-v1` (plpgsql_check su ogni funzione: localmente zero) e
`script/test-rubinetto-primo-motivo-v1` test 5 (il verbo non chiama l'helper: il conteggio
non si sposta).

### 5.3 Cosa resta

* ✅ **Tid, 2026-10-01**: `20261001-35` applicato; pgTAP rilanciati, nessuna regressione.
* ⏳ **Backend**: §4 — `CampoCifrato` che scrive attraverso il verbo,
  `config.auth_totp_device.secret_encrypted` in `CAMPI_CIFRATI`, i due casi nuovi in
  `test_ricifra_campi_cifrati_db`. Il verbo è a DB: il backend non aspetta più niente.
