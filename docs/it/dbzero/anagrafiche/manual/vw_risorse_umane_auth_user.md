## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_risorse_umane_auth_user`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user) (bridge legacy)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) (concettualmente equivalente, non usata direttamente dalla vista per ragioni di performance)
> [anagrafiche.trgfn_risorse_umane_auth_user_sync_identita](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_auth_user_sync_identita) (trigger-ponte di transizione)

---
### 🎯 Scopo Principale
(latest review 19-04-2026)

La vista **`anagrafiche.vw_risorse_umane_auth_user`** è la **vista di
compatibilità** (§4.6.F.1 WIP multi-face-auth) che riproduce il layout
della tabella legacy `risorse_umane_auth_user` leggendo dal nuovo bridge
`identita_digitali` (filtrato su `ruolo_applicativo = 'OPERATORE'`).

Creata per permettere il **cutover a due fasi**:

1. **PR1 DB** (questa fase): la vista nasce con prefisso `vw_` e convive
   con la tabella omonima `risorse_umane_auth_user`. Read-only.
2. **PR3 DB** (cutover §4.6.H.2): la tabella legacy viene rinominata in
   `_legacy_risorse_umane_auth_user`; la vista viene rinominata in
   `risorse_umane_auth_user` (nome canonico). Tutti i reader esistenti
   continuano a funzionare senza modifiche.

---

### Read-only

La vista è **letta** (nessuna regola INSTEAD OF). Tutti i writer saranno
migrati a `identita_digitali` prima del cutover:

* `fn_registra_tentativo_login`, `fn_check_blocco_login` (PR1 DB, fatto)
* `auth_repository`, `amm_software_repository` (PR2 backend)
* `fn_crea_risorsa_umana` → al cutover §4.6.H scriverà direttamente sul
  nuovo bridge (durante PR1 il trigger-ponte propaga)

---

### Layout di output

La vista espone **esattamente** le colonne di `risorse_umane_auth_user`:

| Campo | Origine | Note |
|-------|---------|------|
| `id` | `identita_digitali.id` | PK surrogata (tipo diverso ma compatibile per i client) |
| `risorsa_umana_id` | JOIN `risorse_umane.id` via `soggetto_ruolo_id` | Compat legacy |
| `auth_user_id` | `identita_digitali.auth_user_id` | |
| `attivo` | `identita_digitali.attivo` | |
| `meta` | `identita_digitali.meta` | |
| `data_insert` / `user_insert` / `data_update` / `user_update` | `identita_digitali.*` | Audit standard |
| **`ruolo_sistema`** | **Calcolato (CASE)** | Vedi sotto |
| `storicizza` | `identita_digitali.storicizza` | |
| `tx_id` | `identita_digitali.tx_id` | |
| `tentativi_falliti` | `identita_digitali.tentativi_falliti` | |
| `bloccato_fino_a` | `identita_digitali.bloccato_fino_a` | |
| `deve_cambiare_password` | `identita_digitali.deve_cambiare_password` | |
| `invito_inviato_at` | `identita_digitali.invito_inviato_at` | |
| `totp_obbligatorio` | `identita_digitali.totp_obbligatorio` | |

---

### Ricostruzione `ruolo_sistema`

Il campo legacy `ruolo_sistema` (enum `ADMIN`/`OPERATIVO`/`DISABILITATO`)
è ricostruito dinamicamente:

```sql
CASE
    WHEN NOT id.attivo
      OR id.ruolo_applicativo = 'DISABILITATO'
      OR valido_dal > CURRENT_DATE
      OR valido_al  < CURRENT_DATE
        THEN 'DISABILITATO'
    WHEN sa.identita_digitale_id IS NOT NULL
        THEN 'ADMIN'
    ELSE 'OPERATIVO'
END
```

Dove `sa` è una sub-query `LEFT JOIN` pre-aggregata sui bindings
`SUPER_ADMIN` attivi.

---

### Performance: LEFT JOIN vs chiamata funzione

La vista **non** chiama `fn_is_super_admin(id.auth_user_id)` per ogni
riga (pattern N+1 evitato). Usa invece un **LEFT JOIN** a una sub-query
pre-aggregata:

```sql
LEFT JOIN (
    SELECT pab.identita_digitale_id
      FROM config.profili_accesso_bindings pab
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'SUPER_ADMIN'
       AND pab.identita_digitale_id IS NOT NULL
) sa ON sa.identita_digitale_id = id.id
```

L'indice parziale UNIQUE `uq_profili_accesso_bindings_identita`
garantisce al più una riga per identità, quindi non serve `DISTINCT`.
Un solo piano di query, indici FK sfruttati.

---

### Filtro `ruolo_applicativo = 'OPERATORE'`

La vista espone **solo** le identità operatore, coerentemente con la
semantica di `risorse_umane_auth_user` che era un bridge operatori.
Le identità portale/shop/fornitore **non** compaiono.

Conseguenza: un'identità il cui `ruolo_applicativo` viene cambiato da
`OPERATORE` a qualcos'altro **sparisce** dalla vista. Scenario
improbabile in produzione (il trigger-ponte non fa questo cambio; solo
un UPDATE manuale potrebbe farlo), ma semanticamente coerente.

---

### Convivenza con la tabella legacy

Durante PR1 e PR2:

* `risorse_umane_auth_user` (tabella) contiene righe reali, scritte dal
  backend legacy + propagate dal trigger-ponte §4.6.D.4.
* `vw_risorse_umane_auth_user` (vista) legge da `identita_digitali` e
  deve restituire gli stessi dati per ogni operatore.

Il backfill §4.6.E garantisce allineamento al deploy; il trigger-ponte
mantiene allineamento a runtime.

Al cutover §4.6.H.2 la tabella viene rinominata in
`_legacy_risorse_umane_auth_user` e la vista viene rinominata
`risorse_umane_auth_user`: da quel momento la fonte dati è unica
(`identita_digitali`).

---

{% include-markdown "signature-core.md" %}
