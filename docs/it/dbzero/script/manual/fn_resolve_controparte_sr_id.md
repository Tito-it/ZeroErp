## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_controparte_sr_id(...)`

> 👀 **Vedi anche**
>
> [fn_get_identita_sr_perimetro](fn_get_identita_sr_perimetro.md) — il perimetro di chi guarda
> [fn_resolve_emittente_fiscale_id](fn_resolve_emittente_fiscale_id.md) — la sorella, per l'emittente
> [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
> Brief: `brief-db-perimetro-una-volta-famiglie-residue` §6 (giro 2)

---

### 🎯 Scopo Principale

(nata il 2026-10-21, `20261021-30`)

**Di quale controparte è questa riga?** Restituisce il soggetto (cliente o
fornitore, `soggetto_ruolo_id`) a cui appartiene una riga, partendo da una chiave
secondo un **modo**. `NULL` se il riferimento non porta a nessuno.

È la domanda di **fatto** delle policy di controparte. Il permesso lo decide la
policy, confrontando questo soggetto con il perimetro di chi guarda.

| Modo | Chiave | Il soggetto |
|------|--------|-------------|
| `billing_account` | id del billing account | il cliente del billing account |
| `fattura` | id della fattura | il cliente del billing account della fattura (regola `BA_OWNERSHIP`) |
| `fattura_sdi` | id dell'invio SDI | quello della sua fattura |
| `ordine` | id dell'ordine | il cliente dell'ordine (dal 21-10-2026, `20261021-33`) |
| `ordine_riga` | id della riga d'ordine | il cliente del suo ordine |

| `billing_account_shop` | id del billing account | il cliente, solo se il BA è nato dallo shop; altrimenti `NULL` (dal 21-10-2026, `20261021-37`) |
| `ordine_shop` | id dell'ordine | il cliente, solo se l'ordine è nato dallo shop |
| `ordine_riga_shop` | id della riga d'ordine | quello del suo ordine, solo se nato dallo shop |

⭐ I modi `_shop` portano dentro la seconda condizione della veste
`SHOP_CUSTOMER`: un ordine o un billing account del proprio soggetto, ma nato da
ADMIN, non sono suoi da shop.

⛔ **Un modo sconosciuto solleva** `E_PARAMETRO_INVALIDO`, non risponde `NULL`:
un errore di battitura in una policy la chiuderebbe in silenzio.

⭐ **Perché `SECURITY DEFINER`.** Le catene passano da tabelle sotto RLS (fatture,
invii SDI, billing account). Lette dalla policy di un figlio, ogni lettura
rieseguirebbe per ogni riga la policy del padre, con dentro il perimetro di chi
guarda. Il proprietario delle tabelle, che è anche il proprietario della
funzione, le legge senza filtro. Funziona perché la RLS è **abilitata ma non
forzata**; con un `FORCE` andrebbe rivista, come la sorella.

---

### Parametri e risultato

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_modo` | `text` | Il modo: da quale tabella parte la chiave. |
| `p_valore` | `bigint` | La chiave (polimorfa: l'id della tabella del modo). |

Risultato: `anagrafiche.soggetti_ruoli.id%TYPE`, oppure `NULL`.

Chi la usa: le policy del cliente portale (`20261021-32`) e degli ordini
(`20261021-35`), quelle dello shop (`20261021-39`), gli smistatori delle note di
cliente e shop (`20261021-38`) e `fn_scope_ba_ownership` (`20261021-31`). Presidi
funzionali: `script/test-fn-resolve-controparte-sr-id-v1` (ogni modo, costruito, nei
due versi) e `rls/test-rls-cliente-perimetro-ordini-v1`.

⭐ Dal `20261021-40` prende il posto delle funzioni di scope di cliente e shop che
leggevano la riga da sole, sotto la RLS del padre e per ogni riga:
`fn_scope_cliente_ownership` e `_via_ordine`, `fn_scope_ba_ownership_via_fattura` e
`_via_fattura_sdi`, `fn_scope_shop_via_ordine`, `_via_ordine_riga` e `_via_ba`.

---

{% include-markdown "signature-core.md" %}
