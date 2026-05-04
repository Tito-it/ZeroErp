## 📘 Documentazione Concettuale – Tabella `config.profili_accesso_azioni`

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
> [config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni)

---
### 🎯 Scopo Principale
(latest revision 04-05-2026 — modello legacy `profili_reparto_azioni` dismesso)

La tabella **`config.profili_accesso_azioni`** contiene il dettaglio delle
**azioni di processo** abilitate (o disabilitate) da un profilo di accesso.

Il padre e' `profili_accesso`, generalizzato a tre tipi di profilo
(REPARTO / PORTALE / AD_HOC), legato all'utente tramite
`profili_accesso_bindings`.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `profilo_accesso_id` | FK al profilo header ([`profili_accesso`](/dbzero/config/tabelle/profili_accesso)). |
| `azione_id` | FK all'azione di processo ([`azioni_processo`](/dbzero/config/tabelle/azioni_processo)), es. "can_emit_invoice". |
| `abilitata` | `true` se il profilo consente l'azione, `false` altrimenti. Default `false` (chiuso di default). |

Vincolo `UNIQUE (profilo_accesso_id, azione_id)` garantisce una sola
riga per coppia profilo-azione.

---

### Default sicuro

Come per [`profili_accesso_aree`](/dbzero/config/tabelle/profili_accesso_aree),
il default di `abilitata` è `false`: una riga inserita senza flag esplicito
**non concede** l'azione. Pattern deny-by-default.

---

### Catena di risoluzione (azione di processo)

Interviene al **punto 3** della catena di risoluzione di
[`fn_check_azione_processo`](/dbzero/script/funzioni/fn_check_azione_processo):

```
1. Ruolo sistema                     → ADMIN → true; DISABILITATO → false
2. Override utente azione            → SI: applica; NO: continua ↓
3. Profilo applicato all'identità    → SI: leggi abilitata dalla riga; NO: continua ↓
4. Default                            → false (negata)
```

`fn_check_azione_processo` legge questa tabella tramite
`script.fn_get_profili_accesso_applicabili` (cutover completato 2026-04-19,
modello legacy droppato 2026-05-04).

---

### Azioni "pericolose"

Le righe in [`azioni_processo`](/dbzero/config/tabelle/azioni_processo) hanno
un flag `pericolosa`: abilitare azioni pericolose via profilo deve essere
fatto con cautela (es. mai su profili `SHOP_CUSTOMER_STANDARD`). La UI di
gestione dovrebbe evidenziare le azioni pericolose e richiedere conferma.

---

{% include-markdown "signature-core.md" %}
