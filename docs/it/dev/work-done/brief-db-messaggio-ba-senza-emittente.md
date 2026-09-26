# Brief DB — Il messaggio di `E_BA_ADMIN_GLOBALE_VIETATO` sulla regola vera

> **Destinatari:** team DB (`dev/db-tid`). Ricaduta BE (§4) **dopo** il merge
> DB, non prima: il backend non si rigenera col DB avanti rispetto a git.
>
> **Tipo:** allineamento di testi, nessuna logica. Richiesta del team BE del
> 2026-09-26.
>
> **Stato:** 🟡 lato DB scritto il 2026-09-26 (CSV + `20260926-12` + pgTAP),
> **da applicare**; ricaduta BE (§4) aperta.

---

## 1. Il disallineamento

Dalla rev 2026-08-04 `script.fn_check_user_can_create_ba` lascia creare un
billing account anche a chi non ha righe in `config.user_emittenti_fiscali`,
purché lavori **dentro** un emittente del suo perimetro
(`app.current_emittente_id`, verificata da `fn_check_user_emittente_scope`).
Il divieto vero è quindi: **nessun emittente su cui scrivere** (tipicamente il
super admin in «Tutti gli emittenti»), quando esistono emittenti attivi.

Il messaggio, il `COMMENT` del guard e il `detail` del contesto raccontavano
ancora la regola del 2026-04-08 («un amministratore globale non può…») e
suggerivano di «creare un operatore di emittente»: oggi basta scegliere
l'emittente in alto.

## 2. Cosa è cambiato (lato DB)

| Pezzo | Cambio |
| --- | --- |
| `80_data/sql/config/messaggi_errore.csv`, riga `E_BA_ADMIN_GLOBALE_VIETATO,it` (id 358) | messaggio, causa e soluzione riscritti. Nessun `%s`: la frase non prende valori (il guard ne passa uno, `NEW.codice`, che resta inutilizzato come prima) |
| `20_code/anagrafiche/20260926-12-update-trgfn-billing-account-guard-admin-globale-testi` | `COMMENT ON FUNCTION` e chiave `detail` del contesto sulla regola vera. Corpo dalla doc auto-gen, logica identica; rollback al corpo del `20260408-14` |
| `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql`, test 4 | riconosceva il rifiuto dal **testo** (`'%amministratore globale%'`): col messaggio nuovo sarebbe diventato rosso a guard invariato. Ora legge il **codice** dal canale `CONSTRAINT` (contratto `P0001` + `CONSTRAINT` = codice) |
| `docs/it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_admin_globale.md`, `billing_account.md` | scopo e tabella del codice sulla regola vera; tolta l'affermazione falsa `runOnChange: true` |

⭐ **Il nome del codice resta** (`…ADMIN_GLOBALE…`): lo usano
`apps/anagrafiche/error_codes.py` e il guard di `clienti_service.py`. Un
rinomina si decide prima, col BE.

## 3. Prove fatte, e cosa non coprono

* `guardrail_sql_letterali.py` verde sul changeSet.
* SQL **estratto** dallo YAML (forward e rollback) eseguito con
  `ON_ERROR_STOP=1` su un cluster PG18 usa-e-getta, con stub di
  `fn_check_user_can_create_ba` (→ false) e di `fn_log_and_raise_error`: la
  funzione compila, il `COMMENT` si legge, il rifiuto esce con
  `CONSTRAINT = E_BA_ADMIN_GLOBALE_VIETATO` e il `detail` nuovo; il rollback
  rimette il `COMMENT` vecchio.
* ⚠️ **Non coperto**: il confronto doc auto-gen ↔ `pg_get_functiondef` su dbdev
  e CI (credenziali non leggibili dalla sessione), e il ri-upsert completo del
  CSV `messaggi_errore` (§11.2: mina irriscrivibile). Il pgTAP lo lancia Tid.

## 4. Ricaduta BE — dopo il merge DB

1. `error_messages_fallback.py`: allineare il ripiego di
   `E_BA_ADMIN_GLOBALE_VIETATO` al messaggio nuovo.
2. `clienti_service.py._guard_can_create_ba`: allineare il messaggio del guard
   applicativo.
3. Doc BE con il testo vecchio: `docs/it/backend/anagrafiche/manual/api_clienti.md`
   (riga del codice 403) e la voce `ClientiService.crea_cliente` del catalogo BB
   backend («blocca admin globale + emittenti»).
