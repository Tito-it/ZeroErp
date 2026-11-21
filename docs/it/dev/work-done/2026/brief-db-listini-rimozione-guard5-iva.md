# Brief DB — Rimozione Guard 5 (IVA padre=figlio) dal trigger listino componenti

> Destinatario: team DB (`dev/db-tid`).
> Data: 2026-06-03. Autore: backend (mctit).
> Tipo: modifica trigger/funzione DB (runOnChange). **Non** eseguita dal backend.
>
> **STATO: APPLICATO** (commit DB `e1192fadf`). Migrazioni:
> `20260603-03` (rimozione Guard 5 listino) + `20260603-01`/`20260603-02`
> (hardening sorgente, vedi nota sotto) + pgTAP `test-guard-iva-reactivation-v1.sql`.

## Decisione

Adottiamo **enforcement a punto unico** dell'invariante IVA uniforme dei
compositi (padre composito e figli BoM stessa aliquota). L'invariante è
**già garantito alla sorgente** dai due guard su catalogo:

- `catalogo.trgfn_articoli_componenti_guard_iva` (BEFORE INSERT su
  `articoli_componenti`): figlio.iva_id deve = padre.iva_id.
- `catalogo.trgfn_articoli_guard_iva_bom_attiva` (BEFORE UPDATE OF
  `articoli.iva_id`): blocca ogni modifica che renda incoerente una BoM
  attiva (sia lato padre sia lato figlio).

Verifica fatta sul sorgente reale (migrazioni `20260513-33` / `20260513-34`).
Con entrambi i guard attivi una BoM attiva non può avere padre e figlio
con IVA diversa, **ma due percorsi potevano aggirarlo**:

1. stato padre+figlio entrambi NULL — passa l'INSERT (`NULL = NULL`) ma è
   bloccato in popolamento (`NULL IS DISTINCT FROM <valore>` = TRUE);
2. **spegni → cambia IVA → riaccendi** — deattivando il legame il guard su
   `articoli.iva_id` lo ignora (`attivo = TRUE` only), quindi si poteva
   cambiare l'IVA del figlio e riattivare con IVA incoerente. **Questo
   secondo buco è stato chiuso dal team DB** (migrazioni `20260603-01`/`02`:
   `trgfn_articoli_componenti_guard_iva` ora su `BEFORE INSERT OR UPDATE OF
   attivo`, re-check IVA sulla riaccensione). Con questo, la sorgente è
   ora davvero airtight.

Quindi il ri-controllo IVA fatto a valle dal listino è
ridondante e crea un'**asimmetria** confusiva: il listino rifiuta dati
incoerenti mentre i guard documento (`trgfn_componenti_guard_coerenza_bom`
su contratti/preventivi/ordini/ddt) **non** controllano l'IVA.

Scelta operativa (B — snella): **uniformare verso il basso** rimuovendo il
controllo IVA dal listino, lasciando la sorgente come unico punto di
enforcement. I dati legacy incoerenti (2 padri di test) sono già stati
bonificati manualmente.

## Modifica richiesta

Rimuovere **Guard 5** ("IVA figlio = IVA padre") da
`script.trgfn_listini_righe_comp_guard_coerenza_bom()`, mantenendo
invariati i Guard 1, 2, 3, 4 e 7.

### Come (regola Liquibase v2)

Il changelog `20260515-01-update-trgfn-listini-righe-comp-guard-coerenza-bom-coalesce-mctit.yaml`
è già mergiato: **non modificarlo**. Creare un **nuovo** file con
numerazione successiva e `runOnChange: true`, es.:

```
db/changelog/migrations_v2/20_code/script/20260603-NN-update-trgfn-listini-righe-comp-guard-coerenza-bom-remove-guard5-mctit.yaml
```

`CREATE OR REPLACE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()`
identica all'attuale **tranne**:

1. **Eliminare il blocco Guard 5** per intero:

   ```sql
   -- Guard 5: IVA figlio = IVA padre
   IF v_padre_iva_id IS DISTINCT FROM v_figlio_iva_id THEN
       PERFORM script.fn_log_and_raise_error(
           'script', TG_NAME, 'E_LISTINO_COMPONENTE_COERENZA_BOM',
           jsonb_build_object(
               'causa', 'IVA padre != IVA figlio',
               'iva_padre', v_padre_iva_id,
               'iva_figlio', v_figlio_iva_id
           ),
           NULL::uuid,
           format('IVA padre=%s != figlio=%s',
                  v_padre_iva_id, v_figlio_iva_id)
       );
   END IF;
   ```

2. **Rimuovere le variabili ora inutilizzate** dal blocco `DECLARE`:
   `v_padre_iva_id` e `v_figlio_iva_id`.

3. **Rimuovere dalla SELECT** le colonne `a_padre.iva_id` e
   `a_figlio.iva_id` (e i relativi target `INTO`).

4. **Opzionale (cleanup):** dopo il punto 3 il `JOIN catalogo.articoli
   a_figlio` non è più referenziato (Guard 3 usa `v_ac_componente_id` da
   `ac`, non `a_figlio`). Si può rimuovere quel JOIN. Il `JOIN
   catalogo.articoli a_padre` **resta** (serve `a_padre.is_composito` per
   Guard 4). `componente_id` è comunque FK verso `articoli`, quindi togliere
   il JOIN non altera la semantica di Guard 1.

5. **Aggiornare la docstring** della funzione: `guards 1-5 + 7` → `guards 1-4 + 7`.
   Aggiornare anche il `COMMENT ON FUNCTION` se presente.

### Cosa NON cambiare

- `config.messaggi_errore`: il codice `E_LISTINO_COMPONENTE_COERENZA_BOM`
  resta in uso (Guard 1/2/3/4/7). Nessuna riga da rimuovere.
- I due guard sorgente su catalogo (`trgfn_articoli_componenti_guard_iva`,
  `trgfn_articoli_guard_iva_bom_attiva`): **invariati**, restano il punto
  unico di enforcement.
- I guard documento (`trgfn_componenti_guard_coerenza_bom`): invariati
  (NON aggiungere il check IVA — decisione B).

## Impatti da verificare (team DB)

- **pgTAP**: cercare in `db/pgtap/` i test che asseriscono il caso IVA
  discordante su `listini_righe_componenti` (grep `E_LISTINO_COMPONENTE_COERENZA_BOM`
  + "IVA"/"iva_padre"). Rimuovere/aggiornare quegli assert; mantenere i
  test sugli altri guard (1/2/3/4/7).
- Verificare che nessun altro oggetto (view/funzione) dipenda dal blocco
  rimosso.

## Impatti backend / frontend

- **Nessuno funzionale.** `upsert_bundle_componenti` continua a passare
  `iva_id` (IVA del figlio dal catalogo) nella colonna
  `listini_righe_componenti.iva_id`: con la sorgente coerente quel valore
  coincide col padre. La colonna resta, nessuna migrazione dati.
- Il flusso FE bundle (ComponentiDialog) non cambia.

## Esito atteso

Dopo l'applicazione: salvare i prezzi bundle di un composito con BoM
coerente (caso normale) continua a funzionare; l'unico comportamento che
sparisce è il rifiuto `E_LISTINO_COMPONENTE_COERENZA_BOM` per causa
"IVA padre != IVA figlio", che ora non può comunque verificarsi perché la
sorgente lo impedisce.
