
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
DECLARE
  v_count INTEGER;
BEGIN
-- ====================================================================
-- Funzione di validazione dei contatti sui soggetti (livello di commit)
-- Verifica che il soggetto abbia almeno:
--   • un contatto di default (is_default = TRUE), oppure
--   • un contatto con almeno un canale non nullo
-- ====================================================================
  SELECT COUNT(*) INTO v_count
    FROM anagrafiche.contatti c
   WHERE c.soggetto_id = NEW.id
     AND (
       c.is_default
       OR c.email IS NOT NULL
       OR c.telefono IS NOT NULL
       OR c.cellulare IS NOT NULL
       OR c.pec IS NOT NULL
     );

  IF v_count = 0 THEN
    RAISE EXCEPTION '%', script.fn_get_messaggio('E_SOGGETTO_NO_CONTATTI');
  END IF;

  RETURN NEW;
END;
$BODY$;

ALTER FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()
    OWNER TO postgres;

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ins_upd_check_soggetto_contatti()
    IS 'Constraint trigger che verifica la presenza di almeno un contatto default o con canale valorizzato per ogni soggetto.';
