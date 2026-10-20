{% include-markdown "it/dbzero/pratiche/manual/fn_copia_definizione.md" %}
# ⚙️ Funzione `fn_copia_definizione`

```sql
CREATE FUNCTION fn_copia_definizione(p_sorgente_id integer, p_emittente_dest bigint, p_provenance boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_copia_definizione(p_sorgente_id integer, p_emittente_dest bigint, p_provenance boolean)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: copiare un'edizione di workflow (header + template + figli)
--        in una nuova edizione BOZZA, rimappando i template per
--        codice. Motore condiviso di fork e nuova-versione.
DECLARE
  v_tipo_id      pratiche.workflow_definizioni.tipo_prestazione_id%TYPE;
  v_src_versione pratiche.workflow_definizioni.versione%TYPE;
  v_src_descr    pratiche.workflow_definizioni.descrizione%TYPE;
  v_src_meta     pratiche.workflow_definizioni.meta%TYPE;
  v_versione     pratiche.workflow_definizioni.versione%TYPE;
  v_new_id       pratiche.workflow_definizioni.id%TYPE;
BEGIN
  IF p_sorgente_id IS NULL OR p_sorgente_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_copia_definizione', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','p_sorgente_id','valore',p_sorgente_id),
      NULL::uuid, 'p_sorgente_id obbligatorio e > 0');
  END IF;

  SELECT wd.tipo_prestazione_id, wd.versione, wd.descrizione, wd.meta
    INTO v_tipo_id, v_src_versione, v_src_descr, v_src_meta
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_sorgente_id;
  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_copia_definizione', 'E_VALORE_MANCANTE',
      jsonb_build_object('definizione_sorgente_id', p_sorgente_id),
      NULL::uuid, concat('workflow_definizioni id ', p_sorgente_id));
  END IF;

  -- Versione progressiva nello scope (tipo, emittente destinazione).
  SELECT COALESCE(MAX(wd.versione), 0) + 1
    INTO v_versione
    FROM pratiche.workflow_definizioni wd
   WHERE wd.tipo_prestazione_id = v_tipo_id
     AND wd.emittente_fiscale_id IS NOT DISTINCT FROM p_emittente_dest;

  -- Header nuova edizione (BOZZA).
  INSERT INTO pratiche.workflow_definizioni
         (tipo_prestazione_id, emittente_fiscale_id, versione, stato,
          preset_origine_id, versione_origine, descrizione, meta)
  VALUES (v_tipo_id, p_emittente_dest, v_versione, 'BOZZA',
          CASE WHEN p_provenance THEN p_sorgente_id ELSE NULL END,
          CASE WHEN p_provenance THEN v_src_versione ELSE NULL END,
          v_src_descr, v_src_meta)
  RETURNING id INTO v_new_id;

  -- 1) Template (codice preservato; definizione_id = nuova; id nuovo).
  --    GUIDA D4/G1: attende_sorgente_tipo_id propagato (config di step).
  INSERT INTO pratiche.template_flussi
         (tipo_prestazione_id, handler_id, codice, descrizione, sequenza,
          obbligatorio, direzione, attivo, meta, handler_params, ripetibilita,
          chiude_pratica, azione_ui_id, modalita_esito, esito_default,
          obsoleto_dal, attende_sorgente_tipo_id, definizione_id)
  SELECT tf.tipo_prestazione_id, tf.handler_id, tf.codice, tf.descrizione,
         tf.sequenza, tf.obbligatorio, tf.direzione, tf.attivo, tf.meta,
         tf.handler_params, tf.ripetibilita, tf.chiude_pratica, tf.azione_ui_id,
         tf.modalita_esito, tf.esito_default, tf.obsoleto_dal,
         tf.attende_sorgente_tipo_id, v_new_id
    FROM pratiche.template_flussi tf
   WHERE tf.definizione_id = p_sorgente_id;

  -- 2) Canali (remap singolo per codice).
  INSERT INTO pratiche.template_flussi_canali
         (template_flusso_id, canale_id, attivo)
  SELECT nt.id, c.canale_id, c.attivo
    FROM pratiche.template_flussi_canali c
    JOIN pratiche.template_flussi ot
         ON ot.id = c.template_flusso_id AND ot.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nt
         ON nt.definizione_id = v_new_id AND nt.codice = ot.codice;

  -- 3) Handler-eventi (remap singolo; handler_id globale invariato).
  INSERT INTO pratiche.template_flussi_handler_eventi
         (template_flusso_id, evento, esito_richiesto, handler_id,
          handler_params, sequenza, attivo)
  SELECT nt.id, e.evento, e.esito_richiesto, e.handler_id,
         e.handler_params, e.sequenza, e.attivo
    FROM pratiche.template_flussi_handler_eventi e
    JOIN pratiche.template_flussi ot
         ON ot.id = e.template_flusso_id AND ot.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nt
         ON nt.definizione_id = v_new_id AND nt.codice = ot.codice;

  -- 4) Competenze (remap singolo).
  INSERT INTO pratiche.competenze_flussi
         (template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo, meta)
  SELECT nt.id, cf.unita_organizzativa_id, cf.risorsa_umana_id, cf.attivo, cf.meta
    FROM pratiche.competenze_flussi cf
    JOIN pratiche.template_flussi ot
         ON ot.id = cf.template_flusso_id AND ot.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nt
         ON nt.definizione_id = v_new_id AND nt.codice = ot.codice;

  -- 5) Prerequisiti (remap DOPPIO: entrambi i lati sono template della
  --    stessa definizione).
  INSERT INTO pratiche.template_flussi_prerequisiti
         (template_flusso_id, prerequisito_id, esito_richiesto)
  SELECT nt.id, np.id, p.esito_richiesto
    FROM pratiche.template_flussi_prerequisiti p
    JOIN pratiche.template_flussi ot
         ON ot.id = p.template_flusso_id AND ot.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi op
         ON op.id = p.prerequisito_id AND op.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nt
         ON nt.definizione_id = v_new_id AND nt.codice = ot.codice
    JOIN pratiche.template_flussi np
         ON np.definizione_id = v_new_id AND np.codice = op.codice;

  -- 6) Formule tempo (remap DOPPIO da/a; tipo_prestazione_id invariato).
  INSERT INTO pratiche.formule_tempo
         (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
          giorni_esecuzione, giorni_warning, giorni_critico, attivo, descrizione, meta)
  SELECT ft.tipo_prestazione_id, nda.id, na.id,
         ft.giorni_esecuzione, ft.giorni_warning, ft.giorni_critico,
         ft.attivo, ft.descrizione, ft.meta
    FROM pratiche.formule_tempo ft
    JOIN pratiche.template_flussi oda
         ON oda.id = ft.template_flusso_da_id AND oda.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi oa
         ON oa.id = ft.template_flusso_a_id AND oa.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nda
         ON nda.definizione_id = v_new_id AND nda.codice = oda.codice
    JOIN pratiche.template_flussi na
         ON na.definizione_id = v_new_id AND na.codice = oa.codice;

  -- 7) Regole generazione (remap ORIGINE per codice; dest lasciata
  --    invariata: fn_genera_pratica_da_flusso la rimappa per codice a
  --    runtime nella definizione pinnata della figlia, D2-8).
  INSERT INTO pratiche.regole_generazione
         (template_flusso_origine_id, tipo_prestazione_dest_id,
          template_flusso_dest_id, esito_richiesto, auto, attivo, descrizione, meta)
  SELECT no.id, rg.tipo_prestazione_dest_id, rg.template_flusso_dest_id,
         rg.esito_richiesto, rg.auto, rg.attivo, rg.descrizione, rg.meta
    FROM pratiche.regole_generazione rg
    JOIN pratiche.template_flussi oo
         ON oo.id = rg.template_flusso_origine_id AND oo.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi no
         ON no.definizione_id = v_new_id AND no.codice = oo.codice;

  -- 8) Binding avanzamento su proiezione (GUIDA D4/G2; remap per codice).
  INSERT INTO pratiche.template_flussi_avanzamento_proiezione
         (template_flusso_id, esito_richiesto, attivo, meta)
  SELECT nt.id, b.esito_richiesto, b.attivo, b.meta
    FROM pratiche.template_flussi_avanzamento_proiezione b
    JOIN pratiche.template_flussi ot
         ON ot.id = b.template_flusso_id AND ot.definizione_id = p_sorgente_id
    JOIN pratiche.template_flussi nt
         ON nt.definizione_id = v_new_id AND nt.codice = ot.codice;

  RETURN v_new_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_copia_definizione(p_sorgente_id integer, p_emittente_dest bigint, p_provenance boolean)
IS 'Motore di copia di un''edizione di workflow: header + template (incl. attende_sorgente_tipo_id, GUIDA D4/G1) + 7 figli (canali, handler_eventi, competenze, prerequisiti, formule_tempo, regole_generazione, avanzamento_proiezione) in una nuova edizione BOZZA, con remap dei template per codice. Unico punto del set di copia (C6). p_provenance=true valorizza preset_origine_id/versione_origine (fork). Usato da fn_fork_definizione e fn_nuova_versione_definizione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
