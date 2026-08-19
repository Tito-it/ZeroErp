## 📘 Documentazione Concettuale – Funzione `vendite.fn_resi_riga_accreditato_partita(...)`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti) ·
> [vw_resi_da_accreditare](vw_resi_da_accreditare.md) ·
> [fn_accredita_riga_reso](fn_accredita_riga_reso.md) ·
> [fn_resi_riga_residuo_riconsegna](fn_resi_riga_residuo_riconsegna.md) — la sorella per l'altra uscita
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-note-credito-resi.md` (slice **N9**)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

Quanti pezzi — in **unità di merce**, cioè unità padre della partita — sono già
stati accreditati per una riga di reso.

**Punto UNICO della formula.** La consuma `vw_resi_da_accreditare` per non
ri-offrire una quota già accreditata.

---

### 🔴 Il difetto che questa funzione chiude

La coda accrediti ripartisce l'accredito della **partita** fra le righe di reso
con una finestra `ORDER BY resi_riga_id`. Fino al 2026-08-18 quella finestra non
sapeva nulla degli accrediti già fatti. Misurato sulla partita 17163 — accredito
8, due righe di reso da 5 e da 3:

```text
prima                  5797 → 5   ·  5799 → 3            ✅
si accredita 5797, poi l'emissione: l'accredito della partita scende a 3
dopo, col difetto      5797 → 3   ·  5799 → 0 (sparita)  🔴
```

Cioè: **la riga già accreditata torna in coda a chiedere altri 3**, e la riga che
quei 3 li deve davvero **esce dalla coda**. La madre respinge la prima
(`E_ACCREDITO_GIA_ESEGUITO`), e la seconda non è più raggiungibile.

⚠️ **È la malattia per cui il cantiere della nota di credito esiste** — la riga
che resta in coda a chiedere per sempre — in una forma nuova, creata proprio dal
rimedio.

✅ La correzione: la finestra si applica alla quantità **ancora accreditabile**
(`quantità − già accreditato`), non alla quantità resa. Ed è questa funzione a
dire il secondo addendo.

---

### ⭐ E regala l'idempotenza

Con la quota già accreditata dentro la distribuzione, una riga **esce dalla coda
al VERBO**, non alla generazione della fattura. Il §12.6-E del brief descriveva
una finestra da presidiare — fra il verbo e l'emissione l'attività fatturabile
non esiste ancora, il conto della merce non è cambiato, e un secondo click
sarebbe stato coerente col conto. Quella finestra **non c'è più**: c'è un numero
che è già sceso.

---

### ⚠️ La somma è UNA VOLTA PER GRUPPO, non per riga

Due casi tirano in direzioni opposte, e coesistono:

```text
kit           →  N righe con la STESSA quota padre   →  sommarle la MOLTIPLICA
consumo LIFO  →  N righe con quote padre DIVERSE     →  vanno SOMMATE
```

La colonna `gruppo` di `resi_righe_accrediti` — il segmento della rettifica
privato del suffisso `#CMP` — distingue i due casi: **un gruppo = un'unità
fatturante consumata**. Da qui il `DISTINCT (gruppo, qta_partita)` prima della
somma.

---

### Nessun raise, e non è una dimenticanza

È letta da una **vista**, su insiemi in movimento: una riga cancellata non deve
farla fallire. Stessa scelta della sorella `fn_resi_riga_residuo_riconsegna`, e
per la stessa ragione.

---

### Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `p_resi_riga_id` | `vendite.resi_righe.id%TYPE` | la riga di reso |

### 📦 Output

| Tipo | Descrizione |
|---|---|
| `vendite.resi_righe_accrediti.qta_partita%TYPE` | pezzi già accreditati in unità di **merce**. `0` se non ce ne sono |

---

### Esempio d'uso

```sql
-- Quanto resta ancora accreditabile di una riga di reso
SELECT rr.quantita
     - vendite.fn_resi_riga_accreditato_partita(rr.id) AS ancora_accreditabile
  FROM vendite.resi_righe rr
 WHERE rr.id = :resi_riga_id;
```

---

{% include-markdown "signature-core.md" %}
