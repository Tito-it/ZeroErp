## 📘 Documentazione Concettuale – View `dbops.vw_sorgenti_orfane`

> 👀 **Vedi anche**
>
> • [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — chi la calcola
> • [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — su quali tabelle
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei bersagli
> • [dbops.presidi](/dbzero/dbops/tabelle/presidi) — dove è iscritta
>
Guide: [Sorgente polimorfa](/guide/sorgente-polimorfa) · [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) · brief `brief-db-magazzino-lotto-2-motore` (§4.7, D-9)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Le righe la cui sorgente punta a un record che non c'è più.** Un movimento di magazzino
dice da quale riga di documento nasce (tipo a catalogo + una chiave); la relazione non è una
chiave esterna e non può esserlo (il bersaglio cambia con il tipo). Il guard tipizzato
impedisce di *inserire* una riga verso un bersaglio inesistente; questa vista trova quelle
rimaste orfane **dopo**, quando qualcuno ha cancellato il bersaglio.

> ⚠️ **Deve restare a zero righe.** Una riga qui è un movimento (o un atteso, una testata)
> che parla di una riga di documento sparita. Il rimedio non è cancellare il movimento: è
> capire chi ha cancellato il bersaglio — di norma è un `DELETE` fuori dalle porte, perché
> i documenti interni registrati non si eliminano.

Natura `ZERO`, perimetro `DEFINER` (la funzione attraversa la row level security: un orfano
in una tabella protetta va visto comunque), cadenza `SETTIMANALE`.

Il perimetro delle tabelle esaminate si **deriva dal catalogo** e si legge da
[fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro): oggi le
sei di magazzino. Presidio: `db/pgtap/dbops/test-sorgenti-orfane-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-25`).

---

{% include-markdown "signature-core.md" %}
