## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_reso`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) (simmetrica) ·
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) ·
> [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti) ·
> [vendite.fn_annulla_accredito_riga_reso](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso)
> (la strada da prendere prima)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Funzione madre atomica** (`SECURITY INVOKER`) che annulla un reso e **storna** gli effetti,
simmetrica a `fn_conferma_reso`. Stati ammessi: `DRAFT` o `CONFERMATO`
(`E_RESO_STATO_NON_ANNULLABILE`).

### Logica

1. **Due guard anti-storno complesso**, gemelli fra loro e tutti e due prima di qualunque
   scrittura. In entrambi i casi c'è **un effetto già partito**, che l'annullo del documento non
   saprebbe riportare indietro:
   - un reso già **ri-spedito** (righe nel ponte `resi_righe_riconsegne`) **non** è annullabile —
     lo storno di una ri-spedizione emessa è fuori perimetro (`E_RESO_ANNULLO_CON_RICONSEGNE`);
   - *(rev 2026-08-19)* un reso già **accreditato** (almeno una riga in `resi_righe_accrediti`)
     **non** è annullabile (`E_RESO_ANNULLO_CON_ACCREDITO`). L'accredito ha già creato una
     rettifica a quantità negativa che il giro di fatturazione raccoglie da solo: annullare il
     reso senza disfarla farebbe uscire **una nota di credito per un reso che non esiste più**.
     Il messaggio dice la strada: annullare prima l'accredito sulla riga, poi il reso.
2. Transizione → `ANNULLATO`.
3. **Solo se era CONFERMATO** — storno: l'addendo reso decade (l'helper filtra i CONFERMATI) →
   **ri-proiezione stato ordine** (`PARZIALMENTE_EVASO`/`EVASO`); e **ri-flip DDT** `RESO →
   CONSEGNATO` se non è più reso totale (transizione seedata nella matrice DDT).

Un annullo in `DRAFT` non ha effetti (nulla era stato applicato).

### ⚠️ La guardia dell'accredito: cosa guarda e cosa non guarda (rev 2026-08-19)

Il predicato è **l'esistenza della riga di ponte**, non lo stato delle rettifiche. Se
l'accredito è ormai troppo tardi per essere disfatto lo dice la sua madre
(`fn_annulla_accredito_riga_reso`, con `E_ACCREDITO_ANNULLO_NON_AMMESSO`): ricalcolare qui
«tutte NON_EMESSA» sarebbe una **seconda copia della stessa regola**, destinata a divergere.

**Si rifiuta, non si cascata.** L'annullo dell'accredito pretende un *motivo obbligatorio* e la
traccia del perché vive solo in `commesse_attivita_log`: una cascata automatica dovrebbe
inventarselo. E se anche una sola rettifica non è più `NON_EMESSA`, l'annullo del reso non deve
avvenire **affatto** — non avvenire a metà.

⭐ **Vincolo reciproco, su tre posti** (C-3), con
[script.fn_check_rinuncia_reversibile](/dbzero/script/funzioni/fn_check_rinuncia_reversibile) e
[vendite.fn_annulla_accredito_riga_reso](/dbzero/vendite/funzioni/fn_annulla_accredito_riga_reso):
la guardia **si auto-ripara** perché l'annullo dell'accredito *cancella* le righe di ponte. Se un
giorno quell'annullo diventasse un *soft-delete*, questo ramo continuerebbe a vedere la riga e
vieterebbe per sempre l'annullo di un reso ormai annullabile, **in silenzio**. I tre posti si
cambiano insieme.

**Il verso opposto era già chiuso**: accreditare un reso *annullato* non passa, perché
`vw_resi_da_accreditare` si costruisce su `vw_resi_righe_effettive`, che filtra i soli
`CONFERMATO` — la riga esce dalla coda e `fn_accredita_riga_reso` risponde
`E_ACCREDITO_NON_IN_CODA`.

Verifica: `db/pgtap/vendite/test-annulla-reso-gate-accredito-v1.sql` (8 asserzioni).

---

### Il ri-flip conta solo la merce

(rev 3-11-2026, `20261103-32`, brief `brief-db-addebito-trasporto-ordine` §8.1)

Il ri-flip `RESO → CONSEGNATO` usa lo stesso predicato del flip di
[`fn_conferma_reso`](fn_conferma_reso.md), e come lui conta solo le righe di
**merce** della bolla
([`script.fn_natura_e_merce`](/dbzero/script/funzioni/fn_natura_e_merce)): un
onere non si rende e non pesa sul «reso totale». Le due madri cambiano insieme.

Verifica: `db/pgtap/vendite/test-bolla-onere-partita-reso-v1.sql`.
