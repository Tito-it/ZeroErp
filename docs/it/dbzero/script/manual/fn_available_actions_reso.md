## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_reso`

> 👀 **Vedi anche**
>
> [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) ·
> [vendite.trgfn_resi_guard_transizione](/dbzero/vendite/funzioni/trgfn_resi_guard_transizione) (lato write) ·
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Capability del reso per il detail API, **data-driven** da `config.transizioni_stati_reso`. È il
lato-**lettura** simmetrico al guard `trgfn_resi_guard_transizione` (stessa matrice: uno valida, uno
espone), così il FE **non hardcoda** i pulsanti.

`STABLE`, `SECURITY INVOKER`. Ritorna JSONB: `available_actions` (transizioni ammesse col filtro
`manuale`, ordinate), `can_change_state`, `can_edit_testata`/`can_edit_righe` (solo DRAFT),
`non_editable_fields`, `stato_codice`.

### ⭐ La transizione ad ANNULLATO si spegne col motivo (20-08-2026)

Se il reso ha un **accredito registrato** (una riga di ponte in
`vendite.resi_righe_accrediti`), l'azione `annulla` esce con:

```text
enabled     = false
reason      = RESO_CON_ACCREDITI
reason_key  = vendite.reso.annulla_reason.con_accrediti
```

**Perché disabilitata e non nascosta, e non lasciata accesa.** È la regola di
[linee-guida-sql §12](/linee-guida-sql) — *permesso ⇒ nascondi, **stato** ⇒
disabilita col motivo*: avere un accredito è uno **stato che cambia**, si disfa
l'accredito e l'annullo torna possibile. Nasconderla non direbbe perché;
lasciarla accesa manderebbe l'operatore a prendersi un 409 in faccia.

⚠️ **Il predicato è lo STESSO `EXISTS`** del guard in `vendite.fn_annulla_reso`
(`E_RESO_ANNULLO_CON_ACCREDITO`, 933). Se i due divergono, il bottone è grigio
su un annullo che sarebbe passato — o, peggio, acceso su uno che verrà
rifiutato. Il pgTAP `test-annulla-reso-gate-accredito-v1` verifica **entrambi
nello stesso file** (test 2/4 il guard, 9/10/11 la capability) proprio per
questo.

⭐ **Niente flag di testata `ha_accrediti`**, che era la richiesta iniziale del
BE: la terna `enabled`/`reason`/`reason_key` esiste **per azione** ed è già letta
dal frontend, mentre un flag di documento spegnerebbe anche le transizioni che
non c'entrano.

⚠️ **`vendite.resi_righe_accrediti` non ha RLS** (verificato il 20-08-2026), e la
funzione è `SECURITY INVOKER`: contava saperlo. Se un domani la RLS ci
arrivasse, chi non vede il ponte leggerebbe «nessun accredito» e si troverebbe
il bottone acceso — lì servirebbe una `SECURITY DEFINER`, non un `COALESCE`.

**Precedenza fra motivi**: lo **specifico** batte il generico — accrediti prima
di `requires_righe`. Oggi non si incontrano (le transizioni `annulla` non
dichiarano `requires_righe`, e un reso con accrediti ha per forza righe), ma un
ordine non scritto è un ordine che il prossimo cambia senza accorgersene.

### Mirror RIDOTTO del DDT

Rispetto a `fn_available_actions_ddt` **omette** `push_commessa` (nessun push reso in questa slice) e
il blocco `pdf` (i resi sono fuori dal motore stampa). Copia solo matrice→azioni + capability di
editing.
