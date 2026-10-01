# Brief DB — Il verbo che ri-cifra il segreto TOTP alla rotazione delle chiavi

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`).
> **Origine:** T-1 di [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md)
> §3.4-bis; decisione 9 di §6 (Tid, 2026-10-01: strada A).
> **Stato:** 🟡 da fare. Il backend va avanti con T-2, che non ne dipende; il segreto entra in
> `CAMPI_CIFRATI` all'arrivo del verbo, e **prima** che T-3 metta in esercizio la registrazione
> dei device.
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
