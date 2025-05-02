
UPDATE config.province
SET extra_country = jsonb_strip_nulls(jsonb_build_object(
  'stato_utilizzo', 'ITA',
  'codice_istat', codice_istat,
  'provincia_accisa_id', provincia_accisa_id
))
WHERE codice_istat IS NOT NULL OR provincia_accisa_id IS NOT NULL;
