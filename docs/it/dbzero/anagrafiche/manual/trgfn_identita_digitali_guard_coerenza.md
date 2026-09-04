## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_identita_digitali_guard_coerenza`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli)
>
**Approfondimento funzioni:**
>
[script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)
> [script.fn_guard_soggetto_pf_pura](/dbzero/script/funzioni/fn_guard_soggetto_pf_pura)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale
(latest review 04-09-2026 — biforcazione sul flag `tecnica`; prima: 18-04-2026)
La trigger function
**`anagrafiche.trgfn_identita_digitali_guard_coerenza()`** verifica la
coerenza tra il **ruolo applicativo** di una identità digitale e il
**tipo di soggetto_ruolo** a cui è collegata.

Trigger BEFORE INSERT OR UPDATE sulla tabella
[`anagrafiche.identita_digitali`](/dbzero/anagrafiche/tabelle/identita_digitali),
fase `a10` (guard fail-fast).

---

### Matrice di coerenza

| `ruolo_applicativo` | `tipi_ruoli.codice_interno` atteso | Vincoli aggiuntivi |
|---------------------|-----------------------------------|--------------------|
| `OPERATORE`, `tecnica = false` | `RIS_UMANA` | Soggetto persona fisica pura (CF obbligatorio, P.IVA vietata) |
| `OPERATORE`, `tecnica = true` | ⭐ `PROC_AUTO` | nessuno: un processo non ha codice fiscale |
| `CLIENTE_PORTALE` | `CL` | — |
| `SHOP_CUSTOMER` | `CL` | — |
| `FORNITORE_PORTALE` | `FO` | — |
| `API_CLIENT` | nessun vincolo di coerenza | (rinviato a Fase 2 del modello multi-face auth) |
| `DISABILITATO` | nessun vincolo di coerenza | Permette di conservare identità disattivate |

---

### Regole applicate

* Per i ruoli `API_CLIENT` e `DISABILITATO` la funzione fa **early-exit**
  senza query: nessun vincolo di coerenza è richiesto in questa fase.
* Per `OPERATORE`: un'unica SELECT su `soggetti_ruoli` recupera il
  `soggetto_id`, poi la funzione **si biforca sul flag `tecnica`**
  *(dal 2026-09-04)*:
  * `tecnica = false` — è una **persona**:
    [`fn_guard_soggetto_ruolo`](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)
    verifica che il `tipo_ruolo` sia `RIS_UMANA`, e
    [`fn_guard_soggetto_pf_pura`](/dbzero/script/funzioni/fn_guard_soggetto_pf_pura)
    che sia persona fisica pura (CF + no P.IVA);
  * `tecnica = true` — è un **processo automatico**: si pretende `PROC_AUTO` e
    **non** si chiede la persona fisica. ⚠️ Un processo non ha codice fiscale, e
    pretenderglielo avrebbe costretto a inventargli un'anagrafica finta.
* Per gli altri ruoli portale/shop, la funzione passa `NULL` come
  `p_soggetto_id` a `fn_guard_soggetto_ruolo` (la funzione accetta il
  parametro come opzionale: in questo caso verifica solo la coerenza
  `soggetto_ruolo_id ↔ tipo_ruolo`, evitando una query ridondante).
* Il ramo `ELSE` del dispatch CASE solleva `E_RUOLO_APPLICATIVO_NON_GESTITO`:
  anti-bypass quando si aggiunge un nuovo valore all'enum
  `config.ruolo_applicativo` senza estendere il guard.

---

### ⛔ La biforcazione è un CANCELLO, non una comodità

Va letta al contrario di come sembra: non serve a *permettere* le identità
tecniche, serve a **impedire l'abuso opposto**.

> Marcare `tecnica = true` l'identità di una **persona** farebbe sparire quella
> persona da tutti i controlli che riguardano le persone.

⇒ Non passa: un'identità tecnica pretende un soggetto-ruolo `PROC_AUTO`, e
quello di una persona è `RIS_UMANA`. ⭐ E vale anche nell'altro verso — un
soggetto `PROC_AUTO` non può ricevere un'identità non tecnica.

⚠️ **Effetto collaterale voluto sui test**: le fixture che costruivano il caso
«persona marcata tecnica» hanno smesso di funzionare. È il guard che fa il suo
mestiere, e quelle fixture sono state riscritte sul caso che *resta* possibile —
un utente tecnico vero il cui legame col processo viene disattivato.

---

### Errori sollevati

| Codice | Quando |
|--------|--------|
| `E_SOGGETTI_RUOLI` | Caso limite: `soggetto_ruolo_id` non trovato (la FK dovrebbe impedirlo, ma fail-fast esplicito per chiarezza). |
| `E_SOGGETTI_RUOLI` (da `fn_guard_soggetto_ruolo`) | `tipo_ruolo` del soggetto_ruolo non coerente con il ruolo applicativo. |
| `E_AUTH_USER_SOGGETTO_CON_PIVA` / `E_AUTH_USER_SOGGETTO_SENZA_CF` (da `fn_guard_soggetto_pf_pura`) | Violazione PF pura per ruolo `OPERATORE`. |
| `E_RUOLO_APPLICATIVO_NON_GESTITO` | Valore enum non gestito dal dispatch CASE. |

---

### Relazione con il bridge storico

Il guard è il gemello generalizzato di
[`trgfn_risorse_umane_auth_user_guard_persona_fisica`](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_auth_user_guard_persona_fisica)
ma lavora su `identita_digitali` (tutti i ruoli) invece che
sul solo bridge operatori. I due condividono la logica PF pura tramite
`fn_guard_soggetto_pf_pura` evitando duplicazione.

---

{% include-markdown "signature-core.md" %}
