## 📘 Documentazione Concettuale – Funzione `script.fn_identita_super_admin_senza_scadenza()`

> 👀 **Vedi anche**
>
> [script.fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo) ·
> [script.fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) ·
> [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)

### 🎯 Scopo

(07-10-2026 — brief `brief-db-veste-utilizzabile`, decisione di Tid)

**Questa identità è un amministratore che non scade?** È la regola dell'anti-lockout:
il sistema deve avere sempre almeno un SUPER_ADMIN così.

Un'identità è «SUPER_ADMIN senza scadenza» se tutte queste cose sono vere:

| Condizione | Perché |
| --- | --- |
| ha un binding `SUPER_ADMIN` attivo verso un profilo attivo | è un amministratore |
| è `OPERATORE` e **utilizzabile oggi** ([fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)) | entra oggi: veste accesa e nelle sue date, rapporto attivo e nelle sue date |
| la veste **non ha data di fine** | domani entra ancora |
| il rapporto **non ha data di fine** | idem: dal 07-10-2026 la fine del rapporto chiude l'accesso |
| la credenziale non è bloccata dall'amministratore | un amministratore bloccato non entra |

Binding, profili e credenziali non hanno date: la scadenza sta solo su veste e
rapporto.

### Perché «senza scadenza» e non «attivo»

I guard dell'anti-lockout scattano su una **scrittura**: spegnere una veste, togliere un
binding, bloccare una credenziale. Una data che passa non scrive niente. Se tutti gli
amministratori avessero una data di fine, il giorno dopo l'ultima il sistema resterebbe
senza, e nessun guard lo vedrebbe. La garanzia si chiede quindi sulla scrittura che
**mette** la data di fine: si può dare una data di fine a un amministratore solo finché
ne resta un altro che non scade.

### Chi la legge

- [fn_check_almeno_un_super_admin_attivo](/dbzero/script/funzioni/fn_check_almeno_un_super_admin_attivo):
  esiste almeno un'identità così? La chiamano i guard su binding, veste, rapporto e
  credenziale.
- [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo):
  questo utente è l'unico? Accende le capability del drawer operatore.

Prima ognuna delle due aveva il suo blocco di filtri, e non coincidevano: una guardava
la finestra della veste, l'altra no.

### Forma

`LANGUAGE sql`, `BEGIN ATOMIC`, `STABLE`, `SECURITY INVOKER`. Ragiona per identità, non
per credenziale: i guard su veste e rapporto lavorano su righe.

### Test

`db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql`.
