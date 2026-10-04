## 📘 Documentazione Concettuale – Funzione `script.fn_get_user_object_permissions_map()`

> 👀 **Vedi anche**
>
> **La catena, scritta una volta:** [script.fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti)

---

### 🎯 Scopo Principale
(riscritta il 04-10-2026, brief-db-permessi-tetto-area)

Restituisce, in una sola chiamata, il livello **effettivo** di un utente su
ogni oggetto del catalogo
([area_model_overrides](/dbzero/config/tabelle/area_model_overrides)):
`{"vendite.fattura": "LETTURA", …}`. Alimenta `/me/` → `permessi_oggetto` (via
`fn_get_user_profile`).

⚠️ Fino al 04-10-2026 restituiva solo gli override scritti, e il frontend
ricalcolava il livello da sé. Ora il valore è già quello col **tetto d'area**,
letto da
[fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti):
il frontend lo legge e basta. Per un oggetto fuori catalogo vale l'area del suo
`app_label`. Utente mancante o ≤ 0 → `E_ADMIN_VALIDAZIONE`.

{% include-markdown "signature-core.md" %}
