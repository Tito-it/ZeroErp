## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_magazzini_guard_usa_ubicazioni`

> 👀 **Vedi anche**
>
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — `usa_ubicazioni`, dove è montato
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — ciò che legge
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§3 D-L2-m)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**`usa_ubicazioni` si cambia solo a registro vuoto.** Il flag decide la *grana* del registro
di quel magazzino (ogni movimento nomina un'ubicazione, o nessuno). Cambiarlo con merce a
registro lascerebbe righe scritte con l'altra grana — cioè la convivenza «con e senza
posizione» che il flag esiste per rendere impossibile. Si decide alla nascita; se esiste un
movimento del magazzino il cambio è rifiutato con `E_MAG_MAGAZZINO_CON_GIACENZA` (campo
`usa_ubicazioni`, il codice del magazzino nella frase). Con merce dentro, la strada è un
magazzino nuovo con l'impostazione giusta e un trasferimento.

Contano i **movimenti**, non il saldo (anche a saldo zero le righe hanno la grana vecchia), e
non gli attesi (una promessa non è merce a registro). Riscrivere lo stesso valore non è un
cambio. Montato `BEFORE UPDATE OF usa_ubicazioni`.

Presidio: `db/pgtap/magazzino/test-fn-scrivi-movimento-controlli-v1.sql` (16-17).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-09`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
