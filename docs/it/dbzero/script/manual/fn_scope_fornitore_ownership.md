## Documentazione Concettuale – Funzione `script.fn_scope_fornitore_ownership`

> **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
**Tabelle correlate:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [config.scope_policy](/dbzero/config/tabelle/scope_policy)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`script.fn_scope_fornitore_ownership`** implementa la policy
di scope `FORNITORE_OWNERSHIP`: verifica che un'identità `FORNITORE_PORTALE`
possa vedere dati riferiti a un `soggetto_ruolo` di tipo fornitore.

Regola: il fornitore target coincide con il `soggetto_ruolo` dell'identità,
e l'identità stessa è in veste `FORNITORE_PORTALE` utilizzabile oggi.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | Identità corrente. |
| `p_fornitore_sr_id` | `anagrafiche.soggetti_ruoli.id%TYPE` | `soggetto_ruolo_id` del fornitore target. |

---

### Output

`BOOLEAN` — `true` se il fornitore target è quello dell'identità, `false` altrimenti.

---

### Semantica (fail-closed)

| Caso | Risultato |
|------|-----------|
| Identità inesistente / non utilizzabile oggi | `false` |
| Identità con `ruolo_applicativo ≠ FORNITORE_PORTALE` | `false` |
| Target `soggetto_ruolo_id` diverso da quello dell'identità | `false` |
| Tutte le condizioni soddisfatte | `true` |

⭐ **Dal 07-10-2026** (brief `brief-db-veste-utilizzabile`): l'identità deve essere
**utilizzabile oggi** secondo
[script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)
(accesa, nelle sue date, soggetto attivo), non solo accesa. Prima una veste
scaduta, ma ancora accesa, continuava a vedere i suoi dati.


---

### Come è fatta (dal 21-10-2026)

La regola è scritta **una volta**, nei building block delle policy di controparte, e
questa funzione li compone per la domanda su **una** riga:
[`fn_get_identita_sr_perimetro`](fn_get_identita_sr_perimetro.md) nella veste
`FORNITORE_PORTALE` (il soggetto dell'identità, se utilizzabile oggi) confrontato con
`p_fornitore_sr_id` da `fn_scope_sr_perimetro`.

⭐ **Le policy di `acquisti.ordini` e `acquisti.ddt` non passano più di qui**
(`20261021-43`): chiamano i building block direttamente, col perimetro calcolato una
volta per istruzione (linee-guida-sql §10.3). Questa funzione resta come funzione della
regola `FORNITORE_OWNERSHIP` nel catalogo `config.scope_policy`.

---

### Check `ruolo_applicativo = 'FORNITORE_PORTALE'` — ridondanza difensiva

Il filtro sul ruolo applicativo è **tecnicamente ridondante** se il binding
`FORNITORE_OWNERSHIP` viene creato solo per identità `FORNITORE_PORTALE`
(come prescrive il workflow). Tuttavia è mantenuto come **defense-in-depth**:

* Se per errore amministrativo un binding `FORNITORE_OWNERSHIP` fosse creato
  su un'identità di altro ruolo, la policy non aprirebbe dati sbagliati.
* Rende la funzione self-contained: leggibile e verificabile senza conoscere
  il workflow di assegnazione dei binding.

---

### Uso tipico

Policy RLS su tabelle acquisti (ordini ricevuti, pagamenti verso fornitore):

```sql
CREATE POLICY rls_acquisti_ordini_fornitore_ownership ON acquisti.ordini
    FOR SELECT
    USING (
        script.fn_scope_fornitore_ownership(
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
            fornitore_soggetto_ruolo_id
        )
    );
```

---

{% include-markdown "signature-core.md" %}
