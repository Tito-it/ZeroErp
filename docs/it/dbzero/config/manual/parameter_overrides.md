## Documentazione Concettuale — Tabella `config.parameter_overrides`

> **Ultimo aggiornamento**: 9 novembre 2026

> **Vedi anche**
>
> [config.parameters](/dbzero/config/tabelle/parameters)
> [script.fn_get_parameter_full](/dbzero/script/funzioni/fn_get_parameter_full)
> [script.fn_list_parameters_for_user](/dbzero/script/funzioni/fn_list_parameters_for_user)

---

### Scopo

La tabella `config.parameter_overrides` contiene gli override dei parametri di sistema
definiti in `config.parameters`. Ogni riga rappresenta un override valido per una
specifica **dimensione di scope**: utente Django, gruppo Django, emittente fiscale,
categoria cliente o funzione chiamante.

Un override è **configurazione che resta**: non esiste un livello di sessione. Una
sessione di login scade, e nessuna porta creerebbe o pulirebbe un override legato a lei.

Lo scope è espresso con colonne dedicate (non con scope_type/scope_id generici):
ogni colonna è nullable e la combinazione valorizzata determina a quale livello
della cascata di risoluzione appartiene l'override.

---

### Cascata di risoluzione

La funzione `script.fn_get_parameter_full` risolve il valore di un parametro
applicando gli override in ordine di priorità decrescente:

```
1. user          (django_user_id)          — massima priorità
2. categoria_cliente (categoria_cliente_id)
3. group         (django_group_id)
4. emittente     (emittente_fiscale_id)
5. function      (function_name)
6. default       (config.parameters.default_value)
```

Un override scatta solo quando il parametro di scope passato alla funzione
corrisponde alla colonna valorizzata nella riga. Se il parametro è `NULL`,
il livello viene saltato (NULL-equality è sempre FALSE in SQL).

---

### Dimensioni di scope

| Colonna | Tipo | Livello cascata | Note |
|---|---|---|---|
| `django_user_id` | `integer NULL` | 1 — user | FK a `django.auth_user(id)` via surrogate. Override personale dell'operatore. |
| `categoria_cliente_id` | `smallint NULL` | 2 — categoria | FK a `anagrafiche.categorie_clienti(id)`. Regola commerciale per categoria (es. PREMIUM max sconto 5%). Vince sul gruppo. |
| `django_group_id` | `integer NULL` | 3 — group | FK a `django.auth_group(id)` via surrogate. Override per ruolo/seniority operatore. |
| `emittente_fiscale_id` | `bigint NULL` | 4 — emittente | FK a `anagrafiche.emittenti_fiscali(id)`. Override per persona giuridica emittente. |
| `function_name` | `text NULL` | 5 — function | Override per specifica funzione applicativa chiamante. |

**Regola:** ogni riga ha esattamente UNA dimensione valorizzata e le restanti a
NULL. Dal 2026-10-07 è un vincolo, `chk_parameter_overrides_un_ambito`
(`20261007-72`): una riga con due ambiti (per esempio utente + categoria) o
senza nessun ambito è rifiutata (`23514`). Il perché: fra due ambiti la cascata
sceglie **un** valore, non li combina — se Mario ha il 15% e la categoria PREMIUM
il 5%, per Mario su un cliente PREMIUM vale il 15%; un override «Mario + PREMIUM»
non ha un significato commerciale. La UNIQUE `uq_overrides_full_scope_v6` garantisce che non
esistano due override con la stessa combinazione completa di scope, **NULL
compresi**: due override personali puri per lo stesso parametro e lo stesso utente
sono la stessa riga, e la seconda è rifiutata (`23505`).

Fino al vincolo una riga mista era ammessa, e la cascata la prendeva al primo
livello che combaciava ignorando le altre dimensioni: «Mario + PREMIUM» valeva
per Mario sempre, anche fuori da PREMIUM (`brief-db-codici-sfilati-e-lista-parametri` §7.6).

---

### Vincoli principali

| Tipo | Nome | Colonne | Note |
|---|---|---|---|
| PRIMARY KEY | `parameter_overrides_pkey` | `id` | |
| UNIQUE | `uq_overrides_full_scope_v6` | `parameter_id, emittente_fiscale_id, django_user_id, django_group_id, categoria_cliente_id, function_name` | `NULLS NOT DISTINCT`: un ambito, un override, anche quando l'ambito ha dei NULL (cioè sempre). `attivo` è fuori: una riga spenta occupa il suo ambito. |
| CHECK | `chk_parameter_overrides_un_ambito` | le cinque dimensioni | `num_nonnulls(...) = 1`: esattamente un ambito per override |
| FOREIGN KEY | `fk_overrides_parameter` | `parameter_id` | `ON UPDATE CASCADE ON DELETE RESTRICT` |
| FOREIGN KEY | `fk_overrides_emittente_fiscale` | `emittente_fiscale_id` | `ON UPDATE CASCADE ON DELETE RESTRICT` |
| FOREIGN KEY | `fk_overrides_categoria_cliente` | `categoria_cliente_id` | `ON UPDATE CASCADE ON DELETE RESTRICT` |
| FOREIGN KEY | `fk_overrides_django_user` | `django_user_id` | surrogate tramite trigger |
| FOREIGN KEY | `fk_overrides_django_group` | `django_group_id` | surrogate tramite trigger |

> **Nota**: la UNIQUE è alla versione v6 (`20261111-17`): come la v5, senza
> `session_key`. La v5 (`20261007-70`) aveva le stesse colonne della v4,
> ma `NULLS NOT DISTINCT`. La v4 (2026-05-15, aggiunta `categoria_cliente_id`) era
> `NULLS DISTINCT`, il default di PostgreSQL: non scattava su nessuna riga con una
> dimensione NULL, cioè su nessun override reale, e due override puri per lo stesso
> ambito convivevano — la cascata ne sceglieva uno a caso (`LIMIT 1` senza ordine).

---

### Trigger

| Nome | Timing | Evento | Azione |
|---|---|---|---|
| `trg_parameter_overrides_a05_guard_ammette_override_ins_upd` | BEFORE | INSERT, UPDATE OF `parameter_id` | Rifiuta un override, anche spento, su un parametro che vale per tutti (`config.parameters.ammette_override = false`): `E_PARAMETER_OVERRIDE_NON_AMMESSO`. In `a05`, prima del dispatcher: se il parametro non si personalizza, la frase giusta è questa ([la funzione](/dbzero/config/funzioni/trgfn_parameter_overrides_guard_ammette_override)) |
| `trg_parameter_overrides_a10_fk_surrogate_dispatch_ins_upd` | BEFORE | INSERT, UPDATE OF `parameter_id, overridden_value` | Valida `overridden_value` contro le FK-surrogate registrate in `config.parameter_fk_surrogate` |
| `trg_parameter_overrides_a10_emittenti_fiscali_require_at_...` | AFTER | INSERT, UPDATE | Blocca override su emittente disattivato |
| `trg_parameter_overrides_a10_cat_clienti_req_attivo_ins_upd` | AFTER | INSERT, UPDATE OF `categoria_cliente_id` | Blocca override su categoria cliente disattivata |
| `trg_parameter_overrides_audit_data_user_upd` | BEFORE | INSERT, UPDATE | Aggiorna campi audit `data_update`, `user_update` |
| `trg_parameter_overrides_gen_tx_id_ins_upd` | BEFORE | INSERT, UPDATE | Gestisce `tx_id` di sessione |
| `trg_parameter_overrides_z90_storico_upd_dlt` | BEFORE | UPDATE, DELETE | Storicizza la riga in `storico.parameter_overrides` |

---

### Indici per la cascata

Ogni livello della cascata usa un indice composto `(parameter_id, <dimensione>)`
per la subquery COALESCE in `fn_get_parameter_full`:

| Indice | Colonne | Livello |
|---|---|---|
| `ix_overrides_param_user` | `(parameter_id, django_user_id)` | 1 — user |
| `ix_overrides_param_categoria_cliente` | `(parameter_id, categoria_cliente_id)` | 2 — categoria |
| `ix_overrides_param_group` | `(parameter_id, django_group_id)` | 3 — group |
| `ix_parameter_overrides_emittente` | `(parameter_id, emittente_fiscale_id)` | 4 — emittente |

Il livello function non ha indice dedicato (uso raro; la tabella
config è tipicamente piccola).

---

### Esempi

#### Override a livello categoria cliente

Limite sconto per clienti PREMIUM: la regola commerciale vince sul gruppo
dell'operatore (Mario SENIOR ottiene comunque 5% se serve un cliente PREMIUM).

```sql
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, categoria_cliente_id)
SELECT p.id, '5', cc.id
  FROM config.parameters p
  JOIN anagrafiche.categorie_clienti cc ON cc.codice = 'PREMIUM'
 WHERE p.code = 'VENDITE_MAX_SCONTO_PCT';
```

#### Override a livello utente (eccezione individuale)

Maria.DirettoreVendite può applicare sconti fino al 20% su qualsiasi cliente:

```sql
INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
SELECT p.id, '20', au.id
  FROM config.parameters p
  JOIN django.auth_user au ON au.username = 'maria.direttorev'
 WHERE p.code = 'VENDITE_MAX_SCONTO_PCT';
```

Grazie alla cascata, il livello user (priorità 1) sovrascrive il livello
categoria (priorità 2): Maria ottiene sempre 20%, anche su clienti PREMIUM.

---

### Storia

* 2026-11-09 — esce il livello sessione degli override, da tutte e due le catene: via la
  colonna `session_key`. La UNIQUE diventa `uq_overrides_full_scope_v6` (`NULLS NOT DISTINCT`,
  `parameter_id` più le cinque dimensioni); `chk_parameter_overrides_un_ambito` tiene il nome e
  conta cinque dimensioni. Commento della tabella riscritto. ChangeSet
  `20261111-17-alter-parameter-overrides-drop-session-key`, `brief-db-revisione-dbops`, giro 13.
  Cancellato anche il CSV orfano `80_data/sql/config/parameter_overrides.csv`: aveva solo
  l'intestazione, con colonne che non esistono più (`tenant_id`, `session_key`), e nessun
  changeSet lo caricava.
