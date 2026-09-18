## 📘 Documentazione Concettuale – Vista `magazzino.vw_disponibilita_articolo`

> 👀 **Vedi anche**
>
> • [magazzino.vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) — la grana articolo × magazzino, da cui questa somma
> • [magazzino.vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale) — lo stesso «globale = visibile»
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.6)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**La disponibilità di un articolo su tutti i magazzini visibili**: `giacenza`, `bloccata`,
`disponibile` sommate da [vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita), più
`n_magazzini` (quanti ne concorrono).

«Globale» vuol dire **visibile a chi interroga**: dentro l'emittente attivo è tutto, ed è la
row level security dei magazzini a decidere il perimetro, non un filtro scritto qui — come
per [vw_costo_medio_globale](/dbzero/magazzino/views/vw_costo_medio_globale).
`security_invoker`.

Presidio: `db/pgtap/magazzino/test-vw-disponibilita-v1.sql` (5, 7).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-24`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
