## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_usato`

> 👀 **Vedi anche**
>
> [catalogo.articoli](/dbzero/catalogo/manual/articoli) — la regola «un articolo usato non cambia la sua struttura»
> [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/manual/trgfn_articoli_guard_struttura_se_usato) — il guard che legge questo predicato

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)

Dice se un articolo è **usato**: se compare in un documento, in un listino, in una commessa o in
magazzino, in qualunque stato. È il predicato unico della regola A-10: lo leggono il guard
sull'articolo e il form (le regole in `dbops.lock_columns_conditional`).

---

### Che cosa conta come uso

Una riga in una tabella che punta all'articolo con una FK, **in qualunque stato**: anche chiusa,
annullata o con `attivo = false`. I documenti chiusi si rileggono (fatture, resi, giacenze), quindi
devono restare coerenti con l'articolo.

Le tabelle **non** sono elencate: si leggono da `pg_constraint`. Una tabella nuova che punta
all'articolo conta da sola come uso (fail-closed), senza toccare questa funzione.

Si escludono, dichiarate nella funzione, le tabelle che sono **anagrafica dell'articolo** e non un
suo uso:

| Tabella | Perché non è un uso |
| --- | --- |
| `catalogo.articoli_componenti` | la distinta è struttura dell'articolo, e ha i suoi guard |
| `catalogo.articoli_uom_operativa` | le unità di misura dell'articolo |
| `catalogo.note_articoli` | note |
| `vendite.articoli_descrizioni_aggiuntive` | descrizioni |
| `vendite.articolo_regole_fatturazione` | regole dell'articolo |
| `anagrafiche.soggetti_titoli_iva_ambiti` | configurazione fiscale |

---

### Perché SECURITY DEFINER

Gli articoli sono **unici per tutte le aziende** (il catalogo non ha emittente né RLS), mentre i
documenti hanno la RLS per emittente. Letto con la RLS di chi modifica l'articolo, il predicato non
vedrebbe i documenti delle altre aziende, e un articolo usato da un'altra azienda risulterebbe
libero. La funzione ritorna solo un `boolean`: non rivela niente di quei documenti.

`search_path` bloccato; l'SQL dinamico usa solo la tabella e la colonna lette dal catalogo, e
l'id dell'articolo come parametro.

---
{% include-markdown "signature-core.md" %}
