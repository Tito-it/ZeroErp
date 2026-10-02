# Brief BE → DB — Credenziale: il motivo del blocco dal DB e gli utenti di sistema

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`);
> poi BE/FE (§4).
> **Origine:** le tre richieste rimaste aperte nel
> [brief area Accessi](../work-done/brief-db-be-fe-area-accessi.md) §8.3, che si è chiuso il
> 2026-10-02. Il loro contesto (le viste dei tab, il blocco sulla credenziale, la categoria)
> sta lì.
> **Stato:** ⏳ in attesa del team DB. Nessuna richiesta è bloccante: l'area Accessi funziona.
> R-DB-A6 è **decisa da Tid** (2026-10-02).

## 1. In una riga

Il blocco di una credenziale dice **perché** è spento con un motivo che oggi compone il backend,
non il DB; i verbi dell'amministratore toccano anche gli **utenti di sistema**, che a video sono in
sola lettura; una colonna della lista «Di sistema» non si può ordinare.

## 2. Richieste al team DB

### R-DB-A5 — Il motivo del blocco lo dà il DB

**Oggi.** Il pannello della credenziale spegne «Blocca accesso» sull'ultimo super admin attivo. Il
**predicato** viene dal DB (`script.fn_check_ultimo_super_admin_attivo`, letto dal repository), ma il
**codice** del motivo (`ULTIMO_SUPER_ADMIN`) e la **chiave i18n**
(`amministrazione.accessi.blocca_reason.ultimo_super_admin`) li scrive il backend
(`amm_software/services/accessi_service.py`, debito dichiarato). È la forma che api.md
§«Capability di riga» chiede di non avere: il motivo lo produce la stessa funzione che rifiuta.

**Richiesta.** Una `script.fn_check_credenziale_bloccabile(p_auth_user_id)` → `reason`,
`reason_key` (NULL se si può bloccare), sul modello delle altre `fn_check_*`:

* la chiama il guard `trgfn_credenziali_guard_ultimo_super_admin` (o `fn_blocca_credenziale`):
  una regola, due lettori;
* la legge il backend per la capability `can_block` / `block_reason` / `block_reason_key` di
  `GET /amm-software/credenziali/<id>/`;
* i motivi sono **due**, in quest'ordine: `CREDENZIALE_DI_SISTEMA` (R-DB-A6, sotto) e
  `ULTIMO_SUPER_ADMIN`.

### R-DB-A6 — I verbi dell'amministratore rifiutano gli utenti di sistema

**Decisione di Tid (2026-10-02): sì, il DB rifiuta.**

**Oggi.** Le credenziali di categoria `SISTEMA` (`script.fn_categoria_accesso`: l'utente tecnico di
un processo) hanno a video una scheda in sola lettura, senza gesti. Una chiamata diretta all'API però
le blocca o ne tocca il secondo fattore, e bloccarne una **ferma un processo automatico** senza che
il suo pannello lo sappia.

**Richiesta.** I verbi che l'amministratore usa su una credenziale **rifiutano** una credenziale
`SISTEMA` con un codice nuovo, qualunque sia la strada (video, API, script):

| Verbo | Rifiuta | Nota |
| --- | --- | --- |
| `script.fn_blocca_credenziale` | sì | Motivo anche in `fn_check_credenziale_bloccabile` (R-DB-A5) |
| `script.fn_imposta_totp_obbligatorio` | sì | |
| `script.fn_totp_disabilita_device` | sì, quando ad agire è un **altro** (amministratore) | Quando agisce la credenziale stessa la regola non cambia |
| `script.fn_sblocca_credenziale` | **no** | Una credenziale `SISTEMA` bloccata **prima** di questa regola deve potersi sbloccare: l'uscita resta aperta |

Codice proposto: `E_CREDENZIALE_DI_SISTEMA`, classe `NON_PERMESSO` (o quella che il catalogo usa per
«operazione non ammessa su questo oggetto»), in `codici_errore.csv` e `messaggi_errore.csv` (it, con
causa e soluzione). Frase proposta: «Le credenziali di sistema non si modificano da qui.» — causa
«La credenziale è quella di un processo automatico.», soluzione «Usare il pannello del processo.».

La sessione del migratore (`dbops.fn_sessione_del_migratore`), che oggi `fn_totp_disabilita_device`
ammette come uscita d'emergenza (D-T4), è manutenzione del DB e non una strada dell'applicazione:
la regola non la riguarda.

### R-DB-A4 — Lista 105, `emittente_ragione_sociale` ordinabile

`ui.lista_colonna` id 1094 (lista 105, «Di sistema»), `emittente_ragione_sociale`: `ordinabile = t`.
È NUCLEO («ragione sociale»: `gen_seed_lista --verifica-ordinamento` dice KO): chi la accende deve
poterla ordinare. Verificato il 2026-10-02 su `dev/db-tid`: oggi `ordinabile = f`.

## 3. Ordine suggerito

1. R-DB-A6 e R-DB-A5 insieme: la funzione di check nasce con i due motivi.
2. R-DB-A4, indipendente.
3. Apply e corsa pgTAP di Tid.

## 4. Ricadute BE/FE (dopo il DB)

* **BE**: `accessi_service.get_credenziale` legge `fn_check_credenziale_bloccabile` e smette di
  comporre motivo e chiave (via `_MOTIVO_ULTIMO_SUPER_ADMIN`, `_CHIAVE_ULTIMO_SUPER_ADMIN`);
  `E_CREDENZIALE_DI_SISTEMA` in `error_policies_generated.py` (rigenerato) e ripiego senza
  segnaposto in `error_messages_fallback.py`; `emittente_ragione_sociale` entra in
  `ACCESSI_SISTEMA_ORDER_COLUMNS` (`accessi_repository.py`); test dei rifiuti; doc
  `api_amm_software.md` §1-bis.
* **FE**: chiave i18n del motivo nuovo (se la `reason_key` del DB è nuova); nessun gesto nuovo, la
  scheda «Di sistema» resta in sola lettura.

---
{% include-markdown "signature-core.md" %}
