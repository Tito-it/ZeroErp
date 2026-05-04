## 📘 Documentazione Concettuale – Tabella `config.profili_accesso_aree`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)

---
### 🎯 Scopo Principale
(latest revision 04-05-2026 — modello legacy `profili_reparto_aree` dismesso)

La tabella **`config.profili_accesso_aree`** contiene il dettaglio delle
aree funzionali coperte da un profilo di accesso, con il **livello** consentito
su ciascuna area.

Il padre e' `profili_accesso`, generalizzato a tre tipi di profilo
(REPARTO / PORTALE / AD_HOC), legato all'utente tramite
`profili_accesso_bindings`.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `profilo_accesso_id` | FK al profilo header ([`profili_accesso`](/dbzero/config/tabelle/profili_accesso)). |
| `area_id` | FK all'area funzionale ([`aree_funzionali`](/dbzero/config/tabelle/aree_funzionali)). |
| `livello` | `config.livello_accesso`: `TUTTO` / `LETTURA` / `BLOCCATO`. Default `BLOCCATO` (chiuso di default). |

Vincolo `UNIQUE (profilo_accesso_id, area_id)` garantisce una sola riga
per coppia profilo-area.

---

### Default sicuro

Il default del campo `livello` è `BLOCCATO`: se per errore si inserisce una
riga senza specificare il livello, l'area resta chiusa. Questo allinea il
comportamento al pattern "deny-by-default" anche nel caso di configurazioni
incomplete.

---

### Catena di risoluzione (livello area)

Questa tabella interviene al **punto 3** della catena di risoluzione del
livello di accesso per area:

```
1. Override utente su SINGOLO OGGETTO? → SI: applica → NO: continua ↓
2. Override utente su AREA?            → SI: applica → NO: continua ↓
3. Profilo applicato all'identità      → SI: applica livello della profili_accesso_aree
   (via binding reparto/ruolo/ad-hoc)    NO: continua ↓
4. Default                              → BLOCCATO
```

`script.fn_resolve_livello_area` legge questa tabella tramite
`script.fn_get_profili_accesso_applicabili` (cutover completato 2026-04-19,
modello legacy droppato 2026-05-04).

---

### Seed portali

Il seed iniziale popola 6 righe con livello `LETTURA`:

| profilo | area | livello |
|---------|------|---------|
| `CLIENTE_PORTALE_STANDARD` | `vendite` | LETTURA |
| `CLIENTE_PORTALE_STANDARD` | `pagamenti` | LETTURA |
| `FORNITORE_PORTALE_STANDARD` | `acquisti` | LETTURA |
| `FORNITORE_PORTALE_STANDARD` | `pagamenti` | LETTURA |
| `SHOP_CUSTOMER_STANDARD` | `vendite` | LETTURA |
| `SHOP_CUSTOMER_STANDARD` | `pagamenti` | LETTURA |

---

### ⚠️ Impatto delle modifiche

Modificare il livello di un'area su un profilo ha **impatto immediato** su
tutti gli utenti che ereditano quel profilo (tramite binding). Per i profili
di tipo `REPARTO` o `PORTALE`, l'impatto può coinvolgere molti utenti; la UI
di gestione deve mostrare la lista dei bindings prima di confermare.

---

{% include-markdown "signature-core.md" %}
