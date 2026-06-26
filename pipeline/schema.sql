-- ProvBench — Supabase/Postgres schema. Run by s8_load_supabase.py (drop + recreate).

drop table if exists source_records cascade;
drop table if exists consensus cascade;
drop table if exists compounds cascade;
drop table if exists qc_metrics cascade;
drop table if exists dataset_meta cascade;
drop table if exists targets cascade;

create table targets (
  uniprot    text primary key,
  chembl_id  text,
  pref_name  text,
  organism   text
);

create table compounds (
  inchikey   text primary key,
  std_smiles text,
  n_records  int,
  n_sources  int
);

-- Every original measurement, link-preserved (this is the heart of the project).
create table source_records (
  id                  bigserial primary key,
  source_record_id    text,
  source              text,          -- upstream database (Scientific Literature, PubChem BioAssays, ...)
  access_path         text,          -- how we fetched it (ChEMBL API / BindingDB REST)
  source_compound_id  text,
  inchikey            text,
  target_uniprot      text,
  std_smiles          text,
  original_smiles     text,
  standard_type       text,
  standard_relation   text,
  standard_value      double precision,
  standard_units      text,
  value_nm            double precision,
  p_activity          double precision,
  pchembl_value       double precision,
  is_exact            boolean,
  assay_id            text,
  assay_description   text,
  confidence_score    int,
  bao_format          text,
  document_id         text,
  source_url          text,
  raw_validity_comment text,
  validity_flag       text,          -- our flag (null = OK); annotate-don't-delete
  flag_reason         text
);

-- The harmonized answer per (compound, target).
create table consensus (
  id                   bigserial primary key,
  inchikey             text,
  target_uniprot       text,
  consensus_p_activity double precision,
  consensus_value_nm   double precision,
  n_records_used       int,
  n_sources            int,
  spread_log           double precision,
  p_min                double precision,
  p_max                double precision,
  p_std                double precision,
  agreement            text
);

-- Landrum-Riniker before/after QC.
create table qc_metrics (
  id             bigserial primary key,
  curation_level text,
  n_pairs        int,
  kendall_tau    double precision,
  frac_gt_03     double precision,
  frac_gt_10     double precision,
  mae_log        double precision
);

-- The catalog "nutrition label".
create table dataset_meta (
  id                  bigserial primary key,
  name                text,
  version             text,
  created_at          text,
  n_compounds         int,
  n_consensus_records int,
  n_source_records    int,
  sources             jsonb,
  license             text,
  sha256_consensus    text,
  hf_url              text,
  croissant_url       text,
  qc                  jsonb
);

create index idx_sr_inchikey  on source_records(inchikey);
create index idx_sr_target    on source_records(target_uniprot);
create index idx_sr_flag      on source_records(validity_flag);
create index idx_sr_source    on source_records(source);
create index idx_cons_inchikey on consensus(inchikey);
create index idx_cons_agree    on consensus(agreement);
