# Brief DB — Il blocco login e il cambio password obbligatorio passano alla credenziale

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-09-24 · **Stato**: 🟡 **DA FARE** — nessun changeSet.
>
> **Origine**: difetto M-4 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](analisi-be-difetti-emersi-verifica-doc-api-core.md),
> diventato il cantiere
> [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md).
> Decisioni di Tid del 2026-09-24 (§5 dell'analisi):
>
> - **D-1** — il blocco per password errate ha una **sede della credenziale**:
>   una tabella nostra 1:1 con `auth_user`, e le colonne escono da
>   `identita_digitali`;
> - **D-2** — un **reset password riuscito sblocca** la credenziale;
> - **D-7** — il **cambio password obbligatorio** (`deve_cambiare_password`) è
>   della credenziale, nella stessa sede.
>
> Il perché, sul modello: la password è **una** e vive su `auth_user`, vale per
> tutte le porte (operatore, portale, shop). Chi prova password la sta provando
> per tutte; chi deve cambiarla deve cambiare quella.

---

## 1. Com'è oggi (verificato sulla doc auto-generata, 2026-09-24)

| Oggetto | Cosa fa | Il difetto |
| --- | --- | --- |
| `script.fn_check_blocco_login(p_auth_user_id)` | legge `bloccato_fino_a` e fa l'auto-sblocco sulla riga `identita_digitali` con `ruolo_applicativo = 'OPERATORE'` | chi non ha quella riga non è mai bloccato |
| `script.fn_registra_tentativo_login(p_auth_user_id, p_successo)` | se non esiste una riga OPERATORE ritorna `{bloccato:false}` **senza contare**; altrimenti incrementa e blocca lì | le vesti portale/shop non contano; un operatore-cliente si blocca come operatore sbagliando sul portale |
| `anagrafiche.identita_digitali` | porta `tentativi_falliti`, `bloccato_fino_a`, `deve_cambiare_password` per **riga di veste** | lo stato di una cosa sola (la credenziale) è distribuito su N righe |
| `script.fn_get_user_profile`, `script.fn_get_operatore_detail` | leggono `deve_cambiare_password` dall'identità | — (da ripuntare) |

Il filtro `OPERATORE` è un **residuo**, non una scelta: le funzioni sono nate su
`risorse_umane_auth_user` (operatori per natura), e l'hotfix
`20260419-93/-94` ha spostato le scritture su `identita_digitali` tenendo il
perimetro di allora. ⚠️ I manual delle due funzioni citano ancora
`risorse_umane_auth_user`.

I parametri `login_max_tentativi_falliti` (5) e `login_blocco_minuti` (15)
**restano globali** come oggi: la decisione non li tocca.

---

## 2. Cosa si chiede

### 2.1 La sede della credenziale (D-1, D-7)

Una tabella 1:1 con `django.auth_user`, in uno schema nostro. Nome e schema a
scelta del team DB; un precedente di forma è `config.auth_totp_device`, già
1:1 con `auth_user`.

Contenuto minimo:

| Colonna | Note |
| --- | --- |
| `auth_user_id` | PK e FK verso `django.auth_user` |
| `tentativi_falliti` | contatore dei fallimenti consecutivi |
| `bloccato_fino_a` | `timestamptz`, NULL = non bloccata |
| `deve_cambiare_password` | D-7 |
| audit standard | come da linee guida |

⚠️ **Una decisione di forma che spetta al team DB, e va scritta:** la riga
esiste per **ogni** credenziale (creata con l'`auth_user`) oppure nasce alla
prima scrittura, con l'**assenza** che vale «nessun tentativo, non bloccata,
nessun obbligo»? Le credenziali oggi nascono da due strade — la madre
`anagrafiche.fn_crea_auth_user` per gli operatori e un `INSERT` del backend per
portale/shop (`PortaleRepository.create_auth_user_portale`) — quindi la prima
forma chiede anche di chiudere la seconda strada (o un trigger su
`django.auth_user`). La seconda forma non la chiede, ma ogni lettore deve
trattare l'assenza. Qualunque sia la scelta, il valore dell'assenza va
dichiarato in un posto solo.

**Nello stesso giro**: `tentativi_falliti`, `bloccato_fino_a` e
`deve_cambiare_password` **escono** da `anagrafiche.identita_digitali` (non c'è
produzione; nessuna doppia sede nemmeno per un giorno).

Migrazione dei valori (dati di sviluppo): `deve_cambiare_password` della
credenziale = OR dei valori delle sue identità (è già la lettura del reset, che
li azzera tutti); contatori e blocchi si possono ripartire da zero.

### 2.2 Le due funzioni del login

`fn_check_blocco_login(p_auth_user_id)` e
`fn_registra_tentativo_login(p_auth_user_id, p_successo)` lavorano sulla sede
della credenziale, **senza nessun filtro su veste o `ruolo_applicativo`**.
Firma e contratto di ritorno invariati — il backend le chiama già col solo
`auth_user_id`, prima di sapere in quale veste l'utente entrerà. Codice
`E_UTENTE_BLOCCATO` invariato.

⛔ Il caso «credenziale senza riga OPERATORE → non contare» sparisce: ogni
credenziale conta.

### 2.3 Lo sblocco al reset password (D-2)

Un verbo che azzera contatore e blocco di una credenziale, che il backend
chiama quando un reset password va a buon fine (e che il ramo «successo» di
`fn_registra_tentativo_login` può usare a sua volta, così la regola
dell'azzeramento sta in un posto). ⚠️ Non chiedo di riusare
`fn_registra_tentativo_login(uid, true)` dal reset: un reset non è un
tentativo di login, e il nome mentirebbe nel giornale.

### 2.4 I lettori

`script.fn_get_user_profile` e `script.fn_get_operatore_detail` leggono
`deve_cambiare_password` dalla nuova sede (nome del campo in uscita invariato).

---

## 3. Test (pgTAP) — casi costruiti, non popolazione

1. credenziale con la **sola** veste portale (o shop): N fallimenti → bloccata;
   `fn_check_blocco_login` solleva `E_UTENTE_BLOCCATO`;
2. credenziale con veste OPERATORE **e** cliente portale: un contatore solo — i
   fallimenti si sommano, qualunque porta si stia provando;
3. credenziale **senza nessuna identità**: conta anch'essa (la password c'è);
4. blocco scaduto → auto-sblocco e contatore azzerato;
5. successo → contatore azzerato;
6. verbo di sblocco (D-2) → contatore e blocco azzerati;
7. `deve_cambiare_password` letto da `fn_get_user_profile` dalla nuova sede;
8. le tre colonne **non** esistono più su `identita_digitali`.

---

## 4. Ricaduta sul backend (la faccio io dopo il changeSet)

- `AuthRepository.get_deve_cambiare_password` / `set_deve_cambiare_password`
  sulla nuova sede, **senza** il parametro `identita_id` (D-7): il login, il
  middleware, `apply_new_password` (cambio, reset, attivazione), l'invito
  operatore;
- lo sblocco (D-2) chiamato dal reset password riuscito;
- `PortaleRepository.create_identita_portale` e `ProfileActivateShopView` non
  passano più `deve_cambiare_password`; `IdentitaDigitale` (model) perde le tre
  colonne;
- `PortaleRepository.create_auth_user_portale`, se il team DB sceglie «la riga
  esiste sempre» (§2.1);
- test aggiornati.

⚠️ **Ordine**: il backend si allinea **subito dopo** il changeSet e nello
stesso giro, perché le colonne tolte da `identita_digitali` sono lette da
`auth_repository` con SQL diretto — un mock non vede il binding.

## 5. Documentazione

- manual di `fn_check_blocco_login` e `fn_registra_tentativo_login` (citano
  ancora `risorse_umane_auth_user`) e manual `anagrafiche/manual/identita_digitali.md`
  («lockout per-veste»): da riscrivere;
- guida `architettura-multi-face-auth.md` §3.1 («lo stato di lockout è
  per-identità»): la riscrivo io con la ricaduta BE.

---
{% include-markdown "signature-core.md" %}
