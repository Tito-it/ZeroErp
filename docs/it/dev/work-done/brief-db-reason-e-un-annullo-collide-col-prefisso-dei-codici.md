# Brief DB — il `reason` `E_UN_ANNULLO` collide col prefisso dei codici errore

> ## ✅ CHIUSO il 2026-08-31
>
> | Cosa | Dove | Esito |
> | --- | --- | --- |
> | il `reason` rinominato in **`RIGA_DI_ANNULLO`** | changeSet `20260831-35`, applicato | ✅ verificato sulla funzione **viva** (`pg_proc`), non sullo YAML |
> | il `reason_key` **non** toccato | — | ✅ resta `…annullo_blocco.e_un_annullo`: è un indirizzo, e il testo a video non cambia |
> | la convenzione scritta dove si legge | `linee-guida-sql` §12.5.1 | ✅ con il caso reale e il criterio «si guardano i vicini» |
> | lo smoke che asseriva il valore vecchio | `smoke-titoli-iva-annullo-movimento.py` | ✅ aggiornato — `scripts/smoke-baseline.sh titoli-iva-annullo-movimento` verde |
> | la doc manuale della funzione | `dbzero/script/manual/…` | ✅ la tabella dei motivi diceva ancora `E_UN_ANNULLO` |
> | il cancello | `test_error_codes_db_policy_guardrail` | ✅ **verde**, registro del debito a zero |
>
> ⭐ **Il nome scelto è quello proposto** (`RIGA_DI_ANNULLO`) e non
> `GIA_UN_ANNULLO`: nella stessa funzione vive `GIA_ANNULLATO`, che dice il
> contrario, e due motivi che differiscono per una parola si leggono male
> proprio su un pulsante spento.
>
> ---
>
> **Destinatario:** team DB (`dev/db-tid`).
>
> **In una riga:** `script.fn_check_annullo_movimento_titolo_iva` emette un
> `reason` che si chiama `E_UN_ANNULLO`, e il cancello dei codici errore lo legge
> come un **codice** senza policy. Un solo valore da rinominare.
>
> **Costo:** un changeSet `CREATE OR REPLACE`, una riga cambiata.
>
> **Origine:** trovato il 2026-08-31 sanando le policy del cantiere
> `brief-db-registri-di-numerazione-emittente-e-trasloco`. Non nasce da quel
> cantiere: viene da `brief-be-fe-iva-fase-3-consumatori-risolutore`
> (`20260830-23`), già mergiato.

---

## 1. Il fatto

`apps/core/tests/test_error_codes_db_policy_guardrail.py` è **rosso**, e dice:

```
1 codici errore che il database puo' nominare non hanno una policy in
error_policies.py e non sono nel registro del debito
dbops.codici_errore_senza_policy:
  - E_UN_ANNULLO  (script.fn_check_annullo_movimento_titolo_iva)
```

⛔ **Ma `E_UN_ANNULLO` non è un codice errore.** È un `reason` della capability
§12.5.1 — il motivo macchina che spegne il cestino di riga:

```sql
IF v_mov.annulla_movimento_id IS NOT NULL THEN
    v_motivi := v_motivi || jsonb_build_object(
        'codice',     'E_TITOLO_IVA_ANNULLO_NON_AMMESSO',   -- ← il CODICE
        'reason',     'E_UN_ANNULLO',                        -- ← il MOTIVO
        'reason_key', 'anagrafiche.titoli_iva.annullo_blocco.e_un_annullo',
        ...
```

Il codice vero (`E_TITOLO_IVA_ANNULLO_NON_AMMESSO`) c'è ed è a catalogo. È il
`reason` a portare per caso il prefisso `E_`, e il cancello — che cerca i
letterali `E_*` nei corpi delle funzioni — non ha modo di distinguerli.

## 2. Perché è un difetto e non un falso positivo da tollerare

⭐ **Gli altri quattro `reason` della stessa funzione non ce l'hanno:**

| `reason` | prefisso `E_` |
| --- | --- |
| `MOVIMENTO_NON_TROVATO` | no |
| `NON_FORZATURA` | no |
| `GIA_ANNULLATO` | no |
| **`E_UN_ANNULLO`** | **sì** |
| `PLAFOND_NEGATIVO` | no |

Ed è la stessa convenzione dei `reason` di
`script.fn_check_ba_cambio_emittente` (`BA_CON_STORIA`, `DEFAULT_SINGLETON`).
Quindi non c'è una seconda convenzione da rispettare: ce n'è **una**, e questa
riga è fuori.

⚠️ **La lettura sbagliata è comprensibile e va detta**, perché è il motivo per
cui è successo: `E_UN_ANNULLO` non nasce come `E_` di «errore», nasce come
**«È un annullo»** — la frase italiana abbreviata. Due grammatiche che si
scrivono uguale.

⛔ **Non si allunga il registro del debito.** `dbops.codici_errore_senza_policy`
è a zero dal 2026-08-07 e fotografa il debito del 2026-08-05: metterci dentro un
valore che non è un codice lo trasformerebbe da registro in valvola. E non si
può dichiarare una policy lato backend, perché `error_policies_generated.py` è
**generato** dal catalogo e `E_UN_ANNULLO` a catalogo non c'è (verificato:
`config.codici_errore` non lo contiene, e nemmeno `codici_errore.csv`).

⇒ **L'unica sede della correzione è la funzione che lo emette.**

## 3. La modifica

`CREATE OR REPLACE` di `script.fn_check_annullo_movimento_titolo_iva`, con il
solo `reason` cambiato:

```diff
-        'reason',     'E_UN_ANNULLO',
+        'reason',     'RIGA_DI_ANNULLO',
```

⛔ **Il vincolo è uno solo: niente prefisso `E_`.** Il nome preciso lo sceglie
chi scrive il changeSet; qui c'è la ragione per cui **non** ho proposto
`GIA_UN_ANNULLO`, che era la traduzione più diretta.

⚠️ In quella funzione esiste già `GIA_ANNULLATO`, e i due dicono cose
**opposte**: `GIA_ANNULLATO` = questa riga *è stata* annullata; l'altro = questa
riga *è* l'annullo di un'altra. Due motivi che differiscono per una parola, su
un pulsante spento, si leggono male esattamente quando conta. `RIGA_DI_ANNULLO`
dice *cosa è la riga* invece di ripetere l'avverbio, e la coppia torna
distinguibile a colpo d'occhio.

⚠️ **Il `reason_key` NON si tocca**, e non è pigrizia: è un **indirizzo**, non un
valore. Cambiarlo costerebbe due file di `locales` per comprare zero — e il
frontend legge la chiave (`labelOrCode(t, te, riga.annullo_blocco_reason_key,
riga.annullo_blocco_codice)`), quindi il testo a video **non cambia in nessuno
dei due casi**. Il `reason` si vede solo come ripiego, quando la chiave manca.

✅ **Il frontend non confronta il valore.** `TitoloIvaDrawer.vue` accende il
blocco su `!!data.annullo_blocco_codice` — sulla **presenza** del motivo — e
rende il testo da `annullo_blocco_reason_key`. Nessun `if reason === ...`.

✅ **La vista segue da sé.** `anagrafiche.vw_stiva_movimenti_dettaglio` fa
`blk.reason AS annullo_blocco_codice`: è una **proiezione**, non una copia. Non
c'è niente da rigenerare.

⛔ **MA UN CONSUMATORE CHE CONFRONTA IL VALORE C'È, ed è quello che si romperebbe
in silenzio.** Cercato su tutto il repo il 2026-08-31, `E_UN_ANNULLO` compare in
**due** posti oltre alla funzione:

| Dove | Cosa fa |
| --- | --- |
| `20_code/script/20260830-23-…yaml` | il changeSet che l'ha creata (⛔ **non si modifica**: numerazione nuova) |
| `backend/scripts/tests/smoke-titoli-iva-annullo-movimento.py:186` | **asserisce** `righe[annullo_id]["annullo_blocco_codice"] == "E_UN_ANNULLO"` |

⚠️ **Va cambiato nello stesso giro, e la ragione è che nessuno se ne
accorgerebbe:** gli smoke non li raccoglie il runner Django (stanno fuori da
`apps/`, hanno il trattino nel nome) e **non li esegue la CI**. Il 2026-08-27 sei
degli undici erano rossi **da un giorno** senza che nessuno lo sapesse. Un
rename fatto qui e non lì produce esattamente quella forma di rosso.

```bash
scripts/smoke-baseline.sh titoli-iva-annullo-movimento   # dopo la modifica
```

⭐ È anche la **prova** che la modifica ha funzionato end-to-end: quello smoke
costruisce il caso — un movimento che è già un annullo — e legge il motivo dalla
vista, cioè attraversa funzione, vista e proiezione.

## 4. Come si verifica che è chiuso

```bash
cd backend && ZEROERP_TEST_DB_E2E=1 \
  ./manage-test.sh apps.core.tests.test_error_codes_db_policy_guardrail -v 1
```

Verde. Al 2026-08-31 quel test è rosso **solo** per questa riga: gli altri dieci
codici che segnalava sono stati dichiarati lo stesso giorno (rigenerazione di
`error_policies_generated.py` + gli undici ripieghi in
`error_messages_fallback.py`).

## 5. Il presidio che manca, e non è di questo brief

⛔ **Il cancello non sa distinguere un codice da un `reason`, e continuerà a non
saperlo.** Oggi ha ragione per caso: cerca `E_*` e i `reason` non lo portano —
ma è una convenzione **non scritta e non presidiata**, e il prossimo
`reason` chiamato `E_QUALCOSA` farà lo stesso rumore.

⚠️ Questo brief **non** propone di allargare il cancello a capire la differenza:
sarebbe un'euristica su un letterale in un corpo PL/pgSQL, e vale il criterio già
scritto per il rubinetto degli accumulatori — *un cancello che capisce un caso su
cinque boccia a caso e passa a caso; dopo due blocchi sbagliati qualcuno lo
spegne, e un presidio spento è peggio di uno assente.*

⭐ La strada praticabile è **scrivere la convenzione dove si legge**: un `reason`
di `fn_check_*` non porta il prefisso `E_`, che è riservato ai codici a catalogo.
Sede naturale: `linee-guida-sql` §12.5.1, accanto alla forma
`{codice, reason, reason_key, dettaglio, valori}` che già descrive. È una riga, e
va scritta nello stesso changeSet — o il prossimo la rifà uguale.
