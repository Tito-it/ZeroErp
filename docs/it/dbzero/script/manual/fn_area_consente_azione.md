## 📘 Documentazione Concettuale – Funzione `script.fn_area_consente_azione()`

> 👀 **Vedi anche**
>
> **Chi la chiama:** [script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni) · `dbops.fn_pgtap_concedi_azione` (fixture dei pgTAP)

---

### 🎯 Scopo Principale
(scritta il 04-10-2026)

Dice se il livello d'area di un operatore **basta** per un'azione che chiede un
certo minimo (`config.azioni_processo.livello_minimo_area`).

| Livello dell'area | Minimo TUTTO | Minimo LETTURA |
| --- | --- | --- |
| TUTTO | sì | sì |
| LETTURA | no | sì |
| BLOCCATO | no | no |

Un valore mancante vale «no».

⚠️ Nel database i tre livelli sono ordinati TUTTO < LETTURA < BLOCCATO (il
contrario di come si leggono): il confronto giusto è «livello ≤ minimo». È
scritto **solo qui**, perché un verso sbagliato concederebbe tutto a chi è
bloccato.

Presidio: `db/pgtap/script/test-permessi-tetto-area-v1.sql` test 3.

{% include-markdown "signature-core.md" %}
