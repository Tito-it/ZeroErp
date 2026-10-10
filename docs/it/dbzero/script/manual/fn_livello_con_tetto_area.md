## 📘 Documentazione Concettuale – Funzione `script.fn_livello_con_tetto_area()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [script.fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti)

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

Dato il livello di un override su un oggetto e il livello della sua area,
restituisce **il più restrittivo dei due**: l'override può togliere, non
aggiungere. Senza override vale l'area; un'area sconosciuta vale BLOCCATO.

La tabella dei casi è nella pagina di
[fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti).

⚠️ Nel database i livelli sono ordinati TUTTO < LETTURA < BLOCCATO: «il più
restrittivo» è il **maggiore**. Il confronto è scritto solo qui.

Presidio: `db/pgtap/script/test-permessi-tetto-area-v1.sql` test 4.

{% include-markdown "signature-core.md" %}
