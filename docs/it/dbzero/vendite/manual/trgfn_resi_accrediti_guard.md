## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_accrediti_guard()`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti) ·
> [fn_resi_riga_tetti_accredito](fn_resi_riga_tetti_accredito.md) ·
> [fn_accredita_riga_reso](fn_accredita_riga_reso.md) ·
> [trgfn_resi_riconsegne_guard](trgfn_resi_riconsegne_guard.md) — il gemello ·
> [trgfn_resi_rinunce_guard](trgfn_resi_rinunce_guard.md) — l'altro gemello
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-note-credito-resi.md` (§12.6-ter)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

Il **tetto del documento** sul ponte degli accrediti:

```text
Σ qta per riga di FATTURA  ≤  qta della riga
```

Cioè: *«questa riga di fattura ha fatturato 10 pezzi, non se ne possono
accreditare 11»*.

⭐ **È un limite che prima non esisteva.** Fino al 2026-08-18 l'unico tetto
all'accredito era il conto della **merce** (`fatturati − tenuti`). Questo parla
la lingua del **documento**, ed è una misura indipendente: due conti che devono
concordare, e quando divergono non c'è un numero di cui fidarsi — c'è un difetto
da guardare.

Trigger: `trg_resi_accrediti_a10_guard_ins_upd`, fase `_a10_` (guard),
`BEFORE INSERT OR UPDATE OF qta, qta_partita, resi_riga_id, fattura_riga_rettificata_id`.

---

### ⚠️ Perché tiene UN tetto solo, e non due

Il piano ne prevedeva due qui. **Non regge sull'articolo composito**, ed è il
caso più comune della coda accrediti di oggi:

```text
la MERCE si misura in UNITÀ PADRE          →  accredito dovuto = 1
il DOCUMENTO in unità di riga di fattura   →  tre righe di ponte, qta 1 + 1 + 1
```

Un tetto «Σ qta per riga di reso ≤ accredito dovuto» valutato **riga per riga**
direbbe «3» dove la merce dice «1», e **rifiuterebbe il secondo componente** di
un accredito perfettamente legittimo. È lo stesso motivo per cui
`vw_af_merce_per_riga` calcola `quantita_padre = max(quantita / coeff_qta)`
invece di sommare i componenti.

✅ Ciascun tetto vive dove è esattamente definibile:

| Tetto | Chi | Forma | Perché lì |
|---|---|---|---|
| **DOCUMENTO** | questo guard | `≤`, riga per riga | è esatto a livello di riga, e vale anche contro una scrittura diretta sul ponte |
| **MERCE** | `fn_accredita_riga_reso` | **uguaglianza** | è l'unica a conoscere l'unità padre e a sapere quando l'operazione è finita |
| doppione esatto | `uq_resi_accrediti_pair` | unicità | il doppio click |

⚠️ **Non è un tetto in meno**: è lo stesso tetto messo dove può essere vero.
Metterlo qui l'avrebbe reso una cintura che si strappa sul caso più comune.

---

### 🔴 Perché il tetto si legge da una `SECURITY DEFINER`

Un guard che legge sotto RLS **non distingue «non lo vedo» da «non c'è»**.
`vendite.fatture_righe` ha policy attive, e la riga di fattura da accreditare
potrebbe stare fuori dal perimetro di chi scrive: la lettura tornerebbe zero
righe, e un tetto letto come zero **smette di dire la verità** — blocca a
sproposito, o (con un confronto indeterminato) lascia passare.

È il difetto già visto in `trgfn_resi_righe_guard_origine_coerente`, e la cura è
la stessa: la riga correlata si legge da
[`fn_resi_riga_tetti_accredito`](fn_resi_riga_tetti_accredito.md), che è
`SECURITY DEFINER` con `search_path` fissato.

---

### Lock: nessun advisory lock

`FOR UPDATE` sulla **riga di reso padre** e sul **gruppo di accrediti della
stessa riga di fattura**. Serializza il caso che questo tetto esiste per fermare:
**resi diversi** che accreditano la stessa riga di fattura in momenti diversi.

È il pattern dei due gemelli (`trgfn_resi_riconsegne_guard`,
`trgfn_resi_rinunce_guard`), e protegge anche le scritture dirette sul ponte, non
solo quelle che passano dalla madre.

---

### Le verifiche, in ordine

| # | Cosa | Errore |
|---|---|---|
| 0 | `qta > 0` e `qta_partita > 0` (difesa oltre ai `CHECK`) | `E_QTA_NON_POSITIVA` |
| 1 | lock sulla riga di reso e sul gruppo della riga di fattura | — |
| 2 | lettura del tetto **sopra la RLS** | — |
| 3 | `Σ qta` (esclusa la riga corrente in UPDATE) `+ NEW.qta ≤ qta della riga di fattura` | `E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA` |

⚠️ **Ogni `fn_log_and_raise_error` porta almeno un valore VARIADIC**: senza, la
risoluzione dell'overload fallisce e l'errore che esce è *«la funzione non
esiste»* (`42883`) invece del codice di dominio (`P0001`). Un `throws_ok` senza
SQLSTATE lo accetterebbe, e il guard **sembrerebbe funzionare**.

---

### Codici errore

| Codice | Quando |
|---|---|
| `E_QTA_NON_POSITIVA` | `qta` o `qta_partita` nulle o non positive |
| `E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA` | la somma degli accrediti supererebbe la quantità che la riga di fattura ha fatturato |

---

{% include-markdown "signature-core.md" %}
