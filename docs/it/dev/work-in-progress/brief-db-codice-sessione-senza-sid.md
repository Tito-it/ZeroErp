# Brief DB — Codice errore per il guard sul claim `sid`

> **STATO (2026-09-04)**: ✅ **seminato dal team DB** come **`E_JWT_SENZA_SID`**,
> classe **`NON_AUTENTICATO`**, messaggio id 1044 senza segnaposto. Righe nei CSV
> su `dev/db-tid`, applicate sul DB di sviluppo, **non ancora su `Tito-dev`**.
> ✅ **Lato BE il lavoro è fatto** (vedi §5) — con una **dipendenza d'ordine sul
> merge**, §6.
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend agent. · **Priorità**: 🟢 BASSA.
> **Data**: 2026-09-04. · **Correlato**: `api_multi_veste_token.md`.

---

## 0. Le tre correzioni del team DB, accettate

Il brief originale chiedeva `E_SESSIONE_SENZA_SID` di classe `TECNICO`, con il
guard dentro la view. **Erano sbagliate tutte e tre, e le ragioni sono le loro.**

| Chiedevo | È diventato | Perché la loro versione è giusta |
| --- | --- | --- |
| classe `TECNICO` (500) | **`NON_AUTENTICATO` (401)** | Il brief era **incoerente con sé stesso**: chiedeva `TECNICO` — che per definizione è «l'operatore non può farci niente» — e insieme un messaggio che dice «esci e rientra», cioè un rimedio che l'operatore esegue da solo. È il caso identico di `E_JWT_SENZA_IDENTITA`, che è `NON_AUTENTICATO`. |
| nome `E_SESSIONE_SENZA_SID` | **`E_JWT_SENZA_SID`** | Il nome segue la **sede**, e la sede è cambiata (riga sotto). |
| guard nella view | **guard in `JwtAuditAuthentication`** | Il contratto del JWT interno ha **tre** claim obbligatori (`identita_id`, `ruolo_applicativo`, `sid`); il primo era verificato una volta in autenticazione, il terzo **da nessuna parte**. Un guard per view ne copre **una su tre** e lascia scoperti logout, audit del refresh e la lista sessioni. |

⭐ La terza è la correzione che vale di più: cambia il **perimetro** del difetto,
non il modo di scriverlo.

## 1. E il §4 del brief era falso

Dicevo «oggi la probabilità è zero, ogni login passa dal serializer che mette il
`sid`». Il team ha portato il controesempio, **in casa**:
`change_password_view.py:96` emette la coppia di token con
`RefreshToken.for_user`, che **non** passa da `SidTokenObtainPairSerializer` →
niente `sid`. Il codice lo sa già: due righe sotto ripiega su `jti`.

⚠️ È la Regola Zero applicata a me: *«oggi non capita» non significa che il caso
non esiste, significa che non hai ancora cercato il controesempio.* Qui non era
nemmeno raro — era a dieci righe di distanza.

⛔ E ne discende un **difetto vivo suo**, fuori dal perimetro di questo brief:
dopo un cambio password il FE salva quei token e chiama `fetchProfile`, che
prende 401. Vedi §7.

## 2. Cosa serviva (fatto)

| Campo | Valore seminato |
| --- | --- |
| `codice` | `E_JWT_SENZA_SID` |
| `classe` | `NON_AUTENTICATO` (→ 401) |
| messaggio (id 1044, `it`) | «La sessione in corso non è identificabile: esci e rientra per continuare.» |
| segnaposto | nessuno |

## 3. La condizione

`JwtAuditAuthentication.authenticate` verifica i claim obbligatori. Senza `sid`
il token è incompleto e viene rifiutato con 401, come già accade senza
`identita_id`.

⛔ Cosa rompeva l'assenza, quando il token arrivava alle view — sono **tre**
danni silenziosi su una funzione di sicurezza:

* «revoca tutte le altre sessioni» non sa quale risparmiare e **revoca anche la
  propria** (`current_sid` vuoto ⇒ il confronto `current_sid and …` è sempre
  falso);
* il rifiuto «non puoi revocare la sessione corrente» viene **scavalcato** dallo
  stesso cortocircuito;
* il diario delle sessioni non sa a quale riga attribuire logout e refresh.

## 4. Perché non si è riusato `E_JWT_SENZA_IDENTITA`

È il claim `identita_id`, non `sid`: due **condizioni** diverse sotto lo stesso
codice sono la definizione di accumulatore ([api.md §Tassonomia errori](../api.md)).
E non è stato aperto l'`_ALLOWLIST` del guardrail dei codici, che è **vuota**:
un registro in pari non si riapre per una riga.

## 5. Lavoro BE — fatto

* ✅ `./manage-env.sh genera_error_policies` → `E_JWT_SENZA_SID` → `NON_AUTENTICATO`
  (diff di **una sola voce**: il DB di sviluppo non era avanti su altro).
  `--check` risponde «allineato al catalogo».
* ✅ `error_messages_fallback.py` — la frase senza segnaposto.
* ✅ `error_ui_overrides.py` — `"E_JWT_SENZA_SID": "redirect_login"`. ⚠️ Sul 401 il
  default è `show_error_banner` per scelta esplicita: **senza questa riga**
  l'operatore leggerebbe un banner restando con un token che non funziona.
* ✅ Il guard in `JwtAuditAuthentication`, con l'eccezione dedicata
  `JwtSenzaSidError` (gemella di `JwtSenzaIdentitaError`) e il
  `logger.warning("security.jwt_senza_sid …")` gemello.
  ⚠️ `sid` **vuoto = assente**: le view leggono `str(auth.get("sid", ""))`, quindi
  un claim vuoto e uno mancante producono a valle lo stesso danno.
* ✅ `JWT_CLAIM_SID` in `auth_constants.py`, accanto agli altri due.
* ✅ Nelle view sessioni: tolto il tampone `revoked: 0` e corretti i due
  confronti `current_sid and …` che il sid vuoto scavalcava.
* ✅ Due test nuovi (`sid` assente, `sid` vuoto): 883 test core verdi.

## 6. ⚠️ Dipendenza d'ordine sul merge

`error_policies_generated.py` ora **contiene** `E_JWT_SENZA_SID`, ma i CSV che lo
creano sono su `dev/db-tid`. Se il BE arrivasse su `Tito-dev` **prima** del DB,
`test_error_policies_divergenza_db` sarebbe **rosso in CI**: là il database è
ricostruito da zero dai changelog, e il codice non esisterebbe.

⇒ **Il DB entra per primo**, o i due entrano insieme.

## 7. 🔴 Difetto vivo, cantiere separato: i token del cambio password

`change_password_view.py` emette token **senza `sid` e senza `identita_id`**;
`ChangePasswordView.vue` li salva nello store e chiama `fetchProfile`, che prende
401. Oggi l'utente resta con un token morto — e con il guard nuovo il rifiuto
arriva prima e più chiaro, ma il difetto resta: **dopo un cambio password la
sessione va rifatta**.

⭐ La correzione è emettere quei token dalla stessa strada del login (il
serializer multi-veste), non aggiungere claim a mano. Non è in questo brief
perché tocca il flusso password, non il catalogo errori.
