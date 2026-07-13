## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_default_emittente()`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
>
> Funzioni correlate:
> [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
> [vendite.trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize)
> [vendite.trgfn_ddt_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ddt_guard_emittente_ba)
>
> Pattern simmetrico (con differenze):
> [vendite.trgfn_ordini_default_emittente](/dbzero/vendite/funzioni/trgfn_ordini_default_emittente)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Valorizza automaticamente `vendite.ddt.emittente_fiscale_id` a **INSERT-time**,
leggendo l'operatore loggato dalla GUC `app.current_user_id` (popolata da
`JwtAuditAuthentication`) e risolvendone l'emittente fiscale tramite
`script.fn_resolve_emittente_for_user` (modello 1-a-1 operatore→emittente).

Applicata dal trigger `trg_ddt_a10_default_emittente_ins`
(fase `_a10_`, `BEFORE INSERT`).

---

### Due softenature DDT-specifiche (differenza da ordini)

A differenza di `trgfn_ordini_default_emittente`, questa funzione è **soft** e
non blocca mai: delega i casi non risolvibili alla catena di normalizzazione.

1. **Skip DDT da evasione**: se `NEW.sorgente_tipo_id` e `NEW.sorgente_uid`
   sono valorizzati, la funzione restituisce `NEW` senza toccare l'emittente.
   Lì l'emittente si **eredita dall'ordine sorgente** in
   `trgfn_ddt_normalize` (ereditarietà da preservare).
2. **No-raise su GUC non risolta**: se la GUC è vuota (contesto non-API) o
   l'operatore è admin globale (nessuna riga in `config.user_emittenti_fiscali`,
   `fn_resolve_emittente_for_user` ritorna NULL), la funzione **lascia
   `emittente_fiscale_id` a NULL senza sollevare**. Agisce poi il
   **fallback-da-BA** di `trgfn_ddt_normalize` (deriva l'emittente dal
   `billing_account_id`).

Conseguenza: il create DDT **non** produce `E_..._EMITTENTE_NON_RISOLTO`
(a differenza di ordini/preventivi/contratti).

---

### Logica

1. Se `NEW.emittente_fiscale_id IS NOT NULL` → **skip** (payload esplicito).
2. Se `NEW.sorgente_tipo_id` e `NEW.sorgente_uid` valorizzati → **skip**
   (evasione: eredita da ordine in `trgfn_ddt_normalize`).
3. Legge la GUC `app.current_user_id` (`missing_ok=true`). Se vuota → **skip**
   (RETURN NEW, emittente resta NULL).
4. `NEW.emittente_fiscale_id := script.fn_resolve_emittente_for_user(user_id)`.
   Se NULL (admin globale) → resta NULL (no raise).

---

### Firing order nella fase `_a10_` e rapporto col normalize

I trigger BEFORE si ordinano alfabeticamente per nome. `default_emittente`
(`...a10_default...`) fira **prima** di `trg_ddt_normalize_ins_upd` (che non ha
token di fase e quindi fira dopo tutti gli `a10`) e **prima** del write-guard di
scope emittente:

| Trigger | Effetto |
|---|---|
| `trg_ddt_a10_default_emittente_ins` | Setta emittente da GUC (se risolve) |
| `trg_ddt_a10_guard_emittente_scope_ins_upd` | Write-guard RLS (tollera NULL) |
| `trg_ddt_normalize_ins_upd` | Eredità da ordine / fallback-da-BA |
| `trg_ddt_z10_guard_emittente_ba_ins_upd` | Coerenza finale emittente↔BA |

---

### Errori sollevati

Nessuno direttamente: la funzione è volutamente non-bloccante (vedi
softenature). Gli errori di coerenza li solleva a valle
`trgfn_ddt_guard_emittente_ba` (`E_DDT_EMITTENTE_BA_INCOERENTE`).

---

### Note operative

- Il BE manda comunque `emittente_fiscale_id` nel payload (prefill dal profilo
  operatore, mirror ordini): in quel caso vale il ramo 1 (skip).
- `emittente_fiscale_id` è NOT NULL sulla tabella: la risoluzione finale è
  garantita dalla catena default → normalize (evasione/fallback) prima del
  check del vincolo.

---

{% include-markdown "signature-core.md" %}
