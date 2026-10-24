## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_guard_struttura_se_usato`

> 👀 **Vedi anche**
>
> [catalogo.articoli](/dbzero/catalogo/manual/articoli) — la regola, con le colonne bloccate e quelle libere
> [catalogo.fn_articolo_usato](/dbzero/catalogo/manual/fn_articolo_usato) — il predicato «usato»
> [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/manual/fn_articolo_correggi_struttura) — la porta amministratore

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)

Un articolo **usato** non cambia i flag che decidono come si vende e come sta a magazzino.

---

### Logica applicata

* Trigger `trg_articoli_a10_guard_struttura_se_usato_upd`, **BEFORE UPDATE OF** le otto colonne:
  `is_composito`, `is_solo_componente`, `natura_vendita_id`, `causale_onere_id`,
  `listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`, `requires_serial`.
  L'elenco leggibile è `catalogo.fn_articolo_colonne_struttura()`; qui (trigger e `CASE`) è
  scritto perché un trigger non legge le sue colonne da una funzione, e il pgTAP
  `catalogo/test-articolo-colonne-struttura-v1` controlla che le due cose coincidano.
* Se nessuna cambia davvero (`IS DISTINCT FROM`), esce: un salvataggio del form che riscrive gli
  stessi valori passa.
* Se l'articolo è usato (`catalogo.fn_articolo_usato`) → `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`.
  Campo: la prima colonna cambiata, nell'ordine dell'elenco. Valori: il codice dell'articolo e il
  nome leggibile del campo.
* Il messaggio **non dice dove** l'articolo è usato: può essere un documento di un'altra azienda,
  che chi modifica non vede.

### La porta amministratore

Passa solo il verbo `catalogo.fn_articolo_correggi_struttura` (SUPER_ADMIN). Il verbo apre la GUC
transazionale `zeroerp.articolo_correggi_struttura` = id dell'articolo, e il guard la onora **solo
insieme al proprietario della tabella** (`script.fn_is_proprietario_tabella`): il verbo è SECURITY
DEFINER, e una GUC accesa a mano da una sessione applicativa non apre niente. È lo stesso idioma
di `zeroerp.ddt_riga_correggi_qta`.

Dalla porta passa solo questa regola: i guard della distinta e dell'onere parlano lo stesso.

### Che cosa ha sostituito

Il guard «solo componente in bozza» (`20261013-44/-45`) e la sua regola del form (`-46`), ritirati
da `20261013-49` e `-51`. Proteggevano un caso solo (le righe in bozza, per `is_solo_componente`)
e leggevano i documenti con la RLS di chi modifica: le bozze delle altre aziende non le vedevano.

---
{% include-markdown "signature-core.md" %}
