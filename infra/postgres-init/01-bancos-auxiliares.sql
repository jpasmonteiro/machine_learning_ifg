-- Bancos auxiliares criados na primeira inicializacao do container Postgres.
--
--   suporte_dw   -> warehouse analitico (criado pelo POSTGRES_DB do compose)
--   metabase_app -> metadados do proprio Metabase (usuarios, cards, dashboards).
--                   Sem isto o Metabase usa um H2 dentro do container, que se
--                   perde a cada `docker compose down`. Com o banco aqui, o
--                   painel sobrevive a reinicios.
--   airflow      -> metadata DB do Airflow (DAG runs, task instances, logs).
CREATE DATABASE metabase_app OWNER suporte;
CREATE DATABASE airflow OWNER suporte;
