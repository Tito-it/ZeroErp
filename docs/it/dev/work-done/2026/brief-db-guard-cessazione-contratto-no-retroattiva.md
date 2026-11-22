# Brief DB — Guard cessazione contratto: vietare data retroattiva

> **Data**: 2026-05-14
>
> **Branch**: `dev/db-tid`
>
> **Tipo**: bug logico modello — priorita' alta (consente cessazioni con riscrittura storica)
>
> **Funzione da modificare**: `vendite.trgfn_contratti_guard_transizione_stato`
> (file 20260426-05).

---

## Sintomo

Workflow utente reale (testato 2026-05-14):

1. Contratto ATTIVO esistente con `valido_al` futuro.
2. L'admin apre il form cessazione, imposta `valido_al = data retroattiva arbitraria`
   (es. un mese fa), conferma transizione `ATTIVO -> CESSATO`.
3. **Il sistema accetta**: il guard DB ammette qualsiasi `valido_al < CURRENT_DATE`,
   senza limite inferiore.

## Causa

In `trgfn_contratti_guard_transizione_stato` (file `20260426-05-...mctit.yaml`,
riga 103-104) la regola per `ATTIVO -> CESSATO` e':

```sql
v_ammessa := (NEW.valido_al IS NOT NULL
              AND NEW.valido_al < CURRENT_DATE);
```

Cioe' ammette **solo** date passate, senza limite inferiore: una data 5 anni fa
e una data ieri sono equivalenti per il guard.

## Conseguenza

Cessazione retroattiva consente di "riscrivere la storia": un contratto attivo
per N mesi puo' essere cessato come se fosse finito mesi prima. Tutti i
documenti emessi nel periodo `(nuovo valido_al, oggi]` diventano riferiti a un
contratto che ufficialmente non esisteva — incongruenza di audit + rischio di
pricing applicato su contratto "cessato a posteriori".

## Correzione richiesta

Cambiare la regola della transizione `ATTIVO -> CESSATO` a:

```sql
v_max_giorni_retroattivi := COALESCE(
    (script.fn_get_parameter('CONTRATTO_CESSAZIONE_RETROAZIONE_GG_MAX'))::integer,
    0
);
v_ammessa := (NEW.valido_al IS NOT NULL
              AND NEW.valido_al >= CURRENT_DATE - v_max_giorni_retroattivi);
```

**Parametrizzazione**: il numero massimo di giorni retroattivi ammessi e' letto
dal parametro `config.parameters.codice = 'CONTRATTO_CESSAZIONE_RETROAZIONE_GG_MAX'`
(seed `default_value = '0'`, scope `SISTEMA`, tipo `integer`).

**Default 0**: cessazione ammessa solo con `valido_al >= CURRENT_DATE` (oggi o
futuro). Coerente con la decisione di dominio 2026-05-14: niente riscrittura
storica per default. L'azienda puo' alzare il parametro in futuro (es. a 1 per
tollerare la chiusura "di ieri sera" il giorno dopo) senza modifica DDL,
seguendo il pattern `feedback_no_hardcoded_ids` + `feedback_pattern_config`.

### Implicazioni semantiche del cambio

Il design pre-fix interpretava `valido_al` come "ultimo giorno effettivamente
valido nel passato" + job notturno pgAgent che porta in CESSATO il giorno dopo.
Il design post-fix mantiene `valido_al` come "ultimo giorno valido", ma vincola
la cessazione manuale a essere immediata (`= oggi`) o programmata (`> oggi`).

**Job notturno pgAgent**: nessun cambiamento richiesto. Continua a portare in
CESSATO i contratti con `valido_al < CURRENT_DATE` (cessazione automatica il
giorno dopo). Il cambio del guard tocca solo la transizione manuale lato UI.

**Conseguenza pratica**:

- Cessazione "oggi"   → `valido_al = CURRENT_DATE` ammessa. Il contratto resta
  ATTIVO fino al COMMIT del CESSATO (transizione manuale immediata), poi
  stato CESSATO con `valido_al = oggi` (ultimo giorno valido).
- Cessazione programmata → `valido_al = data futura`, transizione manuale
  immediata a CESSATO. Il contratto e' in stato CESSATO ma con `valido_al`
  futuro: rimane "valido per pricing" fino a `valido_al`? **DA CHIARIRE COL
  TEAM DB**: la presenza dello stato CESSATO blocca il pricing? Se si',
  occorre allineare anche `fn_resolve_prezzo_listino_v2` che oggi guarda
  `s.codice_interno = 'ATTIVO'` (vedi file 20260513-35, riga ~136).
  Se no, niente da fare.

Suggerimento: per evitare ambiguita' sullo stato post-cessazione programmata,
**lasciare cessazione manuale solo a `valido_al = CURRENT_DATE`** (oggi)
e usare il job notturno per le cessazioni programmate (`valido_al > today` ->
attendere il giorno dopo `valido_al` per la transizione automatica).
Da decidere col team DB.

### Errore sollevato

Codice: `E_CONTRATTO_VALIDO_AL_RETROATTIVO` (nuovo, registrare in
`config.messaggi_errore` + `apps/core/services/error_policies.py`).

Messaggio: "Cessazione contratto non ammessa con data retroattiva. La data
di fine validita' deve essere oggi o futura."

HTTP: 409 (conflict).

## Test attesi (pgTAP)

1. Transizione ATTIVO -> CESSATO con `valido_al = CURRENT_DATE` → OK.
2. Transizione ATTIVO -> CESSATO con `valido_al = CURRENT_DATE + 30` (futura) → OK.
3. Transizione ATTIVO -> CESSATO con `valido_al = CURRENT_DATE - 1` (ieri) →
   `E_CONTRATTO_VALIDO_AL_RETROATTIVO`.
4. Transizione ATTIVO -> CESSATO con `valido_al IS NULL` → errore (gia' coperto
   dalla regola attuale `NOT NULL`).
5. Job notturno pgAgent: continua a portare in CESSATO i contratti con
   `valido_al < CURRENT_DATE` automaticamente (transizione non bypassa il
   guard? **DA VERIFICARE**: se il job esegue UPDATE come transizione, scatta
   il guard e fallisce. Soluzione: il job deve usare `BYPASS_GUARD_VALIDATION`
   GUC oppure il guard deve avere clausola di esenzione `WHEN session_user =
   'pgagent'` o simili. Da decidere col team DB.).

## Migration file

Proposta nome: `20260514-NN-update-trgfn-contratti-guard-cessazione-no-retroattiva-mctit.yaml`
con `runOnChange: true` sul body della trigger function.

In aggiunta:

- Nuovo file seed `config.parameters` con `CONTRATTO_CESSAZIONE_RETROAZIONE_GG_MAX`
  (scope SISTEMA, default `'0'`, tipo integer).
- Nuovo file seed `config.messaggi_errore` con `E_CONTRATTO_VALIDO_AL_RETROATTIVO`
  (template IT/EN).

## Riferimenti

- File attuale: `db/changelog/migrations_v2/20_code/vendite/20260426-05-create-trgfn-contratti-guard-transizione-stato-mctit.yaml`
- Update precedente: `20260512-30-update-trgfn-contratti-guard-transizione-remove-null-mctit.yaml`
- Resolver pricing (per coerenza stato/pricing): `20260513-35-update-fn-resolve-prezzo-listino-v2-bundle-prioritario-mctit.yaml`
