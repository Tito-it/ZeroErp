## Documentazione Concettuale – Funzione `script.fn_scope_ba_ownership`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Tabelle correlate:**
>
[anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [config.scope_policy](/dbzero/config/tabelle/scope_policy)

---
### 🎯 Scopo Principale
(latest review 20-04-2026 — ruolo-aware)

La funzione **`script.fn_scope_ba_ownership`** implementa la policy di scope
`BA_OWNERSHIP`: verifica che un'identità digitale di tipo cliente possa
vedere uno specifico `billing_account`.

Regola: il BA appartiene all'identità se e solo se (1) condividono il
**soggetto_ruolo** (ovvero il cliente) e (2) l'identità è in veste cliente
(`ruolo_applicativo IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')`). Il filtro
veste fa parte del contratto della scope function — non è delegato alle
policy RLS (difesa-in-profondità §V sviluppo-concentrico).

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente. |
| `p_billing_account_id` | `anagrafiche.billing_account.id%TYPE` | BA target da verificare. |

---

### Output

`BOOLEAN` — `true` se il BA appartiene all'identità, `false` altrimenti.

---

### Semantica (fail-closed)

| Caso | Risultato |
|------|-----------|
| Identità inesistente / non utilizzabile oggi | `false` |
| Identità in veste non-cliente (es. OPERATORE, FORNITORE_PORTALE, API_CLIENT) | `false` |
| BA inesistente | `false` |
| BA appartiene a un altro `soggetto_ruolo` | `false` |
| Identità CLIENTE_PORTALE o SHOP_CUSTOMER utilizzabile oggi + BA con stesso SR | `true` |

⭐ **Dal 07-10-2026** (brief `brief-db-veste-utilizzabile`): l'identità deve essere
**utilizzabile oggi** secondo
[script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)
(accesa, nelle sue date, soggetto attivo), non solo accesa. Prima una veste
scaduta, ma ancora accesa, continuava a vedere i suoi dati.


---

### Come è fatta (dal 21-10-2026)

La regola `BA_OWNERSHIP` è scritta **una volta**, nei building block delle policy
di controparte, e questa funzione li compone per la domanda su **una** riga:

* [`fn_get_identita_sr_perimetro`](fn_get_identita_sr_perimetro.md) — il soggetto
  dell'identità, se è in veste di cliente (`CLIENTE_PORTALE` o `SHOP_CUSTOMER`) e
  utilizzabile oggi;
* [`fn_resolve_controparte_sr_id`](fn_resolve_controparte_sr_id.md) — il cliente
  della riga (modo `billing_account`), letto `SECURITY DEFINER` senza rieseguire la policy del padre;
* `fn_scope_sr_perimetro` — il confronto.

⭐ **Le policy del portale non passano più di qui** (`20261021-32`): chiamano i
building block direttamente, con il perimetro calcolato **una volta per
istruzione** invece che a ogni riga (linee-guida-sql §10.3). Questa funzione resta
per chi chiede di una riga sola: è la funzione della regola nel catalogo
`config.scope_policy`. Le sorelle `_via_fattura` e `_via_fattura_sdi`, e gli
adattatori dello shop che la chiamavano, sono ritirati dal `20261021-40`: al loro
posto i modi `fattura`, `fattura_sdi` e `billing_account_shop` del risolutore.

---

### Perché non serve una policy `SELF_OWNERSHIP` separata per shop

La guida architetturale inizialmente prevedeva una policy `SELF_OWNERSHIP`
distinta per `SHOP_CUSTOMER`. In fase di design (18-04-2026) si è deciso di
unificarla con `BA_OWNERSHIP` perché:

* Il ruolo anagrafico è lo stesso (`CL`) per entrambi: la differenza è solo
  nel namespace API e nel profilo capability.
* Lo scope dati è identico: "vedi solo i BA del tuo soggetto_ruolo".
* Meno policy da mantenere, meno rischio di divergenza.

---

{% include-markdown "signature-core.md" %}
