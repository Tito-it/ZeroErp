## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_colonne_struttura`

> 👀 **Vedi anche**
>
> [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/manual/fn_articolo_correggi_struttura) — il verbo che la usa per le colonne ammesse
> [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato) — la regola «un articolo usato non cambia la sua struttura»
> [dbops.lock_columns_conditional](/dbzero/dbops/manual/lock_columns_conditional) — il registro da cui legge

### 🎯 Scopo Principale

(nasce 2026-10-18, brief-db-articoli-ammessi-per-documento R-DB-3)

Dice **quali sono le colonne strutturali** di un articolo: quelle che non cambiano più quando
l'articolo è usato, e che il SUPER_ADMIN può correggere. È l'unico posto da cui si legge l'elenco.

---

### Da dove legge

L'elenco non è scritto qui. Sono le regole **accese** del form in `dbops.lock_columns_conditional`
su `catalogo.articoli` con il predicato dell'uso (`catalogo.fn_articolo_usato($1::uuid)`): le colonne
che il form spegne quando l'articolo è usato sono le stesse che la correzione deve riaprire.

* Ordine: quello della dichiarazione nel registro.
* Array vuoto se il registro non ha regole su quel predicato.
* Una regola spenta (`enabled = false`) esce dall'elenco.

### Chi la legge

| Lettore | Per che cosa |
| --- | --- |
| `catalogo.fn_articolo_correggi_struttura` | le colonne ammesse in `p_campi`, e quelle che scrive |
| backend (dettaglio dell'articolo) | i campi che la scheda riapre in correzione, al posto della sua lista |

### Le copie che restano scritte

Il guard `catalogo.trgfn_articoli_guard_struttura_se_usato` ha l'elenco scritto due volte: nel
trigger (`BEFORE UPDATE OF …`) e nel suo `CASE`. Un trigger non può leggere le sue colonne da una
funzione. Le confronta con questa il pgTAP `catalogo/test-articolo-colonne-struttura-v1`: chi
aggiunge una nona colonna al registro senza toccare il guard lo vede rosso.

SECURITY INVOKER: il registro lo legge anche l'app.

---
{% include-markdown "signature-core.md" %}
